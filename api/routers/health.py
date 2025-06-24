"""
Health and configuration endpoints
Following 2025 best practices for API routing
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from backend import ChatBot
from api.dependencies import get_chatbot_status, get_chatbot
from api.services.connection_manager import ConnectionManager
from api.dependencies import get_connection_manager

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "ChatBot Backend API", "status": "running"}


@router.get("/health")
async def health_check(
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Detailed health check"""
    try:
        status = get_chatbot_status()
        is_ready = status.get("mcp_connected", False)
        
        return {
            "status": "healthy" if is_ready else "not_ready",
            "chatbot_ready": is_ready,
            "active_connections": connection_manager.get_connection_count(),
            "details": status
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/api/config")
async def get_config(chatbot: ChatBot = Depends(get_chatbot)):
    """Get current chatbot configuration"""
    try:
        config = {
            "chatbot": chatbot.config.chatbot_config,
            "openai": chatbot.config.openai_config,
            "logging": chatbot.config.logging_config,
            "server_info": chatbot.get_current_server_info()
        }
        return {"config": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 