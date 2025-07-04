import asyncio
import logging
import shlex
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from .exceptions import (
    ServerConnectionError,
    SessionNotInitializedError,
)
from .utils import log_and_wrap_error


class MCPSession:
    """Manages MCP server connection and tool operations for any compatible MCP server."""

    def __init__(self) -> None:
        """Initialize the MCPSession with empty session and logging setup."""
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self.logger = logging.getLogger(__name__)
        self.server_info: dict[str, Any] = {}

    async def connect(
        self, server_command: str | list[str], **server_params: Any  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Connect to any MCP server.

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
            command_args = shlex.split(server_command)
            command = command_args[0]
            args = command_args[1:] if len(command_args) > 1 else []
        else:
            # server_command is already a list
            command = server_command[0]
            args = server_command[1:] if len(server_command) > 1 else []

        # Store server info for debugging
        self.server_info = {
            "command": command,
            "args": args,
            "full_command": [command, *args],
        }

        self.logger.info(
            "Connecting to MCP server: %s", " ".join(self.server_info["full_command"])
        )

        try:
            # Filter server_params to only include valid StdioServerParameters fields
            valid_params: dict[str, Any] = {}
            if "env" in server_params:
                valid_params["env"] = server_params["env"]
            if "cwd" in server_params:
                valid_params["cwd"] = server_params["cwd"]
            if "encoding" in server_params:
                valid_params["encoding"] = server_params["encoding"]
            if "encoding_error_handler" in server_params:
                valid_params["encoding_error_handler"] = server_params[
                    "encoding_error_handler"
                ]

            server_params_obj = StdioServerParameters(
                command=command, args=args, **valid_params
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
            self.logger.info(
                "Successfully connected to MCP server with %s tools",
                len(tools_result.tools),
            )

        except (OSError, RuntimeError, ValueError, ConnectionError) as e:
            wrapped_error = log_and_wrap_error(
                e,
                ServerConnectionError,
                "Could not connect to MCP server",
                error_code="MCP_CONNECTION_FAILED",
                context={"server_command": self.server_info["full_command"]},
                logger=self.logger,
            )
            raise wrapped_error from e
        else:
            return tools_result

    async def get_tools_for_openai(self) -> list[dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format."""
        if self.session is None:
            msg = "Session is not initialized. Call connect() first."
            raise SessionNotInitializedError(msg, error_code="SESSION_NOT_INITIALIZED")

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

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> Any:  # noqa: ANN401
        """Call a tool on the MCP server."""
        if self.session is None:
            msg = "Session is not initialized"
            raise SessionNotInitializedError(msg, error_code="SESSION_NOT_INITIALIZED")

        return await self.session.call_tool(name, arguments=arguments)

    def get_server_info(self) -> dict[str, Any]:
        """Get information about the connected server."""
        return self.server_info.copy()

    async def cleanup(self) -> None:
        """Clean up session resources."""
        if self.server_info.get("command"):
            self.logger.info(
                "Cleaning up connection to: %s",
                " ".join(self.server_info["full_command"]),
            )
        try:
            await self.exit_stack.aclose()
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Handle graceful shutdown when interrupted
            pass
        except (OSError, RuntimeError, ValueError, ConnectionError) as e:
            self.logger.warning("Error during session cleanup: %s", e)
