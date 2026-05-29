from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.routes.delivery import router as delivery_router
import os

api_router = APIRouter()

# Include sub-routers. Prefix is handled when registered in main.py
api_router.include_router(delivery_router, tags=["Delivery"])


BOT_TOKENS_STR = os.getenv("BOT_TOKENS", "")
BOT_TOKENS = [t.strip() for t in BOT_TOKENS_STR.split(",") if t.strip()]


class BroadcastRequest(BaseModel):
    bot_token: str
    message: str


class BroadcastResponse(BaseModel):
    bot_persona: str
    total_users: int
    sent: int
    failed: int
    details: list


@api_router.post("/broadcast", response_model=BroadcastResponse, tags=["Broadcast"])
async def broadcast_message(body: BroadcastRequest):
    """Broadcast a message to all users who have chatted with the specified bot."""
    if body.bot_token not in BOT_TOKENS:
        raise HTTPException(status_code=403, detail="Unauthorized bot token")

    import core_logic
    result = await core_logic.send_broadcast_message(body.bot_token, body.message)
    return result
