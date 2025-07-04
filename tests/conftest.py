"""Pytest configuration and shared fixtures."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_chatbot():
    """Mock ChatBot instance for testing."""
    mock = MagicMock()
    mock.connect_to_server = AsyncMock()
    mock.process_message = AsyncMock()
    mock.cleanup = AsyncMock()
    mock.get_server_requirements = MagicMock(return_value={})
    mock.get_current_server_info = MagicMock(return_value={})
    return mock


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager for WebSocket testing."""
    mock = MagicMock()
    mock.connect = AsyncMock(return_value="test-client-id")
    mock.disconnect = MagicMock()
    mock.send_personal_message = AsyncMock()
    mock.broadcast = AsyncMock()
    return mock


@pytest.fixture
def sample_websocket_message():
    """Sample WebSocket message for testing."""
    return {
        "type": "text",
        "message": "Hello, how can you help me?",
        "message_id": "test-msg-123",
    }
