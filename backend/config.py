import json
import logging
from typing import Any

from .exceptions import (
    ConfigurationError,
    ServerIncompatibleError,
)
from .utils import extract_tool_content, handle_config_errors, log_and_wrap_error


class ServerConfig:
    """Configuration manager that gets all config from any MCP server that implements the config interface."""

    # Required tools that any compatible MCP server must provide
    REQUIRED_TOOLS = {
        "get_config": "Get configuration from server",
        "get_config_version": "Get configuration version for change detection"
    }

    # Optional tools that enhance functionality if available
    OPTIONAL_TOOLS = {
        "update_config": "Update configuration on server",
        "list_config_keys": "List available configuration keys",
        "save_config": "Save configuration to server",
        "load_config": "Load configuration from server file"
    }

    def __init__(self):
        self.config: dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._server_capabilities: dict[str, bool] = {}

        # Setup basic logging (will be updated from server config later)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    @handle_config_errors("Failed to load configuration from server", "CONFIG_LOAD_FAILED")
    async def load_from_server(self, session):
        """Load configuration from any compatible MCP server."""
        # First, check what tools the server provides
        await self._check_server_capabilities(session)

        # Ensure required tools are available
        missing_tools = []
        for tool_name in self.REQUIRED_TOOLS:
            if not self._server_capabilities.get(tool_name, False):
                missing_tools.append(tool_name)

        if missing_tools:
            raise ServerIncompatibleError(
                f"Server is not compatible. Missing required tools: {missing_tools}. "
                f"Any compatible MCP server must implement: {list(self.REQUIRED_TOOLS.keys())}",
                error_code="SERVER_MISSING_TOOLS",
                context={"missing_tools": missing_tools, "required_tools": list(self.REQUIRED_TOOLS.keys())}
            )

        # Load configuration from server
        result = await session.call_tool("get_config", arguments={})
        content_text = extract_tool_content(result)
        self.config = json.loads(content_text)

        # Update logging configuration
        if "logging" in self.config and self.config["logging"]["enabled"]:
            log_level = getattr(logging, self.config["logging"]["level"].upper())
            logging.getLogger().setLevel(log_level)

        self.logger.info("Configuration loaded from server")

        # Log server capabilities for debugging
        available_optional = [tool for tool, available in self._server_capabilities.items()
                            if available and tool in self.OPTIONAL_TOOLS]
        if available_optional:
            self.logger.info(f"Server provides optional tools: {available_optional}")

    async def _check_server_capabilities(self, session):
        """Check what configuration tools the server provides."""
        try:
            tools_result = await session.list_tools()
            available_tools = {tool.name for tool in tools_result.tools}

            # Check required tools
            for tool_name in self.REQUIRED_TOOLS:
                self._server_capabilities[tool_name] = tool_name in available_tools

            # Check optional tools
            for tool_name in self.OPTIONAL_TOOLS:
                self._server_capabilities[tool_name] = tool_name in available_tools

            self.logger.debug(f"Server capabilities: {self._server_capabilities}")

        except Exception as e:
            wrapped_error = log_and_wrap_error(
                e, ConfigurationError, "Failed to check server capabilities",
                error_code="SERVER_CAPABILITIES_CHECK_FAILED", logger=self.logger
            )
            raise wrapped_error



    def has_server_capability(self, tool_name: str) -> bool:
        """Check if the server supports a specific configuration tool."""
        return self._server_capabilities.get(tool_name, False)

    @property
    def openai_config(self) -> dict[str, Any]:
        return self.config.get("openai", {})

    @property
    def server_config(self) -> dict[str, Any]:
        return self.config.get("server", {})

    @property
    def chatbot_config(self) -> dict[str, Any]:
        return self.config.get("chatbot", {})

    @property
    def logging_config(self) -> dict[str, Any]:
        return self.config.get("logging", {})

    def get_required_server_interface(self) -> dict[str, str]:
        """Get the required server interface specification."""
        return self.REQUIRED_TOOLS.copy()

    def get_optional_server_interface(self) -> dict[str, str]:
        """Get the optional server interface specification."""
        return self.OPTIONAL_TOOLS.copy()
