# ChatBot Error Handling Guide

## Overview

This document describes the comprehensive error handling system implemented following 2025 best practices. The system provides structured, consistent error handling across all modules with proper context preservation and debugging capabilities.

## Exception Hierarchy

### Base Exception

All ChatBot exceptions inherit from `ChatBotBaseException`, which provides:

- **Structured error data** with message, error code, and context
- **Cause tracking** to preserve original exception information
- **JSON serialization** for logging and monitoring
- **Rich string representation** for debugging

```python
from backend import ChatBotBaseException

# Basic usage
raise ChatBotBaseException(
    message="Something went wrong",
    error_code="ERR_001",
    context={"module": "config", "file": "settings.yaml"}
)
```

### Exception Categories

#### Configuration Errors
- `ConfigurationError` - Base for configuration issues
- `ConfigurationValidationError` - Invalid configuration values
- `ConfigurationMissingError` - Required configuration missing
- `ConfigurationLoadError` - Failed to load configuration
- `ServerIncompatibleError` - MCP server doesn't support required features

#### Connection Errors
- `ChatBotConnectionError` - Base for connection issues
- `ServerConnectionError` - MCP server connection failed
- `WebSocketConnectionError` - WebSocket connection issues
- `STTConnectionError` - Speech-to-Text connection problems

#### Session Errors
- `SessionError` - Base for session management issues
- `SessionNotInitializedError` - Session not properly initialized
- `SessionInvalidStateError` - Session in wrong state for operation
- `ToolExecutionError` - MCP tool execution failed

#### Message Processing Errors
- `MessageError` - Base for message handling issues
- `MessageValidationError` - Message validation failed
- `MessageProcessingError` - Error processing message
- `ConversationError` - Conversation management issues

#### WebSocket Errors
- `WebSocketError` - Base for WebSocket issues
- `WebSocketMessageError` - WebSocket message handling failed
- `WebSocketClientError` - WebSocket client issues
- `ChatBotUnavailableError` - ChatBot service unavailable

#### STT (Speech-to-Text) Errors
- `STTError` - Base for STT issues
- `STTInitializationError` - STT initialization failed
- `STTConfigurationError` - STT configuration issues
- `STTServiceError` - STT service problems
- `DeepgramSTTError` - Deepgram-specific issues

#### Resource Management Errors
- `ResourceError` - Base for resource issues
- `ResourceNotFoundError` - Required resource not found
- `ResourceCleanupError` - Resource cleanup failed
- `ResourceExhaustionError` - System resources exhausted

#### External Service Errors
- `ExternalServiceError` - Base for external service issues
- `OpenAIError` - OpenAI API problems
- `DeepgramError` - Deepgram API issues

## Usage Patterns

### Basic Error Raising

```python
from backend import ConfigurationMissingError

# Raise with context
raise ConfigurationMissingError(
    "OpenAI API key not found",
    error_code="CONFIG_OPENAI_KEY_MISSING",
    context={
        "env_var": "OPENAI_API_KEY",
        "config_file": "config.yaml"
    }
)
```

### Exception Wrapping

Use `wrap_exception()` to convert generic exceptions to ChatBot exceptions:

```python
from backend import wrap_exception, ServerConnectionError

try:
    # Some operation that might fail
    connect_to_server()
except Exception as e:
    # Wrap the generic exception
    wrapped = wrap_exception(
        e,
        ServerConnectionError,
        "Failed to connect to MCP server",
        error_code="MCP_CONN_FAILED",
        context={"server_host": "localhost", "port": 8080}
    )
    raise wrapped
```

### Error Handling

```python
from backend import ChatBotBaseException

try:
    # Some operation
    pass
except ChatBotBaseException as e:
    # Access structured error data
    logger.error(f"Operation failed: {e.to_dict()}")
    
    # Check specific error types
    if e.error_code == "CONFIG_001":
        # Handle configuration errors specially
        pass
    
    # Access context data
    if "retry_count" in e.context:
        retry_count = e.context["retry_count"]
        # Implement retry logic
```

## Logging Integration

The structured exceptions integrate well with logging systems:

```python
import logging
from backend import ChatBotBaseException

logger = logging.getLogger(__name__)

try:
    # Some operation
    pass
except ChatBotBaseException as e:
    # Log structured error data
    logger.error("Operation failed", extra=e.to_dict())
    
    # Or log as JSON for structured logging systems
    import json
    logger.error(json.dumps(e.to_dict()))
```

## Error Codes

Error codes follow a consistent pattern:
- `CONFIG_xxx` - Configuration errors
- `CONN_xxx` - Connection errors  
- `SESSION_xxx` - Session errors
- `MSG_xxx` - Message processing errors
- `WS_xxx` - WebSocket errors
- `STT_xxx` - Speech-to-Text errors
- `RESOURCE_xxx` - Resource management errors
- `EXT_xxx` - External service errors

## Benefits

1. **Consistency** - Uniform error handling across all modules
2. **Debugging** - Rich context information for troubleshooting
3. **Monitoring** - Structured data for alerting and metrics
4. **Maintenance** - Clear error categorization and handling
5. **Integration** - Easy integration with logging and monitoring systems

## Migration Guide

To migrate existing code:

1. **Replace generic exceptions**:
   ```python
   # Old
   raise ValueError("Configuration missing")
   
   # New
   raise ConfigurationMissingError(
       "Configuration missing",
       error_code="CONFIG_MISSING",
       context={"setting": "api_key"}
   )
   ```

2. **Update exception handling**:
   ```python
   # Old
   except Exception as e:
       logger.error(f"Error: {e}")
   
   # New
   except ChatBotBaseException as e:
       logger.error("Operation failed", extra=e.to_dict())
   except Exception as e:
       wrapped = wrap_exception(e, SomeSpecificError, "Operation failed")
       logger.error("Unexpected error", extra=wrapped.to_dict())
       raise wrapped
   ```

3. **Add error codes and context**:
   - Define meaningful error codes for each error type
   - Include relevant context information
   - Preserve original exception information when wrapping

## Testing

Test exceptions using the structured data:

```python
def test_configuration_error():
    with pytest.raises(ConfigurationMissingError) as exc_info:
        # Code that should raise the exception
        pass
    
    error = exc_info.value
    assert error.error_code == "CONFIG_MISSING"
    assert "setting" in error.context
    assert error.context["setting"] == "api_key"
```

## Examples

The error handling system is demonstrated throughout the codebase with comprehensive examples in all modules. 