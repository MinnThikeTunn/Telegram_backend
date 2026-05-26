from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import logging

import core_logic

logger = logging.getLogger(__name__)

telegram_router = Router()

@telegram_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command for Telegram."""
    bot_user = await message.bot.get_me()
    
    reply = await core_logic.generate_start_reply(
        channel="telegram",
        user_name=message.from_user.first_name,
        bot_name=bot_user.first_name,
        user_id=str(message.from_user.id)
    )
    
    await message.answer(reply)

@telegram_router.message(F.text)
async def echo_all(message: Message) -> None:
    """Handle text messages for Telegram."""
    bot_token = message.bot.token
    user_id = str(message.from_user.id)
    user_text = message.text

    if not user_text:
        return

    reply_text = await core_logic.generate_echo_reply(
        channel="telegram",
        bot_token=bot_token,
        user_id=user_id,
        text=user_text
    )
    
    await message.answer(reply_text)
