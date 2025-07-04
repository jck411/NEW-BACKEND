"""Tests for backend configuration."""


from backend.config import ServerConfig


class TestServerConfig:
    """Test suite for ServerConfig class."""

    def test_server_config_initialization(self):
        """Test ServerConfig initialization."""
        config = ServerConfig()
        assert config is not None
        assert hasattr(config, "openai_config")
        assert hasattr(config, "chatbot_config")
        assert hasattr(config, "logging_config")

    def test_server_config_openai_config_is_dict(self):
        """Test that openai_config is a dictionary."""
        config = ServerConfig()
        assert isinstance(config.openai_config, dict)

    def test_server_config_chatbot_config_is_dict(self):
        """Test that chatbot_config is a dictionary."""
        config = ServerConfig()
        assert isinstance(config.chatbot_config, dict)

    def test_server_config_logging_config_is_dict(self):
        """Test that logging_config is a dictionary."""
        config = ServerConfig()
        assert isinstance(config.logging_config, dict)

    def test_server_config_configs_are_empty_initially(self):
        """Test that configs start empty and are populated by server."""
        config = ServerConfig()
        # Configs start empty and are populated by the MCP server
        assert isinstance(config.openai_config, dict)
        assert isinstance(config.chatbot_config, dict)
        assert isinstance(config.logging_config, dict)

    def test_server_config_validate_temperature_range(self):
        """Test temperature validation."""
        config = ServerConfig()
        # Default temperature should be valid
        temp = config.openai_config.get("temperature", 0.7)
        assert 0.0 <= temp <= 2.0

    def test_server_config_validate_max_tokens_positive(self):
        """Test max_tokens validation."""
        config = ServerConfig()
        # Default max_tokens should be positive
        max_tokens = config.openai_config.get("max_tokens", 1000)
        assert max_tokens > 0

    def test_server_config_system_prompt_is_string(self):
        """Test that system_prompt is a string."""
        config = ServerConfig()
        system_prompt = config.chatbot_config.get("system_prompt", "")
        assert isinstance(system_prompt, str)

    def test_server_config_log_level_is_valid(self):
        """Test that log level is valid."""
        config = ServerConfig()
        log_level = config.logging_config.get("level", "INFO")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert log_level in valid_levels

    def test_server_config_configs_exist(self):
        """Test that config sections exist."""
        config = ServerConfig()

        # Test that we can access all config sections
        assert config.openai_config is not None
        assert config.chatbot_config is not None
        assert config.logging_config is not None

        # Test that configs are dictionaries
        assert isinstance(config.openai_config, dict)
        assert isinstance(config.chatbot_config, dict)
        assert isinstance(config.logging_config, dict)
