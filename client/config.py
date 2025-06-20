import json
import logging
from typing import Any, Dict


class ServerConfig:
    """Configuration manager that gets all config from the MCP server."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Setup basic logging (will be updated from server config later)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def load_from_server(self, session):
        """Load configuration from the MCP server."""
        try:
            result = await session.call_tool("get_config", arguments={})
            content_text = self._extract_tool_content(result)
            self.config = json.loads(content_text)
            
            # Update logging configuration
            if 'logging' in self.config and self.config['logging']['enabled']:
                log_level = getattr(logging, self.config['logging']['level'].upper())
                logging.getLogger().setLevel(log_level)
            
            self.logger.info("Configuration loaded from server")
        except Exception as e:
            self.logger.error(f"Failed to load config from server: {e}")
            raise
    
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

    @property
    def openai_config(self) -> Dict[str, Any]:
        return self.config.get('openai', {})
    
    @property
    def server_config(self) -> Dict[str, Any]:
        return self.config.get('server', {})
    
    @property
    def chatbot_config(self) -> Dict[str, Any]:
        return self.config.get('chatbot', {}) 