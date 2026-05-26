# AGENTS.md

Agent instructions for this repository.

## Scope

- This repository is a Python backend for a multi-tenant Telegram (and Viber) bot webhook service.
- Keep changes focused on backend behavior in `main.py`, `telegram_router.py`, `ai_service.py`, and `core_logic.py`.

## Quick Start

- Use Python 3.11+ on Windows.
- Create and activate a local virtual environment in the repo root.
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Run Commands

- Start dev server:
  ```bash
  python -m uvicorn main:app --reload
  ```
- Run tests:
  ```bash
  python -m pytest -v
  ```

## Configuration

- Environment variables are loaded in `main.py` using `python-dotenv` when available.
- Required vars are documented in `.env.example`.
- Expected values:
  - `BOT_TOKENS`: comma-separated Telegram bot tokens.
  - `BASE_URL`: public HTTPS base URL (for local dev, usually ngrok URL).
  - `GEMINI_API_KEY`: Google Gemini API key for AI responses.

## Architecture Overview

```
User → Telegram → POST /telegram/{bot_token} → FastAPI Route
                                                      ↓
                                            aiogram feed_update
                                                      ↓
                                            Shared Router (telegram_router.py)
                                                      ↓
                                            Core Logic (core_logic.py)
                                                      ↓
                                            AI Service (ai_service.py → Gemini)
```

### File Responsibilities

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app: webhook endpoints, lifecycle hooks (webhook registration), dispatcher wiring |
| `telegram_router.py` | Shared aiogram router with bot handlers (`/start`, text messages) |
| `ai_service.py` | AI service - manages bot personas, connects to Google Gemini 2.5 Flash |
| `core_logic.py` | Core business logic - connects router to AI service |

## Key Components

### 1. Multi-Tenant Webhook Routing (`main.py`)

- Single FastAPI instance accepts webhooks for multiple bots
- Endpoint `POST /telegram/{bot_token}` validates token, creates Bot context, feeds update to dispatcher
- Also includes Viber webhook endpoint at `POST /viber/{bot_token}` (HTTP-based, not bot API)
- Lifespan context manager registers all bot webhooks on startup

### 2. Shared Router (`telegram_router.py`)

- Contains universal handlers shared by all configured bots
- `cmd_start()` - handles `/start` command
- `echo_all()` - handles text messages, connects to AI service
- Handlers adapt to bot identity via `message.bot.get_me()`

### 3. AI Service (`ai_service.py`)

- Manages bot personas (e.g., "Ma Thida" - a polite Burmese sales assistant)
- Uses Google Generative AI SDK with `gemini-2.5-flash` model
- In-memory chat session store for conversational memory (per bot_token, per user_id)
- Fallback to default persona if no custom config registered

### 4. Core Logic (`core_logic.py`)

- Bridges router handlers to AI service
- `generate_start_reply()` - welcome message with bot/user info
- `generate_echo_reply()` - sends user messages to AI and returns response

## Security Considerations

- Telegram webhooks require a public HTTPS URL. `localhost` will not work for Telegram callbacks.
- If `BOT_TOKENS` is empty or malformed, requests are rejected with 403 by token validation.
- Prefer `python -m uvicorn ...` to avoid shell-specific PATH issues on Windows/Git Bash.
- Keep bot tokens secret — do not commit `.env` to source control.
- GEMINI_API_KEY must be set for AI responses to work; otherwise falls back to error message.

### Implemented Security Measures

1. **API Key Validation** (`ai_service.py`):
   - Validates key format (must match `AIza...` pattern)
   - Never logs API key in error messages
   - Uses safe error messages that don't expose internals

2. **Input Sanitization** (`ai_service.py`):
   - Blocks common prompt injection patterns (ignore instructions, system:, etc.)
   - Limits message length to 2000 characters
   - Returns safe fallback for blocked content

3. **Rate Limiting** (`telegram_router.py`):
   - 20 requests per minute per user (configurable)
   - In-memory rate limiter using sliding window
   - Returns polite message when rate exceeded

## Key Files

- `main.py` - FastAPI app entry point
- `telegram_router.py` - Shared aiogram router (note: not `router.py`)
- `ai_service.py` - AI persona and Gemini integration
- `core_logic.py` - Business logic bridge
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies

## Decision Records

Refer to `decision-log/` for architectural decisions:

- `DEC-001-multi-tenant-webhook-routing.md` - Initial multi-tenant architecture
- `DEC-002-gemini-model-upgrade.md` - Gemini model upgrade decisions
- `DEC-003-controller-service-architecture.md` - Controller/service architecture

## Editing Rules For Agents

- Preserve the multi-tenant flow: validate `bot_token` against configured tokens before processing updates.
- Avoid introducing per-bot duplicated routers unless explicitly requested.
- Use descriptive commit messages following the decision log format when making architectural changes.
- When adding new bot platforms, follow the existing pattern in `main.py` (validate token, parse payload, route to handler).