import os, json, traceback, secrets, re
from datetime import timedelta
from flask import Flask, request, jsonify, send_from_directory, render_template_string, session
from dotenv import load_dotenv
import bcrypt
from openai import OpenAI
from mailer import send_mail, send_password_reset_email, send_verification_email
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from auth_utils import (
    validate_reset_token,
    set_user_password,
    validate_verification_token,
    mark_user_verified,
    consume_token,
)
from sqlalchemy import text

# --- Load config ---
load_dotenv()
from db import (
    init_db,
    SessionLocal,
    get_session,
    find_user_by_email,
    create_user,
    issue_token,
    User,
)
init_db()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o-mini")          # safe default
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", "5055"))              # local dev port only
ADMIN_SETUP_TOKEN = os.getenv("ADMIN_SETUP_TOKEN")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Put it in .env or export it before running.")

# --- Init app/client ---
client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__, static_folder="web", static_url_path="")
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")
app.permanent_session_lifetime = timedelta(days=30)

limiter = Limiter(get_remote_address, app=app, default_limits=[])


BCRYPT_PREFIX_RE = re.compile(r"^\$2[aby]?\$")


def is_bcrypt_hash(h: str) -> bool:
    return bool(h) and bool(BCRYPT_PREFIX_RE.match(h or ""))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """True if hashed is valid bcrypt and matches; otherwise False (no exceptions)."""
    if not is_bcrypt_hash(hashed):
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def require_login():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


def issue_csrf():
    token = secrets.token_urlsafe(16)
    session["csrf_token"] = token
    return token


def check_csrf(req):
    token = session.get("csrf_token")
    header = req.headers.get("X-CSRF-Token") or ""
    return token and header and secrets.compare_digest(token, header)

# --- Serve homepage (same-origin) ---
@app.get("/")
def home():
    return send_from_directory("web", "index.html")

@app.get("/health")
def health():
    ok = True
    details = {"model": MODEL, "fallback_model": FALLBACK_MODEL}
    try:
        spath = os.path.join(os.path.dirname(__file__), "system_prompt.md")
        details["system_prompt_exists"] = os.path.exists(spath)
    except Exception as e:
        ok = False
        details["error"] = str(e)
    return jsonify({"ok": ok, "details": details})


# --- Basic auth endpoints ---

@app.post("/signup")
def signup():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password or len(password) < 8:
        return jsonify({"ok": False, "error": "Invalid email or password"}), 400

    sess = get_session()
    try:
        user = find_user_by_email(sess, email)
        if user and user.is_verified:
            return jsonify({"ok": False, "error": "User already exists"}), 400

        if not user:
            user = create_user(sess, email=email)

        user.password_hash = hash_password(password)
        sess.add(user)
        sess.commit()

        token = secrets.token_urlsafe(32)
        issue_token(sess, user, token, "verify", ttl_minutes=60)
        sess.commit()

        try:
            send_verification_email(email, token)
        except Exception as e:
            print(f"Email send failed: {e}")

        return (
            jsonify({"ok": True, "message": "Account created. Please verify via email."}),
            201,
        )
    finally:
        sess.close()


@app.post("/login")
@limiter.limit("5 per minute")
def login():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = (data.get("password") or "")
        if not email or not password:
            return jsonify({"ok": False, "error": "missing email or password"}), 400

        sess = get_session()
        try:
            user = sess.query(User).filter(User.email == email).first()
            # constant-time dummy to equalize timing a bit
            _ = bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt()))

            if not user or not user.password_hash or not verify_password(password, user.password_hash):
                # If the stored hash is legacy (not bcrypt), force a reset rather than 500
                if user and user.password_hash and not is_bcrypt_hash(user.password_hash):
                    return jsonify({"ok": False, "error": "password needs reset"}), 401
                return jsonify({"ok": False, "error": "invalid credentials"}), 401

            if not user.is_verified:
                return jsonify({"ok": False, "error": "user not verified"}), 403

            # success: session + CSRF cookie
            session.permanent = True
            session["user_id"] = user.id
            tok = issue_csrf()
            resp = jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "phase": user.phase}})
            resp.set_cookie("csrf_token", tok, httponly=False, samesite="Lax", secure=True)
            return resp, 200
        finally:
            sess.close()
    except Exception as e:
        app.logger.error("LOGIN exception: %s", e)
        app.logger.error("Trace:\n%s", traceback.format_exc())
        return jsonify({"ok": False, "error": "internal error"}), 500


@app.post("/logout")
def logout():
    session.clear()
    resp = jsonify({"ok": True})
    resp.set_cookie("csrf_token", "", expires=0, samesite="Lax", secure=True)
    return resp


@limiter.limit("2 per minute")
@app.post("/admin/set_password")
def admin_set_password():
    # Strongly guarded: require header token
    token = request.headers.get("X-Setup-Token", "")
    if not ADMIN_SETUP_TOKEN or token != ADMIN_SETUP_TOKEN:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    new_password = (data.get("new_password") or "")

    if not email or not new_password or len(new_password) < 8:
        return jsonify({"ok": False, "error": "invalid input"}), 400

    sess = get_session()
    try:
        user = sess.query(User).filter(User.email == email).first()
        if not user:
            return jsonify({"ok": False, "error": "not found"}), 404
        user.password_hash = hash_password(new_password)
        sess.add(user)
        sess.commit()
        return jsonify({"ok": True}), 200
    finally:
        sess.close()

# --- User phase helpers ---

@app.get("/me")
def me():
    uid = require_login()
    if not uid:
        return jsonify({"ok": False, "error": "not logged in"}), 401
    sess = get_session()
    try:
        user = sess.get(User, uid)
        if not user:
            return jsonify({"ok": False, "error": "not found"}), 404
        phase = user.phase if user.phase in ALLOWED_PHASES else "stabilize"
        return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "phase": phase}})
    finally:
        sess.close()


ALLOWED_PHASES = {
    "stabilize",
    "reframe",
    "position",
    "explore",
    "apply",
    "secure",
    "transition",
}


@app.post("/phase")
@limiter.limit("10 per minute")
def set_phase():
    uid = require_login()
    if not uid:
        return jsonify({"ok": False, "error": "not logged in"}), 401
    if not check_csrf(request):
        return jsonify({"ok": False, "error": "invalid csrf"}), 403
    data = request.get_json(silent=True) or {}
    phase = (data.get("phase") or "").strip().lower()

    if phase not in ALLOWED_PHASES:
        return jsonify({"ok": False, "error": "invalid phase"}), 400

    sess = get_session()
    try:
        user = sess.get(User, uid)
        if not user:
            return jsonify({"ok": False, "error": "not found"}), 404
        user.phase = phase
        sess.add(user)
        sess.commit()
        return jsonify({"ok": True, "user": {"id": user.id, "email": user.email, "phase": user.phase}})
    finally:
        sess.close()

# Forgot password
@app.post("/forgot_password")
def forgot_password():
    """
    Accepts JSON: { "email": "user@example.com" }
    Always returns a generic success message without revealing whether the user exists.
    If the user exists, creates a reset token (purpose='reset', default TTL 60m) and emails the link.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    # Always return generic success to avoid user enumeration
    generic_ok = jsonify({"ok": True, "message": "If the account exists, a reset email has been sent."})

    if not email:
        # Still return generic to avoid enumeration
        return generic_ok, 200

    sess = get_session()
    try:
        user = find_user_by_email(sess, email)
        if user:
            token = secrets.token_urlsafe(32)
            # 60 minutes default TTL; adjust as desired
            issue_token(sess, user, token=token, purpose="reset", ttl_minutes=30)
            sess.commit()
            try:
                send_password_reset_email(email, token)
            except Exception as e:
                # Do not leak details to the client
                print(f"[forgot_password] email send failed for {email}: {e}")
        # Always return generic success
        return generic_ok, 200
    finally:
        sess.close()


# --- Load system prompt (fallback if missing/empty) ---
SP_PATH = os.path.join(os.path.dirname(__file__), "system_prompt.md")
DEFAULT_SYSTEM = (
    "You are JTBD Journey Coach. You coach calmly and concretely through phases: "
    "stabilize, reframe, position, explore, apply, secure, transition. "
    "Be concise, practical, and encouraging. Prefer short lists, checklists, and micro-steps."
)
if os.path.exists(SP_PATH):
    with open(SP_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = (f.read() or "").strip() or DEFAULT_SYSTEM
else:
    SYSTEM_PROMPT = DEFAULT_SYSTEM

def compose_prompt(kind, user_state, note):
    header = (
        "You are JTBD Journey Coach.\n"
        "User state JSON:\n" + json.dumps(user_state or {}, ensure_ascii=False, indent=2) + "\n\n"
    )
    task_map = {
        "plan": "Please produce a **Weekly Plan** using your default output structure.",
        "standup": "Please output a **Daily Stand-up** using the template.",
        "gate": "Run a **Phase Gate Review** for the current phase.",
        "triage": "Run **Setback Triage**. Keep it concise and directive."
    }
    task = task_map.get(kind, "Provide guidance using the default structure.")
    if note:
        task += f"\nContext note from user: {note}"
    return header + task

def respond(kind, user_state, note):
    prompt = compose_prompt(kind, user_state, note)
    comp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return comp.choices[0].message.content

def respond_chat(user_state, message, context_md="", context_kind=""):
    system = (
        SYSTEM_PROMPT +
        "\nIf context_md is provided, treat it as the user's current panel. "
        "When they say 'bullet 1' or 'the first item', identify the first actionable bullet "
        "from context_md and help them complete it step-by-step with concrete instructions."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "State JSON:\n" + json.dumps(user_state or {}, ensure_ascii=False)}
    ]
    if context_md:
        messages.append({
            "role": "user",
            "content": f"Context ({context_kind or 'panel'}; markdown the user is seeing):\n{context_md}"
        })
    messages.append({"role": "user", "content": message})

    comp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2
    )
    return comp.choices[0].message.content

def get_state_from_request(req):
    data = req.get_json(silent=True) or {}
    user_state = data.get("user_state") or {}
    note = data.get("note", "")
    return user_state, note

# --- Endpoints ---
@app.post("/reset-password")
@limiter.limit("3 per minute")
def reset_password():
    """Legacy endpoint to initiate a password reset email."""
    try:
        data = request.get_json(force=True)
        email = (data.get("email") or "").strip().lower()
        if not email:
            return jsonify({"error": "Email required"}), 400

        generic_resp = jsonify({"sent": True, "message": "Reset email sent"})
        sess = get_session()
        try:
            user = find_user_by_email(sess, email)
            if not user:
                return generic_resp, 200

            token = secrets.token_urlsafe(32)
            issue_token(sess, user, token, purpose="reset", ttl_minutes=30)
            sess.commit()
            send_password_reset_email(email, token)
            return generic_resp, 200
        finally:
            sess.close()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
@app.post("/plan")
def plan():
    try:
        user_state, note = get_state_from_request(request)
        text = respond("plan", user_state, note)
        return jsonify({"reply": text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/standup")
def standup():
    try:
        user_state, note = get_state_from_request(request)
        text = respond("standup", user_state, note)
        return jsonify({"reply": text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/gate")
def gate():
    try:
        user_state, note = get_state_from_request(request)
        text = respond("gate", user_state, note)
        return jsonify({"reply": text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/triage")
def triage():
    try:
        user_state, note = get_state_from_request(request)
        text = respond("triage", user_state, note)
        return jsonify({"reply": text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.post("/chat")
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_state = data.get("user_state") or {}
        message = (data.get("message") or "").strip()
        context_md = (data.get("context_md") or "").strip()
        context_kind = (data.get("context_kind") or "").strip()
        if not message:
            return jsonify({"reply": "Please type a message."})
        text = respond_chat(user_state, message, context_md, context_kind)
        return jsonify({"reply": text})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

RESET_FORM_HTML = """
<html>
  <head><title>Reset your password</title></head>
  <body style="font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width:640px; margin:40px auto;">
    <h1>Reset your password</h1>
    {% if error %}<p style="color:#b00020">{{ error }}</p>{% endif %}
    {% if not user %}
      <p>Invalid or expired reset link.</p>
    {% else %}
      <form method="post" action="/reset">
        <input type="hidden" name="token" value="{{ token }}">
        <div style="margin:8px 0">
          <label>New password</label><br>
          <input type="password" name="password" minlength="8" required style="width:100%;padding:8px">
        </div>
        <div style="margin:8px 0">
          <label>Confirm password</label><br>
          <input type="password" name="confirm" minlength="8" required style="width:100%;padding:8px">
        </div>
        <button type="submit" style="padding:10px 16px;border-radius:8px;">Update password</button>
      </form>
    {% endif %}
  </body>
</html>
"""

RESET_SUCCESS_HTML = """
<html>
  <head><title>Password updated</title></head>
  <body style="font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width:640px; margin:40px auto;">
    <h1>Password updated</h1>
    <p>Your password has been changed successfully. You can now sign in.</p>
  </body>
</html>
"""

@app.get("/reset")
def reset_view():
    token = request.args.get("token", "")
    user = validate_reset_token(token)
    return render_template_string(RESET_FORM_HTML, token=token, user=user, error=None)


@app.post("/reset")
def reset_submit():
    token = request.form.get("token", "")
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    user = validate_reset_token(token)

    if (
        not user
        or not password
        or len(password) < 8
        or password != confirm
    ):
        return render_template_string(RESET_SUCCESS_HTML), 200

    phash = hash_password(password)
    set_user_password(user["user_id"], phash)
    consume_token(token, "reset")
    return render_template_string(RESET_SUCCESS_HTML), 200


VERIFY_ERROR_HTML = """
<html>
  <head><title>Verification error</title></head>
  <body style="font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width:640px; margin:40px auto;">
    <h1>Verification error</h1>
    <p>{{ message }}</p>
  </body>
</html>
"""

VERIFY_SUCCESS_HTML = """
<html>
  <head><title>Email verified</title></head>
  <body style="font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width:640px; margin:40px auto;">
    <h1>Email verified</h1>
    <p>Thanks! Your email has been verified. You can now sign in.</p>
  </body>
</html>
"""


@app.get("/verify")
@limiter.limit("3 per minute")
def verify_view():
    token = request.args.get("token", "").strip()
    user = validate_verification_token(token)
    if not user:
        return render_template_string(VERIFY_ERROR_HTML, message="Invalid or expired verification link."), 400
    try:
        mark_user_verified(user["user_id"])
        consume_token(token, "verify")
    except Exception as e:
        # Log and show a generic error
        import logging
        logging.exception("mark_user_verified failed")
        return render_template_string(VERIFY_ERROR_HTML, message="Could not complete verification. Please try again."), 500
    return render_template_string(VERIFY_SUCCESS_HTML), 200


@app.get("/_dev_issue_token")
def _dev_issue_token():
    """
    DEV-ONLY: Creates a token row in the database for a user and (optionally) emails it.
    Query params:
      - email: required (user email)
      - purpose: required ('reset' or 'verify')
      - ttl: optional minutes (default 60)
      - send: optional 'true' to also send email
      - token: optional; if omitted, a secure random token is generated
    Disabled when ENV=production.
    """
    if os.getenv("ENV", "development").lower() == "production":
        return "Not available in production", 404

    email = (request.args.get("email") or "").strip().lower()
    purpose = (request.args.get("purpose") or "").strip().lower()
    ttl_str = request.args.get("ttl", "60").strip()
    send_flag = (request.args.get("send", "false").strip().lower() == "true")
    token = (request.args.get("token") or "").strip() or secrets.token_urlsafe(32)

    if not email or purpose not in ("reset", "verify"):
        return jsonify({"error": "missing or invalid params: email, purpose in {reset,verify}"}), 400

    try:
        ttl = int(ttl_str)
    except ValueError:
        return jsonify({"error": "ttl must be an integer (minutes)"}), 400

    sess = get_session()
    try:
        user = find_user_by_email(sess, email)
        if not user:
            user = create_user(sess, email=email)  # password_hash=None by default
            sess.commit()

        t = issue_token(sess, user, token=token, purpose=purpose, ttl_minutes=ttl)
        sess.commit()

        # Build link the same way mailer helpers do
        base_url = os.getenv("APP_BASE_URL", "https://nextchapter.onrender.com").rstrip("/")
        path = "/reset" if purpose == "reset" else "/verify"
        link = f"{base_url}{path}?token={token}"

        if send_flag:
            try:
                if purpose == "reset":
                    send_password_reset_email(email, token)
                else:
                    send_verification_email(email, token)
            except Exception as e:
                # don't fail issuance just because email failed
                print(f"[DEV] email send failed: {e}")

        return jsonify({
            "ok": True,
            "email": email,
            "purpose": purpose,
            "token": token,
            "link": link,
            "ttl_minutes": ttl
        }), 200
    finally:
        sess.close()


@app.get("/_mail_test")
def _mail_test():
    """Send a test email to verify SMTP is working."""
    to = request.args.get("to", os.environ.get("EMAIL_FROM"))
    try:
        send_mail(to, "SMTP test", "If you read this, SMTP works.")
        return "OK", 200
    except Exception as e:
        return str(e), 500


@app.get("/_mail_reset_test")
def _mail_reset_test():
    """
    Dev-only helper: sends a password reset email to ?to=<email>
    with an optional ?token=<token>. Enabled in non-production only.
    """
    if os.getenv("ENV", "development").lower() == "production":
        return "Not available in production", 404

    to = request.args.get("to")
    if not to:
        return "Missing ?to=<email>", 400

    token = request.args.get("token") or secrets.token_urlsafe(32)

    sess = get_session()
    try:
        user = find_user_by_email(sess, to)
        if not user:
            user = create_user(sess, email=to)
            sess.commit()
        issue_token(sess, user, token, purpose="reset", ttl_minutes=30)
        sess.commit()
        send_password_reset_email(to, token)
        return "OK", 200
    except Exception as e:
        sess.rollback()
        return str(e), 500
    finally:
        sess.close()


@app.get("/_mail_verify_test")
def _mail_verify_test():
    """
    Dev-only helper: sends a verification email to ?to=<email>
    with a dummy or provided ?token=<token>. Disabled in production.
    """
    if os.getenv("ENV", "development").lower() == "production":
        return "Not available in production", 404

    to = request.args.get("to")
    token = request.args.get("token") or secrets.token_urlsafe(32)
    if not to:
        return "Missing ?to=<email>", 400
    try:
        send_verification_email(to, token)
        return "OK", 200
    except Exception as e:
        return str(e), 500


@app.after_request
def security_headers(resp):
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
    # Start with a relaxed CSP, tighten later as needed
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'"
    )
    resp.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    return resp

if __name__ == "__main__":
    print(f"Starting JTBD Coach on http://localhost:{PORT} (model={MODEL}, fallback={FALLBACK_MODEL})")
    app.run(host="0.0.0.0", port=PORT, debug=True)
