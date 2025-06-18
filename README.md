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

### Basic Usage

```python
import asyncio
from client.client import connect_to_server, process_query, cleanup

async def main():
    # Connect to your MCP server
    await connect_to_server("path/to/your/server.py")
    
    # Process a query
    response = await process_query("What tools are available?")
    print(response)
    
    # Clean up resources
    await cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration

The client can be configured by modifying the global variables in `client.py`:

- `model`: OpenAI model to use (default: "gpt-4o")
- Server path in `connect_to_server()` function
- Python interpreter path in `StdioServerParameters`

## Project Structure

```
NEW BACKEND/
├── client/
│   └── client.py          # Main MCP client implementation
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## API Reference

### `connect_to_server(server_script_path: str)`
Establishes connection to an MCP server.

### `get_mcp_tools() -> List[Dict[str, Any]]`
Retrieves available tools from the MCP server in OpenAI format.

### `process_query(query: str) -> str`
Processes a user query using OpenAI with available MCP tools.

### `cleanup()`
Cleans up resources and closes connections.

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
