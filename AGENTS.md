I # AGENTS.md

Agent instructions for this repository.

## Scope
- This repository is a Python backend for a multi-tenant Telegram bot webhook service.
- Keep changes focused on backend behavior in `main.py`, `router.py`, and `test_main.py`.

## Quick Start
- Use Python 3.11+ on Windows.
- Create and activate a local virtual environment in the repo root.
- Install dependencies:
  - `pip install fastapi "uvicorn[standard]" aiogram httpx pytest pytest-asyncio python-dotenv`

## Run Commands
- Start dev server:
  - `python -m uvicorn main:app --reload`
- Run tests:
  - `python -m pytest test_main.py -v`
- Run one test:
  - `python -m pytest test_main.py::test_handle_telegram_webhook_authorized -v`

## Configuration
- Environment variables are loaded in `main.py` using `python-dotenv` when available.
- Required vars are documented in `.env.example`.
- Expected values:
  - `BOT_TOKENS`: comma-separated Telegram bot tokens.
  - `BASE_URL`: public HTTPS base URL (for local dev, usually ngrok URL).

## Architecture Notes
- `main.py` owns app bootstrapping, webhook registration, and request entrypoint `/telegram/{bot_token}`.
- `router.py` contains shared aiogram handlers reused by all configured bots.
- `test_main.py` uses async tests with mocked `main.Bot` and `main.dp.feed_update`.

## Pitfalls
- Telegram webhooks require a public HTTPS URL. `localhost` will not work for Telegram callbacks.
- If `BOT_TOKENS` is empty or malformed, requests are rejected with 403 by token validation.
- Prefer `python -m uvicorn ...` to avoid shell-specific PATH issues on Windows/Git Bash.

## Editing Rules For Agents
- Preserve the multi-tenant flow: validate `bot_token` against configured tokens before processing updates.
- Avoid introducing per-bot duplicated routers unless explicitly requested.
- Keep tests updated when webhook validation or lifespan startup behavior changes.

## Key Files
- `main.py`
- `router.py`
- `test_main.py`
- `.env.example`

## Hackathon Plan (Multi-Tenant Shared Space)

This project is intentionally minimal and focused: a single FastAPI instance serves as a unified control tower that accepts webhooks for many bots and feeds them into a shared aiogram router. The goal is to prove the shared-space concept quickly for a hackathon demo.

### The Hackathon Architecture (Keep It Simple)

```
          [ Webhook Traffic ]
               |
               v
        POST /telegram/{bot_token}
               |
               v
          +-----------------+
          |  FastAPI Route  |
          +-----------------+
               |
               v
       +---------------------------+
       |  aiogram Feed Webhook     |  <-- Injects running Bot context
       +---------------------------+
               |
               v
       +---------------------------+
       |   Shared Router Logic     |  <-- Universal code execution
       +---------------------------+

```

### Step-by-Step Hackathon Execution Plan

#### Step 1: Install Dependencies

Run the following to install the core async web and Telegram libraries:

```bash
pip install fastapi uvicorn aiogram
```

#### Step 2: Build the Shared Logic Router (`router.py`)

Write your handlers once and make them independent from the bot identity. Example:

```python
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

shared_router = Router()

@shared_router.message(CommandStart())
async def cmd_start(message: Message):
  bot_user = await message.bot.get_me()
  await message.answer(
    f"🚀 Shared Logic Working!\n\n"
    f"You are talking to: **{bot_user.first_name}**\n"
    f"Your Telegram ID: `{message.from_user.id}`"
  )

@shared_router.message(F.text)
async def echo_all(message: Message):
  await message.answer(f"Echo from shared space: {message.text}")
```

#### Step 3: Build the FastAPI Master Control (`main.py`)

Boot the web server, register webhooks, and feed updates into the shared dispatcher:

```python
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Dispatcher, Bot
from aiogram.types import Update
from router import shared_router

BOT_TOKENS = ["YOUR_FIRST_BOT_TOKEN_HERE", "YOUR_SECOND_BOT_TOKEN_HERE"]
BASE_URL = "https://your-ngrok-url.ngrok-free.app"

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
dp.include_router(shared_router)

app = FastAPI(title="Multi-Bot Hackathon Backend")

@app.on_event("startup")
async def startup_event():
  for token in BOT_TOKENS:
    try:
      bot = Bot(token=token)
      webhook_url = f"{BASE_URL}/telegram/{token}"
      await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
      print(f"✅ Webhook linked for Bot: ...{token[-6:]}")
      await bot.session.close()
    except Exception as e:
      print(f"❌ Failed to register bot ...{token[-6:]}: {e}")

@app.post("/telegram/{bot_token}")
async def handle_telegram_webhook(bot_token: str, request: Request):
  if bot_token not in BOT_TOKENS:
    return Response(status_code=403, content="Unauthorized Bot Token")

  update_json = await request.json()
  async with Bot(token=bot_token) as bot:
    update = Update.model_validate(update_json, context={"bot": bot})
    await dp.feed_update(bot, update)

  return Response(status_code=200)
```

### How to Demo This Live to Judges

1. Expose localhost with ngrok:

```bash
ngrok http 8000
```

2. Start the server:

```bash
uvicorn main:app --reload
```

3. Demo steps:
- Open two different bot chats.
- Send `/start` to Bot A → it replies with its identity.
- Send a message to Bot B → it echoes using the same server and router.

Explain the shared-space concept: multiple independent bot identities handled by the same live instance and codebase.

---

Notes:
- Keep this plan minimal and focused for hackathon speed. If the project later requires scaling, move to queued worker architectures and per-bot persistent storage.
