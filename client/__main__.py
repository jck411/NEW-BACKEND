#!/usr/bin/env python3
"""
Simple entry point for the MCP ChatBot.
Usage: python -m client [--server-path PATH] [--show-config]
"""

import argparse
import asyncio
import logging
import sys

from .chatbot import ChatBot


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP ChatBot - Connect to specialized MCP servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use configured server
  python -m client
  
  # Use specific server
  python -m client --server-path "/path/to/medical_server.py"
  
  # Show current config
  python -m client --show-config
        """
    )
    
    parser.add_argument(
        "--server-path",
        help="Path to MCP server to use"
    )
    
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show current server configuration"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    
    try:
        # Initialize chatbot
        chatbot = ChatBot()
        
        if args.show_config:
            print(f"\n📋 Current Server Configuration:")
            try:
                server_path = chatbot.get_configured_server_path()
                print(f"  Server Path: {server_path}")
            except Exception as e:
                print(f"  Error: {e}")
            return
        
        # Set server path if provided
        if args.server_path:
            chatbot.set_server_path(args.server_path)
            print(f"✅ Using server: {args.server_path}")
        
        # Connect to server
        server_path = chatbot.get_configured_server_path()
        print(f"🔌 Connecting to MCP server: {server_path}")
        
        tools = await chatbot.connect_to_server()
        
        # Show connection info
        server_info = chatbot.get_current_server_info()
        print(f"✅ Connected! Available tools: {len(tools.tools)}")
        for tool in tools.tools:
            print(f"  - {tool.name}")
            
        print("\n💬 Start chatting (Ctrl+C to exit):")
        
        # Chat loop
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye!")
                    break
                if user_input:
                    print("\n🤖 Assistant: ", end="", flush=True)
                    async for chunk in chatbot.process_message(user_input):
                        print(chunk, end="", flush=True)
                    print()  # New line after response
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'chatbot' in locals():
            await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 