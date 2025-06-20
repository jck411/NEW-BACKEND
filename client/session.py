import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPSession:
    """Manages MCP server connection and tool operations."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, python_path: str = None, script_path: str = None):
        """Connect to an MCP server."""
        # Use current Python executable if not specified
        if python_path is None:
            python_path = sys.executable
        
        # Use relative path to server.py if not specified
        if script_path is None:
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py")
        
        server_params = StdioServerParameters(
            command=python_path,
            args=[script_path],
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio_transport[0], stdio_transport[1])
        )

        await self.session.initialize()
        return await self.session.list_tools()
    
    async def get_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format."""
        if self.session is None:
            raise RuntimeError("Session is not initialized. Call connect() first.")
            
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call a tool on the MCP server."""
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        
        return await self.session.call_tool(name, arguments=arguments)
    
    async def cleanup(self):
        """Clean up session resources."""
        await self.exit_stack.aclose() 