"""
MCP ChatBot Client Package

A server-agnostic chatbot client that connects to any compatible MCP server 
and integrates with OpenAI for conversational AI capabilities.

This client is designed to be 100% dependent on the MCP server for configuration,
but can work with any MCP server that implements the required configuration interface.
Server connections are managed through a clean configuration file system.

Main Components:
- ChatBot: Main orchestrating class (server-agnostic)
- ServerConfig: Configuration management (validates server compatibility)
- MCPSession: MCP server connection and tool management (any server location)
- ConversationManager: Message processing and conversation history
- ConnectionConfig: Server connection configuration management

Server Requirements:
Any MCP server used with this client must implement:
- get_config: Return configuration as JSON
- get_config_version: Return config version for change detection

Optional server features that enhance functionality:
- update_config: Update configuration on server
- list_config_keys: List available configuration keys  
- save_config: Save configuration to server
- load_config: Load configuration from server file

Quick Start:
    from client import ChatBot
    
    bot = ChatBot()
    
    # Connect using server profiles from client/client_config.yaml
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
    Server connections are managed via client/client_config.yaml:
    
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
"""

from .chatbot import ChatBot
from .config import ServerConfig
from .session import MCPSession
from .conversation import ConversationManager
from .connection_config import ConnectionConfig
from .cli import main

__all__ = [
    'ChatBot',
    'ServerConfig', 
    'MCPSession',
    'ConversationManager',
    'ConnectionConfig',
    'main'
]

__version__ = '1.0.0' 