"""API dependency injection utilities.

Provides FastAPI dependencies for chatbot and connection manager.
"""

import logging
from typing import Any

from fastapi import HTTPException

from api.services.connection_manager import ConnectionManager
from backend import ChatBot

logger = logging.getLogger(__name__)

# Global services - will be initialized in lifespan
_chatbot: ChatBot | None = None
_connection_manager = ConnectionManager()


def get_chatbot() -> ChatBot:
    """Dependency provider for ChatBot instance."""
    if _chatbot is None:
        raise HTTPException(
            status_code=503,
            detail="ChatBot not initialized. Please restart the backend.",
        )
    return _chatbot


def get_connection_manager() -> ConnectionManager:
    """Dependency provider for ConnectionManager instance."""
    return _connection_manager


def get_chatbot_status() -> dict[str, Any]:
    """Get chatbot status for health checks."""
    if _chatbot is None:
        return {"status": "not_initialized"}

    return {
        "initialized": True,
        "mcp_connected": _chatbot.mcp_session.session is not None,
        "conversation_length": len(_chatbot.conversation_manager.conversation_history),
        "server_info": _chatbot.get_current_server_info(),
    }


def validate_message(message: str) -> bool:
    """Validate incoming message before processing."""
    if not message or not message.strip():
        return False
    if len(message) > 10000:  # Reasonable limit
        return False
    return True


# Functions for lifecycle management
def set_chatbot(chatbot: ChatBot | None) -> None:
    """Set chatbot instance during startup."""
    global _chatbot
    _chatbot = chatbot


def get_chatbot_internal() -> ChatBot | None:
    """Get chatbot instance (can be None)."""
    return _chatbot
