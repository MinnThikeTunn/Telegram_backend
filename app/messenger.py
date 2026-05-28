import os
import logging

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

load_dotenv(".env.local")
load_dotenv("app/.env")

import core_logic

router = APIRouter()
logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
MESSENGER_BOT_ID = os.getenv("MESSENGER_BOT_ID", "messenger")
MESSENGER_BOT_NAME = os.getenv("MESSENGER_BOT_NAME", "Messenger Bot")


# =========================================
# VERIFY WEBHOOK
# =========================================

@router.get("/messenger")
async def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):

    if hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)

    return PlainTextResponse("Verification failed", status_code=403)


# =========================================
# SEND MESSAGE TO FACEBOOK USER
# =========================================

async def send_message(recipient_id: str, text: str) -> None:

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


# =========================================
# RECEIVE FACEBOOK MESSAGE
# =========================================

@router.post("/messenger")
async def receive_message(request: Request):

    body = await request.json()

    logger.info("Messenger webhook payload received")

    if body.get("object") == "page":

        for entry in body["entry"]:

            for event in entry["messaging"]:

                sender_id = event["sender"]["id"]

                if "message" in event:

                    user_message = event["message"].get("text", "")

                    logger.info("Messenger message from %s: %s", sender_id, user_message)

                    if user_message == "/start":
                        reply = await core_logic.generate_start_reply(
                            channel="messenger",
                            user_name=sender_id,
                            bot_name=MESSENGER_BOT_NAME,
                            user_id=str(sender_id),
                        )
                    elif user_message:
                        reply = await core_logic.generate_echo_reply(
                            channel="messenger",
                            bot_token=MESSENGER_BOT_ID,
                            user_id=str(sender_id),
                            text=user_message,
                        )
                    else:
                        continue

                    await send_message(sender_id, reply)

    return {"status": "ok"}
