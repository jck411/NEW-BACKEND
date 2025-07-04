"""Simple tests for chatbot module."""

from unittest.mock import AsyncMock

import pytest

from backend.chatbot import ChatBot


class TestChatBot:
    """Test suite for ChatBot class."""

    def test_chatbot_initialization(self):
        """Test ChatBot initialization."""
        chatbot = ChatBot()
        assert chatbot is not None
        assert hasattr(chatbot, "config")
        assert hasattr(chatbot, "conversation_manager")
        assert hasattr(chatbot, "mcp_session")

    def test_chatbot_get_current_server_info(self):
        """Test getting current server info."""
        chatbot = ChatBot()
        server_info = chatbot.get_current_server_info()
        assert server_info is not None
        assert isinstance(server_info, dict)

    def test_chatbot_has_mcp_session(self):
        """Test that chatbot has MCP session."""
        chatbot = ChatBot()
        # Should have an MCP session
        assert chatbot.mcp_session is not None
        assert chatbot.mcp_session.session is None  # Not connected initially

    @pytest.mark.asyncio
    async def test_chatbot_cleanup(self):
        """Test chatbot cleanup."""
        chatbot = ChatBot()

        # Mock the MCP session cleanup
        chatbot.mcp_session.cleanup = AsyncMock()

        await chatbot.cleanup()

        # Should call cleanup on MCP session
        chatbot.mcp_session.cleanup.assert_called_once()

    def test_chatbot_conversation_manager_exists(self):
        """Test that conversation manager exists."""
        chatbot = ChatBot()
        assert chatbot.conversation_manager is not None

    def test_chatbot_config_exists(self):
        """Test that config exists."""
        chatbot = ChatBot()
        assert chatbot.config is not None

    def test_chatbot_mcp_session_exists(self):
        """Test that MCP session exists."""
        chatbot = ChatBot()
        assert chatbot.mcp_session is not None
