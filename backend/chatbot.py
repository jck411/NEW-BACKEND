import asyncio
import json
import logging
import shlex
from collections.abc import AsyncGenerator
from typing import Any

from .config import ServerConfig
from .connection_config import ConnectionConfig
from .conversation import ConversationManager
from .exceptions import (
    ConfigurationError,
    ServerConnectionError,
)
from .session import MCPSession
from .utils import extract_tool_content


class ChatBot:
    """Main ChatBot class that orchestrates configuration, session, and conversation management.

    This chatbot is designed to be 100% dependent on the MCP server for configuration,
    but can work with any MCP server that implements the required configuration interface.
    """

    def __init__(
        self, connection_config_file: str = "backend/backend_config.yaml"
    ) -> None:
        """Initialize the ChatBot with configuration and session management."""
        self.config = ServerConfig()
        self.mcp_session = MCPSession()
        self.conversation_manager = ConversationManager(self.mcp_session)
        self.connection_config = ConnectionConfig(connection_config_file)
        self.logger = logging.getLogger(__name__)
        self._config_version: str = ""

        self.logger.info(
            "ChatBot initialized (will load all configuration from MCP server)"
        )

    async def connect_to_server(
        self,
        server_command: str | list[str] | None = None,
        **server_params: object,
    ) -> object:
        """Connect to any MCP server that implements the required configuration interface.

        Args:
            server_command: Override command to run the server (optional)
            **server_params: Additional server parameters

        Returns:
            Server tools list

        Raises:
            RuntimeError: If server doesn't implement required configuration interface

        Examples:
            # Connect using configured server path
            await bot.connect_to_server()

            # Override with direct command
            await bot.connect_to_server(server_command=["python", "/path/to/server.py"])
        """
        try:
            # Determine server command
            if server_command:
                # Direct command overrides config
                if isinstance(server_command, str):
                    command = shlex.split(server_command)
                else:
                    command = server_command
            else:
                # Use connection config
                command = self.connection_config.get_server_command()

            # Connect to the server
            tools = await self.mcp_session.connect(
                server_command=command, **server_params
            )

            server_info = self.mcp_session.get_server_info()
            self.logger.info(
                "Connected to MCP server: %s", " ".join(server_info["full_command"])
            )

            # Load configuration from server (this validates server compatibility)
            if self.mcp_session.session is not None:
                await self.config.load_from_server(self.mcp_session.session)

            # Initialize system message from server config
            system_prompt = self.config.chatbot_config.get("system_prompt", "")
            if not system_prompt:
                msg = (
                    "Server configuration missing required 'chatbot.system_prompt'. "
                    "The server must provide a complete chatbot configuration including "
                    "system_prompt."
                )
                raise ConfigurationError(msg, error_code="MISSING_SYSTEM_PROMPT")

            self.conversation_manager.set_system_message(system_prompt)

            self.logger.info("ChatBot fully configured from server")

        except (RuntimeError, ValueError, ConnectionError, OSError):
            self.logger.exception("Failed to connect and configure from server")
            raise
        else:
            return tools

    async def _update_config_if_changed(self) -> None:
        """Check if configuration version has changed and update if necessary."""
        if self.mcp_session.session is None:
            return

        try:
            # Only check version if server supports it
            if not self.config.has_server_capability("get_config_version"):
                self.logger.debug(
                    "Server doesn't support config versioning, skipping version check"
                )
                return

            # Lightweight version check
            result = await self.mcp_session.call_tool(
                "get_config_version", arguments={}
            )
            new_version = extract_tool_content(result).strip()

            # Only reload if version changed
            if (
                not hasattr(self, "_config_version")
                or self._config_version != new_version
            ):
                # Get full config only when needed
                result = await self.mcp_session.call_tool("get_config", arguments={})
                content_text = extract_tool_content(result)
                server_config = json.loads(content_text)

                # Update local config directly
                self.config.config = server_config

                # Update logging configuration if changed
                if "logging" in server_config and server_config["logging"]["enabled"]:
                    log_level = getattr(
                        logging, server_config["logging"]["level"].upper()
                    )
                    logging.getLogger().setLevel(log_level)

                # Update system message if changed
                new_system_prompt = server_config.get("chatbot", {}).get(
                    "system_prompt", ""
                )
                if not new_system_prompt:
                    self.logger.warning(
                        "Server config missing system_prompt after update"
                    )
                    return

                current_system_content = ""
                if (
                    self.conversation_manager.conversation_history
                    and self.conversation_manager.conversation_history[0]["role"]
                    == "system"
                ):
                    current_system_content = (
                        self.conversation_manager.conversation_history[0]["content"]
                    )

                if current_system_content != new_system_prompt:
                    self.conversation_manager.set_system_message(new_system_prompt)
                    self.logger.info(
                        "System prompt updated: %s...", new_system_prompt[:50]
                    )

                self._config_version = new_version
                self.logger.info(
                    "Configuration updated from server (version: %s)", new_version
                )

        except (RuntimeError, ValueError, ConnectionError, OSError) as e:
            self.logger.warning("Failed to check config version: %s", e)

    async def process_message(self, user_message: str) -> AsyncGenerator[str]:
        """Process a user message maintaining conversation context."""
        # Ensure we're connected to a server
        if self.mcp_session.session is None:
            msg = (
                "No server connection. Call connect_to_server() first with a compatible "
                "MCP server."
            )
            raise ServerConnectionError(msg, error_code="NO_SERVER_CONNECTION")

        # Check if any configuration has changed and update if necessary
        await self._update_config_if_changed()

        async for chunk in self.conversation_manager.process_message_streaming(
            user_message, self.config
        ):
            yield chunk

    def get_server_requirements(self) -> dict[str, str]:
        """Get the MCP server interface requirements for this chatbot.

        Any MCP server used with this chatbot must implement these tools.
        """
        return self.config.get_required_server_interface()

    def get_server_optional_features(self) -> dict[str, str]:
        """Get optional server features that enhance functionality if available."""
        return self.config.get_optional_server_interface()

    def get_current_server_info(self) -> dict[str, Any]:
        """Get information about the currently connected server."""
        server_info = self.mcp_session.get_server_info()
        server_info["capabilities"] = {
            tool: self.config.has_server_capability(tool)
            for tool in {**self.config.REQUIRED_TOOLS, **self.config.OPTIONAL_TOOLS}
        }
        return server_info

    def get_configured_server_path(self) -> str:
        """Get the configured server path."""
        return self.connection_config.get_server_path()

    def set_server_path(self, path: str) -> None:
        """Set the server path in configuration."""
        self.connection_config.set_server_path(path)

    def get_connection_config_path(self) -> str:
        """Get the path to the connection configuration file."""
        return self.connection_config.get_config_file_path()

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.config.chatbot_config.get("clear_history_on_exit", False):
                self.conversation_manager.clear_history()
                self.logger.info(
                    "Conversation history cleared on exit (per server configuration)"
                )
            await self.mcp_session.cleanup()
        except (KeyboardInterrupt, asyncio.CancelledError):
            # Handle graceful shutdown when interrupted
            pass
        except (RuntimeError, ValueError, ConnectionError, OSError) as e:
            self.logger.warning("Error during chatbot cleanup: %s", e)
