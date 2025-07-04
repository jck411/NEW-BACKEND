"""API application lifecycle events.

Handles startup and shutdown for backend API.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.dependencies import get_chatbot_internal, set_chatbot
from backend import ChatBot

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    # Startup
    logger.info("Starting ChatBot backend...")
    try:
        chatbot = ChatBot()
        await chatbot.connect_to_server()
        set_chatbot(chatbot)
        logger.info("ChatBot initialized successfully")
    except (RuntimeError, ValueError, AttributeError) as e:
        logger.error("ChatBot initialization error: %s", e)
        raise
    except (OSError, ConnectionError) as e:
        logger.error("Network error initializing ChatBot: %s", e)
        raise
    except Exception as e:
        logger.exception("Unexpected error initializing ChatBot: %s", e)
        raise

    yield

    # Shutdown
    logger.info("Shutting down ChatBot backend...")
    chatbot = get_chatbot_internal()
    if chatbot:
        await chatbot.cleanup()
    logger.info("ChatBot backend shutdown complete")
