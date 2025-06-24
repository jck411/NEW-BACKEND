#!/usr/bin/env python3
"""
Demo script showing the improved error handling with structured exceptions
"""
import logging
from backend.exceptions import (
    ChatBotBaseException,
    ConfigurationError,
    ServerConnectionError,
    WebSocketError,
    STTError,
    wrap_exception
)

# Configure logging to show structured error information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_structured_exceptions():
    """Demonstrate the structured exception hierarchy."""
    
    print("🎯 ChatBot Exception Hierarchy Demo")
    print("=" * 50)
    
    # Example 1: Configuration Error with Context
    try:
        raise ConfigurationError(
            "Missing required configuration setting",
            error_code="CONFIG_001",
            context={
                "setting_name": "openai.api_key",
                "config_file": "config.yaml"
            }
        )
    except ChatBotBaseException as e:
        print(f"\n📋 Configuration Error Example:")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")
        print(f"   Context: {e.context}")
        print(f"   Structured Data: {e.to_dict()}")
    
    # Example 2: Connection Error with Cause
    try:
        # Simulate a connection failure
        original_error = ConnectionError("Network unreachable")
        wrapped = wrap_exception(
            original_error,
            ServerConnectionError,
            "Failed to connect to MCP server",
            error_code="CONN_001",
            context={"server_host": "localhost", "server_port": 8080}
        )
        raise wrapped
    except ChatBotBaseException as e:
        print(f"\n🔌 Connection Error Example:")
        print(f"   Message: {e.message}")
        print(f"   Error Code: {e.error_code}")
        print(f"   Context: {e.context}")
        print(f"   Original Cause: {e.cause}")
    
    # Example 3: Nested Exception Handling
    try:
        try:
            # Inner operation that fails
            raise ValueError("Invalid input format")
        except ValueError as inner_e:
            # Wrap and re-raise with context
            wrapped = wrap_exception(
                inner_e,
                WebSocketError,
                "WebSocket message processing failed",
                error_code="WS_MSG_001",
                context={"client_id": "client-123", "message_type": "text"}
            )
            raise wrapped
    except ChatBotBaseException as e:
        print(f"\n💬 WebSocket Error Example:")
        print(f"   Error Type: {e.__class__.__name__}")
        print(f"   Message: {e.message}")
        print(f"   Full String: {str(e)}")
        logger.error(f"WebSocket error occurred: {e.to_dict()}")
    
    # Example 4: STT Error Chain
    try:
        # Simulate STT service failure
        service_error = RuntimeError("Deepgram service unavailable")
        stt_error = wrap_exception(
            service_error,
            STTError,
            "Speech-to-Text service failed",
            error_code="STT_SERVICE_DOWN",
            context={"service": "deepgram", "retry_count": 3}
        )
        raise stt_error
    except ChatBotBaseException as e:
        print(f"\n🎤 STT Error Example:")
        print(f"   Service: {e.context.get('service', 'unknown')}")
        print(f"   Retry Count: {e.context.get('retry_count', 0)}")
        print(f"   Root Cause: {e.cause}")
    
    print(f"\n✅ Demo completed successfully!")
    print("Benefits of this approach:")
    print("  • Consistent error handling across all modules")
    print("  • Structured error data for logging and monitoring")  
    print("  • Error context preservation")
    print("  • Easy error categorization and filtering")
    print("  • Better debugging and troubleshooting")


if __name__ == "__main__":
    demo_structured_exceptions() 