"""Simple tests for API logging configuration."""

from unittest.mock import MagicMock, patch

from api.config.logging import configure_structured_logging, get_logger


class TestLogging:
    """Test suite for logging configuration."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger."""
        logger = get_logger(__name__)
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")

    def test_get_logger_with_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")

        assert logger1 is not None
        assert logger2 is not None
        # Different names should potentially return different loggers
        # (though they might be the same instance in some implementations)

    def test_configure_structured_logging_callable(self):
        """Test that configure_structured_logging is callable."""
        # Just test that the function exists and is callable
        assert callable(configure_structured_logging)

    @patch("api.config.logging.structlog")
    def test_configure_structured_logging_configures_structlog(
        self, mock_structlog: MagicMock
    ) -> None:
        """Test that configure_structured_logging configures structlog."""
        configure_structured_logging()

        # Should call structlog.configure
        mock_structlog.configure.assert_called_once()

    def test_get_logger_auto_detection(self):
        """Test logger auto-detection functionality."""
        # Test without providing a name
        logger = get_logger()
        assert logger is not None

    def test_logger_has_required_methods(self):
        """Test that logger has all required methods."""
        logger = get_logger("test")

        # Standard logging methods
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")

    def test_multiple_get_logger_calls(self):
        """Test multiple calls to get_logger."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        # Should return consistent loggers
        assert logger1 is not None
        assert logger2 is not None
