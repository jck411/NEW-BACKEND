"""Backend settings configuration
"""

from pydantic_settings import BaseSettings

from backend.connection_config import ConnectionConfig


class Settings(BaseSettings):
    """Application settings"""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS settings
    allowed_origins: list[str] = [
        "http://localhost:3000",  # SvelteKit dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Allow all origins for now - restrict in production
    ]

    # WebSocket settings
    websocket_ping_interval: int = 30  # seconds
    websocket_ping_timeout: int = 10   # seconds
    max_connections: int = 100

    # Logging
    log_level: str = "INFO"
    log_format_json: bool = True

    # ChatBot specific settings
    chatbot_config_file: str = "backend/backend_config.yaml"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load client configuration to override defaults
        try:
            client_config = ConnectionConfig(self.chatbot_config_file)
            backend_config = client_config.get_backend_config()

            # Override with client config values if available
            if "host" in backend_config:
                self.host = backend_config["host"]
            if "port" in backend_config:
                self.port = backend_config["port"]
            if "max_connections" in backend_config:
                self.max_connections = backend_config["max_connections"]

        except Exception as e:
            # If client config fails to load, continue with defaults
            print(f"Warning: Could not load client config for backend settings: {e}")

    class Config:
        env_file = ".env"
        env_prefix = "CHATBOT_"
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
