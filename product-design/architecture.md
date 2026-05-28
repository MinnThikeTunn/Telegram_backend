# Architecture Overview

This document serves as a critical, living template designed to equip agents with a rapid and comprehensive understanding of the codebase's architecture, enabling efficient navigation and effective contribution from day one. Update this document as the codebase evolves.

## 1. Project Structure
This repository is a focused backend for a multi-tenant, multi-platform bot system (currently Telegram and Viber) used for hackathons and demos. It intentionally keeps a minimal, easy-to-understand layout so contributors can iterate quickly.

[Project Root]/
├── main.py                 # FastAPI app: webhook endpoints (Telegram, Viber) and dispatcher wiring
├── telegram_router.py      # Telegram Controller: aiogram router handling Telegram specific payloads
├── core_logic.py           # Core Service: Platform-agnostic business logic
├── bot_store.py            # State Registry: Redux-style centralized store for bot specific rules/personas
├── persona_factory.py      # Persona Compiler: builds prompt layers from category + axis config
├── personas_config.json    # Persona source of truth: bot profiles, categories, axes, dynamic state
├── ai/                     # AI & Analytics module
│   ├── ai_service.py       # Integration with Google Generative AI (Gemini 2.5 Flash)
│   ├── user_store.py       # User Analytics Store: Customer profile and preference tracking
│   └── sales_brain_state.json  # Persistent storage for user profiles and order history
├── test_main.py            # Async pytest tests for webhook routing and lifespan startup
├── AGENTS.md               # Agent instructions and run/debug guidance for AI assistants
├── .env.example            # Environment variable template (BOT_TOKENS, BASE_URL, GEMINI_API_KEY)
├── decision-log/           # Architectural decision records
├── product-design/         # Product & UX docs (this folder)
├── knowledge-base/         # Notes, lessons, retrospects
└── visual-assets/          # Flowcharts, wireframes, placeholders

Notes:
- There is no frontend code in this repository; the project is a backend-only service that receives Telegram webhooks and dispatches them to shared handlers.

## 2. High-Level System Diagram
The service uses a Controller-Service pattern to accept webhooks for multiple bots across different channels and feeds them into a shared agnostic logic layer. Dataflow (text-based):

[User] -> [Telegram] -> POST /telegram/{bot_token} -> [aiogram dispatcher] -> [telegram_router] -
                                                                                                -> [core_logic] -> [ai/ai_service]
[User] -> [Viber]    -> POST /viber/{bot_token}    -> [FastAPI route]      -----------------------/

This pattern keeps runtime memory small, decouples the business logic from platform specifics, and keeps code reuse high for hackathon demos.

## 3. Core Components

### 3.1. Backend (Controllers & Ingress)
Name: Multi-Tenant Webhook Endpoints
Description: FastAPI application that exposes dynamic endpoints (`POST /telegram/{bot_token}` and `POST /viber/{bot_token}`). It validates tokens, parses platform-specific payloads, and delegates processing to `core_logic.py`.
Technologies: Python 3.11+, FastAPI, aiogram 3, Uvicorn (ASGI), python-dotenv (optional for `.env`).
Deployment: Local dev (uvicorn) for hackathon; can be deployed to cloud (Cloud Run, Heroku, or a VM) for stable public endpoints.

### 3.2. Telegram Controller
Name: `telegram_router.py`
Description: Contains the `aiogram.Router` instance and message/command handlers for Telegram. Handlers parse Telegram's objects and pass generic fields (text, user_id) to `core_logic.py`.
Technologies: aiogram Router, handler filters (e.g., `CommandStart`, `F.text`).

### 3.3. Core Business Service
Name: `core_logic.py`
Description: Pure Python functions defining the bot's behavior for commands (like /start) and echo/AI chats, completely separate from platform implementations.
Technologies: Python

### 3.4. AI Service
Name: `ai/ai_service.py`
Description: Manages interactions with the Google Generative AI SDK, assembling the final instruction from global rules plus compiled bot state, and generating context-aware chat responses using a normalized Gemini model id (defaults to `gemini-2.5-flash-lite`).
Technologies: `google-generativeai` SDK, configurable GEMINI_MODEL_NAME.

### 3.5. Bot Context Store
Name: `bot_store.py`
Description: Acts as a centralized Redux-style state registry mapping `bot_token`s to their specific `BotStateSlice` (containing personas, specific rules, dynamic state/inventory, and few-shot examples).
Technologies: Python dataclasses.

### 3.6. User Analytics Store
Name: `ai/user_store.py`
Description: Persistent user profile store for tracking customer preferences, likes/dislikes, order history, and predicted interests. Supports loading from and saving to JSON (`ai/sales_brain_state.json`).
Technologies: Python dataclasses, JSON file persistence.

## 4. Data Stores
- **User Analytics Store** (`ai/user_store.py`): JSON-based persistent storage for user profiles and order history.
  - State file: `ai/sales_brain_state.json`
  - Tracks: user preferences (likes/dislikes), order history, predicted interests
  - Auto-saves on updates

Future options:
- Redis for short-lived session/caching or aiogram storage backends.
- PostgreSQL or similar for long-term user data or per-bot configuration.

## 5. External Integrations / APIs
- Telegram Bot API — receives user messages and sends updates via webhook or getUpdates.
- Viber REST API — secondary platform for bot interactions.
- Google Generative AI (Gemini) — powers intelligent chat responses via `gemini-2.5-flash-lite` (configurable via GEMINI_MODEL_NAME env var).
- `GEMINI_MODEL_NAME` — optional override for the normalized Gemini model id used in `ai/ai_service.py`.
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
- Persona behavior is compiled at startup from `personas_config.json`; runtime prompt branching should stay limited to request-specific context.

## 8. Development & Testing Environment
Local setup (quick):
```bash
python -m venv venv
.\venv\Scripts\activate   # PowerShell/Command Prompt on Windows
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
- Expand the persona factory with richer category and axis mappings as new SME bot types are added.

## 10. Project Identification
Project Name: Multi-Tenant Telegram Bot Backend (Hackathon)
Repository URL: (local workspace)
Primary Contact: Repository owner / maintainer
Date of Last Update: 2026-05-27

## 11. Glossary / Acronyms
- `dp`: Dispatcher (aiogram) — central dispatcher that routes updates into handlers.
- `BOT_TOKENS`: Comma-separated list of Telegram bot tokens used to validate incoming webhooks.