"""FastAPI ChatBot Backend - Main Application
Refactored following 2025 best practices with proper separation of concerns
"""
from fastapi import Depends, FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.config.logging import configure_structured_logging, get_logger
from api.config.settings import get_settings
from api.dependencies import get_connection_manager
from api.handlers.websocket_handlers import handle_test_websocket, handle_websocket_connection
from api.lifecycle import lifespan
from api.routers.health import router as health_router
from api.services.connection_manager import ConnectionManager

# Configure structured logging
settings = get_settings()
configure_structured_logging(
    level=settings.log_level,
    format_json=settings.log_format_json
)
logger = get_logger(__name__)

# Create FastAPI app with lifespan management
app = FastAPI(
    title="ChatBot Backend API",
    description="Frontend-agnostic ChatBot backend with WebSocket support",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)


@app.websocket("/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    """Simple test WebSocket endpoint"""
    await handle_test_websocket(websocket)


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Main WebSocket endpoint for chat functionality"""
    await handle_websocket_connection(websocket, connection_manager)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
