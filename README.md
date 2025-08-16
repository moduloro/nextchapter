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
