"""WebSocket message handlers for backend API.

Implements message routing and streaming for chat frontends.
"""

import json
import logging
import uuid
from typing import Any

from fastapi import Depends, WebSocket, WebSocketDisconnect
from openai import OpenAIError
from websockets.exceptions import ConnectionClosed, WebSocketException

from api.dependencies import get_chatbot, get_connection_manager, validate_message
from api.services.connection_manager import ConnectionManager
from backend.exceptions import (
    ChatBotUnavailableError,
    ConversationError,
    MessageProcessingError,
    MessageValidationError,
    SessionError,
    WebSocketError,
    WebSocketMessageError,
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

            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON from client %s: %s", client_id, e)
                await send_error_message(websocket, "Invalid JSON format")
            except (MessageValidationError, WebSocketError) as e:
                logger.warning("WebSocket message error for %s: %s", client_id, e)
                await send_error_message(websocket, str(e))
            except (ConnectionClosed, WebSocketException) as e:
                logger.info("WebSocket connection issue for %s: %s", client_id, e)
                break  # Exit the loop to handle cleanup
            except (OSError, ConnectionError) as e:
                logger.error("Network error for client %s: %s", client_id, e)
                wrapped_error = wrap_exception(
                    e,
                    WebSocketError,
                    "Network connection error",
                    error_code="NETWORK_ERROR",
                    context={"client_id": client_id},
                )
                await send_error_message(websocket, str(wrapped_error))
                break
            except Exception as e:
                logger.exception("Unexpected error handling message from %s", client_id)
                wrapped_error = wrap_exception(
                    e,
                    WebSocketError,
                    "Internal server error",
                    error_code="INTERNAL_ERROR",
                    context={"client_id": client_id},
                )
                await send_error_message(websocket, str(wrapped_error))

    except WebSocketDisconnect:
        logger.info("Client %s disconnected", client_id)
    except (ConnectionClosed, WebSocketException) as e:
        logger.info("WebSocket connection closed for %s: %s", client_id, e)
    except (OSError, ConnectionError) as e:
        logger.error("Network error for client %s: %s", client_id, e)
        wrapped_error = wrap_exception(
            e,
            WebSocketError,
            "WebSocket network error",
            error_code="NETWORK_ERROR",
            context={"client_id": client_id},
        )
        logger.error("Network error details: %s", wrapped_error.to_dict())
    except Exception as e:
        logger.exception("Unexpected WebSocket error for client %s", client_id)
        wrapped_error = wrap_exception(
            e,
            WebSocketError,
            "WebSocket connection error",
            error_code="CONNECTION_ERROR",
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
        raise MessageValidationError(msg, error_code="INVALID_MESSAGE")

    # Get chatbot instance
    try:
        chatbot = get_chatbot()
    except (RuntimeError, ValueError, AttributeError) as e:
        msg = "ChatBot is not available"
        raise ChatBotUnavailableError(
            msg, error_code="CHATBOT_UNAVAILABLE", cause=e
        ) from e

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

    except OpenAIError as e:
        logger.error("OpenAI API error for %s: %s", client_id, e)
        error_msg = "AI service temporarily unavailable"
        await send_error_message(websocket, error_msg, message_id)
    except (ConnectionClosed, WebSocketException) as e:
        logger.info(
            "WebSocket disconnected during message processing for %s", client_id
        )
        # Don't try to send error message if connection is closed
        raise
    except SessionError as e:
        logger.warning("Session error for %s: %s", client_id, e)
        await send_error_message(websocket, f"Session error: {e!s}", message_id)
    except ConversationError as e:
        logger.warning("Conversation error for %s: %s", client_id, e)
        await send_error_message(websocket, f"Conversation error: {e!s}", message_id)
    except (OSError, ConnectionError) as e:
        logger.error("Network error during message processing for %s: %s", client_id, e)
        wrapped_error = wrap_exception(
            e,
            MessageProcessingError,
            "Network error during message processing",
            error_code="NETWORK_ERROR",
            context={"client_id": client_id, "message_id": message_id},
        )
        await send_error_message(websocket, str(wrapped_error), message_id)
    except Exception as e:
        logger.exception("Unexpected error processing message for %s: %s", client_id, e)
        wrapped_error = wrap_exception(
            e,
            MessageProcessingError,
            "Unexpected error processing message",
            error_code="PROCESSING_ERROR",
            context={"client_id": client_id, "message_id": message_id},
        )
        await send_error_message(websocket, str(wrapped_error), message_id)


async def handle_get_history(
    websocket: WebSocket, client_id: str, message: dict[str, Any]
) -> None:
    """Get conversation history."""
    try:
        chatbot = get_chatbot()
        history = chatbot.conversation_manager.conversation_history.copy()
        await websocket.send_text(json.dumps({"type": "history", "data": history}))
    except (RuntimeError, ValueError, AttributeError) as e:
        logger.warning(
            "ChatBot unavailable for history request from %s: %s", client_id, e
        )
        await send_error_message(websocket, "ChatBot service unavailable")
    except ConversationError as e:
        logger.warning("Conversation error getting history for %s: %s", client_id, e)
        await send_error_message(websocket, f"Failed to get history: {e!s}")
    except (ConnectionClosed, WebSocketException) as e:
        logger.info("WebSocket disconnected during history request for %s", client_id)
        raise
    except Exception as e:
        logger.exception("Unexpected error getting history for %s: %s", client_id, e)
        wrapped_error = wrap_exception(
            e,
            WebSocketMessageError,
            "Failed to get conversation history",
            error_code="HISTORY_ERROR",
            context={"client_id": client_id},
        )
        await send_error_message(websocket, str(wrapped_error))


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
    except (RuntimeError, ValueError, AttributeError) as e:
        logger.warning(
            "ChatBot unavailable for clear history from %s: %s", client_id, e
        )
        await send_error_message(websocket, "ChatBot service unavailable")
    except ConversationError as e:
        logger.warning("Conversation error clearing history for %s: %s", client_id, e)
        await send_error_message(websocket, f"Failed to clear history: {e!s}")
    except (ConnectionClosed, WebSocketException) as e:
        logger.info("WebSocket disconnected during clear history for %s", client_id)
        raise
    except Exception as e:
        logger.exception("Unexpected error clearing history for %s: %s", client_id, e)
        wrapped_error = wrap_exception(
            e,
            WebSocketMessageError,
            "Failed to clear conversation history",
            error_code="CLEAR_HISTORY_ERROR",
            context={"client_id": client_id},
        )
        await send_error_message(websocket, str(wrapped_error))


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
    except (RuntimeError, ValueError, AttributeError) as e:
        logger.warning(
            "ChatBot unavailable for config request from %s: %s", client_id, e
        )
        await send_error_message(websocket, "ChatBot service unavailable")
    except (ConnectionClosed, WebSocketException) as e:
        logger.info("WebSocket disconnected during config request for %s", client_id)
        raise
    except Exception as e:
        logger.exception("Unexpected error getting config for %s: %s", client_id, e)
        wrapped_error = wrap_exception(
            e,
            WebSocketMessageError,
            "Failed to get configuration",
            error_code="CONFIG_ERROR",
            context={"client_id": client_id},
        )
        await send_error_message(websocket, str(wrapped_error))


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
            try:
                message = json.loads(data)
                echo_response = {
                    "type": "echo",
                    "original_message": message,
                    "timestamp": str(uuid.uuid4()),
                }
                await websocket.send_text(json.dumps(echo_response))
            except json.JSONDecodeError as e:
                logger.warning(
                    "Invalid JSON in test WebSocket from %s: %s", client_id, e
                )
                await websocket.send_text(
                    json.dumps({"type": "error", "error": "Invalid JSON format"})
                )
            except (ConnectionClosed, WebSocketException) as e:
                logger.info("Test WebSocket connection closed for %s: %s", client_id, e)
                break
            except (OSError, ConnectionError) as e:
                logger.error("Network error in test WebSocket for %s: %s", client_id, e)
                break

    except WebSocketDisconnect:
        logger.info("Test client %s disconnected", client_id)
    except (ConnectionClosed, WebSocketException) as e:
        logger.info("Test WebSocket connection closed for %s: %s", client_id, e)
    except (OSError, ConnectionError) as e:
        logger.error("Network error in test WebSocket for %s: %s", client_id, e)
    except Exception as e:
        logger.exception(
            "Unexpected test WebSocket error for client %s: %s", client_id, e
        )
        wrapped_error = wrap_exception(
            e,
            WebSocketError,
            "Test WebSocket error",
            error_code="TEST_ERROR",
            context={"client_id": client_id},
        )
        logger.exception("Test WebSocket error details: %s", wrapped_error.to_dict())
