"""
Error handling utilities and decorators for standardized error management
"""
import functools
import logging
from typing import Any, Callable, Dict, Optional, Type

from ..exceptions import ChatBotBaseException, wrap_exception


def handle_errors(
    exception_class: Type[ChatBotBaseException],
    message: str,
    error_code: Optional[str] = None,
    log_level: int = logging.ERROR,
    reraise: bool = True
):
    """
    Decorator for standardized error handling with logging and exception wrapping.
    
    Args:
        exception_class: Exception class to wrap to
        message: Error message template  
        error_code: Optional error code
        log_level: Logging level (default ERROR)
        reraise: Whether to reraise the wrapped exception
        
    Usage:
        @handle_errors(ConfigurationError, "Failed to load config", "CONFIG_LOAD_FAILED")
        async def load_config(self):
            # Implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Get logger from self if available, otherwise create one
                logger = getattr(args[0], 'logger', None) if args else None
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                # Format message with function name
                formatted_message = f"{message} in {func.__name__}"
                logger.log(log_level, f"{formatted_message}: {e}")
                
                if reraise:
                    wrapped_error = wrap_exception(
                        e, exception_class, formatted_message, 
                        error_code=error_code,
                        context={"function": func.__name__, "args": str(args[1:]) if len(args) > 1 else None}
                    )
                    raise wrapped_error
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get logger from self if available, otherwise create one
                logger = getattr(args[0], 'logger', None) if args else None
                if logger is None:
                    logger = logging.getLogger(func.__module__)
                
                # Format message with function name
                formatted_message = f"{message} in {func.__name__}"
                logger.log(log_level, f"{formatted_message}: {e}")
                
                if reraise:
                    wrapped_error = wrap_exception(
                        e, exception_class, formatted_message,
                        error_code=error_code,
                        context={"function": func.__name__, "args": str(args[1:]) if len(args) > 1 else None}
                    )
                    raise wrapped_error
                    
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def log_and_wrap_error(
    exception: Exception,
    exception_class: Type[ChatBotBaseException],
    message: str,
    error_code: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> ChatBotBaseException:
    """
    Standardized error logging and wrapping utility.
    
    Args:
        exception: Original exception
        exception_class: Target exception class
        message: Error message
        error_code: Optional error code
        context: Additional context information
        logger: Logger instance (if None, creates one)
        
    Returns:
        Wrapped exception
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.error(f"{message}: {exception}")
    
    return wrap_exception(
        exception, exception_class, message,
        error_code=error_code,
        context=context
    )


# Convenience decorators for common error types
def handle_config_errors(message: str, error_code: Optional[str] = None):
    """Decorator for configuration-related errors"""
    from ..exceptions import ConfigurationError
    return handle_errors(ConfigurationError, message, error_code)


def handle_connection_errors(message: str, error_code: Optional[str] = None):
    """Decorator for connection-related errors"""  
    from ..exceptions import ServerConnectionError
    return handle_errors(ServerConnectionError, message, error_code)


def handle_session_errors(message: str, error_code: Optional[str] = None):
    """Decorator for session-related errors"""
    from ..exceptions import SessionError
    return handle_errors(SessionError, message, error_code) 