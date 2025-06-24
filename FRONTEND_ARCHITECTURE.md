# Frontend Architecture - Option 2 Implementation

This document describes the new frontend architecture where the server handles multiple frontend types directly, eliminating the need for a client-as-host pattern.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Server    │    │  Backend API    │    │   Frontends     │
│   (server.py)   │◄───┤   (FastAPI)     │◄───┤  (Independent)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       WebSocket Endpoint
                        ws://host:port/ws/chat
```

## Components

### 1. Backend API Server (`api/main.py`)
- FastAPI-based WebSocket server
- Handles multiple concurrent frontend connections
- Manages chat sessions and conversation history
- Connects to MCP server for AI functionality

### 2. Frontend Types

#### Server-Only Mode
- Runs backend without any frontend
- Frontends connect independently via WebSocket
- Configured with `frontend.type: "server_only"`

#### Terminal Frontend
- Simple command-line interface
- Supports Speech-to-Text integration
- Can run standalone or via client launcher

#### Kivy Frontend
- GUI interface using Kivy framework
- Real-time streaming chat UI
- Connects directly to backend WebSocket

## Configuration

### Backend Configuration (`backend/backend_config.yaml`)

```yaml
# Frontend Configuration
frontend:
  type: "server_only"              # Options: "terminal", "kivy", "server_only"

# Backend API Configuration (used when frontend.type is "server_only")
backend:
  host: "localhost"                # Backend host
  port: 8000                       # Backend port
  enable_cors: true                # Enable CORS for web frontends
  max_connections: 100             # Maximum WebSocket connections

# Speech-to-Text Configuration
stt:
  enabled: true                    # Enable/disable STT functionality
  api_key_env: "DEEPGRAM_API_KEY"  # Environment variable containing API key
  model: "nova-2"                  # Deepgram model to use
  language: "en-US"                # Language for transcription
```

## Usage Examples

### 1. Start Backend API
```bash
# Start the backend API server
python run_backend.py
# or with uv:
uv run python run_backend.py
```

### 2. Start Frontend (connects to backend)
```bash
# Terminal frontend
python frontends/terminal_frontend.py
# or with uv:
uv run python frontends/terminal_frontend.py

# Additional frontends can be developed following the same WebSocket protocol
```

## WebSocket Protocol

### Connection Endpoint
```
ws://localhost:8000/ws/chat
```

### Message Format
All messages are JSON with a `type` field and optional `id` for tracking:

```json
{
  "type": "message_type",
  "id": "optional_uuid",
  "content": "message content"
}
```

### Message Types

#### Client to Server

**Text Chat Message:**
```json
{
  "type": "text_message",
  "id": "uuid",
  "content": "user message"
}
```

**Clear Conversation History:**
```json
{
  "type": "clear_history",
  "id": "uuid"
}
```

**Get Conversation History:**
```json
{
  "type": "get_history",
  "id": "uuid"
}
```

**Get Configuration:**
```json
{
  "type": "get_config",
  "id": "uuid"
}
```

**Health Check:**
```json
{
  "type": "ping",
  "id": "uuid"
}
```

#### Server to Client

**Message Start (Streaming):**
```json
{
  "type": "message_start",
  "id": "uuid",
  "user_message": "echoed user message"
}
```

**Text Chunk (Streaming):**
```json
{
  "type": "text_chunk",
  "id": "uuid", 
  "content": "streaming text chunk"
}
```

**Message Complete:**
```json
{
  "type": "message_complete",
  "id": "uuid",
  "full_content": "complete response"
}
```

**History Response:**
```json
{
  "type": "history",
  "data": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user", 
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi there! How can I help you?"
    }
  ]
}
```

**History Cleared:**
```json
{
  "type": "history_cleared"
}
```

**Configuration Response:**
```json
{
  "type": "config",
  "data": {
    "chatbot": {...},
    "openai": {...},
    "logging": {...},
    "server_info": {...}
  }
}
```

**Health Check Response:**
```json
{
  "type": "pong"
}
```

**Connection Established:**
```json
{
  "type": "connection_established",
  "client_id": "uuid"
}
```

**Error Response:**
```json
{
  "type": "error",
  "error": "error message description"
}
```

## API Endpoints

### HTTP Endpoints

- **Health Check**: `GET /health`
- **Root**: `GET /`
- **Configuration**: `GET /api/config`

### WebSocket Endpoints

- **Main Chat**: `ws://host:port/ws/chat` (production endpoint)
- **Test Endpoint**: `ws://host:port/ws/test` (debugging/testing only)

## Benefits of This Architecture

1. **Clean Separation**: Frontends are completely independent of the backend
2. **Scalability**: Multiple frontends can connect to one backend instance
3. **Flexibility**: Easy to add new frontend types without modifying core logic
4. **Development**: Frontend and backend can be developed/tested independently
5. **Deployment**: Can run backend on server and frontends on different machines

## Migration from Previous Architecture

1. **Update Configuration**: Change `frontend.type` to `"server_only"` in config
2. **Start Backend**: Use `python run_server_only.py` or `python -m client --frontend server_only`
3. **Launch Frontends**: Use standalone frontend launchers in `frontends/` directory
4. **Multiple Frontends**: Can run multiple frontend instances connecting to same backend

## Development

### Adding New Frontend Types

1. Create frontend in `frontends/` directory
2. Implement WebSocket client following the protocol
3. Add launcher script
4. Update documentation

### Testing

1. Start backend: `python run_server_only.py`
2. Test WebSocket endpoint: `ws://localhost:8000/ws/test` (simple echo test)
3. Launch frontend and verify connection to `ws://localhost:8000/ws/chat`
4. Test message flow and error handling

### Frontend Implementation Guidelines

1. **Connection Management**: Implement reconnection logic with exponential backoff
2. **Message Handling**: Handle all message types gracefully with error fallbacks
3. **UI Updates**: Use proper threading/async patterns for UI updates
4. **Configuration**: Read backend connection details from client config
5. **Error Handling**: Display user-friendly error messages and connection status 