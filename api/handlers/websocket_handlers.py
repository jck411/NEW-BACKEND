"""WebSocket message handlers for backend API.

Implements message routing and streaming for chat frontends.
"""

import json
import logging
import uuid
from typing import Any

from fastapi import Depends, WebSocket, WebSocketDisconnect

from api.dependencies import get_chatbot, get_connection_manager, validate_message
from api.services.connection_manager import ConnectionManager
from backend.exceptions import (
    ChatBotUnavailableError,
    MessageValidationError,
    WebSocketError,
    wrap_exception,
)

logger = logging.getLogger(__name__)


async def handle_websocket_connection(
    websocket: WebSocket,
    connection_manager: ConnectionManager = Depends(get_connection_manager),
) -> None:
    """Main WebSocket connection handler."""
    client_id = await connection_manager.connect(websocket)
    logger.info("Client %s connected", client_id)

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, client_id, message)

            except json.JSONDecodeError:
                await send_error_message(websocket, "Invalid JSON format")
            except WebSocketError as e:
                await send_error_message(websocket, str(e))
            except Exception as e:
                logger.exception("Unexpected error handling message from %s", client_id)
                wrapped_error = wrap_exception(
                    e,
                    WebSocketError,
                    "Internal server error",
                    context={"client_id": client_id},
                )
                await send_error_message(websocket, str(wrapped_error))

    except WebSocketDisconnect:
        logger.info("Client %s disconnected", client_id)
    except Exception as e:
        logger.exception("WebSocket error for client %s", client_id)
        wrapped_error = wrap_exception(
            e,
            WebSocketError,
            "WebSocket connection error",
            context={"client_id": client_id},
        )
        logger.exception("Wrapped error details: %s", wrapped_error.to_dict())
    finally:
        connection_manager.disconnect(client_id)


async def handle_websocket_message(
    websocket: WebSocket,
    client_id: str,
    message: dict[str, Any],
) -> None:
    """Route WebSocket messages to appropriate handlers."""
    message_type = message.get("type")

    handlers = {
        "text_message": handle_text_message,
        "get_history": handle_get_history,
        "clear_history": handle_clear_history,
        "get_config": handle_get_config,
        "ping": handle_ping,
    }

    handler = handlers.get(message_type) if message_type else None
    if handler:
        await handler(websocket, client_id, message)
    else:
        await send_error_message(websocket, f"Unknown message type: {message_type}")


async def handle_text_message(
    websocket: WebSocket,
    client_id: str,
    message: dict[str, Any],
) -> None:
    """Handle text message with streaming response."""
    user_message = message.get("content", "")
    message_id = message.get("id", "")

    # Validate message
    if not validate_message(user_message):
        msg = "Invalid message content"
        raise MessageValidationError(msg)

    # Get chatbot instance
    try:
        chatbot = get_chatbot()
    except (RuntimeError, ValueError, AttributeError):
        msg = "ChatBot is not available"
        raise ChatBotUnavailableError(msg)

    try:
        # Send acknowledgment
        await websocket.send_text(
            json.dumps(
                {
                    "type": "message_start",
                    "id": message_id,
                    "user_message": user_message,
                }
            )
        )

        # Stream response chunks
        full_response = ""
        async for chunk in chatbot.process_message(user_message):
            full_response += chunk

            await websocket.send_text(
                json.dumps({"type": "text_chunk", "id": message_id, "content": chunk})
            )

        # Send completion signal
        await websocket.send_text(
            json.dumps(
                {
                    "type": "message_complete",
                    "id": message_id,
                    "full_content": full_response,
                }
            )
        )

    except Exception as e:
        logger.exception("Error processing message for %s: %s", client_id, e)
        await send_error_message(websocket, str(e), message_id)


async def handle_get_history(
    websocket: WebSocket, client_id: str, message: dict[str, Any]
) -> None:
    """Get conversation history."""
    try:
        chatbot = get_chatbot()
        history = chatbot.conversation_manager.conversation_history.copy()
        await websocket.send_text(json.dumps({"type": "history", "data": history}))
    except Exception as e:
        logger.exception("Error getting history for %s: %s", client_id, e)
        await send_error_message(websocket, f"Failed to get history: {e!s}")


async def handle_clear_history(
    websocket: WebSocket,
    client_id: str,
    message: dict[str, Any],
) -> None:
    """Clear conversation history."""
    try:
        chatbot = get_chatbot()
        chatbot.conversation_manager.clear_history()

        # Re-set system message if available
        system_prompt = chatbot.config.chatbot_config.get("system_prompt", "")
        if system_prompt:
            chatbot.conversation_manager.set_system_message(system_prompt)

        await websocket.send_text(json.dumps({"type": "history_cleared"}))
    except Exception as e:
        logger.exception("Error clearing history for %s: %s", client_id, e)
        await send_error_message(websocket, f"Failed to clear history: {e!s}")


async def handle_get_config(
    websocket: WebSocket, client_id: str, message: dict[str, Any]
) -> None:
    """Get current configuration."""
    try:
        chatbot = get_chatbot()
        config = {
            "chatbot": chatbot.config.chatbot_config,
            "openai": chatbot.config.openai_config,
            "logging": chatbot.config.logging_config,
            "server_info": chatbot.get_current_server_info(),
        }
        await websocket.send_text(json.dumps({"type": "config", "data": config}))
    except Exception as e:
        logger.exception("Error getting config for %s: %s", client_id, e)
        await send_error_message(websocket, f"Failed to get config: {e!s}")


async def handle_ping(
    websocket: WebSocket, client_id: str, message: dict[str, Any]
) -> None:
    """Handle ping message."""
    await websocket.send_text(json.dumps({"type": "pong"}))


async def send_error_message(
    websocket: WebSocket,
    error: str,
    message_id: str | None = None,
) -> None:
    """Send error message to client."""
    error_data = {"type": "error", "error": error}
    if message_id:
        error_data["id"] = message_id

    await websocket.send_text(json.dumps(error_data))


async def handle_test_websocket(websocket: WebSocket) -> None:
    """Simple test WebSocket endpoint for development/debugging."""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    logger.info("Test client %s connected", client_id)

    try:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "client_id": client_id,
                    "message": "Test WebSocket connection successful!",
                }
            )
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "echo",
                            "message": f"Test echo: {message.get('content', 'No content')}",
                        }
                    )
                )

    except WebSocketDisconnect:
        logger.info("Test client %s disconnected", client_id)
    except Exception as e:
        logger.exception("Test WebSocket error for client %s: %s", client_id, e)
