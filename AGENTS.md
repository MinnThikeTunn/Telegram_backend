# AGENTS.md

Agent instructions for this repository.

## Scope

- This repository is a Python backend for a multi-tenant Telegram (and Viber) bot webhook service.
- Keep changes focused on backend behavior in `main.py`, `telegram_router.py`, `ai/`, and `core_logic.py`.

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
  - `DELIVERY_API_BASE`: (Optional) Base URL for the Delivery Matrix API (default: `http://localhost:8000`).
  - `DELIVERY_CACHE_TTL_SECONDS`: (Optional) In-memory cache validity duration in seconds (default: `300` / 5 minutes).

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
                                            AI Service (ai/ai_service.py → Gemini 2.5 Flash Lite)
```

### File Responsibilities

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app: webhook endpoints, lifecycle hooks (webhook registration), dispatcher wiring |
| `telegram_router.py` | Shared aiogram router with bot handlers (`/start`, text messages), rate limiter |
| `bot_store.py` | State Registry - Centralized Redux-style store mapping bot tokens to compiled persona slices and few-shots |
| `persona_factory.py` | Persona compiler - builds prompt layers from category and axis config |
| `personas_config.json` | Persona source of truth - bot profiles, categories, axes, and dynamic state |
| `ai/ai_service.py` | AI service - manages bot personas, connects to Google Gemini 2.5 Flash, handles quota cooldowns |
| `ai/user_store.py` | User Analytics Store - Customer profile tracking, order history, preferences |
| `core_logic.py` | Core business logic - connects router to AI service |
| `api/routes/delivery.py` | Delivery Matrix REST endpoint implementation |
| `api/delivery_service.py` | Business logic for rate & timeline calculation |
| `api/delivery_client.py` | Async HTTP Client - cached dynamic query fetching from Delivery Matrix API |

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

### 3. AI Service (`ai/ai_service.py`)

- Manages bot personas (e.g., "Ma Thida" - a polite Burmese sales assistant)
- Uses Google Generative AI SDK with `gemini-2.5-flash-lite` model (configurable via GEMINI_MODEL_NAME env var)
- In-memory chat session store for conversational memory (per bot_token, per user_id)
- Fallback to default persona if no custom config registered

### 4. Core Logic (`core_logic.py`)

- Bridges router handlers to AI service
- `generate_start_reply()` - welcome message with bot/user info
- `generate_echo_reply()` - sends user messages to AI and returns response

### 5. Bot Context Store (`bot_store.py`)

- Acts as a centralized, Redux-style state registry.
- Decouples bot-specific rules, personas, inventory, and few-shots from the AI logic.
- `ai/ai_service.py` fetches the `BotStateSlice` from here before constructing the AI prompt.

### 6. User Analytics Store (`ai/user_store.py`)

- JSON-based persistent storage for user profiles and order tracking.
- Tracks: user_id, likes, dislikes, order_history, predicted_interests.
- State file: `ai/sales_brain_state.json`.
- Used by `core_logic.py` hooks (e.g., `process_checkout`) for order tracking.

### 7. Dynamic Delivery Matrix Client (`api/delivery_client.py`)

- Coordinates communication with the Delivery Matrix REST API (`GET /api/v1/delivery-matrix`).
- **Performance Caching**: Uses short-lived in-memory caching to bypass redundant backend hits.
- **Surgical Single-Zone Search**: Includes `fetch_single_zone(township_name)` to selectively query the API via dynamic filter parameters (`search` & `limit=1`) instead of pulling down the entire dataset.
- **Resilient Fallback**: Reverts automatically to compiled static defaults in `BotStateSlice` or stale cache entries if the API backend fails or timeouts.

## Security Considerations

- Telegram webhooks require a public HTTPS URL. `localhost` will not work for Telegram callbacks.
- If `BOT_TOKENS` is empty or malformed, requests are rejected with 403 by token validation.
- Prefer `python -m uvicorn ...` to avoid shell-specific PATH issues on Windows/Git Bash.
- Keep bot tokens secret — do not commit `.env` to source control.
- GEMINI_API_KEY must be set for AI responses to work; otherwise falls back to error message.

### Implemented Security Measures

1. **API Key Validation** (`ai/ai_service.py`):
   - Validates key format (must match `AIza...` pattern)
   - Never logs API key in error messages
   - Uses safe error messages that don't expose internals

2. **Input Sanitization** (`ai/ai_service.py`):
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
- `bot_store.py` - Centralized Bot context registry
- `ai/ai_service.py` - AI persona and Gemini integration
- `ai/user_store.py` - User Analytics Store for customer profiles and preferences
- `ai/sales_brain_state.json` - User analytics state file
- `core_logic.py` - Business logic bridge
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies

## Decision Records

Refer to `decision-log/` for architectural decisions:

- `DEC-001-multi-tenant-webhook-routing.md` - Initial multi-tenant architecture
- `DEC-002-gemini-model-upgrade.md` - Gemini model upgrade decisions
- `DEC-003-controller-service-architecture.md` - Controller/service architecture
- `DEC-004-bot-specific-context-store.md` - Context Store architecture
- `DEC-005-user-analytics-store.md` - User Analytics Store for customer profiling
- `DEC-006-persona-factory-prompt-stacking.md` - Persona Factory prompt stacking for SME bots

## Editing Rules For Agents

- Preserve the multi-tenant flow: validate `bot_token` against configured tokens before processing updates.
- Avoid introducing per-bot duplicated routers unless explicitly requested.
- Keep persona behavior compile-time driven through `personas_config.json` and `persona_factory.py`; do not move category logic back into runtime prompt branching.
- Use descriptive commit messages following the decision log format when making architectural changes.
- When adding new bot platforms, follow the existing pattern in `main.py` (validate token, parse payload, route to handler).