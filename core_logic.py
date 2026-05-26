from ai_service import generate_chat_response
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
