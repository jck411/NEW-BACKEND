"""Tests for structured logging configuration."""

from api.config.logging import configure_structured_logging, get_logger


class TestStructuredLogging:
    """Test suite for structured logging configuration."""

    def test_get_logger_returns_valid_logger(self):
        """Test that get_logger returns a valid logger instance."""
        configure_structured_logging(level="INFO", format_json=True)
        logger = get_logger("test_logger")

        # Should be able to call logging methods
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')

    def test_structured_logging_configuration(self):
        """Test that structured logging configures without errors."""
        # Should not raise any exceptions
        configure_structured_logging(level="DEBUG", format_json=False)
        configure_structured_logging(level="INFO", format_json=True)

        logger = get_logger("config_test")

        # Should be able to log without errors
        logger.info("Configuration test", user_id=123, success=True)

    def test_logger_with_different_levels(self):
        """Test logging at different levels."""
        configure_structured_logging(level="DEBUG", format_json=True)
        logger = get_logger("level_test")

        # Test different log levels
        logger.debug("Debug message", test_type="debug")
        logger.info("Info message", test_type="info")
        logger.warning("Warning message", test_type="warning")
        logger.error("Error message", test_type="error")

    def test_logger_with_custom_fields(self):
        """Test logging with custom structured data."""
        configure_structured_logging(level="INFO", format_json=True)
        logger = get_logger("custom_test")

        # Log with custom structured data
        logger.info(
            "User performed action",
            user_id=456,
            action="login",
            success=True,
            ip_address="127.0.0.1"
        )

    def test_get_logger_auto_detection(self):
        """Test that get_logger can auto-detect module name."""
        configure_structured_logging(level="INFO", format_json=True)

        # Call without explicit name - should auto-detect
        logger = get_logger()

        # Should work without errors
        logger.info("Auto-detection test", auto_detect=True)
