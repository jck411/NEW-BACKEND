"""
MCP ChatBot Client Package

A modular chatbot client that connects to MCP servers and integrates with OpenAI 
for conversational AI capabilities.

Main Components:
- ChatBot: Main orchestrating class
- ServerConfig: Configuration management
- MCPSession: MCP server connection and tool management  
- ConversationManager: Message processing and conversation history

Quick Start:
    from client import ChatBot
    
    bot = ChatBot()
    await bot.connect_to_server()
    
    async for response in bot.process_message("Hello!"):
        print(response, end="")
"""

from .chatbot import ChatBot
from .config import ServerConfig
from .session import MCPSession
from .conversation import ConversationManager
from .cli import main

__all__ = [
    'ChatBot',
    'ServerConfig', 
    'MCPSession',
    'ConversationManager',
    'main'
]

__version__ = '1.0.0' 