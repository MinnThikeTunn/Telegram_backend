from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import logging

from ai_service import generate_chat_response

logger = logging.getLogger(__name__)

shared_router = Router()


@shared_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Dynamically find out who I am right now
    bot_user = await message.bot.get_me()

    await message.answer(
        f"🚀 Shared Logic Working!\n\n"
        f"You are talking to: **{bot_user.first_name}**\n"
        f"Your Telegram ID: `{message.from_user.id}`"
    )


@shared_router.message(F.text)
async def echo_all(message: Message) -> None:
    bot_token = message.bot.token
    user_id = message.from_user.id
    user_text = message.text

    if not user_text:
        return

    # Serve contextual reply using our Gemini layer
    ai_response = await generate_chat_response(
        bot_token=bot_token,
        user_id=user_id,
        user_message=user_text
    )
    
    await message.answer(ai_response)

