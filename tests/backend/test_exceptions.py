"""Tests for backend exceptions."""

from backend.exceptions import (
    ChatBotBaseException,
    ConfigurationError,
    MessageProcessingError,
    ServerConnectionError,
    get_exception_for_domain,
    wrap_exception,
)


class TestChatBotBaseException:
    """Test suite for ChatBotBaseException."""

    def test_basic_exception_creation(self) -> None:
        """Test creating a basic exception."""
        exc = ChatBotBaseException("Test message")
        assert str(exc) == "Test message"
        assert exc.message == "Test message"
        assert exc.error_code is None
        assert exc.context == {}
        assert exc.cause is None

    def test_exception_with_all_params(self) -> None:
        """Test creating exception with all parameters."""
        context = {"key": "value"}
        cause = ValueError("Original error")

        exc = ChatBotBaseException(
            message="Test message",
            error_code="TEST_ERROR",
            context=context,
            cause=cause
        )

        assert exc.message == "Test message"
        assert exc.error_code == "TEST_ERROR"
        assert exc.context == context
        assert exc.cause == cause

    def test_to_dict_method(self) -> None:
        """Test the to_dict method."""
        context = {"key": "value"}
        cause = ValueError("Original error")

        exc = ChatBotBaseException(
            message="Test message",
            error_code="TEST_ERROR",
            context=context,
            cause=cause
        )

        result = exc.to_dict()

        assert result["error_type"] == "ChatBotBaseException"
        assert result["message"] == "Test message"
        assert result["error_code"] == "TEST_ERROR"
        assert result["context"] == context
        assert result["cause"] == "Original error"

    def test_str_representation(self) -> None:
        """Test string representation with error code and context."""
        exc = ChatBotBaseException(
            message="Test message",
            error_code="TEST_ERROR",
            context={"key": "value"}
        )

        str_repr = str(exc)
        assert "Test message" in str_repr
        assert "[TEST_ERROR]" in str_repr
        assert "Context:" in str_repr


class TestDomainSpecificExceptions:
    """Test suite for domain-specific exceptions."""

    def test_configuration_error_inheritance(self) -> None:
        """Test that ConfigurationError inherits from base exception."""
        exc = ConfigurationError("Config error")
        assert isinstance(exc, ChatBotBaseException)
        assert exc.message == "Config error"

    def test_server_connection_error(self) -> None:
        """Test ServerConnectionError creation."""
        exc = ServerConnectionError(
            "Connection failed",
            error_code="CONNECTION_TIMEOUT"
        )
        assert isinstance(exc, ChatBotBaseException)
        assert exc.error_code == "CONNECTION_TIMEOUT"

    def test_message_processing_error(self) -> None:
        """Test MessageProcessingError creation."""
        exc = MessageProcessingError("Processing failed")
        assert isinstance(exc, ChatBotBaseException)


class TestWrapException:
    """Test suite for wrap_exception utility."""

    def test_wrap_basic_exception(self) -> None:
        """Test wrapping a basic exception."""
        original = ValueError("Original error")
        wrapped = wrap_exception(original)

        assert isinstance(wrapped, ChatBotBaseException)
        assert wrapped.cause == original
        assert "Original error" in wrapped.message

    def test_wrap_with_custom_class(self) -> None:
        """Test wrapping with custom exception class."""
        original = ValueError("Original error")
        wrapped = wrap_exception(
            original,
            exception_class=ConfigurationError,
            message="Custom message",
            error_code="CUSTOM_ERROR"
        )

        assert isinstance(wrapped, ConfigurationError)
        assert wrapped.message == "Custom message"
        assert wrapped.error_code == "CUSTOM_ERROR"
        assert wrapped.cause == original


class TestGetExceptionForDomain:
    """Test suite for get_exception_for_domain utility."""

    def test_get_configuration_domain_exception(self) -> None:
        """Test getting exception class for configuration domain."""
        exc_class = get_exception_for_domain("configuration")
        assert exc_class == ConfigurationError

    def test_get_connection_domain_exception(self) -> None:
        """Test getting exception class for connection domain."""
        get_exception_for_domain("connection")
        # Should return a connection-related exception class

    def test_get_unknown_domain_exception(self) -> None:
        """Test getting exception class for unknown domain."""
        exc_class = get_exception_for_domain("unknown")
        assert exc_class == ChatBotBaseException
