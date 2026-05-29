import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Bot

from bot_profile_util import (
    update_bot_name,
    update_bot_short_description,
    update_bot_description,
    update_bot_profile,
)


async def test_update_bot_name():
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.set_my_name = AsyncMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=None)

    with patch("bot_profile_util.Bot", return_value=mock_bot):
        result = await update_bot_name("test_token", "New Bot Name")
        mock_bot.set_my_name.assert_called_once_with(name="New Bot Name")
        assert result is True
        print("test_update_bot_name passed")


async def test_update_bot_short_description():
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.set_my_short_description = AsyncMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=None)

    with patch("bot_profile_util.Bot", return_value=mock_bot):
        result = await update_bot_short_description("test_token", "Short desc")
        mock_bot.set_my_short_description.assert_called_once_with(short_description="Short desc")
        assert result is True
        print("test_update_bot_short_description passed")


async def test_update_bot_description():
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.set_my_description = AsyncMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=None)

    with patch("bot_profile_util.Bot", return_value=mock_bot):
        result = await update_bot_description("test_token", "Full desc")
        mock_bot.set_my_description.assert_called_once_with(description="Full desc")
        assert result is True
        print("test_update_bot_description passed")


async def test_update_bot_profile_partial():
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.set_my_name = AsyncMock()
    mock_bot.set_my_short_description = AsyncMock()
    mock_bot.set_my_description = AsyncMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=None)

    with patch("bot_profile_util.Bot", return_value=mock_bot):
        results = await update_bot_profile(
            token="test_token",
            name="New Name",
            short_description="Short",
        )
        assert results == {"name": "updated", "short_description": "updated"}
        mock_bot.set_my_name.assert_called_once_with(name="New Name")
        mock_bot.set_my_short_description.assert_called_once_with(short_description="Short")
        mock_bot.set_my_description.assert_not_called()
        print("test_update_bot_profile_partial passed")


if __name__ == "__main__":
    asyncio.run(test_update_bot_name())
    asyncio.run(test_update_bot_short_description())
    asyncio.run(test_update_bot_description())
    asyncio.run(test_update_bot_profile_partial())
    print("All tests passed!")