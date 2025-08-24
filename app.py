import os, json, traceback
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI
from mailer import send_mail, send_password_reset_email, send_verification_email

# --- Load config ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o-mini")          # safe default
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
PORT = int(os.getenv("PORT", "5055"))              # local dev port only

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Put it in .env or export it before running.")

# --- Init app/client ---
client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__, static_folder="web", static_url_path="")

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
def reset_password():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        if not email:
            return jsonify({"error": "Email required"}), 400
        token = data.get("token", "demo-token")
        try:
            send_password_reset_email(email, token)
            sent = True
        except Exception:
            traceback.print_exc()
            sent = False
        if sent:
            return jsonify({"sent": True, "message": "Reset email sent"})
        else:
            return jsonify({"sent": False, "error": "Email service not configured"}), 500
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
    with a dummy or provided ?token=<token>. Enabled in non-production only.
    """
    if os.getenv("ENV", "development").lower() == "production":
        return "Not available in production", 404

    to = request.args.get("to")
    token = request.args.get("token", "demo-token")
    if not to:
        return "Missing ?to=<email>", 400
    try:
        send_password_reset_email(to, token)
        return "OK", 200
    except Exception as e:
        return str(e), 500


@app.get("/_mail_verify_test")
def _mail_verify_test():
    """
    Dev-only helper: sends a verification email to ?to=<email>
    with a dummy or provided ?token=<token>. Disabled in production.
    """
    if os.getenv("ENV", "development").lower() == "production":
        return "Not available in production", 404

    to = request.args.get("to")
    token = request.args.get("token", "demo-verify-token")
    if not to:
        return "Missing ?to=<email>", 400
    try:
        send_verification_email(to, token)
        return "OK", 200
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    print(f"Starting JTBD Coach on http://localhost:{PORT} (model={MODEL}, fallback={FALLBACK_MODEL})")
    app.run(host="0.0.0.0", port=PORT, debug=True)
