"""
WebSocket message handlers
Following 2025 best practices for WebSocket handling with proper error handling
"""
import json
import logging
import uuid
from typing import Dict, Any

from fastapi import WebSocket, WebSocketDisconnect, Depends
from backend import ChatBot
from backend.exceptions import (
    WebSocketError, 
    MessageValidationError, 
    ChatBotUnavailableError,
    wrap_exception
)
from api.services.connection_manager import ConnectionManager
from api.dependencies import get_chatbot, get_connection_manager, validate_message

logger = logging.getLogger(__name__)


async def handle_websocket_connection(
    websocket: WebSocket, 
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Main WebSocket connection handler"""
    client_id = await connection_manager.connect(websocket)
    logger.info(f"Client {client_id} connected")
    
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
                logger.error(f"Unexpected error handling message from {client_id}: {e}")
                wrapped_error = wrap_exception(e, WebSocketError, "Internal server error", 
                                             context={"client_id": client_id})
                await send_error_message(websocket, str(wrapped_error))
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        wrapped_error = wrap_exception(e, WebSocketError, "WebSocket connection error", 
                                     context={"client_id": client_id})
        logger.error(f"Wrapped error details: {wrapped_error.to_dict()}")
    finally:
        connection_manager.disconnect(client_id)


async def handle_websocket_message(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """Route WebSocket messages to appropriate handlers"""
    message_type = message.get("type")
    
    handlers = {
        "text_message": handle_text_message,
        "get_history": handle_get_history,
        "clear_history": handle_clear_history,
        "get_config": handle_get_config,
        "ping": handle_ping,
    }
    
    handler = handlers.get(message_type)
    if handler:
        await handler(websocket, client_id, message)
    else:
        await send_error_message(websocket, f"Unknown message type: {message_type}")


async def handle_text_message(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """Handle text message with streaming response"""
    user_message = message.get("content", "")
    message_id = message.get("id", "")
    
    # Validate message
    if not validate_message(user_message):
        raise MessageValidationError("Invalid message content")
    
    # Get chatbot instance
    try:
        chatbot = get_chatbot()
    except Exception:
        raise ChatBotUnavailableError("ChatBot is not available")
    
    try:
        # Send acknowledgment
        await websocket.send_text(json.dumps({
            "type": "message_start",
            "id": message_id,
            "user_message": user_message
        }))
        
        # Stream response chunks
        full_response = ""
        async for chunk in chatbot.process_message(user_message):
            full_response += chunk
            
            await websocket.send_text(json.dumps({
                "type": "text_chunk",
                "id": message_id,
                "content": chunk
            }))
        
        # Send completion signal
        await websocket.send_text(json.dumps({
            "type": "message_complete",
            "id": message_id,
            "full_content": full_response
        }))
        
    except Exception as e:
        logger.error(f"Error processing message for {client_id}: {e}")
        await send_error_message(websocket, str(e), message_id)


async def handle_get_history(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """Get conversation history"""
    try:
        chatbot = get_chatbot()
        history = chatbot.conversation_manager.conversation_history.copy()
        await websocket.send_text(json.dumps({
            "type": "history",
            "data": history
        }))
    except Exception as e:
        logger.error(f"Error getting history for {client_id}: {e}")
        await send_error_message(websocket, f"Failed to get history: {str(e)}")


async def handle_clear_history(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """Clear conversation history"""
    try:
        chatbot = get_chatbot()
        chatbot.conversation_manager.clear_history()
        
        # Re-set system message if available
        system_prompt = chatbot.config.chatbot_config.get('system_prompt', '')
        if system_prompt:
            chatbot.conversation_manager.set_system_message(system_prompt)
            
        await websocket.send_text(json.dumps({
            "type": "history_cleared"
        }))
    except Exception as e:
        logger.error(f"Error clearing history for {client_id}: {e}")
        await send_error_message(websocket, f"Failed to clear history: {str(e)}")


async def handle_get_config(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """Get current configuration"""
    try:
        chatbot = get_chatbot()
        config = {
            "chatbot": chatbot.config.chatbot_config,
            "openai": chatbot.config.openai_config,
            "logging": chatbot.config.logging_config,
            "server_info": chatbot.get_current_server_info()
        }
        await websocket.send_text(json.dumps({
            "type": "config",
            "data": config
        }))
    except Exception as e:
        logger.error(f"Error getting config for {client_id}: {e}")
        await send_error_message(websocket, f"Failed to get config: {str(e)}")


async def handle_ping(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
    """Handle ping message"""
    await websocket.send_text(json.dumps({"type": "pong"}))


async def send_error_message(websocket: WebSocket, error: str, message_id: str = None):
    """Send error message to client"""
    error_data = {
        "type": "error",
        "error": error
    }
    if message_id:
        error_data["id"] = message_id
    
    await websocket.send_text(json.dumps(error_data))


async def handle_test_websocket(websocket: WebSocket):
    """Simple test WebSocket endpoint for development/debugging"""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    logger.info(f"Test client {client_id} connected")
    
    try:
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "client_id": client_id,
            "message": "Test WebSocket connection successful!"
        }))
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            else:
                await websocket.send_text(json.dumps({
                    "type": "echo",
                    "message": f"Test echo: {message.get('content', 'No content')}"
                }))
                
    except WebSocketDisconnect:
        logger.info(f"Test client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Test WebSocket error for client {client_id}: {e}") 