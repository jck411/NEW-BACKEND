"""Security utilities for safe handling of secrets and sensitive data.

This module provides utilities to ensure secrets are never logged or exposed
in stack traces, following security best practices.
"""

import os
import re
from typing import Any, Dict

# Pattern to identify potential secrets in strings
SECRET_PATTERNS = [
    # API keys, secrets, tokens, passwords with key=value format
    re.compile(r'(?i)(api[_\-]?key|secret|token|password|auth)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9._\-/+=]{8,})', re.IGNORECASE),
    # Bearer tokens
    re.compile(r'(?i)(bearer\s+)([a-zA-Z0-9._\-/+=]{20,})', re.IGNORECASE),
    # OpenAI API keys (standalone)
    re.compile(r'(sk-[a-zA-Z0-9._\-/+=]{20,})', re.IGNORECASE),
    # JWT tokens
    re.compile(r'(eyJ[a-zA-Z0-9._\-/+=]+)', re.IGNORECASE),
    # Generic long alphanumeric strings that might be secrets
    re.compile(r'(?i)([a-zA-Z0-9._\-/+=]{32,})', re.IGNORECASE),
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
    from ..exceptions import ConfigurationError
    
    value = os.getenv(var_name)
    if not value:
        raise ConfigurationError(f"{var_name} environment variable is required")
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
    elif isinstance(data, dict):
        # First apply key-based masking, then recursive sanitization
        masked_dict = mask_sensitive_keys(data)
        return {k: sanitize_for_logging(v) if not _is_masked_value(v) else v 
                for k, v in masked_dict.items()}
    elif isinstance(data, (list, tuple)):
        return [sanitize_for_logging(item) for item in data]
    else:
        return data


def _is_masked_value(value: Any) -> bool:
    """Check if a value is already masked."""
    return isinstance(value, str) and value == "***REDACTED***"


def _sanitize_string(text: str) -> str:
    """Sanitize a string to mask potential secrets."""
    result = text
    for i, pattern in enumerate(SECRET_PATTERNS):
        if i == 0:  # API key pattern with groups
            result = pattern.sub(r'\1***REDACTED***', result)
        elif i == 1:  # Bearer token pattern
            result = pattern.sub(r'\1***REDACTED***', result)
        else:  # Standalone secret patterns
            result = pattern.sub('***REDACTED***', result)
    return result


def mask_sensitive_keys(data: Dict[str, Any], sensitive_keys: set[str] = None) -> Dict[str, Any]:
    """Mask specific keys that are known to contain sensitive data.
    
    Args:
        data: Dictionary to sanitize
        sensitive_keys: Set of keys to mask (default: common secret keys)
        
    Returns:
        Dictionary with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = {
            'api_key', 'secret', 'token', 'password', 'auth', 'credential',
            'openai_api_key', 'deepgram_api_key', 'authorization'
        }
    
    result = {}
    for key, value in data.items():
        if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = mask_sensitive_keys(value, sensitive_keys)
        else:
            result[key] = value
    
    return result


class SecureLogger:
    """A wrapper around standard logger that automatically sanitizes sensitive data."""
    
    def __init__(self, logger):
        self.logger = logger
    
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with sanitization."""
        self.logger.debug(sanitize_for_logging(msg), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log info message with sanitization."""
        self.logger.info(sanitize_for_logging(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with sanitization."""
        self.logger.warning(sanitize_for_logging(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log error message with sanitization."""
        self.logger.error(sanitize_for_logging(msg), *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        """Log exception message with sanitization."""
        self.logger.exception(sanitize_for_logging(msg), *args, **kwargs) 