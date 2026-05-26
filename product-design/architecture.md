# Architecture Overview

This document serves as a critical, living template designed to equip agents with a rapid and comprehensive understanding of the codebase's architecture, enabling efficient navigation and effective contribution from day one. Update this document as the codebase evolves.

## 1. Project Structure
This repository is a focused backend for a multi-tenant Telegram bot system used for hackathons and demos. It intentionally keeps a minimal, easy-to-understand layout so contributors can iterate quickly.

[Project Root]/
├── main.py                 # FastAPI app: webhook endpoint, lifecycle hooks, and dispatcher wiring
├── router.py               # Shared `aiogram` router with bot handlers (universal handlers)
├── test_main.py            # Async pytest tests for webhook routing and lifespan startup
├── AGENTS.md               # Agent instructions and run/debug guidance for AI assistants
├── .env.example            # Environment variable template (BOT_TOKENS, BASE_URL)
├── product-design/         # Product & UX docs (this folder)
├── ai-agents/              # AI prompt/context templates
├── knowledge-base/         # Notes, lessons, retrospects
└── visual-assets/          # Flowcharts, wireframes, placeholders

Notes:
- There is no frontend code in this repository; the project is a backend-only service that receives Telegram webhooks and dispatches them to shared handlers.

## 2. High-Level System Diagram
The service is intentionally simple: a single FastAPI instance accepts webhooks for multiple bots and feeds them into a shared aiogram dispatcher. Dataflow (text-based):

[User] -> [Telegram] -> POST /telegram/{bot_token} -> [FastAPI route] -> [aiogram feed_update] -> [Shared router handlers]

This pattern keeps runtime memory small and code reuse high for hackathon demos.

## 3. Core Components

### 3.1. Backend (Single Service)
Name: Multi-Tenant Webhook Router
Description: FastAPI application that registers multiple Telegram bot webhooks on startup and exposes a single dynamic endpoint `POST /telegram/{bot_token}` which validates tokens, creates a short-lived `Bot` context, and calls `dp.feed_update(bot, update)` to process incoming updates via `aiogram`.
Technologies: Python 3.11+, FastAPI, aiogram 3, Uvicorn (ASGI), python-dotenv (optional for `.env`).
Deployment: Local dev (uvicorn) for hackathon; can be deployed to cloud (Cloud Run, Heroku, or a VM) for stable public endpoints.

### 3.2. Shared Router
Name: `router.py`
Description: Contains the shared `aiogram.Router` instance and message/command handlers that run for every bot configured. Handlers are written once and adapt to `message.bot` identity at runtime.
Technologies: aiogram Router, handler filters (e.g., `CommandStart`, `F.text`).

### 3.3. Test Harness
Name: `test_main.py`
Description: Async tests using `httpx.AsyncClient` and `ASGITransport` to exercise the FastAPI route. Mocks `main.Bot` and `dp.feed_update` to validate routing and lifecycle behavior.
Technologies: pytest, pytest-asyncio, httpx, unittest.mock.

## 4. Data Stores
- Currently no persistent datastore required for the hackathon demo. All state is ephemeral and handled in-memory via `aiogram` runtime.

Future options:
- Redis for short-lived session/caching or aiogram storage backends.
- PostgreSQL or similar for long-term user data or per-bot configuration.

## 5. External Integrations / APIs
- Telegram Bot API — receives user messages and sends updates via webhook or getUpdates.
- ngrok (local dev) — exposes local `http://localhost:8000` to a public HTTPS URL for webhook registration during demos.

## 6. Deployment & Infrastructure
Cloud Provider: Any provider supporting Python ASGI apps (GCP Cloud Run, Heroku, AWS ECS/Fargate, or a simple VM).

Run (development):
```bash
# from repo root
python -m uvicorn main:app --reload
```

CI/CD: None configured in repository; add `.github/workflows` for automated tests and deployment when needed.

## 7. Security Considerations
- Telegram Bot Tokens must be kept secret — keep them out of source control and use `.env` or secret manager.
- Webhooks must be registered to a public HTTPS endpoint; never expose plain `http://localhost` to Telegram.
- Validate `bot_token` path parameter against configured tokens to avoid unauthorized updates (the project already rejects unknown tokens with 403).

## 8. Development & Testing Environment
Local setup (quick):
```bash
python -m venv venv
.\\venv\\Scripts\\activate   # PowerShell/Command Prompt on Windows
python -m pip install -r requirements.txt  # or install fastapi, uvicorn, aiogram
python -m uvicorn main:app --reload
```

Tests:
```bash
python -m pytest -v
```

## 9. Future Considerations / Roadmap
- If load increases, replace synchronous webhook processing with a lightweight queue (Redis / RQ / Celery) and worker pool to process `dp.feed_update` calls.
- Add persistent storage for per-bot configuration and conversation history.

## 10. Project Identification
Project Name: Multi-Tenant Telegram Bot Backend (Hackathon)
Repository URL: (local workspace)
Primary Contact: Repository owner / maintainer
Date of Last Update: 2026-05-26

## 11. Glossary / Acronyms
- `dp`: Dispatcher (aiogram) — central dispatcher that routes updates into handlers.
- `BOT_TOKENS`: Comma-separated list of Telegram bot tokens used to validate incoming webhooks.

