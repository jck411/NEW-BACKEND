"""Security tests to ensure proper secret management and logging protection."""

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.exceptions import ConfigurationError
from backend.utils.security import (
    SecureLogger,
    get_optional_env_var,
    get_required_env_var,
    mask_sensitive_keys,
    sanitize_for_logging,
)


class TestEnvironmentVariableHandling:
    """Test secure environment variable handling."""

    def test_get_required_env_var_success(self):
        """Test getting a required environment variable that exists."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = get_required_env_var("TEST_VAR")
            assert result == "test_value"

    def test_get_required_env_var_missing(self):
        """Test getting a required environment variable that doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ConfigurationError, match="TEST_VAR environment variable is required"
            ):
                get_required_env_var("TEST_VAR")

    def test_get_optional_env_var_exists(self):
        """Test getting an optional environment variable that exists."""
        with patch.dict(os.environ, {"OPTIONAL_VAR": "optional_value"}):
            result = get_optional_env_var("OPTIONAL_VAR", "default")
            assert result == "optional_value"

    def test_get_optional_env_var_missing_with_default(self):
        """Test getting an optional environment variable that doesn't exist with default."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_optional_env_var("MISSING_VAR", "default_value")
            assert result == "default_value"

    def test_get_optional_env_var_missing_no_default(self):
        """Test getting an optional environment variable that doesn't exist without default."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_optional_env_var("MISSING_VAR")
            assert result == ""


class TestDataSanitization:
    """Test data sanitization for logging safety."""

    def test_sanitize_string_with_api_key(self):
        """Test sanitizing a string containing an API key."""
        text = "api_key=sk-1234567890abcdef1234567890abcdef"
        result = sanitize_for_logging(text)
        assert "sk-1234567890abcdef1234567890abcdef" not in result
        assert "***REDACTED***" in result

    def test_sanitize_string_with_bearer_token(self):
        """Test sanitizing a string containing a bearer token."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_for_logging(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "***REDACTED***" in result

    def test_sanitize_string_with_openai_key(self):
        """Test sanitizing a string containing an OpenAI API key."""
        text = "Using OpenAI key: sk-proj-1234567890abcdef1234567890abcdef"
        result = sanitize_for_logging(text)
        assert "sk-proj-1234567890abcdef1234567890abcdef" not in result
        assert "***REDACTED***" in result

    def test_sanitize_dict_with_secrets(self):
        """Test sanitizing a dictionary containing secrets."""
        data = {"api_key": "secret123", "username": "user", "token": "token456"}
        result = sanitize_for_logging(data)
        assert result["api_key"] == "***REDACTED***"
        assert result["username"] == "user"  # Not sensitive
        assert result["token"] == "***REDACTED***"

    def test_sanitize_list_with_secrets(self):
        """Test sanitizing a list containing secrets."""
        data = ["normal text", "api_key=secret123", {"token": "secret456"}]
        result = sanitize_for_logging(data)
        assert result[0] == "normal text"
        assert "***REDACTED***" in result[1]
        assert result[2]["token"] == "***REDACTED***"

    def test_sanitize_nested_data(self):
        """Test sanitizing nested data structures."""
        data = {
            "config": {"api_key": "secret123", "timeout": 30},
            "users": [{"name": "Alice", "token": "secret456"}],
        }
        result = sanitize_for_logging(data)
        assert result["config"]["api_key"] == "***REDACTED***"
        assert result["config"]["timeout"] == 30
        assert result["users"][0]["name"] == "Alice"
        assert result["users"][0]["token"] == "***REDACTED***"


class TestSensitiveKeyMasking:
    """Test specific sensitive key masking."""

    def test_mask_default_sensitive_keys(self):
        """Test masking with default sensitive keys."""
        data = {
            "api_key": "secret",
            "password": "pass123",
            "token": "token456",
            "username": "user",
            "timeout": 30,
        }
        result = mask_sensitive_keys(data)
        assert result["api_key"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"
        assert result["token"] == "***REDACTED***"
        assert result["username"] == "user"  # Not in default sensitive keys
        assert result["timeout"] == 30

    def test_mask_custom_sensitive_keys(self):
        """Test masking with custom sensitive keys."""
        data = {"api_key": "secret", "custom_secret": "value", "normal_field": "normal"}
        custom_keys = {"custom_secret"}
        result = mask_sensitive_keys(data, custom_keys)
        assert result["api_key"] == "secret"  # Not in custom keys
        assert result["custom_secret"] == "***REDACTED***"
        assert result["normal_field"] == "normal"

    def test_mask_nested_sensitive_keys(self):
        """Test masking sensitive keys in nested dictionaries."""
        data = {
            "config": {
                "api_key": "secret",
                "database": {"password": "dbpass", "host": "localhost"},
            }
        }
        result = mask_sensitive_keys(data)
        assert result["config"]["api_key"] == "***REDACTED***"
        assert result["config"]["database"]["password"] == "***REDACTED***"
        assert result["config"]["database"]["host"] == "localhost"


class TestSecureLogger:
    """Test the secure logger wrapper."""

    def test_secure_logger_sanitizes_messages(self):
        """Test that SecureLogger sanitizes log messages."""
        mock_logger = MagicMock()
        secure_logger = SecureLogger(mock_logger)

        message = "API key is api_key=secret123"
        secure_logger.info(message)

        # Check that the logger was called with sanitized message
        mock_logger.info.assert_called_once()
        args, _ = mock_logger.info.call_args
        sanitized_message = args[0]
        assert "secret123" not in sanitized_message
        assert "***REDACTED***" in sanitized_message

    def test_secure_logger_all_levels(self):
        """Test that all logging levels sanitize messages."""
        mock_logger = MagicMock()
        secure_logger = SecureLogger(mock_logger)

        test_message = "token=secret456"

        secure_logger.debug(test_message)
        secure_logger.info(test_message)
        secure_logger.warning(test_message)
        secure_logger.error(test_message)
        secure_logger.exception(test_message)

        # Check that all methods were called and messages were sanitized
        for method in [
            mock_logger.debug,
            mock_logger.info,
            mock_logger.warning,
            mock_logger.error,
            mock_logger.exception,
        ]:
            method.assert_called_once()
            args, _ = method.call_args
            assert "secret456" not in args[0]
            assert "***REDACTED***" in args[0]


class TestConversationManagerSecurity:
    """Test security aspects of ConversationManager."""

    def test_openai_api_key_required(self):
        """Test that ConversationManager requires OPENAI_API_KEY."""
        from backend.conversation import ConversationManager
        from backend.session import MCPSession

        mock_session = MagicMock(spec=MCPSession)

        # Test without API key
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ConfigurationError,
                match="OPENAI_API_KEY environment variable is required",
            ):
                ConversationManager(mock_session)

    @patch("backend.conversation.AsyncOpenAI")
    def test_openai_client_uses_explicit_key(self, mock_openai):
        """Test that ConversationManager uses explicit API key."""
        from backend.conversation import ConversationManager
        from backend.session import MCPSession

        mock_session = MagicMock(spec=MCPSession)
        test_key = "sk-test1234567890abcdef1234567890abcdef"

        with patch.dict(os.environ, {"OPENAI_API_KEY": test_key}):
            ConversationManager(mock_session)

        # Verify that AsyncOpenAI was called with the explicit API key
        mock_openai.assert_called_once_with(api_key=test_key)


class TestDeepgramSTTSecurity:
    """Test security aspects of Deepgram STT."""

    def test_deepgram_api_key_required(self):
        """Test that DeepgramSTT requires API key."""
        from backend.exceptions import DeepgramSTTError
        from stt.deepgram_stt import DeepgramSTT

        stt_config = {"api_key_env": "DEEPGRAM_API_KEY"}
        utterance_callback = MagicMock()

        # Test without API key
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(DeepgramSTTError, match="Deepgram API key not found"):
                DeepgramSTT(stt_config, utterance_callback)

    def test_deepgram_custom_env_var(self):
        """Test that DeepgramSTT respects custom environment variable name."""
        from backend.exceptions import DeepgramSTTError
        from stt.deepgram_stt import DeepgramSTT

        stt_config = {"api_key_env": "CUSTOM_DEEPGRAM_KEY"}
        utterance_callback = MagicMock()

        # Test with wrong env var name
        with patch.dict(os.environ, {"DEEPGRAM_API_KEY": "key123"}, clear=True):
            with pytest.raises(
                DeepgramSTTError,
                match="Deepgram API key not found: CUSTOM_DEEPGRAM_KEY",
            ):
                DeepgramSTT(stt_config, utterance_callback)


if __name__ == "__main__":
    pytest.main([__file__])
