from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

import core_logic

logger = logging.getLogger(__name__)

telegram_router = Router()


# =============================================================================
# Security Fix #3: Rate Limiting - Prevent abuse of external API
# =============================================================================
@dataclass
class RateLimitConfig:
    """Rate limit configuration per user."""
    max_requests: int = 20  # Max requests per window
    window_seconds: int = 60  # Time window in seconds
    timestamps: list = field(default_factory=list)


class RateLimiter:
    """Simple in-memory rate limiter per user."""
    
    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._user_limits: Dict[str, RateLimitConfig] = defaultdict(
            lambda: RateLimitConfig(max_requests, window_seconds)
        )
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limit. Returns True if allowed."""
        now = time.time()
        config = self._user_limits[user_id]
        
        # Remove timestamps outside the current window
        config.timestamps = [ts for ts in config.timestamps if now - ts < self.window_seconds]
        
        if len(config.timestamps) >= self.max_requests:
            logger.warning("Rate limit exceeded for user_id=%s", user_id)
            return False
        
        # Add current timestamp
        config.timestamps.append(now)
        return True


# Initialize rate limiter: 20 requests per minute per user
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


@telegram_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle the /start command for Telegram."""
    user_id = str(message.from_user.id)
    bot_token = message.bot.token
    bot_user = await message.bot.get_me()
    
    reply_data = await core_logic.handle_start(
        bot_token=bot_token,
        user_id=user_id,
        user_name=message.from_user.first_name,
        bot_name=bot_user.first_name
    )

    await message.answer(
        reply_data["text"],
        reply_markup=reply_data.get("reply_markup"),
        parse_mode=ParseMode.MARKDOWN
    )


@telegram_router.callback_query()
async def handle_callbacks(callback: CallbackQuery) -> None:
    """Handle interactive button clicks."""
    user_id = str(callback.from_user.id)
    bot_token = callback.bot.token
    data = callback.data

    reply_data = await core_logic.handle_callback(
        bot_token=bot_token,
        user_id=user_id,
        callback_data=data
    )

    if reply_data:
        await callback.message.answer(
            reply_data["text"],
            reply_markup=reply_data.get("reply_markup"),
            parse_mode=ParseMode.MARKDOWN
        )

    await callback.answer()


@telegram_router.message(F.photo)
async def handle_photo(message: Message) -> None:
    """Handle payment receipt photos."""
    user_id = str(message.from_user.id)
    bot_token = message.bot.token

    # Get the largest photo
    photo = message.photo[-1]
    file_id = photo.file_id

    reply_text = await core_logic.handle_receipt_photo(
        bot_token=bot_token,
        user_id=user_id,
        file_id=file_id
    )
    
    await message.answer(reply_text, parse_mode=ParseMode.MARKDOWN)


@telegram_router.message(F.text)
async def echo_all(message: Message) -> None:
    """Handle text messages for Telegram."""
    bot_token = message.bot.token
    user_id = str(message.from_user.id)
    user_text = message.text

    if not user_text:
        return

    # Security Fix #3: Check rate limit before processing
    if not rate_limiter.is_allowed(user_id):
        await message.answer(
            "အရမ်းများပါသည်ရှင့်။ တစ်မိနစ်စောင့်ပါရှင့်။ (Too many requests, please wait a moment.)"
        )
        return

    reply_text = await core_logic.generate_echo_reply(
        channel="telegram",
        bot_token=bot_token,
        user_id=user_id,
        text=user_text
    )
    
    await message.answer(reply_text, parse_mode=ParseMode.MARKDOWN)