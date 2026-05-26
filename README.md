# Multi-Tenant Telegram Bot Backend (Hackathon)

This repository demonstrates a lightweight, multi-tenant Telegram bot backend intended for fast hackathon demos. A single FastAPI instance accepts webhooks for multiple bots and feeds updates into a shared `aiogram` router so the same handlers can serve many bot identities.

Quick Links
- Agent guidance: `AGENTS.md`
- Architecture notes: `product-design/architecture.md`
- Environment template: `.env.example`

Quick Start

1. Create and activate a virtual environment

```bash
python -m venv venv
# PowerShell / CMD (Windows)
.\venv\Scripts\Activate.ps1
# Git Bash
source venv/Scripts/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

Run (development)

```bash
python -m uvicorn main:app --reload
```

Configuration
- Copy `.env.example` → `.env` and set `BOT_TOKENS` (comma-separated tokens) and `BASE_URL` (public HTTPS URL from ngrok or your deployment).

Demo with ngrok
1. Start your app (`uvicorn main:app --reload`).
2. In another terminal run:

```bash
ngrok http 8000
```

3. Copy the `https://...` forwarding URL and paste it into `BASE_URL` in your `.env`, then restart the app.

Testing

```bash
python -m pytest -v
```

Notes
- Keep bot tokens secret — do not commit `.env` to source control.
- Use `python -m uvicorn ...` on Windows to avoid shell path issues.

If you want, I can add a short `DEMO.md` with exact checklist items and presentation notes.
