# Architecture Summary

## Overview

The MCP ChatBot client implements a **server-dependent, server-agnostic architecture** that enables seamless configuration management and speech-to-text capabilities. The client connects to any MCP server for configuration while supporting voice input through Deepgram integration.

## Core Architecture Principles

- **Server Dependency**: All configuration sourced from MCP servers
- **Server Agnostic**: Compatible with any MCP server implementation (Python, Node.js, compiled binaries)
- **Configuration-Driven**: Server connections managed via YAML configuration
- **Event-Driven**: Real-time configuration updates and voice processing
- **Hybrid Input**: Simultaneous support for keyboard and voice input

## System Components

### 1. Connection Management (`client/connection_config.py`)
Manages server connection configurations and client settings:

```python
class ConnectionConfig:
    - Server path configuration
    - STT settings management
    - YAML-based configuration persistence
    - Automatic config loading/saving
```

**Key Features:**
- Server path management
- Speech-to-text configuration
- Persistent configuration storage
- Configuration validation

### 2. MCP Session (`client/session.py`)
Handles MCP server communication:

```python
class MCPSession:
    - Server process management
    - MCP protocol communication
    - Tool and resource discovery
    - Configuration synchronization
```

**Capabilities:**
- Any server type support (Python, Node.js, binaries)
- Dynamic tool registration
- Robust error handling
- Clean resource management

### 3. ChatBot Core (`client/chatbot.py`)
Main chatbot functionality with configuration integration:

```python
class ChatBot:
    - Server connection management
    - Configuration validation
    - Conversation handling
    - STT integration coordination
```

**Features:**
- Server compatibility checking
- Configuration management
- Conversation state handling
- Multi-modal input support

### 4. Speech-to-Text Integration

#### STT Architecture
The system implements a robust STT solution using Deepgram:

- **Dedicated Threading**: STT runs in separate thread to avoid blocking
- **Event-Driven Processing**: WebSocket callbacks for real-time transcription
- **KeepAlive Management**: Maintains connection during assistant responses
- **Hybrid Input**: Seamless mixing of voice and keyboard input

#### STT Components

**DeepgramSTT Class** (`STT/deepgram_stt.py`):
```python
class DeepgramSTT:
    - WebSocket connection management
    - Microphone input handling
    - Transcript processing
    - Resource cleanup
```

**ChatBotSTTOfficial** (`client/chatbot_stt_official.py`):
```python
class ChatBotSTTOfficial:
    - Chatbot-specific STT integration
    - KeepAlive during responses
    - Utterance callback handling
    - Thread-safe coordination
```

#### KeepAlive Feature
Implements Deepgram's KeepAlive to optimize costs and performance:

- **Automatic Pause**: STT pauses during assistant responses
- **Connection Maintenance**: Periodic KeepAlive messages prevent disconnection
- **No Transcription Costs**: Assistant speech not processed
- **Seamless Resume**: STT automatically resumes after responses

### 5. CLI Interface (`client/__main__.py`)
Main entry point with integrated STT support:

```python
# STT Integration Flow
1. Load configuration
2. Initialize STT if enabled
3. Start dual input handling (voice + keyboard)
4. Coordinate STT pause/resume during responses
5. Clean shutdown of all components
```

## Configuration Structure

### Client Configuration (`client/client_config.yaml`)
```yaml
# Server Connection
server_path: /path/to/server/server.py

# Speech-to-Text Configuration
stt:
  enabled: true                    # Enable/disable STT
  api_key_env: "DEEPGRAM_API_KEY"  # API key environment variable
  model: "nova-2"                  # Deepgram model
  language: "en-US"                # Transcription language
  utterance_end_ms: 1000           # Utterance end detection (ms)
  keepalive_interval: 3            # KeepAlive interval (seconds)
```

## Usage Patterns

### Basic Operation
```bash
# Start with STT enabled
python -m client

# Output shows:
# 🎤 Speech-to-Text enabled - speak into your microphone!
# 💬 You can also type messages or say 'exit', 'quit', or 'bye' to stop
```

### Programmatic Usage
```python
from client import ChatBot

bot = ChatBot()
await bot.connect_to_server()  # Uses configured server path
```

### Hybrid Input Examples
```
🎤 You (speech): What's the weather today?
🤖 Assistant: I don't have real-time weather data...

Type (or speak): Tell me a joke
⌨️  You: Tell me a joke  
🤖 Assistant: Why don't programmers like nature? It has too many bugs!
```

## Technical Implementation

### STT Processing Flow
1. **Microphone Listening**: Continuous audio capture
2. **Voice Activity Detection**: Automatic speech detection
3. **Real-time Transcription**: Interim and final results
4. **Utterance Completion**: Complete phrases submitted automatically
5. **KeepAlive Management**: Pause during assistant responses

### Error Handling
- **Graceful Degradation**: Falls back to text-only if STT fails
- **Connection Recovery**: Automatic reconnection attempts
- **Resource Cleanup**: Proper cleanup on interruption
- **Thread Safety**: Coordinated multi-threaded operations

### Performance Optimization
- **Dedicated Event Loops**: Separate STT and main processing
- **Non-blocking Operations**: Async/await throughout
- **Resource Management**: Automatic cleanup and connection pooling
- **Cost Optimization**: KeepAlive prevents unnecessary transcription

## Server Requirements

Any MCP server must implement these tools:

### Required Tools
- `get_config`: Return complete configuration as JSON
- `get_config_version`: Return config version for change detection

### Optional Tools
- `update_config`: Update configuration values
- `list_config_keys`: List available configuration keys
- `save_config`: Save configuration to persistent storage
- `load_config`: Load configuration from files

## Integration Benefits

1. **Seamless Voice Input**: Natural speech interaction without interrupting workflow
2. **Cost Efficient**: KeepAlive prevents transcribing assistant responses
3. **Flexible Configuration**: Easy server switching and STT customization
4. **Robust Operation**: Graceful error handling and automatic recovery
5. **Development Friendly**: Clear separation of concerns and clean APIs

## Server Compatibility

The architecture supports any MCP server:

- **Local Servers**: `python ./server/server.py`
- **Remote Servers**: `python /remote/path/server.py`
- **Different Languages**: `node /path/to/server.js`
- **Compiled Binaries**: `/usr/local/bin/config_server`
- **With Parameters**: `python server.py --config custom.json`

The client maintains complete server agnosticism while depending on servers for all configuration, creating a clean separation between connection management and configuration data. 