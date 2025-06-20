import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

from .config import ServerConfig
from .session import MCPSession
from .conversation import ConversationManager


class ChatBot:
    """Main ChatBot class that orchestrates configuration, session, and conversation management."""
    
    def __init__(self):
        self.config = ServerConfig()
        self.mcp_session = MCPSession()
        self.conversation_manager = ConversationManager(self.mcp_session)
        self.logger = logging.getLogger(__name__)
        self._config_version: str = ""
        
        self.logger.info("ChatBot initialized (config will be loaded from server)")

    async def connect_to_server(self, python_path: str = None, script_path: str = None):
        """Connect to an MCP server and load configuration."""
        tools = await self.mcp_session.connect(python_path, script_path)
        
        # Load configuration from server
        await self.config.load_from_server(self.mcp_session.session)
        
        # Initialize system message from server config
        system_prompt = self.config.chatbot_config.get('system_prompt', 'You are a helpful assistant.')
        self.conversation_manager.set_system_message(system_prompt)
        
        return tools

    async def _update_config_if_changed(self):
        """Check if configuration version has changed and update if necessary."""
        if self.mcp_session.session is None:
            return
            
        try:
            # Lightweight version check
            result = await self.mcp_session.call_tool("get_config_version", arguments={})
            new_version = self._extract_tool_content(result).strip()
            
            # Only reload if version changed
            if not hasattr(self, '_config_version') or self._config_version != new_version:
                # Get full config only when needed
                result = await self.mcp_session.call_tool("get_config", arguments={})
                content_text = self._extract_tool_content(result)
                server_config = json.loads(content_text)
                
                # Update local config directly
                self.config.config = server_config
                
                # Update logging configuration if changed
                if 'logging' in server_config and server_config['logging']['enabled']:
                    log_level = getattr(logging, server_config['logging']['level'].upper())
                    logging.getLogger().setLevel(log_level)
                
                # Update system message if changed
                new_system_prompt = server_config.get("chatbot", {}).get("system_prompt", "")
                current_system_content = ""
                if (self.conversation_manager.conversation_history and 
                    self.conversation_manager.conversation_history[0]["role"] == "system"):
                    current_system_content = self.conversation_manager.conversation_history[0]["content"]
                
                if current_system_content != new_system_prompt:
                    self.conversation_manager.set_system_message(new_system_prompt)
                    self.logger.info(f"System prompt updated: {new_system_prompt[:50]}...")
                
                self._config_version = new_version
                self.logger.info(f"Configuration updated from server (version: {new_version})")
                        
        except Exception as e:
            self.logger.warning(f"Failed to check config version: {e}")

    async def process_message(self, user_message: str) -> AsyncGenerator[str, None]:
        """Process a user message maintaining conversation context."""
        # Check if any configuration has changed and update if necessary
        await self._update_config_if_changed()
        
        async for chunk in self.conversation_manager.process_message_streaming(user_message, self.config):
            yield chunk

    def _extract_tool_content(self, result) -> str:
        """Extract content from tool results."""
        content_text = ""
        if result.content:
            for content_item in result.content:
                if hasattr(content_item, 'type'):
                    if content_item.type == 'text' and hasattr(content_item, 'text'):
                        content_text += content_item.text
                    else:
                        content_text += f"[{content_item.type} content]"
                else:
                    content_text += str(content_item)
        return content_text

    async def cleanup(self):
        """Clean up resources."""
        if self.config.chatbot_config.get('clear_history_on_exit', False):
            self.conversation_manager.clear_history()
            self.logger.info("Conversation history cleared on exit")
        await self.mcp_session.cleanup() 