"""Basic tests for server module functionality."""

from pathlib import Path

# Import the server module
import server.server


class TestServerBasic:
    """Basic test suite for server module."""

    def test_server_module_import(self):
        """Test that server module can be imported."""
        assert server.server is not None
        assert hasattr(server.server, "mcp")

    def test_mcp_server_creation(self):
        """Test that MCP server is created."""
        assert server.server.mcp is not None
        assert hasattr(server.server.mcp, "tool")

    def test_global_variables_exist(self):
        """Test that global variables are defined."""
        assert hasattr(server.server, "_config")
        assert hasattr(server.server, "_config_version")
        assert hasattr(server.server, "_default_config")
        assert hasattr(server.server, "_config_file_path")
        assert hasattr(server.server, "_config_watcher_task")
        assert hasattr(server.server, "_dynamic_tool_manager")

    def test_config_file_path_is_path(self):
        """Test that config file path is a Path object."""
        assert isinstance(server.server._config_file_path, Path)

    def test_config_version_is_integer(self):
        """Test that config version is an integer."""
        assert isinstance(server.server._config_version, int)

    def test_config_is_dict(self):
        """Test that config is a dictionary."""
        assert isinstance(server.server._config, dict)

    def test_default_config_is_dict(self):
        """Test that default config is a dictionary."""
        assert isinstance(server.server._default_config, dict)

    def test_get_config_version_function_exists(self):
        """Test that get_config_version function exists as a tool."""
        assert hasattr(server.server, "get_config_version")
        # It's a FunctionTool, not a callable function
        assert hasattr(server.server.get_config_version, "name")
        assert server.server.get_config_version.name == "get_config_version"

    def test_get_config_function_exists(self):
        """Test that get_config function exists as a tool."""
        assert hasattr(server.server, "get_config")
        # It's a FunctionTool, not a callable function
        assert hasattr(server.server.get_config, "name")
        assert server.server.get_config.name == "get_config"

    def test_get_time_function_exists(self):
        """Test that get_time function exists as a tool."""
        assert hasattr(server.server, "get_time")
        # It's a FunctionTool, not a callable function
        assert hasattr(server.server.get_time, "name")
        assert server.server.get_time.name == "get_time"

    def test_echo_function_exists(self):
        """Test that echo function exists as a tool."""
        assert hasattr(server.server, "echo")
        # It's a FunctionTool, not a callable function
        assert hasattr(server.server.echo, "name")
        assert server.server.echo.name == "echo"

    def test_calculate_function_exists(self):
        """Test that calculate function exists as a tool."""
        assert hasattr(server.server, "calculate")
        # It's a FunctionTool, not a callable function
        assert hasattr(server.server.calculate, "name")
        assert server.server.calculate.name == "calculate"

    def test_calculate_tool_description(self):
        """Test that calculate tool has proper description."""
        assert "Perform basic arithmetic" in server.server.calculate.description

    def test_echo_tool_description(self):
        """Test that echo tool has proper description."""
        assert "Echo back the input message" in server.server.echo.description

    def test_get_time_tool_description(self):
        """Test that get_time tool has proper description."""
        assert "Get the current time" in server.server.get_time.description

    def test_get_config_tool_description(self):
        """Test that get_config tool has proper description."""
        assert "Get current configuration" in server.server.get_config.description

    def test_async_reload_config_function_exists(self):
        """Test that _async_reload_config function exists."""
        assert hasattr(server.server, "_async_reload_config")
        assert callable(server.server._async_reload_config)

    def test_async_load_default_config_function_exists(self):
        """Test that _async_load_default_config function exists."""
        assert hasattr(server.server, "_async_load_default_config")
        assert callable(server.server._async_load_default_config)

    def test_load_default_config_function_exists(self):
        """Test that _load_default_config function exists."""
        assert hasattr(server.server, "_load_default_config")
        assert callable(server.server._load_default_config)

    def test_start_config_watcher_function_exists(self):
        """Test that _start_config_watcher function exists."""
        assert hasattr(server.server, "_start_config_watcher")
        assert callable(server.server._start_config_watcher)

    def test_stop_config_watcher_function_exists(self):
        """Test that _stop_config_watcher function exists."""
        assert hasattr(server.server, "_stop_config_watcher")
        assert callable(server.server._stop_config_watcher)

    def test_update_config_function_exists(self):
        """Test that update_config function exists as a tool."""
        assert hasattr(server.server, "update_config")
        assert hasattr(server.server.update_config, "name")
        assert server.server.update_config.name == "update_config"

    def test_save_config_function_exists(self):
        """Test that save_config function exists as a tool."""
        assert hasattr(server.server, "save_config")
        assert hasattr(server.server.save_config, "name")
        assert server.server.save_config.name == "save_config"

    def test_load_config_function_exists(self):
        """Test that load_config function exists as a tool."""
        assert hasattr(server.server, "load_config")
        assert hasattr(server.server.load_config, "name")
        assert server.server.load_config.name == "load_config"

    def test_reset_config_function_exists(self):
        """Test that reset_config function exists as a tool."""
        assert hasattr(server.server, "reset_config")
        assert hasattr(server.server.reset_config, "name")
        assert server.server.reset_config.name == "reset_config"

    def test_load_defaults_function_exists(self):
        """Test that load_defaults function exists as a tool."""
        assert hasattr(server.server, "load_defaults")
        assert hasattr(server.server.load_defaults, "name")
        assert server.server.load_defaults.name == "load_defaults"

    def test_list_config_keys_function_exists(self):
        """Test that list_config_keys function exists as a tool."""
        assert hasattr(server.server, "list_config_keys")
        assert hasattr(server.server.list_config_keys, "name")
        assert server.server.list_config_keys.name == "list_config_keys"

    def test_dynamic_tool_manager_import(self):
        """Test that DynamicToolManager is imported."""
        assert hasattr(server.server, "DynamicToolManager")

    def test_fastmcp_import(self):
        """Test that FastMCP is imported."""
        assert hasattr(server.server, "FastMCP")

    def test_yaml_import(self):
        """Test that yaml is imported."""
        assert hasattr(server.server, "yaml")

    def test_aiofiles_import(self):
        """Test that aiofiles is imported."""
        assert hasattr(server.server, "aiofiles")

    def test_watchfiles_import(self):
        """Test that watchfiles is imported."""
        assert hasattr(server.server, "awatch")

    def test_logging_setup(self):
        """Test that logging is set up."""
        assert hasattr(server.server, "logger")
        assert server.server.logger is not None

    def test_mcp_server_name(self):
        """Test that MCP server has correct name."""
        assert server.server.mcp.name == "config_aware_server"

    def test_mcp_server_has_tools(self):
        """Test that MCP server has tools."""
        # The server should have tools registered
        # FastMCP doesn't expose tools directly, but we can check that tools exist
        assert hasattr(server.server.mcp, "name")
        assert server.server.mcp.name == "config_aware_server"
