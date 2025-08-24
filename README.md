# JTBD Journey Coach — Full Starter (App + Site)

This package serves your homepage from Flask **and** exposes API endpoints the page calls (Weekly Plan, Daily Stand‑up, Phase Gate Review, Setback Triage).

## What’s inside
- `app.py` — Flask server (serves `web/index.html` + `/plan`, `/standup`, `/gate`, `/triage` endpoints)
- `web/index.html` — your latest homepage (with Journey Coach panel, `API_BASE = "/"` for same‑origin)
- `system_prompt.md` — agent instructions
- `journey_playbook.md` — phase playbooks
- `.env.example` — environment variables
- `sample_state.json` — example request body
- `requirements.txt` — Python deps

## Run on macOS
```bash
cd jtbd_coach_full_v4
python3 -m venv .venv
source .venv/bin/activate     # if fish: source .venv/bin/activate.fish
pip install -r requirements.txt
cp .env.example .env
open -e .env    # paste your real OPENAI_API_KEY
python app.py
# Open http://localhost:5055/
```

## Test the API without the page
```bash
curl -X POST http://localhost:5055/plan   -H "Content-Type: application/json"   -d @sample_state.json
```

## Serve HTML from another origin?
- Set `API_BASE = "http://localhost:5055/"` in `web/index.html`.
- Enable CORS in `app.py` (uncomment the lines near the bottom and restrict origins).

## Password reset email
- Set `APP_BASE_URL` (e.g., `https://nextchapter.onrender.com`).
- Test locally: `/_mail_reset_test?to=you@domain.com&token=demo`.
- On Render, configure `SMTP_*`, `EMAIL_*`, and optionally `APP_BASE_URL`.

## Signup verification email
- Set `APP_BASE_URL` (e.g., `https://nextchapter.onrender.com`).
- Test locally: `/_mail_verify_test?to=you@domain.com&token=demo`.
- In production, configure `SMTP_*`, `EMAIL_*`, and `APP_BASE_URL`.

## Dev token issuer
- `/_dev_issue_token?email=<e>&purpose=reset|verify&ttl=60&send=true`
- Only available when `ENV != production`.

## Email verification flow
- Verification link format: GET `/verify?token=...`
- In `ENV=development`, any non-empty token is accepted by the stub
- Real implementations should replace `validate_verification_token()` and `mark_user_verified()` with DB-backed logic

## Database
- Set `DATABASE_URL` in Render to your Postgres connection string
- Tables are auto-created on startup (no migrations yet)
- We’ll wire real token + user operations in subsequent steps

## Signup and login
- `POST /signup {email, password}` → creates user and emails verify link.
- `POST /login {email, password}` → logs in if verified.
- Both return JSON. In production you’d add sessions/JWT; here we return raw JSON for simplicity.

## Forgot password
- `POST /forgot_password {email}` → returns generic success.
- If the user exists, a reset token is created and an email is sent.
- Reset link goes to `/reset?token=...`.

## User phase
- Default phase = `explore`.
- `POST /phase { email, phase }` → update phase. Allowed phases: explore, apply, interview, offer, decide, onboard.
- `GET /me?email=...` → returns `{ id, email, phase }`.
- `POST /login` now includes the user's phase in the response.
- Identity uses email for now; sessions/JWT will replace this later.
