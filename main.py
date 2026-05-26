import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from aiogram import Dispatcher, Bot
from aiogram.types import Update
from router import shared_router

# Hackathon Mock Database (Replace with your actual list of bot tokens)
BOT_TOKENS = [
    "YOUR_FIRST_BOT_TOKEN_HERE",
    "YOUR_SECOND_BOT_TOKEN_HERE"
]
BASE_URL = "https://your-ngrok-url.ngrok-free.app" # Change this during hackathon demo

logging.basicConfig(level=logging.INFO)

# 1. Initialize Shared Dispatcher Workspace
dp = Dispatcher()
dp.include_router(shared_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register all bots to point to our single web server route."""
    for token in BOT_TOKENS:
        if token.startswith("YOUR_"):
            print(f"⚠️ Skipping placeholder token: {token}")
            continue
        try:
            bot = Bot(token=token)
            webhook_url = f"{BASE_URL}/telegram/{token}"
            await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            print(f"✅ Webhook linked for Bot: ...{token[-6:]}")
            await bot.session.close() # Clean up temporary connection session
        except Exception as e:
            print(f"❌ Failed to register bot ...{token[-6:]}: {e}")
    yield
    # Any cleanup can go here

app = FastAPI(title="Multi-Bot Hackathon Backend", lifespan=lifespan)

@app.post("/telegram/{bot_token}")
async def handle_telegram_webhook(bot_token: str, request: Request):
    """The Shared Space: Dynamic routing happens right here!"""
    if bot_token not in BOT_TOKENS:
        return Response(status_code=403, content="Unauthorized Bot Token")

    # Capture the raw update payload from Telegram
    update_json = await request.json()

    # Initialize ephemeral Bot runtime instance context for this specific request
    async with Bot(token=bot_token) as bot:
        # Pass the bot instance to model_validate if needed or let aiogram handle it
        update = Update.model_validate(update_json, context={"bot": bot})
        # Feed the update into the shared logic architecture pool
        await dp.feed_update(bot, update)

    return Response(status_code=200)
