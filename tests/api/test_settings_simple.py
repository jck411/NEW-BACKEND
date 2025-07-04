"""Simple tests for API settings."""


from api.config.settings import Settings, get_settings


class TestSettings:
    """Test suite for Settings class."""

    def test_settings_initialization(self):
        """Test Settings initialization."""
        settings = Settings()
        assert settings is not None
        assert hasattr(settings, "host")
        assert hasattr(settings, "port")
        assert hasattr(settings, "debug")

    def test_settings_has_host(self):
        """Test that settings has host attribute."""
        settings = Settings()
        assert settings.host is not None
        assert isinstance(settings.host, str)

    def test_settings_has_port(self):
        """Test that settings has port attribute."""
        settings = Settings()
        assert settings.port is not None
        assert isinstance(settings.port, int)

    def test_settings_has_debug(self):
        """Test that settings has debug attribute."""
        settings = Settings()
        assert hasattr(settings, "debug")
        assert isinstance(settings.debug, bool)

    def test_get_settings_returns_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_settings_has_allowed_origins(self):
        """Test that settings has allowed_origins."""
        settings = Settings()
        assert hasattr(settings, "allowed_origins")
        assert isinstance(settings.allowed_origins, list)

    def test_settings_has_websocket_config(self):
        """Test that settings has websocket configuration."""
        settings = Settings()
        assert hasattr(settings, "websocket_ping_interval")
        assert hasattr(settings, "websocket_ping_timeout")
        assert hasattr(settings, "max_connections")

    def test_settings_has_logging_config(self):
        """Test that settings has logging configuration."""
        settings = Settings()
        assert hasattr(settings, "log_level")
        assert hasattr(settings, "log_format_json")
