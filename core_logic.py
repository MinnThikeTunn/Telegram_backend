from ai.ai_service import generate_chat_response
from ai.user_store import user_store
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

async def generate_start_reply(channel: str, user_name: str, bot_name: str, user_id: str) -> str:
    """Core logic for handling the /start command."""
    return (
        f"🚀 Shared Logic Working!\n\n"
        f"You are talking to: **{bot_name}** via {channel.capitalize()}\n"
        f"Your ID: `{user_id}`"
    )

async def generate_echo_reply(channel: str, bot_token: str, user_id: str, text: str) -> str:
    """Core logic for handling message replies, connecting to the AI service."""
    # Serve contextual reply using our Gemini layer
    ai_response = await generate_chat_response(
        bot_token=bot_token,
        user_id=str(user_id),
        user_message=text
    )
    return ai_response

async def process_checkout(user_id: str, order_data: Dict[str, Any]) -> str:
    """Core logic hook for whenever an order completes. Logs it to Sales Brain."""
    try:
        user_store.add_order(user_id, order_data)
        logger.info(f"Order successfully tracked for user {user_id} in Analytics Store.")
        return "Order verified and tracked."
    except Exception as e:
        logger.error(f"Failed to track order: {e}")
        return "Order processed but analytics tracking failed."
