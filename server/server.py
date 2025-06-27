import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import yaml
from fastmcp import FastMCP
from watchfiles import awatch

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Modern 2025 approach: Use proper module structure
# Run server with: python -m server.server (from project root)
# Or: mcp run server/server.py (using MCP CLI)
from server.dynamic_tools import DynamicToolManager

# Create an MCP server
mcp = FastMCP("config_aware_server")

# Global configuration storage with proper type hints
_config: dict[str, Any] = {}
_default_config: dict[str, Any] = {}
_config_file_path = Path(__file__).parent / "dynamic_backend_config.yaml"
_config_version = 0
_config_watcher_task = None  # Asyncio task for watching config file
_dynamic_tool_manager = None  # DynamicToolManager instance

async def _async_reload_config():
    """Async reload configuration from file."""
    global _config, _config_version, _dynamic_tool_manager
    try:
        if await aiofiles.os.path.exists(_config_file_path):
            async with aiofiles.open(_config_file_path) as f:
                content = await f.read()
            loaded_config = yaml.safe_load(content) or {}
            if loaded_config:
                _config = loaded_config
                _config_version += 1
                logger.info(f"Configuration auto-reloaded (version {_config_version})")

                # AUTO-UPDATE: Automatically refresh dynamic tools after config change
                if _dynamic_tool_manager:
                    try:
                        _dynamic_tool_manager.config = _config
                        await _dynamic_tool_manager.transform_tools_based_on_config()
                        logger.info("Dynamic tools auto-refreshed after config change")
                    except Exception as e:
                        logger.warning(f"Failed to auto-refresh dynamic tools: {e}")
    except Exception as e:
        logger.error(f"Error auto-reloading configuration: {e}")

async def _config_watcher():
    """Async watcher for config file changes using watchfiles."""
    try:
        async for changes in awatch(_config_file_path.parent):
            for change_type, path in changes:
                if Path(path) == _config_file_path:
                    logger.debug(f"Config file {change_type.name.lower()}: {path}")
                    await _async_reload_config()
    except Exception as e:
        logger.error(f"Config watcher error: {e}")

def _start_config_watcher():
    """Start the asyncio-based config file watcher."""
    global _config_watcher_task
    if _config_watcher_task is None or _config_watcher_task.done():
        loop = asyncio.get_event_loop()
        _config_watcher_task = loop.create_task(_config_watcher())
        logger.info("Config file watcher started")
    return _config_watcher_task

def _stop_config_watcher():
    """Stop the config file watcher."""
    global _config_watcher_task
    if _config_watcher_task and not _config_watcher_task.done():
        _config_watcher_task.cancel()
        _config_watcher_task = None
        logger.info("Config file watcher stopped")

@mcp.tool()
async def get_config_version() -> str:
    """Get current configuration version for efficient change detection."""
    return str(_config_version)

@mcp.tool()
async def get_config(section: str | None = None) -> str:
    """Get current configuration. Available sections: 'openai', 'chatbot', 'logging'. If section parameter is provided, returns only that section. If no section provided, returns all configuration."""
    if section:
        return json.dumps({section: _config.get(section)}, indent=2) if section in _config else \
            f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"
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
        async with aiofiles.open(_config_file_path, "w") as f:
            await f.write(yaml.dump(_config, default_flow_style=False, indent=2))
        save_status = f" (saved to server config, version {_config_version})"
    except Exception as e:
        save_status = f" (warning: could not save to file - {e!s})"

    return f"Updated {section}.{key} from '{old_value}' to '{parsed_value}'{save_status}"

@mcp.tool()
async def save_config(filepath: str = "dynamic_backend_config.yaml") -> str:
    """Save current configuration to a YAML file."""
    try:
        # Use Path objects consistently and simplify path handling
        path = Path(filepath) if Path(filepath).is_absolute() else _config_file_path.parent / filepath
        async with aiofiles.open(path, "w") as f:
            await f.write(yaml.dump(_config, default_flow_style=False, indent=2))
        return f"Configuration saved to {path}"
    except Exception as e:
        return f"Error saving configuration: {e}"

@mcp.tool()
async def load_config(filepath: str = "dynamic_backend_config.yaml") -> str:
    """Load configuration from a YAML file."""
    global _config, _config_version
    try:
        # Use Path objects consistently
        path = Path(filepath) if Path(filepath).is_absolute() else _config_file_path.parent / filepath

        if await aiofiles.os.path.exists(path):
            async with aiofiles.open(path) as f:
                content = await f.read()
            loaded_config = yaml.safe_load(content) or {}
            if loaded_config:
                _config = loaded_config
                _config_version += 1
                return f"Configuration loaded from {path} (version {_config_version})"
            return f"Configuration file {path} is empty or invalid"
        return f"Configuration file {path} not found"
    except Exception as e:
        return f"Error loading configuration: {e}"

@mcp.tool()
async def reset_config() -> str:
    """Reset configuration to default values."""
    global _config, _config_version
    if _default_config:
        _config = _default_config.copy()
        _config_version += 1

        # Auto-save the reset config
        try:
            async with aiofiles.open(_config_file_path, "w") as f:
                await f.write(yaml.dump(_config, default_flow_style=False, indent=2))
            return f"Configuration reset to default values from default_backend_config.yaml (version {_config_version})"
        except Exception as e:
            return f"Configuration reset to defaults but could not save: {e!s}"
    else:
        return "Error: Default configuration not available"

@mcp.tool()
async def load_defaults() -> str:
    """Load default configuration from default_backend_config.yaml."""
    global _config, _config_version
    if await _async_load_default_config():
        _config = _default_config.copy()
        _config_version += 1
        return f"Default configuration loaded from default_backend_config.yaml (version {_config_version})"
    return "Error: Could not load default configuration"

@mcp.tool()
async def list_config_keys(section: str | None = None) -> str:
    """List all configuration keys. If section is provided, lists keys in that section only."""
    if section:
        return f"Keys in section '{section}': {list(_config[section].keys())}" if section in _config else \
            f"Configuration section '{section}' not found. Available sections: {list(_config.keys())}"

    return json.dumps({sec: list(data.keys()) for sec, data in _config.items()}, indent=2)

@mcp.tool()
async def get_time() -> str:
    """Get the current time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@mcp.tool()
async def echo(message: str) -> str:
    """Echo back the input message"""
    return message

@mcp.tool()
async def calculate(operation: str, a: float, b: float) -> str:
    """Perform basic arithmetic"""
    try:
        ops = {"add": a + b, "subtract": a - b, "multiply": a * b, "divide": None}
        if operation == "divide":
            return "Error: Division by zero" if b == 0 else str(a / b)
        return str(ops.get(operation, f"Unknown operation: {operation}"))
    except Exception as e:
        return f"Error: {e}"

# 🔥 REMOVED: refresh_dynamic_tools - now automatic via event-driven config updates

async def _async_load_default_config() -> bool:
    """Async load default configuration from default_backend_config.yaml."""
    global _default_config
    try:
        default_file = _config_file_path.parent / "default_backend_config.yaml"
        if await aiofiles.os.path.exists(default_file):
            async with aiofiles.open(default_file) as f:
                content = await f.read()
            loaded = yaml.safe_load(content) or {}
            if loaded:
                _default_config = loaded
                logger.info(f"Loaded default config from {default_file}")
                return True
    except Exception as e:
        logger.warning(f"Warning loading defaults: {e}")
    return False

# Sync fallback for startup
def _load_default_config() -> bool:
    """Sync load default configuration - used only during startup."""
    global _default_config
    try:
        default_file = _config_file_path.parent / "default_backend_config.yaml"
        if default_file.exists():
            with open(default_file) as f:
                loaded = yaml.safe_load(f) or {}
            if loaded:
                _default_config = loaded
                logger.info(f"Loaded default config from {default_file}")
                return True
    except Exception as e:
        logger.warning(f"Warning loading defaults: {e}")
    return False

if __name__ == "__main__":
    # Load defaults first
    if not _load_default_config():
        logger.info("No default config found; starting with empty defaults")

    # Load dynamic config
    try:
        if _config_file_path.exists():
            loaded = yaml.safe_load(_config_file_path.read_text()) or {}
            if loaded:
                _config = loaded
                _config_version = 1
                logger.info(f"Loaded config from {_config_file_path} (version {_config_version})")
            else:
                logger.info("Config empty; using defaults")
                _config = _default_config.copy()
                _config_version = 1
        else:
            logger.info("No config file; using defaults")
            _config = _default_config.copy()
            _config_version = 1
    except Exception as e:
        logger.error(f"Error loading config: {e}; using defaults")
        _config = _default_config.copy()
        _config_version = 1

    # Start watcher
    _start_config_watcher()

    # Initialize dynamic tools manager and schedule initial transform
    _dynamic_tool_manager = DynamicToolManager(mcp, _config)
    loop = asyncio.get_event_loop()
    loop.create_task(_dynamic_tool_manager.transform_tools_based_on_config())
    logger.info("Dynamic tool initialization scheduled!")

    try:
        mcp.run()
    finally:
        # Clean up the config watcher on exit
        _stop_config_watcher()
