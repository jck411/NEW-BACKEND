import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from .exceptions import (
    ConfigurationLoadError,
    ConfigurationMissingError,
    ResourceNotFoundError,
)
from .utils import log_and_wrap_error


class ConnectionConfig:
    """Manages client connection configuration for MCP servers."""

    def __init__(self, config_file: str = "backend/backend_config.yaml") -> None:
        """Initialize the connection configuration manager.

        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config: dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.load_config()

    def load_config(self) -> None:
        """Load connection configuration from file."""
        config_path = Path(self.config_file)

        if not config_path.exists():
            self.logger.error("Configuration file not found at %s", self.config_file)
            msg = f"Configuration file not found: {self.config_file}"
            raise ResourceNotFoundError(
                msg,
                error_code="CONFIG_FILE_NOT_FOUND",
                context={"config_file": self.config_file},
            )

        try:
            with config_path.open() as f:
                self.config = yaml.safe_load(f) or {}
            self.logger.info("Loaded connection config from %s", self.config_file)
        except (FileNotFoundError, yaml.YAMLError, OSError) as e:
            wrapped_error = log_and_wrap_error(
                e,
                ConfigurationLoadError,
                "Failed to load connection configuration",
                error_code="CONFIG_LOAD_FAILED",
                context={"config_file": self.config_file},
                logger=self.logger,
            )
            raise wrapped_error from e

    def get_server_command(self) -> list[str]:
        """Get server command for connection using 2025 best practices.

        Returns:
            Server command as list using modern MCP execution

        Raises:
            ConfigurationMissingError: If server_path is not configured
        """
        server_path = self.config.get("server_path")
        if not server_path:
            msg = (
                f"No server_path configured in {self.config_file}. "
                "Please set server_path to the path of your MCP server."
            )
            raise ConfigurationMissingError(
                msg,
                error_code="SERVER_PATH_NOT_CONFIGURED",
                context={"config_file": self.config_file},
            )

        # 2025 Best Practice: Use module execution with proper working directory
        # This is the most reliable method for MCP servers in 2025
        python_executable = sys.executable

        # Execute as module from project root to ensure proper imports
        Path(server_path)

        # Use -m flag to run as module from the correct directory
        return [python_executable, "-m", "server.server"]

    def get_server_env(self) -> dict[str, str]:
        """Get environment variables for the MCP server using 2025 best practices.

        Returns:
            Environment variables for module execution
        """
        return os.environ.copy()

    def get_server_cwd(self) -> str:
        """Get the working directory for the MCP server using 2025 best practices.

        Returns:
            Working directory path (project root)
        """
        server_path = self.config.get("server_path")
        if not server_path:
            return str(Path.cwd())

        # Set working directory to project root for proper module execution
        server_path_obj = Path(server_path)
        return str(
            server_path_obj.parent.parent
        )  # Go up from server/server.py to project root

    def get_server_path(self) -> str:
        """Get the configured server path."""
        server_path = self.config.get("server_path")
        if not server_path:
            msg = (
                f"No server_path configured in {self.config_file}. "
                "Please set server_path to the path of your MCP server."
            )
            raise ConfigurationMissingError(
                msg,
                error_code="SERVER_PATH_NOT_CONFIGURED",
                context={"config_file": self.config_file},
            )
        return server_path

    def set_server_path(self, path: str) -> None:
        """Set the server path and save configuration."""
        self.config["server_path"] = path
        self.save_config()
        self.logger.info("Updated server path to: %s", path)

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            # Ensure the directory exists
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with config_path.open("w") as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            self.logger.info("Saved connection config to %s", self.config_file)
        except Exception:
            self.logger.exception("Failed to save connection config")
            raise

    def get_config_file_path(self) -> str:
        """Get the path to the configuration file."""
        return str(Path(self.config_file).absolute())

    def get_stt_config(self) -> dict[str, Any]:
        """Get STT configuration settings."""
        return self.config.get("stt", {})

    def is_stt_enabled(self) -> bool:
        """Check if STT is enabled."""
        stt_config = self.get_stt_config()
        return stt_config.get("enabled", False)

    def get_backend_config(self) -> dict[str, Any]:
        """Get backend configuration settings."""
        return self.config.get(
            "backend",
            {
                "host": "localhost",
                "port": 8000,
                "enable_cors": True,
                "max_connections": 100,
            },
        )

    def get_backend_host(self) -> str:
        """Get the backend host."""
        backend_config = self.get_backend_config()
        return backend_config.get("host", "localhost")

    def get_backend_port(self) -> int:
        """Get the backend port."""
        backend_config = self.get_backend_config()
        return backend_config.get("port", 8000)

    def set_backend_config(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        enable_cors: bool | None = None,
        max_connections: int | None = None,
    ) -> None:
        """Set backend configuration and save."""
        if "backend" not in self.config:
            self.config["backend"] = {}

        if host is not None:
            self.config["backend"]["host"] = host
        if port is not None:
            self.config["backend"]["port"] = port
        if enable_cors is not None:
            self.config["backend"]["enable_cors"] = enable_cors
        if max_connections is not None:
            self.config["backend"]["max_connections"] = max_connections

        self.save_config()
        self.logger.info("Updated backend configuration")
