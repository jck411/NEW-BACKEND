"""Security utilities for safe handling of secrets and sensitive data.

This module provides utilities to ensure secrets are never logged or exposed
in stack traces, following security best practices.
"""

import logging
import os
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from backend.exceptions import ConfigurationError

# Pattern to identify potential secrets in strings
SECRET_PATTERNS = [
    # API keys, secrets, tokens, passwords with key=value format
    re.compile(
        r'(?i)(api[_\-]?key|secret|token|password|auth)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._\-/+=]{8,})',
        re.IGNORECASE,
    ),
    # Bearer tokens
    re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9._\-/+=]{20,})", re.IGNORECASE),
    # OpenAI API keys (standalone)
    re.compile(r"(sk-[a-zA-Z0-9._\-/+=]{20,})", re.IGNORECASE),
    # JWT tokens
    re.compile(r"(eyJ[a-zA-Z0-9._\-/+=]+)", re.IGNORECASE),
    # Generic long alphanumeric strings that might be secrets
    re.compile(r"(?i)([a-zA-Z0-9._\-/+=]{32,})", re.IGNORECASE),
]


def get_required_env_var(var_name: str) -> str:
    """Safely get a required environment variable.

    Args:
        var_name: Name of the environment variable

    Returns:
        The environment variable value

    Raises:
        ConfigurationError: If the environment variable is not set
    """
    value = os.getenv(var_name)
    if not value:
        msg = f"{var_name} environment variable is required"
        raise ConfigurationError(msg)
    return value


def get_optional_env_var(var_name: str, default: str = "") -> str:
    """Safely get an optional environment variable.

    Args:
        var_name: Name of the environment variable
        default: Default value if not set

    Returns:
        The environment variable value or default
    """
    return os.getenv(var_name, default)


def sanitize_for_logging(data: Any) -> Any:
    """Sanitize data to remove potential secrets before logging.

    Args:
        data: Data to sanitize (string, dict, list, etc.)

    Returns:
        Sanitized data with secrets masked
    """
    if isinstance(data, str):
        return _sanitize_string(data)
    if isinstance(data, dict):
        # Type hint for static analysis
        typed_data: dict[str, Any] = cast("dict[str, Any]", data)
        masked_dict = mask_sensitive_keys(typed_data)
        return {
            k: sanitize_for_logging(v) if not _is_masked_value(v) else v
            for k, v in masked_dict.items()
        }
    if isinstance(data, (list, tuple)):
        # Type hint for static analysis
        typed_seq: Sequence[Any] = cast("Sequence[Any]", data)
        return [sanitize_for_logging(item) for item in typed_seq]
    return data


def _is_masked_value(value: Any) -> bool:
    """Check if a value is already masked."""
    return isinstance(value, str) and value == "***REDACTED***"


def _sanitize_string(text: str) -> str:
    """Sanitize a string to mask potential secrets."""
    result = text
    for i, pattern in enumerate(SECRET_PATTERNS):
        if i in {0, 1}:  # API key pattern with groups
            result = pattern.sub(r"\1***REDACTED***", result)
        else:  # Standalone secret patterns
            result = pattern.sub("***REDACTED***", result)
    return result


def mask_sensitive_keys(
    data: Mapping[str, Any], sensitive_keys: set[str] | None = None
) -> dict[str, Any]:
    """Mask specific keys that are known to contain sensitive data.

    Args:
        data: Dictionary to sanitize
        sensitive_keys: Set of keys to mask (default: common secret keys)

    Returns:
        Dictionary with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = {
            "api_key",
            "secret",
            "token",
            "password",
            "auth",
            "credential",
            "openai_api_key",
            "deepgram_api_key",
            "authorization",
        }

    result: dict[str, Any] = {}
    for key, value in data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Type hint for static analysis
            nested_dict: Mapping[str, Any] = cast("Mapping[str, Any]", value)
            result[key] = mask_sensitive_keys(nested_dict, sensitive_keys)
        else:
            result[key] = value

    return result


class SecureLogger:
    """A wrapper around standard logger that automatically sanitizes sensitive data."""

    def __init__(self, logger: logging.Logger) -> None:
        """Initialize the SecureLogger with a standard logger.

        Args:
            logger: The underlying logger to wrap
        """
        self.logger = logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with sanitization."""
        self.logger.debug(sanitize_for_logging(msg), *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with sanitization."""
        self.logger.info(sanitize_for_logging(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with sanitization."""
        self.logger.warning(sanitize_for_logging(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with sanitization."""
        self.logger.error(sanitize_for_logging(msg), *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception message with sanitization."""
        self.logger.exception(sanitize_for_logging(msg), *args, **kwargs)
