import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("config_aware_server")

# Global configuration storage - will be loaded from server's own config file
_config = {}

@mcp.tool()
def get_config(section: Optional[str] = None) -> str:
    """Get current configuration. If section is provided, returns only that section."""
    if section:
        if section in _config:
            return json.dumps({section: _config[section]}, indent=2)
        else:
            return f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"
    return json.dumps(_config, indent=2)

@mcp.tool()
def update_config(section: str, key: str, value: str) -> str:
    """Update a configuration value. Value will be parsed as JSON if possible."""
    if section not in _config:
        return f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"
    
    if key not in _config[section]:
        return f"Configuration key '{key}' not found in section '{section}'. Available keys: {list(_config[section].keys())}"
    
    # Try to parse the value as JSON for proper type conversion
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        # If not valid JSON, treat as string
        parsed_value = value
    
    old_value = _config[section][key]
    _config[section][key] = parsed_value
    
    # Auto-save the configuration to maintain persistence
    try:
        with open("server_config.yaml", 'w') as f:
            yaml.dump(_config, f, default_flow_style=False, indent=2)
        save_status = " (saved to server config)"
    except Exception as e:
        save_status = f" (warning: could not save to file - {str(e)})"
    
    return f"Updated {section}.{key} from '{old_value}' to '{parsed_value}'{save_status}"

@mcp.tool()
def save_config(filepath: str = "server_config.yaml") -> str:
    """Save current configuration to a YAML file."""
    try:
        with open(filepath, 'w') as f:
            yaml.dump(_config, f, default_flow_style=False, indent=2)
        return f"Configuration saved to {filepath}"
    except Exception as e:
        return f"Error saving configuration: {str(e)}"

@mcp.tool()
def load_config(filepath: str = "server_config.yaml") -> str:
    """Load configuration from a YAML file."""
    global _config
    try:
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    _config = loaded_config
                    return f"Configuration loaded from {filepath}"
                else:
                    return f"Configuration file {filepath} is empty or invalid"
        else:
            return f"Configuration file {filepath} not found"
    except Exception as e:
        return f"Error loading configuration: {str(e)}"

@mcp.tool()
def reset_config() -> str:
    """Reset configuration to default values."""
    global _config
    _config = {
        "openai": {
            "model": "gpt-4o-mini",
            "temperature": 0.8,
            "top_p": 1.0,
            "max_tokens": 2000,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        },
        "chatbot": {
            "system_prompt": "You are a sarcastic AI agent and you like to rhyme",
            "max_conversation_history": 100,
            "clear_history_on_exit": True,
            "stream_responses": True
        },
        "logging": {
            "enabled": True,
            "level": "INFO",
            "log_file": "chatbot.log"
        }
    }
    return "Configuration reset to default values"

@mcp.tool()
def list_config_keys(section: Optional[str] = None) -> str:
    """List all configuration keys. If section is provided, lists keys in that section only."""
    if section:
        if section in _config:
            keys = list(_config[section].keys())
            return f"Keys in section '{section}': {keys}"
        else:
            return f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"
    
    result = {}
    for section_name, section_data in _config.items():
        result[section_name] = list(section_data.keys())
    
    return json.dumps(result, indent=2)

@mcp.tool()
def get_time() -> str:
    """Get the current time"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Current time: {current_time}"

@mcp.tool()
def echo(message: str) -> str:
    """Echo back the input message"""
    return f"Echo: {message}"

@mcp.tool()
def calculate(operation: str, a: float, b: float) -> str:
    """Perform basic arithmetic"""
    try:
        result = None
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            result = a / b
        else:
            return f"Unknown operation: {operation}"

        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Load configuration from server's own config file
    config_file = "server_config.yaml"
    if Path(config_file).exists():
        try:
            with open(config_file, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    _config = loaded_config
                    print(f"Loaded server configuration from {config_file}")
                else:
                    print(f"Warning: Configuration file {config_file} is empty, using defaults")
                    # Set default configuration
                    _config = {
                        "openai": {
                            "model": "gpt-4o-mini",
                            "temperature": 0.8,
                            "top_p": 1.0,
                            "max_tokens": 2000,
                            "presence_penalty": 0.0,
                            "frequency_penalty": 0.0
                        },
                        "chatbot": {
                            "system_prompt": "You are a sarcastic AI agent and you like to rhyme",
                            "max_conversation_history": 100,
                            "clear_history_on_exit": True,
                            "stream_responses": True
                        },
                        "logging": {
                            "enabled": True,
                            "level": "INFO",
                            "log_file": "chatbot.log"
                        }
                    }
        except Exception as e:
            print(f"Warning: Could not load configuration from {config_file}: {e}")
            print("Using default configuration")
            # Set default configuration
            _config = {
                "openai": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.8,
                    "top_p": 1.0,
                    "max_tokens": 2000,
                    "presence_penalty": 0.0,
                    "frequency_penalty": 0.0
                },
                "chatbot": {
                    "system_prompt": "You are a sarcastic AI agent and you like to rhyme",
                    "max_conversation_history": 100,
                    "clear_history_on_exit": True,
                    "stream_responses": True
                },
                "logging": {
                    "enabled": True,
                    "level": "INFO",
                    "log_file": "chatbot.log"
                }
            }
    else:
        print(f"No configuration file found at {config_file}, using defaults")
        # Set default configuration
        _config = {
            "openai": {
                "model": "gpt-4o-mini",
                "temperature": 0.8,
                "top_p": 1.0,
                "max_tokens": 2000,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            },
            "chatbot": {
                "system_prompt": "You are a sarcastic AI agent and you like to rhyme",
                "max_conversation_history": 100,
                "clear_history_on_exit": True,
                "stream_responses": True
            },
            "logging": {
                "enabled": True,
                "level": "INFO",
                "log_file": "chatbot.log"
            }
        }
    
    mcp.run() 