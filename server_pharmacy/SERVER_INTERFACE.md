# MCP Server Interface Specification

This document describes the interface that any MCP server must implement to be compatible with the MCP ChatBot client.

## Overview

The MCP ChatBot client is designed to be **100% dependent on the server for configuration** while being **server-location agnostic**. This means:

- The client gets ALL configuration from the server (no local config files)
- The client can connect to any MCP server that implements the required interface
- The server can be located anywhere and implemented in any language
- The server must provide complete configuration for the chatbot to function

## Required Tools

Any compatible MCP server **MUST** implement these tools:

### `get_config`
- **Purpose**: Return the complete configuration for the chatbot
- **Parameters**: 
  - `section` (optional): Specific config section to return
- **Returns**: JSON string containing configuration
- **Required config sections**:
  ```json
  {
    "openai": {
      "model": "gpt-4o-mini",
      "temperature": 0.8,
      "max_tokens": 2000,
      "top_p": 1.0,
      "presence_penalty": 0.0,
      "frequency_penalty": 0.0
    },
    "chatbot": {
      "system_prompt": "You are a helpful assistant.",
      "max_conversation_history": 100,
      "clear_history_on_exit": false
    },
    "logging": {
      "enabled": true,
      "level": "INFO",
      "log_file": "chatbot.log"
    }
  }
  ```

### `get_config_version`
- **Purpose**: Return current configuration version for efficient change detection
- **Parameters**: None
- **Returns**: String representing current config version
- **Behavior**: Version should change whenever configuration is modified

## Optional Tools

These tools enhance functionality if available but are not required:

### `update_config`
- **Purpose**: Update a configuration value
- **Parameters**:
  - `section`: Configuration section (e.g., "openai", "chatbot", "logging")
  - `key`: Configuration key within section
  - `value`: New value (JSON parsed if possible)

### `list_config_keys`
- **Purpose**: List available configuration keys
- **Parameters**:
  - `section` (optional): Specific section to list keys for

### `save_config`
- **Purpose**: Save current configuration to persistent storage
- **Parameters**:
  - `filepath` (optional): File path to save to

### `load_config`
- **Purpose**: Load configuration from persistent storage
- **Parameters**:
  - `filepath` (optional): File path to load from

### `reset_config`
- **Purpose**: Reset configuration to default values

## Server Implementation Examples

### Python Server (using FastMCP)
```python
from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("my_config_server")

config = {
    "openai": {...},
    "chatbot": {...},
    "logging": {...}
}
config_version = 1

@mcp.tool()
def get_config(section: str = None) -> str:
    if section:
        return json.dumps({section: config[section]})
    return json.dumps(config)

@mcp.tool()
def get_config_version() -> str:
    return str(config_version)

if __name__ == "__main__":
    mcp.run()
```

### Node.js Server (conceptual)
```javascript
// Implement MCP server in Node.js with same tools
const server = new MCPServer();

server.addTool('get_config', (params) => {
    return JSON.stringify(config);
});

server.addTool('get_config_version', () => {
    return configVersion.toString();
});
```

## Connection Examples

The client can connect to any compatible server:

```python
from client import ChatBot

bot = ChatBot()

# Connect to Python server
await bot.connect_to_server(server_command=["python", "/path/to/config_server.py"])

# Connect to Node.js server
await bot.connect_to_server(server_command=["node", "/path/to/config_server.js"])

# Connect to any executable
await bot.connect_to_server(server_command=["/path/to/compiled_server"])

# Legacy mode (backwards compatible)
await bot.connect_to_server(python_path="python3", script_path="/path/to/server.py")
```

## Validation

The client automatically validates server compatibility by:

1. Checking that required tools are available
2. Verifying configuration format and required fields
3. Testing configuration version functionality
4. Gracefully handling missing optional tools

## Error Handling

If the server doesn't implement the required interface:
- Clear error messages indicate missing tools
- Client fails fast with helpful guidance
- Server requirements are clearly documented

## Benefits

This design provides:
- **Server flexibility**: Use any MCP server implementation
- **Language independence**: Server can be written in any language
- **Location independence**: Server can be anywhere accessible
- **100% server dependency**: No client-side configuration files
- **Clear interface**: Well-defined contract between client and server 