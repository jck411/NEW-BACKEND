"""
Structured logging configuration using structlog.
Provides JSON logging with event, module, elapsed_ms fields as required by rules.
"""

import logging
import sys
import time
from typing import Any

import structlog
from structlog.types import EventDict


def add_module_name(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add module name to log entries."""
    import inspect
    frame = inspect.currentframe()
    try:
        for _ in range(10):
            frame = frame.f_back
            if frame is None:
                break
            module_name = frame.f_globals.get('__name__', 'unknown')
            if not module_name.startswith('structlog') and not module_name.startswith('logging'):
                event_dict["module"] = module_name
                break
        else:
            event_dict["module"] = "unknown"
    finally:
        del frame
    return event_dict


def add_elapsed_ms():
    """Add elapsed_ms field to track timing."""
    start_time = time.time()

    def processor(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        current_time = time.time()
        event_dict["elapsed_ms"] = round((current_time - start_time) * 1000, 2)
        return event_dict

    return processor


def add_severity_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add severity level for better log filtering."""
    level_mapping = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARNING",
        "error": "ERROR",
        "critical": "CRITICAL"
    }
    event_dict["level"] = level_mapping.get(method_name, method_name.upper())
    return event_dict


def configure_structured_logging(level: str = "INFO", format_json: bool = True) -> None:
    """Configure structured logging with JSON output."""
    # Clear any existing configuration
    structlog.reset_defaults()

    processors = [
        structlog.contextvars.merge_contextvars,
        add_module_name,
        add_elapsed_ms(),
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO", utc=True),
    ]

    if format_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (defaults to calling module)
        
    Returns:
        Configured structlog BoundLogger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("User login", event="user_login", user_id=123, success=True)
    """
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')

    return structlog.get_logger(name)


def log_function_call(func_name: str):
    """
    Decorator to log function calls with timing.
    
    Example:
        @log_function_call("process_message")
        async def process_message(self, message: str):
            ...
    """
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = time.time()

            try:
                logger.info(
                    "Function started",
                    event="function_start",
                    function=func_name,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )

                result = await func(*args, **kwargs)

                elapsed = round((time.time() - start_time) * 1000, 2)
                logger.info(
                    "Function completed",
                    event="function_complete",
                    function=func_name,
                    elapsed_ms=elapsed,
                    success=True
                )

                return result

            except Exception as e:
                elapsed = round((time.time() - start_time) * 1000, 2)
                logger.error(
                    "Function failed",
                    event="function_error",
                    function=func_name,
                    elapsed_ms=elapsed,
                    error=str(e),
                    exception_type=type(e).__name__
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger()
            start_time = time.time()

            try:
                logger.info(
                    "Function started",
                    event="function_start",
                    function=func_name,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )

                result = func(*args, **kwargs)

                elapsed = round((time.time() - start_time) * 1000, 2)
                logger.info(
                    "Function completed",
                    event="function_complete",
                    function=func_name,
                    elapsed_ms=elapsed,
                    success=True
                )

                return result

            except Exception as e:
                elapsed = round((time.time() - start_time) * 1000, 2)
                logger.error(
                    "Function failed",
                    event="function_error",
                    function=func_name,
                    elapsed_ms=elapsed,
                    error=str(e),
                    exception_type=type(e).__name__
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
