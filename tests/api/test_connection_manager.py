"""Tests for ConnectionManager service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.connection_manager import ConnectionManager


class TestConnectionManager:
    """Test suite for ConnectionManager."""

    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = MagicMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_connect_websocket(self, connection_manager, mock_websocket):
        """Test connecting a WebSocket."""
        client_id = await connection_manager.connect(mock_websocket)

        # Verify WebSocket was accepted
        mock_websocket.accept.assert_called_once()

        # Verify client was added
        assert client_id in connection_manager.active_connections
        assert connection_manager.get_connection_count() == 1
        assert client_id in connection_manager.get_client_ids()

    def test_disconnect_client(self, connection_manager):
        """Test disconnecting a client."""
        # Add a mock connection
        client_id = "test-client-id"
        mock_websocket = MagicMock()
        connection_manager.active_connections[client_id] = mock_websocket

        # Disconnect
        connection_manager.disconnect(client_id)

        # Verify client was removed
        assert client_id not in connection_manager.active_connections
        assert connection_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal_message_success(self, connection_manager, mock_websocket):
        """Test sending a personal message successfully."""
        client_id = "test-client-id"
        connection_manager.active_connections[client_id] = mock_websocket

        await connection_manager.send_personal_message("Hello", client_id)

        mock_websocket.send_text.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_send_personal_message_removes_broken_connection(self, connection_manager):
        """Test that broken connections are removed when sending fails."""
        client_id = "test-client-id"
        mock_websocket = MagicMock()
        mock_websocket.send_text = AsyncMock(side_effect=Exception("Connection broken"))
        connection_manager.active_connections[client_id] = mock_websocket

        await connection_manager.send_personal_message("Hello", client_id)

        # Connection should be removed after failure
        assert client_id not in connection_manager.active_connections

    def test_is_connected(self, connection_manager):
        """Test checking if a client is connected."""
        client_id = "test-client-id"

        # Initially not connected
        assert not connection_manager.is_connected(client_id)

        # Add connection
        connection_manager.active_connections[client_id] = MagicMock()

        # Now connected
        assert connection_manager.is_connected(client_id)
