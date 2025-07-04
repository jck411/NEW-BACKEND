"""ChatBot Backend Exception Hierarchy.

Following 2025 best practices for error handling with structured exception classes.
"""

from typing import Any


class ChatBotBaseError(Exception):
    """Base exception for all ChatBot-related errors.

    Provides structured error handling with optional error codes and context.
    Following 2025 best practices for exception design.
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the ChatBot base error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            context: Optional dictionary with additional context
            cause: Optional original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for structured logging and API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " ".join(parts)


# === Configuration Errors ===
class ConfigurationError(ChatBotBaseError):
    """Base class for configuration-related errors."""


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation failed."""


class ConfigurationMissingError(ConfigurationError):
    """Required configuration is missing."""


class ConfigurationLoadError(ConfigurationError):
    """Failed to load configuration from source."""


class ServerIncompatibleError(ConfigurationError):
    """MCP server doesn't implement required interface."""


# === Connection Errors ===
class ChatBotConnectionError(ChatBotBaseError):
    """Base class for connection-related errors."""


class ServerConnectionError(ChatBotConnectionError):
    """Failed to connect to MCP server."""


class WebSocketConnectionError(ChatBotConnectionError):
    """WebSocket connection error."""


class STTConnectionError(ChatBotConnectionError):
    """Speech-to-Text connection error."""


# === Session Errors ===
class SessionError(ChatBotBaseError):
    """Base class for session-related errors."""


class SessionNotInitializedError(SessionError):
    """Session has not been initialized."""


class SessionInvalidStateError(SessionError):
    """Session is in invalid state for requested operation."""


class ToolExecutionError(SessionError):
    """Error executing MCP tool."""


# === Message Processing Errors ===
class MessageError(ChatBotBaseError):
    """Base class for message processing errors."""


class MessageValidationError(MessageError):
    """Message validation failed."""


class MessageProcessingError(MessageError):
    """Error processing message."""


class ConversationError(MessageError):
    """Error in conversation management."""


# === WebSocket Errors ===
class WebSocketError(ChatBotBaseError):
    """Base class for WebSocket-related errors."""


class WebSocketMessageError(WebSocketError):
    """WebSocket message error."""


class WebSocketClientError(WebSocketError):
    """WebSocket client error."""


class ChatBotUnavailableError(WebSocketError):
    """ChatBot service is not available."""


# === STT (Speech-to-Text) Errors ===
class STTError(ChatBotBaseError):
    """Base class for Speech-to-Text errors."""


class STTInitializationError(STTError):
    """STT initialization failed."""


class STTConfigurationError(STTError):
    """STT configuration error."""


class STTServiceError(STTError):
    """STT service error."""


class DeepgramSTTError(STTError):
    """Deepgram-specific STT error."""


# === Resource Management Errors ===
class ResourceError(ChatBotBaseError):
    """Base class for resource management errors."""


class ResourceNotFoundError(ResourceError):
    """Required resource not found."""


class ResourceCleanupError(ResourceError):
    """Error during resource cleanup."""


class ResourceExhaustionError(ResourceError):
    """System resources exhausted."""


# === External Service Errors ===
class ExternalServiceError(ChatBotBaseError):
    """Base class for external service errors."""


class OpenAIError(ExternalServiceError):
    """OpenAI API error."""


class DeepgramError(ExternalServiceError):
    """Deepgram API error."""


# === Utility Functions ===
def wrap_exception(
    exc: Exception,
    exception_class: type = ChatBotBaseError,
    message: str | None = None,
    error_code: str | None = None,
    context: dict[str, Any] | None = None,
) -> ChatBotBaseError:
    """Wrap a generic exception in a ChatBot exception.

    Useful for converting third-party exceptions to our hierarchy.
    """
    if isinstance(exc, ChatBotBaseError):
        return exc

    wrapped_message = message or f"Wrapped exception: {exc!s}"
    wrapped_context = context or {}
    wrapped_context["original_exception"] = exc.__class__.__name__

    return exception_class(
        message=wrapped_message,
        error_code=error_code,
        context=wrapped_context,
        cause=exc,
    )


def get_exception_for_domain(domain: str) -> type:
    """Get the appropriate base exception class for a domain.

    Args:
        domain: The domain name (e.g., 'websocket', 'stt', 'config')

    Returns:
        The appropriate base exception class
    """
    domain_mapping = {
        "config": ConfigurationError,
        "configuration": ConfigurationError,
        "connection": ChatBotConnectionError,
        "session": SessionError,
        "message": MessageError,
        "websocket": WebSocketError,
        "stt": STTError,
        "speech": STTError,
        "resource": ResourceError,
        "external": ExternalServiceError,
        "openai": OpenAIError,
        "deepgram": DeepgramError,
    }

    return domain_mapping.get(domain.lower(), ChatBotBaseError)
