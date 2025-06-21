import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class MCPSession:
    """Manages MCP server connection and tool operations for any compatible MCP server."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.logger = logging.getLogger(__name__)
        self.server_info: Dict[str, Any] = {}
    
    async def connect(self, server_command: Union[str, List[str]], **server_params) -> Any:
        """
        Connect to any MCP server.
        
        Args:
            server_command: Full command as string or list of args to run the server
            **server_params: Additional server parameters
            
        Examples:
            # Connect to any server by command
            await session.connect(server_command=["python", "/path/to/any/server.py"])
            await session.connect(server_command="node /path/to/server.js")
        """
        
        if isinstance(server_command, str):
            # Parse string command into list
            import shlex
            command_args = shlex.split(server_command)
            command = command_args[0]
            args = command_args[1:] if len(command_args) > 1 else []
        else:
            # server_command is already a list
            command = server_command[0]
            args = server_command[1:] if len(server_command) > 1 else []

        # Store server info for debugging
        self.server_info = {
            'command': command,
            'args': args,
            'full_command': [command] + args
        }
        
        self.logger.info(f"Connecting to MCP server: {' '.join(self.server_info['full_command'])}")
        
        try:
            server_params_obj = StdioServerParameters(
                command=command,
                args=args,
                **server_params
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params_obj)
            )
            
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(stdio_transport[0], stdio_transport[1])
            )

            await self.session.initialize()
            
            # Get server info for logging
            tools_result = await self.session.list_tools()
            self.logger.info(f"Successfully connected to MCP server with {len(tools_result.tools)} tools")
            
            return tools_result
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server {self.server_info['full_command']}: {e}")
            raise RuntimeError(f"Could not connect to MCP server: {e}")
    
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
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get information about the connected server."""
        return self.server_info.copy()
    
    async def cleanup(self):
        """Clean up session resources."""
        if self.server_info.get('command'):
            self.logger.info(f"Cleaning up connection to: {' '.join(self.server_info['full_command'])}")
        await self.exit_stack.aclose() 