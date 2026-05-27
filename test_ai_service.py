import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import ai.ai_service
from ai.ai_service import generate_chat_response, _chat_sessions

@pytest.mark.asyncio
async def test_generate_chat_response_initializes_with_history():
    # Clear existing sessions
    _chat_sessions.clear()
    ai.ai_service._is_configured = True  # Mock configured API

    bot_token = "test_bot_token"
    user_id = "test_user_id"
    user_message = "Hello"

    # Mocking genai.GenerativeModel
    with patch("google.generativeai.GenerativeModel") as MockModel:
        mock_model_instance = MockModel.return_value
        mock_chat = MagicMock()
        mock_model_instance.start_chat.return_value = mock_chat

        # Mocking send_message_async to return a mock response
        mock_response = MagicMock()
        mock_response.text = "Mocked AI Response"
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)

        # Call the function
        response = await generate_chat_response(bot_token, user_id, user_message)

        # Verify start_chat was called with history
        assert mock_model_instance.start_chat.called
        args, kwargs = mock_model_instance.start_chat.call_args
        assert "history" in kwargs
        history = kwargs["history"]
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "model"

        # Verify the response
        assert response == "Mocked AI Response"

        # Verify subsequent calls use the same session and don't call start_chat again
        await generate_chat_response(bot_token, user_id, "Second message")
        assert mock_model_instance.start_chat.call_count == 1
