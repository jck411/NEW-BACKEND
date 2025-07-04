#!/usr/bin/env uv run python
"""Startup script for the ChatBot FastAPI backend."""
import uvicorn

from api.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()


    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
