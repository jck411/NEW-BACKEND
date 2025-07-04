# ChatBot Backend Server

A clean, simple Python chatbot backend that connects to MCP (Model Context Protocol) servers for AI functionality. Frontends connect independently via WebSocket from separate terminals or machines.

## Features

- **Pure backend server**: FastAPI WebSocket server supporting multiple concurrent connections
- **Frontend agnostic**: Any frontend can connect via WebSocket protocol
- **Speech-to-Text ready**: STT configuration available for frontends that support it
- **Real-time streaming**: Live response streaming to all connected clients
- **Simple deployment**: Backend and frontends run completely independently
- **Clean architecture**: Complete separation between backend, MCP server, and frontends

## Requirements

- Python 3.10+
- OpenAI API key (configured in MCP server)
- uv (Python package manager)
- Optional: Deepgram API key for Speech-to-Text (used by frontends)

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd NEW-BACKEND
```

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies:
```bash
# Install base dependencies
uv sync

# Install frontend-specific dependencies (optional)
uv sync --extra kivy    # For Kivy GUI frontend
```

4. Set up environment variables (create `.env` file):
```bash
# Required for MCP server
OPENAI_API_KEY=your_openai_api_key_here

# Optional for Speech-to-Text (used by frontends)
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

## Quick Start

### Start the Backend Server

```bash
# Backend server launcher (recommended)
uv run python -m backend
```

### Connect Frontends (from other terminals/machines)

```bash
# Terminal frontend
uv run python frontends/terminal_frontend.py
```

## Usage Examples

### 1. Check Configuration
```bash
# Show current backend and MCP server configuration
uv run python -m backend --show-config
```

### 2. Use Different MCP Server
```bash
# Override the configured MCP server path
uv run python -m backend --server-path "/path/to/your/server.py"
```

### 3. Multiple Frontends
```bash
# Terminal 1: Start backend
uv run python -m backend

# Terminal 2: Connect terminal frontend
uv run python frontends/terminal_frontend.py

# Terminal 3: Connect another terminal frontend
uv run python frontends/terminal_frontend.py
```

## Configuration

### Backend Configuration (`backend/backend_config.yaml`)

```yaml
server_path: /home/jack/NEW-BACKEND/server/server.py

# Backend API Configuration
backend:
  host: "localhost"                # Backend host
  port: 8000                       # Backend port
  enable_cors: true                # Enable CORS for web frontends
  max_connections: 100             # Maximum WebSocket connections

# Speech-to-Text Configuration (used by frontends)
stt:
  enabled: true                    # Enable/disable STT functionality
  api_key_env: "DEEPGRAM_API_KEY"  # Environment variable containing API key
  model: "nova-2"                  # Deepgram model to use
  language: "en-US"                # Language for transcription
  utterance_end_ms: 1000           # Milliseconds to wait before considering utterance ended
  keepalive_interval: 3            # Seconds between keepalive messages during streaming responses
```

### MCP Server Configuration

The MCP server configuration is managed in the `server/` directory. The default server provides AI chat functionality using OpenAI's API.

## Architecture

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

### Components

1. **Backend API Server** (`api/main.py`) - FastAPI WebSocket server
2. **MCP Server** (`server/server.py`) - AI functionality provider
3. **Standalone Frontends** (`frontends/`) - Independent client applications
4. **Backend Library** (`backend/`) - Shared configuration and utilities

## Available Frontends

### Terminal Frontend
- Simple command-line interface
- Optional Speech-to-Text integration
- Real-time streaming responses
- Cross-platform compatibility



## WebSocket Protocol

### Connection Endpoint
```
ws://localhost:8000/ws/chat
```

### Message Format
All messages are JSON with a `type` field:

```json
{
  "type": "message_type",
  "id": "optional_uuid",
  "content": "message content"
}
```

### Message Types

**Send Chat Message:**
```json
{
  "type": "text_message",
  "id": "uuid",
  "content": "user message"
}
```

**Clear History:**
```json
{
  "type": "clear_history",
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

For complete protocol documentation, see `FRONTEND_ARCHITECTURE.md`.

## Development

### Creating New Frontends

1. Create frontend application in `frontends/` directory
2. Implement WebSocket client connecting to `ws://localhost:8000/ws/chat`
3. Follow the message protocol for communication
4. Use backend configuration for backend connection details

### Testing

1. Start backend: `uv run python -m backend`
2. Test WebSocket: Connect to `ws://localhost:8000/ws/test` (echo test)
3. Launch frontend and test message flow

### Package Management with uv

```bash
# Sync dependencies
uv sync

# Add new dependency
uv add package-name

# Run scripts
uv run python script.py

# Show dependency tree
uv tree
```

## Project Structure

```
NEW-BACKEND/
├── api/                    # FastAPI backend server
│   ├── main.py            # Main FastAPI application
│   ├── services/          # Business logic services
│   ├── models/            # Data models
│   └── config/            # Backend configuration
├── backend/               # Backend library and configuration
│   ├── chatbot.py         # Main ChatBot class
│   ├── connection_config.py # Configuration management
│   ├── backend_config.yaml # Backend configuration file
│   └── __main__.py        # Backend server entry point
├── frontends/             # Standalone frontend applications
│   └── terminal_frontend.py # Complete terminal interface
├── server/                # MCP server implementation
│   ├── server.py          # Main MCP server
│   └── *.yaml             # Server configuration files
├── stt/                   # Speech-to-Text integration

├── run_backend.py         # Backend API launcher
└── pyproject.toml         # Project dependencies
```

## Troubleshooting

### Common Issues

1. **Commands not working**: Always use `uv run python` prefix
   ```bash
   # ✅ Correct
   uv run python -m backend --show-config
   
   # ❌ Wrong
   python -m backend --show-config
   ```

2. **Frontend can't connect**: Ensure backend is running first
   ```bash
   # Start backend first
   uv run python -m backend
   
   # Then connect frontend
   uv run python frontends/terminal_frontend.py
   ```

3. **Port already in use**: Change port in `backend/backend_config.yaml`
   ```yaml
   backend:
     port: 8001  # Use different port
   ```

4. **STT not working**: Check Deepgram API key in `.env` file
   ```bash
   # Add to .env file
   DEEPGRAM_API_KEY=your_key_here
   ```

### Debug Mode

Enable verbose logging:
```bash
uv run python -m backend --verbose
```

## API Endpoints

- **WebSocket Chat**: `ws://localhost:8000/ws/chat`
- **Health Check**: `http://localhost:8000/health`
- **Configuration**: `http://localhost:8000/api/config`
- **WebSocket Test**: `ws://localhost:8000/ws/test` (echo test)
