import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("config_aware_server")

# Global configuration storage - will be loaded from server's own config file
_config = {}
_default_config = {}  # Loaded once at startup from default_client_config.yaml
_config_file_path = "dynamic_client_config.yaml"
_config_version = 0  # Increment when config changes
_config_observer = None

class ConfigFileHandler(FileSystemEventHandler):
    """Handle file system events for config file changes."""
    
    def on_modified(self, event):
        if event.src_path.endswith('dynamic_client_config.yaml') and not event.is_directory:
            self._reload_config()
    
    def on_moved(self, event):
        if event.dest_path.endswith('dynamic_client_config.yaml') and not event.is_directory:
            self._reload_config()
    
    def _reload_config(self):
        """Reload configuration from file."""
        global _config, _config_version
        try:
            if Path(_config_file_path).exists():
                with open(_config_file_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        _config = loaded_config
                        _config_version += 1
                        print(f"Configuration auto-reloaded (version {_config_version})")
        except Exception as e:
            print(f"Error auto-reloading configuration: {e}")

def _start_config_watcher():
    """Start watching the config file for changes."""
    global _config_observer
    if _config_observer is None:
        _config_observer = Observer()
        # Watch the server directory
        script_dir = Path(__file__).parent.absolute()
        _config_observer.schedule(ConfigFileHandler(), path=str(script_dir), recursive=False)
        _config_observer.start()
        print("Config file watcher started")
    return _config_observer

def _stop_config_watcher():
    """Stop the config file watcher."""
    global _config_observer
    if _config_observer:
        _config_observer.stop()
        _config_observer.join()
        _config_observer = None
        print("Config file watcher stopped")

@mcp.tool()
def get_config_version() -> str:
    """Get current configuration version for efficient change detection."""
    return str(_config_version)

@mcp.tool()
def get_config(section: Optional[str] = None) -> str:
    """Get current configuration. Available sections: 'openai', 'chatbot', 'logging'. If section parameter is provided, returns only that section. If no section provided, returns all configuration."""
    if section:
        if section in _config:
            return json.dumps({section: _config[section]}, indent=2)
        else:
            return f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"
    return json.dumps(_config, indent=2)

@mcp.tool()
def update_config(section: str, key: str, value: str) -> str:
    """Update a configuration value. Available sections: 'openai' (model, temperature, max_tokens, top_p, presence_penalty, frequency_penalty), 'chatbot' (system_prompt, max_conversation_history, clear_history_on_exit), 'logging' (enabled, level, log_file). Use format: section='openai', key='temperature', value='0.7'. Value will be parsed as JSON if possible."""
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
    
    # Increment version for programmatic changes
    global _config_version
    _config_version += 1
    
    # Auto-save the configuration to maintain persistence
    try:
        script_dir = Path(__file__).parent.absolute()
        config_file = script_dir / "dynamic_client_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(_config, f, default_flow_style=False, indent=2)
        save_status = f" (saved to server config, version {_config_version})"
    except Exception as e:
        save_status = f" (warning: could not save to file - {str(e)})"
    
    return f"Updated {section}.{key} from '{old_value}' to '{parsed_value}'{save_status}"

@mcp.tool()
def save_config(filepath: str = "dynamic_client_config.yaml") -> str:
    """Save current configuration to a YAML file."""
    try:
        # If relative path, make it relative to server directory
        if not Path(filepath).is_absolute():
            script_dir = Path(__file__).parent.absolute()
            filepath = script_dir / filepath
        
        with open(filepath, 'w') as f:
            yaml.dump(_config, f, default_flow_style=False, indent=2)
        return f"Configuration saved to {filepath}"
    except Exception as e:
        return f"Error saving configuration: {str(e)}"

@mcp.tool()
def load_config(filepath: str = "dynamic_client_config.yaml") -> str:
    """Load configuration from a YAML file."""
    global _config
    try:
        # If relative path, make it relative to server directory
        if not Path(filepath).is_absolute():
            script_dir = Path(__file__).parent.absolute()
            filepath = script_dir / filepath
            
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
    if _default_config:
        _config = _default_config.copy()
        return "Configuration reset to default values from default_client_config.yaml"
    else:
        return "Error: Default configuration not available"

@mcp.tool()
def load_defaults() -> str:
    """Load default configuration from default_client_config.yaml."""
    global _config
    if _load_default_config():
        _config = _default_config.copy()
        return "Default configuration loaded from default_client_config.yaml"
    else:
        return "Error: Could not load default configuration"

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

def _load_default_config():
    """Load default configuration from default_client_config.yaml."""
    global _default_config
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent.absolute()
        default_config_file = script_dir / "default_client_config.yaml"
        
        if default_config_file.exists():
            with open(default_config_file, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    _default_config = loaded_config
                    print(f"Loaded default configuration from {default_config_file}")
                    return True
                else:
                    print(f"Warning: {default_config_file} is empty")
                    return False
        else:
            print(f"Warning: {default_config_file} not found")
            return False
    except Exception as e:
        print(f"Warning: Could not load default_client_config.yaml: {e}")
        return False

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Load configuration from server's own config file
    config_file = script_dir / "dynamic_client_config.yaml"
    _config_file_path = str(config_file)
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    _config = loaded_config
                    _config_version = 1  # Start with version 1
                    print(f"Loaded server configuration from {config_file} (version {_config_version})")
                else:
                    print(f"Warning: Configuration file {config_file} is empty, loading defaults")
                    if _load_default_config():
                        _config = _default_config.copy()
                    else:
                        _config = {}
                    _config_version = 1
        except Exception as e:
            print(f"Warning: Could not load configuration from {config_file}: {e}")
            print("Loading default configuration")
            if _load_default_config():
                _config = _default_config.copy()
            else:
                _config = {}
            _config_version = 1
    else:
        print(f"No configuration file found at {config_file}, loading defaults")
        if _load_default_config():
            _config = _default_config.copy()
        else:
            _config = {}
        _config_version = 1
    
    # Start the config file watcher for event-driven updates
    try:
        _start_config_watcher()
    except Exception as e:
        print(f"Warning: Could not start config file watcher: {e}")
        print("Config changes will not be detected in real-time")
    
    try:
        mcp.run()
    finally:
        # Clean up the config watcher on exit
        _stop_config_watcher() 