"""ChatBot Backend Package.

A server-agnostic chatbot backend that connects to any compatible MCP server
and integrates with OpenAI for conversational AI capabilities.

This backend is designed to be 100% dependent on the MCP server for configuration,
but can work with any MCP server that implements the required configuration interface.
Server connections are managed through a clean configuration file system.

Main Components:
- ChatBot: Main orchestrating class (server-agnostic)
- ServerConfig: Configuration management (validates server compatibility)
- MCPSession: MCP server connection and tool management (any server location)
- ConversationManager: Message processing and conversation history
- ConnectionConfig: Server connection configuration management

Server Requirements:
Any MCP server used with this backend must implement:
- get_config: Return configuration as JSON
- get_config_version: Return config version for change detection

Optional server features that enhance functionality:
- update_config: Update configuration on server
- list_config_keys: List available configuration keys
- save_config: Save configuration to server
- load_config: Load configuration from server file

Quick Start:
    from backend import ChatBot

    bot = ChatBot()

    # Connect using server profiles from backend/backend_config.yaml
    await bot.connect_to_server(server_name="production")
    await bot.connect_to_server(server_name="development")

    # Connect with direct command (overrides config)
    await bot.connect_to_server(server_command=["python", "/path/to/server.py"])
    await bot.connect_to_server(server_command="node /path/to/server.js")

    # Connect to default server from config
    await bot.connect_to_server()

    # Process messages (100% configured from server)
    async for response in bot.process_message("Hello!"):
        print(response, end="")

Connection Configuration:
    Server connections are managed via backend/backend_config.yaml:

    default_server:
      command: ["python", "server.py"]
      description: "Default MCP server"

    servers:
      production:
        command: ["python", "/prod/config_server.py"]
        description: "Production configuration server"
      development:
        command: ["python", "/dev/config_server.py"]
        description: "Development configuration server"
      nodejs:
        command: ["node", "/path/to/server.js"]
        description: "Node.js configuration server"

Following 2025 best practices with clean architecture and proper exception handling
"""

from .chatbot import ChatBot
from .config import ServerConfig
from .connection_config import ConnectionConfig
from .conversation import ConversationManager

# Export exception hierarchy for easy access
from .exceptions import (
    # Base exception
    ChatBotBaseException,
    ChatBotUnavailableError,
    # Configuration errors
    ConfigurationError,
    ConfigurationLoadError,
    ConfigurationMissingError,
    ConfigurationValidationError,
    # Connection errors
    ConnectionError,
    ConversationError,
    DeepgramError,
    DeepgramSTTError,
    # External service errors
    ExternalServiceError,
    # Message processing errors
    MessageError,
    MessageProcessingError,
    MessageValidationError,
    OpenAIError,
    ResourceCleanupError,
    # Resource management errors
    ResourceError,
    ResourceExhaustionError,
    ResourceNotFoundError,
    ServerConnectionError,
    ServerIncompatibleError,
    # Session errors
    SessionError,
    SessionInvalidStateError,
    SessionNotInitializedError,
    STTConfigurationError,
    STTConnectionError,
    # STT errors
    STTError,
    STTInitializationError,
    STTServiceError,
    ToolExecutionError,
    WebSocketClientError,
    WebSocketConnectionError,
    # WebSocket errors
    WebSocketError,
    WebSocketMessageError,
    get_exception_for_domain,
    # Utility functions
    wrap_exception,
)
from .session import MCPSession

__all__ = [
    # Main classes
    "ChatBot",
    # Exception hierarchy
    "ChatBotBaseException",
    "ChatBotUnavailableError",
    "ConfigurationError",
    "ConfigurationLoadError",
    "ConfigurationMissingError",
    "ConfigurationValidationError",
    "ConnectionConfig",
    "ConnectionError",
    "ConversationError",
    "ConversationManager",
    "DeepgramError",
    "DeepgramSTTError",
    "ExternalServiceError",
    "MCPSession",
    "MessageError",
    "MessageProcessingError",
    "MessageValidationError",
    "OpenAIError",
    "ResourceCleanupError",
    "ResourceError",
    "ResourceExhaustionError",
    "ResourceNotFoundError",
    "STTConfigurationError",
    "STTConnectionError",
    "STTError",
    "STTInitializationError",
    "STTServiceError",
    "ServerConfig",
    "ServerConnectionError",
    "ServerIncompatibleError",
    "SessionError",
    "SessionInvalidStateError",
    "SessionNotInitializedError",
    "ToolExecutionError",
    "WebSocketClientError",
    "WebSocketConnectionError",
    "WebSocketError",
    "WebSocketMessageError",
    "get_exception_for_domain",
    "wrap_exception",
]

__version__ = "1.0.0"
