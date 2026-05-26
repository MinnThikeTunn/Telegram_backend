from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

shared_router = Router()

@shared_router.message(CommandStart())
async def cmd_start(message: Message):
    # Dynamically find out who I am right now
    bot_user = await message.bot.get_me()

    await message.answer(
        f"🚀 Shared Logic Working!\n\n"
        f"You are talking to: **{bot_user.first_name}**\n"
        f"Your Telegram ID: `{message.from_user.id}`"
    )

@shared_router.message(F.text)
async def echo_all(message: Message):
    # Dynamic contextual reply
    await message.answer(f"Echo from shared space: {message.text}")
