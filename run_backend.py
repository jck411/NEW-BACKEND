#!/usr/bin/env uv run python
"""
Startup script for the ChatBot FastAPI backend
"""
import uvicorn
from api.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"🚀 Starting ChatBot Backend API")
    print(f"   Host: {settings.host}")
    print(f"   Port: {settings.port}")
    print(f"   Debug: {settings.debug}")
    print(f"   WebSocket endpoint: ws://{settings.host}:{settings.port}/ws/chat")
    print(f"   Health check: http://{settings.host}:{settings.port}/health")
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 