"""Tests for MCP session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.exceptions import SessionNotInitializedError
from backend.session import MCPSession


class TestMCPSession:
    """Test suite for MCPSession class."""

    def test_mcp_session_initialization(self):
        """Test MCPSession initialization."""
        session = MCPSession()
        assert session.session is None
        assert session.server_info == {}
        assert session.logger is not None

    def test_get_server_info(self):
        """Test getting server info."""
        session = MCPSession()
        session.server_info = {"command": "test", "args": []}

        info = session.get_server_info()
        assert info["command"] == "test"
        assert info["args"] == []

    @pytest.mark.asyncio
    async def test_get_tools_for_openai_not_initialized(self):
        """Test getting tools when session is not initialized."""
        session = MCPSession()

        with pytest.raises(SessionNotInitializedError) as exc_info:
            await session.get_tools_for_openai()

        assert "Session is not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_not_initialized(self):
        """Test calling tool when session is not initialized."""
        session = MCPSession()

        with pytest.raises(SessionNotInitializedError) as exc_info:
            await session.call_tool("test_tool", {})

        assert "Session is not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test session cleanup."""
        session = MCPSession()
        session.server_info = {"command": "test", "full_command": ["test"]}

        # Mock the exit_stack
        session.exit_stack = AsyncMock()

        await session.cleanup()

        # Should call aclose on exit_stack
        session.exit_stack.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_exception(self):
        """Test session cleanup with exception."""
        session = MCPSession()
        session.server_info = {"command": "test", "full_command": ["test"]}

        # Mock the exit_stack to raise exception
        session.exit_stack = AsyncMock()
        session.exit_stack.aclose.side_effect = Exception("Test error")

        # Should not raise exception
        await session.cleanup()

    @pytest.mark.asyncio
    @patch("backend.session.stdio_client")
    @patch("backend.session.ClientSession")
    async def test_connect_with_string_command(
        self, mock_client_session, mock_stdio_client
    ):
        """Test connecting with string command."""
        session = MCPSession()

        # Mock the stdio client and session
        mock_transport = (MagicMock(), MagicMock())
        mock_stdio_client.return_value.__aenter__.return_value = mock_transport

        mock_session_instance = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session_instance.list_tools.return_value = mock_tools_result
        mock_client_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock exit_stack
        session.exit_stack = AsyncMock()
        session.exit_stack.enter_async_context = AsyncMock(
            side_effect=[mock_transport, mock_session_instance]
        )

        result = await session.connect("python test.py")

        assert session.server_info["command"] == "python"
        assert session.server_info["args"] == ["test.py"]
        assert result == mock_tools_result

    @pytest.mark.asyncio
    @patch("backend.session.stdio_client")
    @patch("backend.session.ClientSession")
    async def test_connect_with_list_command(
        self, mock_client_session, mock_stdio_client
    ):
        """Test connecting with list command."""
        session = MCPSession()

        # Mock the stdio client and session
        mock_transport = (MagicMock(), MagicMock())
        mock_stdio_client.return_value.__aenter__.return_value = mock_transport

        mock_session_instance = AsyncMock()
        mock_tools_result = MagicMock()
        mock_tools_result.tools = []
        mock_session_instance.list_tools.return_value = mock_tools_result
        mock_client_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock exit_stack
        session.exit_stack = AsyncMock()
        session.exit_stack.enter_async_context = AsyncMock(
            side_effect=[mock_transport, mock_session_instance]
        )

        result = await session.connect(["python", "test.py"])

        assert session.server_info["command"] == "python"
        assert session.server_info["args"] == ["test.py"]
        assert result == mock_tools_result
