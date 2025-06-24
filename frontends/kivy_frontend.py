#!/usr/bin/env python3
"""
Standalone Kivy Frontend for ChatBot Backend

A placeholder for the Kivy frontend that will connect directly to the FastAPI backend.
This will be implemented when Kivy support is needed.
"""

import sys

# Import client config to get backend connection details
try:
    from backend.connection_config import ConnectionConfig
    client_config = ConnectionConfig()
    backend_config = client_config.get_backend_config()
    WEBSOCKET_URI = f"ws://{backend_config['host']}:{backend_config['port']}/ws/chat"
except Exception as e:
    print(f"Warning: Could not load client config, using defaults: {e}")
    WEBSOCKET_URI = "ws://localhost:8000/ws/chat"

# Check for Kivy availability
try:
    import kivy
    KIVY_AVAILABLE = True
except ImportError:
    KIVY_AVAILABLE = False


def main():
    """Main entry point"""
    print("🎨 Kivy ChatBot Frontend")
    print(f"   Backend: {WEBSOCKET_URI}")
    print()
    
    if not KIVY_AVAILABLE:
        print("❌ Kivy not installed")
        print("💡 To install Kivy:")
        print("   uv add kivy websockets")
        print("   uv add 'kivy[base]'")
        print()
    
    print("🚧 Kivy frontend implementation coming soon!")
    print("   For now, use the terminal frontend:")
    print("   uv run python frontends/terminal_frontend.py")
    print()
    print("👋 The terminal frontend provides full functionality")
    print("   including Speech-to-Text support!")


if __name__ == "__main__":
    main() 