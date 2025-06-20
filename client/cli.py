#!/usr/bin/env python3
"""
Command Line Interface for MCP ChatBot

Usage:
    python -m client.cli
    python -c "from client.cli import main; import asyncio; asyncio.run(main())"
"""

import asyncio
import logging
import os

import nest_asyncio
from dotenv import load_dotenv

from .chatbot import ChatBot

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


async def main():
    """Main entry point for the chatbot."""
    chatbot = None
    try:
        chatbot = ChatBot()
        tools = await chatbot.connect_to_server()
        
        print("\n🤖 MCP ChatBot initialized with the following tools:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
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
    finally:
        if chatbot is not None:
            await chatbot.cleanup()


def cli():
    """Synchronous entry point for CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    cli() 