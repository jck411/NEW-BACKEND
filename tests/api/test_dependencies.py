"""Tests for API dependencies."""

from unittest.mock import MagicMock

import pytest

from api.dependencies import (
    get_chatbot_internal,
    set_chatbot,
    get_chatbot,
    get_chatbot_status,
    get_connection_manager,
    validate_message,
)
from api.services.connection_manager import ConnectionManager
from backend.chatbot import ChatBot


class TestGetChatbot:
    """Test suite for get_chatbot dependency."""

    def test_get_chatbot_raises_when_not_initialized(self):
        """Test that get_chatbot raises HTTPException when not initialized."""
        # Reset the chatbot to None first
        set_chatbot(None)

        with pytest.raises(Exception) as exc_info:
            get_chatbot()

        assert "ChatBot not initialized" in str(exc_info.value)

    def test_get_chatbot_returns_singleton(self):
        """Test that get_chatbot returns the same instance when initialized."""
        # Set up a mock chatbot
        mock_chatbot = MagicMock(spec=ChatBot)
        set_chatbot(mock_chatbot)

        chatbot1 = get_chatbot()
        chatbot2 = get_chatbot()
        assert chatbot1 is chatbot2

        # Clean up
        set_chatbot(None)


class TestGetConnectionManager:
    """Test suite for get_connection_manager dependency."""

    def test_get_connection_manager_returns_singleton(self):
        """Test that get_connection_manager returns the same instance."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()
        assert manager1 is manager2

    def test_get_connection_manager_returns_connection_manager_instance(self):
        """Test that get_connection_manager returns a ConnectionManager instance."""
        manager = get_connection_manager()
        assert isinstance(manager, ConnectionManager)


class TestGetChatbotStatus:
    """Test suite for get_chatbot_status dependency."""

    def test_get_chatbot_status_returns_dict(self):
        """Test that get_chatbot_status returns a dictionary."""
        status = get_chatbot_status()
        assert isinstance(status, dict)

    def test_get_chatbot_status_contains_required_fields(self):
        """Test that get_chatbot_status contains required fields."""
        status = get_chatbot_status()
        assert "status" in status

    def test_get_chatbot_status_not_initialized(self):
        """Test that get_chatbot_status returns not_initialized when chatbot is None."""
        # Reset the chatbot to None first
        set_chatbot(None)
        status = get_chatbot_status()
        assert status["status"] == "not_initialized"


class TestValidateMessage:
    """Test suite for validate_message function."""

    def test_validate_message_valid_message(self):
        """Test validating a valid message."""
        assert validate_message("Hello, world!") is True

    def test_validate_message_empty_string(self):
        """Test validating an empty string."""
        assert validate_message("") is False

    def test_validate_message_whitespace_only(self):
        """Test validating whitespace-only string."""
        assert validate_message("   ") is False

    def test_validate_message_none(self):
        """Test validating None."""
        # Type ignore because we're testing the function's behavior with None
        assert validate_message(None) is False  # type: ignore

    def test_validate_message_too_long(self):
        """Test validating a message that's too long."""
        long_message = "a" * 10001  # Over 10000 character limit
        assert validate_message(long_message) is False

    def test_validate_message_at_limit(self):
        """Test validating a message at the character limit."""
        limit_message = "a" * 10000  # Exactly 10000 characters
        assert validate_message(limit_message) is True


class TestInternalChatbotFunctions:
    """Test suite for internal chatbot functions."""

    def test_set_chatbot_and_get_chatbot_internal(self):
        """Test setting and getting chatbot internally."""
        mock_chatbot = MagicMock(spec=ChatBot)

        # Set the chatbot
        set_chatbot(mock_chatbot)

        # Get the chatbot
        retrieved_chatbot = get_chatbot_internal()

        assert retrieved_chatbot is mock_chatbot

    def test_get_chatbot_internal_returns_none_initially(self):
        """Test that get_chatbot_internal returns None initially."""
        # Reset the internal state
        set_chatbot(None)

        result = get_chatbot_internal()
        assert result is None
