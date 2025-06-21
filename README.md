# MCP Client

A Python client for interacting with Model Context Protocol (MCP) servers using OpenAI's GPT models.

## Features

- Connect to MCP servers via stdio transport
- Integrate MCP tools with OpenAI chat completions
- Async/await support for modern Python applications
- Comprehensive error handling and content processing
- Support for various MCP content types (text, image, audio, etc.)

## Requirements

- Python 3.8+
- OpenAI API key
- MCP server implementation

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd "NEW BACKEND"
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the parent directory with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Running the Server

You can run the MCP server in several ways:

1. **Using the convenience script (recommended):**
```bash
python run_server.py
```

2. **Directly from the server directory:**
```bash
cd server
python server.py
```

3. **From the root directory:**
```bash
python server/server.py
```

### Basic Client Usage

```python
import asyncio
from client import ChatBot

async def main():
    # Create chatbot instance
    bot = ChatBot()
    
    # Connect to the server
    await bot.connect_to_server(server_command=["python", "server/server.py"])
    # or use the convenience script
    # await bot.connect_to_server(server_command=["python", "run_server.py"])
    
    # Process a message
    async for response in bot.process_message("What tools are available?"):
        print(response, end="")
    
    # Clean up resources
    await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### CLI Usage

```bash
# Connect to the configured server
python -m client.cli

# Connect with direct server command
python -m client.cli --server-command "python server/server.py"

# Show server requirements
python -m client.cli --show-requirements
```

### Configuration

The client configuration is managed through `client/client_config.yaml`:

```yaml
server_path: /path/to/your/server/server.py
```

The server configuration is managed through files in the `server/` directory:
- `server/dynamic_client_config.yaml` - Active server configuration
- `server/default_client_config.yaml` - Default configuration values

For detailed server configuration options, see `server/SERVER_INTERFACE.md`.

## Project Structure

```
NEW BACKEND/
├── client/                 # MCP client implementation
│   ├── __init__.py
│   ├── chatbot.py
│   ├── cli.py
│   ├── config.py
│   ├── connection_config.py
│   ├── conversation.py
│   ├── session.py
│   └── client_config.yaml
├── server/                 # MCP server implementation
│   ├── server.py
│   ├── dynamic_client_config.yaml
│   ├── default_client_config.yaml
│   ├── SERVER_INTERFACE.md
│   └── requirements.txt
├── run_server.py          # Convenience script to run server
├── requirements.txt       # Combined Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## API Reference

### `ChatBot`
Main chatbot class that orchestrates configuration, session, and conversation management.

### `ChatBot.connect_to_server(server_command=None, **server_params)`
Establishes connection to an MCP server.

### `ChatBot.process_message(message: str)`
Processes a user message using OpenAI with available MCP tools.

### `ChatBot.cleanup()`
Cleans up resources and closes connections.

For detailed API documentation, see the docstrings in the client modules.

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol SDK
- `openai>=1.1.0` - OpenAI Python client
- `python-dotenv>=1.0.0` - Environment variable management
- `nest-asyncio>=1.5.6` - Nested async loop support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Troubleshooting

### Common Issues

1. **Session not initialized error**: Make sure to call `connect_to_server()` before using other functions.

2. **Environment variables not loading**: Ensure your `.env` file is in the correct location (parent directory) and contains the required variables.

3. **MCP server connection issues**: Verify the server script path and Python interpreter path in the configuration.

## Support

[Add support information here]
