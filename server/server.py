import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
import os
import time
import aiofiles
import aiofiles.os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from fastmcp import FastMCP
from dynamic_tools import DynamicToolManager

# Create an MCP server
mcp = FastMCP("config_aware_server")

# Global configuration storage - will be loaded from server's own config file
_config = {}
_default_config = {}  # Loaded once at startup from default_client_config.yaml
_config_file_path = "dynamic_client_config.yaml"
_config_version = 0  # Increment when config changes
_config_observer = None
_dynamic_tool_manager = None  # Will be initialized after config loads

class ConfigFileHandler(FileSystemEventHandler):
    """Handle file system events for config file changes."""
    
    def on_modified(self, event):
        if event.src_path.endswith('dynamic_client_config.yaml') and not event.is_directory:
            # Use asyncio.run_coroutine_threadsafe for thread-safe async execution
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(self._async_reload_config(), loop)
            except RuntimeError:
                # No running loop, skip file watcher update (programmatic updates will handle it)
                print("File watcher: No running loop, skipping update")
    
    def on_moved(self, event):
        if event.dest_path.endswith('dynamic_client_config.yaml') and not event.is_directory:
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(self._async_reload_config(), loop)
            except RuntimeError:
                print("File watcher: No running loop, skipping update")
    
    async def _async_reload_config(self):
        """Async reload configuration from file."""
        global _config, _config_version, _dynamic_tool_manager
        try:
            if await aiofiles.os.path.exists(_config_file_path):
                async with aiofiles.open(_config_file_path, 'r') as f:
                    content = await f.read()
                    loaded_config = yaml.safe_load(content)
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
async def get_config_version() -> str:
    """Get current configuration version for efficient change detection."""
    return str(_config_version)

@mcp.tool()
async def get_config(section: Optional[str] = None) -> str:
    """Get current configuration. Available sections: 'openai', 'chatbot', 'logging'. If section parameter is provided, returns only that section. If no section provided, returns all configuration."""
    if section:
        if section in _config:
            return json.dumps({section: _config[section]}, indent=2)
        else:
            return f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"
    return json.dumps(_config, indent=2)

@mcp.tool()
async def update_config(section: str, key: str, value: str) -> str:
    """Update a configuration value. Available sections: 'openai' (model, temperature, max_tokens, top_p, presence_penalty, frequency_penalty), 'chatbot' (system_prompt, max_conversation_history, clear_history_on_exit), 'logging' (enabled, level, log_file). Use format: section='openai', key='temperature', value='0.7'. Value will be parsed as JSON if possible."""
    global _dynamic_tool_manager
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
    
    # Auto-save the configuration to maintain persistence (async)
    try:
        script_dir = Path(__file__).parent.absolute()
        config_file = script_dir / "dynamic_client_config.yaml"
        async with aiofiles.open(config_file, 'w') as f:
            await f.write(yaml.dump(_config, default_flow_style=False, indent=2))
        save_status = f" (saved to server config, version {_config_version})"
    except Exception as e:
        save_status = f" (warning: could not save to file - {str(e)})"
    
    return f"Updated {section}.{key} from '{old_value}' to '{parsed_value}'{save_status}"

@mcp.tool()
async def save_config(filepath: str = "dynamic_client_config.yaml") -> str:
    """Save current configuration to a YAML file."""
    try:
        # If relative path, make it relative to server directory
        if not Path(filepath).is_absolute():
            script_dir = Path(__file__).parent.absolute()
            filepath = script_dir / filepath
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(yaml.dump(_config, default_flow_style=False, indent=2))
        return f"Configuration saved to {filepath}"
    except Exception as e:
        return f"Error saving configuration: {str(e)}"

@mcp.tool()
async def load_config(filepath: str = "dynamic_client_config.yaml") -> str:
    """Load configuration from a YAML file."""
    global _config, _config_version
    try:
        # If relative path, make it relative to server directory
        if not Path(filepath).is_absolute():
            script_dir = Path(__file__).parent.absolute()
            filepath = script_dir / filepath
            
        if await aiofiles.os.path.exists(filepath):
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                loaded_config = yaml.safe_load(content)
                if loaded_config:
                    _config = loaded_config
                    _config_version += 1
                    return f"Configuration loaded from {filepath} (version {_config_version})"
                else:
                    return f"Configuration file {filepath} is empty or invalid"
        else:
            return f"Configuration file {filepath} not found"
    except Exception as e:
        return f"Error loading configuration: {str(e)}"

@mcp.tool()
async def reset_config() -> str:
    """Reset configuration to default values."""
    global _config, _config_version
    if _default_config:
        _config = _default_config.copy()
        _config_version += 1
        
        # Auto-save the reset config
        try:
            script_dir = Path(__file__).parent.absolute()
            config_file = script_dir / "dynamic_client_config.yaml"
            async with aiofiles.open(config_file, 'w') as f:
                await f.write(yaml.dump(_config, default_flow_style=False, indent=2))
            return f"Configuration reset to default values from default_client_config.yaml (version {_config_version})"
        except Exception as e:
            return f"Configuration reset to defaults but could not save: {str(e)}"
    else:
        return "Error: Default configuration not available"

@mcp.tool()
async def load_defaults() -> str:
    """Load default configuration from default_client_config.yaml."""
    global _config, _config_version
    if await _async_load_default_config():
        _config = _default_config.copy()
        _config_version += 1
        return f"Default configuration loaded from default_client_config.yaml (version {_config_version})"
    else:
        return "Error: Could not load default configuration"

@mcp.tool()
async def list_config_keys(section: Optional[str] = None) -> str:
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
async def get_time() -> str:
    """Get the current time"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Current time: {current_time}"

@mcp.tool()
async def echo(message: str) -> str:
    """Echo back the input message"""
    return f"Echo: {message}"

@mcp.tool()
async def calculate(operation: str, a: float, b: float) -> str:
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

@mcp.tool()
async def refresh_dynamic_tools() -> str:
    """Manually refresh dynamic tools based on current configuration. Use this after making configuration changes."""
    global _dynamic_tool_manager
    if _dynamic_tool_manager:
        try:
            _dynamic_tool_manager.config = _config
            await _dynamic_tool_manager.regenerate_all_tools()
            return f"✅ Dynamic tools refreshed successfully! Current tools: {len(_dynamic_tool_manager.dynamic_tools)}"
        except Exception as e:
            return f"❌ Failed to refresh dynamic tools: {str(e)}"
    else:
        return "❌ Dynamic tool manager not initialized"

async def _async_load_default_config():
    """Async load default configuration from default_client_config.yaml."""
    global _default_config
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent.absolute()
        default_config_file = script_dir / "default_client_config.yaml"
        
        if await aiofiles.os.path.exists(default_config_file):
            async with aiofiles.open(default_config_file, 'r') as f:
                content = await f.read()
                loaded_config = yaml.safe_load(content)
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

# Keep the sync version for backward compatibility during startup
def _load_default_config():
    """Sync load default configuration - used only during startup."""
    global _default_config
    try:
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
    
    # 🔥 NEW: Initialize dynamic tool manager with current config
    _dynamic_tool_manager = DynamicToolManager(mcp, _config)
    try:
        # Create initial dynamic tools based on current config
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_dynamic_tool_manager.transform_tools_based_on_config())
        loop.close()
        print("🚀 Dynamic tool system initialized!")
    except Exception as e:
        print(f"Warning: Could not initialize dynamic tools: {e}")
    
    try:
        mcp.run()
    finally:
        # Clean up the config watcher on exit
        _stop_config_watcher()
