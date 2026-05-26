import logging
import os
from typing import List
from contextlib import asynccontextmanager

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Request, Response
from aiogram import Dispatcher, Bot
from aiogram.types import Update
from telegram_router import telegram_router
import core_logic

BOT_TOKENS_STR = os.getenv("BOT_TOKENS", "")
BOT_TOKENS: List[str] = [t.strip() for t in BOT_TOKENS_STR.split(",") if t.strip()]
BASE_URL: str = os.getenv("BASE_URL", "https://your-ngrok-url.ngrok-free.app")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not BOT_TOKENS:
    logger.warning("No BOT_TOKENS configured — webhook routes will reject all tokens until configured.")

# 1. Initialize Shared Dispatcher Workspace for Telegram
dp = Dispatcher()
dp.include_router(telegram_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register all bots to point to our single web server route."""
    for token in BOT_TOKENS:
        if not token:
            continue
        try:
            webhook_url = f"{BASE_URL}/telegram/{token}"
            # Use async context manager for Bot to ensure session cleanup
            async with Bot(token=token) as bot:
                await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
                logger.info("✅ Webhook linked for Bot: ...%s", token[-6:])
        except Exception:
            logger.exception("❌ Failed to register bot ...%s", token[-6:])
    yield

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

@app.post("/viber/{bot_token}")
async def handle_viber_webhook(bot_token: str, request: Request):
    """Viber HTTP ingress point."""
    if bot_token not in BOT_TOKENS:
        return Response(status_code=403, content="Unauthorized Bot Token")

    payload = await request.json()
    
    if payload.get("event") == "message":
        text = payload.get("message", {}).get("text", "")
        user_id = payload.get("sender", {}).get("id", "")
        user_name = payload.get("sender", {}).get("name", "Unknown User")
        
        if text == "/start":
            reply_text = await core_logic.generate_start_reply(
                channel="viber", 
                user_name=user_name,
                bot_name="My Viber Bot",
                user_id=str(user_id)
            )
        elif text:
            reply_text = await core_logic.generate_echo_reply(
                channel="viber",
                bot_token=bot_token,
                user_id=str(user_id),
                text=text
            )
            
        # Example to send back response over HTTPX:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     await client.post(
        #         "https://chatapi.viber.com/pa/send_message",
        #         headers={"X-Viber-Auth-Token": bot_token},
        #         json={"receiver": user_id, "type": "text", "text": reply_text}
        #     )
        
        logger.info(f"[VIBER] Response to {user_id}: {reply_text}")

    return Response(status_code=200)

