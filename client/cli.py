#!/usr/bin/env python3
"""
Command Line Interface for MCP ChatBot

This CLI connects to the MCP server specified in client/client_config.yaml.

Usage:
    # Connect to configured server
    python -m client.cli
    
    # Override with direct server command
    python -m client.cli --server-command "python /path/to/your/server.py"
    python -m client.cli --server-command "node /path/to/server.js"
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import List, Optional

import nest_asyncio
from dotenv import load_dotenv

from .chatbot import ChatBot

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP ChatBot CLI - Connect to any compatible MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect to configured server
  python -m client.cli
  
  # Override with direct command
  python -m client.cli --server-command "python /path/to/config_server.py"
  python -m client.cli --server-command "node /path/to/server.js"
  
  # Show current configuration
  python -m client.cli --show-config
  
  # Set server path
  python -m client.cli --set-server-path "/path/to/your/server.py"
  
Server Requirements:
  Any MCP server used must implement these tools:
  - get_config: Return configuration as JSON
  - get_config_version: Return config version for change detection
        """
    )
    
    parser.add_argument(
        "--server-command",
        type=str,
        help="Direct server command (overrides config)"
    )
    
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show current server configuration"
    )
    
    parser.add_argument(
        "--set-server-path",
        type=str,
        help="Set the server path in configuration"
    )
    
    parser.add_argument(
        "--connection-config",
        type=str,
        default="client/client_config.yaml",
        help="Path to connection configuration file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--show-requirements",
        action="store_true", 
        help="Show server requirements and exit"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point for the chatbot."""
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    
    if args.show_requirements:
        print("\n🤖 MCP ChatBot Server Requirements:")
        print("\nRequired Tools (any compatible MCP server must implement):")
        try:
            chatbot = ChatBot(args.connection_config)
            requirements = chatbot.get_server_requirements()
            for tool, description in requirements.items():
                print(f"  - {tool}: {description}")
                
            print("\nOptional Tools (enhance functionality if available):")
            optional = chatbot.get_server_optional_features()
            for tool, description in optional.items():
                print(f"  - {tool}: {description}")
        except Exception as e:
            print(f"Error: {e}")
        return
    
    try:
        # Initialize chatbot with connection config
        chatbot = ChatBot(args.connection_config)
        
        if args.show_config:
            print(f"\n📋 Current Server Configuration ({chatbot.get_connection_config_path()}):")
            try:
                server_path = chatbot.get_configured_server_path()
                print(f"  Server Path: {server_path}")
            except Exception as e:
                print(f"  Error: {e}")
            return
        
        if args.set_server_path:
            try:
                chatbot.set_server_path(args.set_server_path)
                print(f"✅ Server path updated to: {args.set_server_path}")
            except Exception as e:
                print(f"❌ Error setting server path: {e}")
                sys.exit(1)
            return
        
        # Connect to server
        if args.server_command:
            print(f"🔌 Connecting to MCP server: {args.server_command}")
            tools = await chatbot.connect_to_server(server_command=args.server_command)
        else:
            try:
                server_path = chatbot.get_configured_server_path()
                print(f"🔌 Connecting to configured MCP server: {server_path}")
                tools = await chatbot.connect_to_server()
            except Exception as e:
                print(f"❌ Error: {e}")
                print(f"\nTip: Set server path with --set-server-path \"/path/to/your/server.py\"")
                sys.exit(1)
        
        # Show server info
        server_info = chatbot.get_current_server_info()
        print(f"✅ Connected to: {' '.join(server_info['full_command'])}")
        
        print(f"\n🤖 MCP ChatBot initialized with {len(tools.tools)} tools:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
            
        # Show server capabilities
        capabilities = server_info.get('capabilities', {})
        required_missing = [tool for tool, available in capabilities.items() 
                           if not available and tool in chatbot.get_server_requirements()]
        if required_missing:
            print(f"\n⚠️  Warning: Server missing required tools: {required_missing}")
            
        optional_available = [tool for tool, available in capabilities.items() 
                             if available and tool in chatbot.get_server_optional_features()]
        if optional_available:
            print(f"✨ Server provides optional features: {optional_available}")
            
        print("\n💬 You can start chatting (press Ctrl+C to exit):")
        
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
                logging.error(f"Error during chat: {str(e)}")
                print(f"\n❌ Error: {e}")
                
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        logging.error(f"Initialization error: {str(e)}")
        print(f"\nTip: Use --show-config to see current configuration")
        print(f"     Use --set-server-path to configure server location")
        print(f"     Use --show-requirements to see server requirements")
        sys.exit(1)
    finally:
        if 'chatbot' in locals():
            await chatbot.cleanup()


def cli():
    """Synchronous entry point for CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    cli() 