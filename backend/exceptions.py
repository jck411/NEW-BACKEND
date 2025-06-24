"""
ChatBot Backend Exception Hierarchy
Following 2025 best practices for error handling with structured exception classes
"""
from typing import Optional, Dict, Any


class ChatBotBaseException(Exception):
    """
    Base exception for all ChatBot-related errors.
    
    Provides structured error handling with optional error codes and context.
    Following 2025 best practices for exception design.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging and API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " ".join(parts)


# === Configuration Errors ===
class ConfigurationError(ChatBotBaseException):
    """Base class for configuration-related errors."""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation failed."""
    pass


class ConfigurationMissingError(ConfigurationError):
    """Required configuration is missing."""
    pass


class ConfigurationLoadError(ConfigurationError):
    """Failed to load configuration from source."""
    pass


class ServerIncompatibleError(ConfigurationError):
    """MCP server doesn't implement required interface."""
    pass


# === Connection Errors ===
class ConnectionError(ChatBotBaseException):
    """Base class for connection-related errors."""
    pass


class ServerConnectionError(ConnectionError):
    """Failed to connect to MCP server."""
    pass


class WebSocketConnectionError(ConnectionError):
    """WebSocket connection error."""
    pass


class STTConnectionError(ConnectionError):
    """Speech-to-Text connection error."""
    pass


# === Session Errors ===
class SessionError(ChatBotBaseException):
    """Base class for session-related errors."""
    pass


class SessionNotInitializedError(SessionError):
    """Session has not been initialized."""
    pass


class SessionInvalidStateError(SessionError):
    """Session is in invalid state for requested operation."""
    pass


class ToolExecutionError(SessionError):
    """Error executing MCP tool."""
    pass


# === Message Processing Errors ===
class MessageError(ChatBotBaseException):
    """Base class for message processing errors."""
    pass


class MessageValidationError(MessageError):
    """Message validation failed."""
    pass


class MessageProcessingError(MessageError):
    """Error processing message."""
    pass


class ConversationError(MessageError):
    """Error in conversation management."""
    pass


# === WebSocket Errors ===
class WebSocketError(ChatBotBaseException):
    """Base class for WebSocket-related errors."""
    pass


class WebSocketMessageError(WebSocketError):
    """WebSocket message error."""
    pass


class WebSocketClientError(WebSocketError):
    """WebSocket client error."""
    pass


class ChatBotUnavailableError(WebSocketError):
    """ChatBot service is not available."""
    pass


# === STT (Speech-to-Text) Errors ===
class STTError(ChatBotBaseException):
    """Base class for Speech-to-Text errors."""
    pass


class STTInitializationError(STTError):
    """STT initialization failed."""
    pass


class STTConfigurationError(STTError):
    """STT configuration error."""
    pass


class STTServiceError(STTError):
    """STT service error."""
    pass


class DeepgramSTTError(STTError):
    """Deepgram-specific STT error."""
    pass


# === Resource Management Errors ===
class ResourceError(ChatBotBaseException):
    """Base class for resource management errors."""
    pass


class ResourceNotFoundError(ResourceError):
    """Required resource not found."""
    pass


class ResourceCleanupError(ResourceError):
    """Error during resource cleanup."""
    pass


class ResourceExhaustionError(ResourceError):
    """System resources exhausted."""
    pass


# === External Service Errors ===
class ExternalServiceError(ChatBotBaseException):
    """Base class for external service errors."""
    pass


class OpenAIError(ExternalServiceError):
    """OpenAI API error."""
    pass


class DeepgramError(ExternalServiceError):
    """Deepgram API error."""
    pass


# === Utility Functions ===
def wrap_exception(
    exc: Exception,
    exception_class: type = ChatBotBaseException,
    message: Optional[str] = None,
    error_code: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ChatBotBaseException:
    """
    Wrap a generic exception in a ChatBot exception.
    
    Useful for converting third-party exceptions to our hierarchy.
    """
    if isinstance(exc, ChatBotBaseException):
        return exc
    
    wrapped_message = message or f"Wrapped exception: {str(exc)}"
    wrapped_context = context or {}
    wrapped_context['original_exception'] = exc.__class__.__name__
    
    return exception_class(
        message=wrapped_message,
        error_code=error_code,
        context=wrapped_context,
        cause=exc
    )


def get_exception_for_domain(domain: str) -> type:
    """
    Get the appropriate base exception class for a domain.
    
    Args:
        domain: The domain name (e.g., 'websocket', 'stt', 'config')
        
    Returns:
        The appropriate base exception class
    """
    domain_mapping = {
        'config': ConfigurationError,
        'configuration': ConfigurationError,
        'connection': ConnectionError,
        'session': SessionError,
        'message': MessageError,
        'websocket': WebSocketError,
        'stt': STTError,
        'speech': STTError,
        'resource': ResourceError,
        'external': ExternalServiceError,
        'openai': OpenAIError,
        'deepgram': DeepgramError,
    }
    
    return domain_mapping.get(domain.lower(), ChatBotBaseException) 