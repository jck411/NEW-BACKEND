"""
Application lifecycle management
Handles startup and shutdown of ChatBot backend services
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from backend import ChatBot
from api.dependencies import _set_chatbot, _get_chatbot_internal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources"""
    # Startup
    logger.info("Starting ChatBot backend...")
    try:
        chatbot = ChatBot()
        await chatbot.connect_to_server()
        _set_chatbot(chatbot)
        logger.info("ChatBot initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ChatBot: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ChatBot backend...")
    chatbot = _get_chatbot_internal()
    if chatbot:
        await chatbot.cleanup()
    logger.info("ChatBot backend shutdown complete") 