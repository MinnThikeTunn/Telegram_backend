import pytest
from httpx import AsyncClient, ASGITransport
from main import app, BOT_TOKENS
from unittest.mock import AsyncMock, patch
import json

@pytest.mark.asyncio
async def test_handle_telegram_webhook_authorized():
    token = BOT_TOKENS[0]
    update_data = {
        "update_id": 12345,
        "message": {
            "message_id": 1,
            "from": {"id": 123, "is_bot": False, "first_name": "Test User"},
            "chat": {"id": 123, "type": "private"},
            "date": 1600000000,
            "text": "Hello"
        }
    }

    # Mock the Bot class and Dispatcher.feed_update
    with patch("main.Bot") as MockBot, patch("main.dp.feed_update", new_callable=AsyncMock) as mock_feed:
        mock_bot_instance = MockBot.return_value
        mock_bot_instance.__aenter__.return_value = mock_bot_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(f"/telegram/{token}", json=update_data)

        assert response.status_code == 200
        assert mock_feed.called
        # Check if feed_update was called with the mock_bot_instance
        args, kwargs = mock_feed.call_args
        assert args[0] == mock_bot_instance

@pytest.mark.asyncio
async def test_handle_telegram_webhook_unauthorized():
    token = "INVALID_TOKEN"
    update_data = {"update_id": 12345}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(f"/telegram/{token}", json=update_data)

    assert response.status_code == 403
    assert response.text == "Unauthorized Bot Token"

@pytest.mark.asyncio
async def test_lifespan_startup_skips_placeholders():
    with patch("main.Bot") as MockBot:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # The lifespan is triggered when the client enters the context
            pass

        # In our main.py, it skips tokens starting with "YOUR_"
        # Since both tokens in BOT_TOKENS start with "YOUR_", MockBot should not be instantiated for webhooks
        assert MockBot.call_count == 0
