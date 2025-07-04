#!/usr/bin/env python3
"""ChatBot Backend Server Entry Point
Usage: python -m backend [--server-path PATH] [--show-config].
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from .chatbot import ChatBot


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP ChatBot Backend Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start backend server
  python -m backend

  # Use specific MCP server
  python -m backend --server-path "/path/to/medical_server.py"

  # Show current config
  python -m backend --show-config
        """,
    )

    parser.add_argument("--server-path", help="Path to MCP server to use")

    parser.add_argument(
        "--show-config", action="store_true", help="Show current server configuration"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def launch_backend_server() -> None:
    """Launch the backend API server."""
    try:
        # Get the absolute path to run_backend.py
        backend_script = Path(__file__).parent.parent / "run_backend.py"

        if not backend_script.exists():
            msg = f"Backend script not found: {backend_script}"
            raise FileNotFoundError(msg)

        # Run the backend script
        subprocess.run([sys.executable, str(backend_script)], check=True)

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except (FileNotFoundError, OSError, RuntimeError):
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    try:
        # Initialize chatbot to get config
        chatbot = ChatBot()

        if args.show_config:
            try:
                server_path = chatbot.get_configured_server_path()
                backend_config = chatbot.connection_config.get_backend_config()
                stt_enabled = chatbot.connection_config.is_stt_enabled()

                print(f"Server Path: {server_path}")
                print(f"Backend Config: {backend_config}")
                print(f"STT Enabled: {stt_enabled}")
            except (RuntimeError, ValueError, AttributeError):
                print("Error retrieving configuration")
            return

        # Set server path if provided
        if args.server_path:
            chatbot.set_server_path(args.server_path)

        # Launch backend server
        launch_backend_server()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except (RuntimeError, ValueError, AttributeError, FileNotFoundError) as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
