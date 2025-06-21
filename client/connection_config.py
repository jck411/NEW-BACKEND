import os
import yaml
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class ConnectionConfig:
    """Manages client connection configuration for MCP servers."""
    
    def __init__(self, config_file: str = "client/client_config.yaml"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.load_config()
    
    def load_config(self):
        """Load connection configuration from file."""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            self.logger.error(f"Configuration file not found at {self.config_file}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            self.logger.info(f"Loaded connection config from {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load connection config: {e}")
            raise
    
    def get_server_command(self) -> List[str]:
        """
        Get server command for connection.
        
        Returns:
            Server command as list
            
        Raises:
            ValueError: If server_path is not configured
        """
        server_path = self.config.get('server_path')
        if not server_path:
            raise ValueError(
                f"No server_path configured in {self.config_file}. "
                "Please set server_path to the path of your MCP server."
            )
        
        return ["python3", server_path]
    
    def get_server_path(self) -> str:
        """Get the configured server path."""
        server_path = self.config.get('server_path')
        if not server_path:
            raise ValueError(
                f"No server_path configured in {self.config_file}. "
                "Please set server_path to the path of your MCP server."
            )
        return server_path
    
    def set_server_path(self, path: str):
        """Set the server path and save configuration."""
        self.config['server_path'] = path
        self.save_config()
        self.logger.info(f"Updated server path to: {path}")
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Ensure the directory exists
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Saved connection config to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save connection config: {e}")
            raise
    
    def get_config_file_path(self) -> str:
        """Get the path to the configuration file."""
        return str(Path(self.config_file).absolute()) 