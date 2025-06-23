#!/usr/bin/env python3
"""
Simple entry point for the MCP ChatBot.
Usage: python -m client [--server-path PATH] [--show-config]
"""

import argparse
import asyncio
import logging
import sys
import queue
import threading

from .chatbot import ChatBot
from STT import DeepgramSTT


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
            
        # Check if STT is enabled
        stt_enabled = chatbot.connection_config.is_stt_enabled()
        stt_instance = None
        message_queue = queue.Queue()
        
        if stt_enabled:
            try:
                stt_config = chatbot.connection_config.get_stt_config()
                
                def utterance_callback(utterance: str):
                    """Handle complete utterances from STT."""
                    message_queue.put(('stt', utterance))
                
                stt_instance = DeepgramSTT(stt_config, utterance_callback)
                stt_instance.start()
                print("🎤 Speech-to-Text enabled - speak into your microphone!")
                print("💬 You can also type messages or say 'exit', 'quit', or 'bye' to stop")
            except Exception as e:
                print(f"⚠️  STT initialization failed: {e}")
                print("💬 Continuing with text-only mode")
                stt_enabled = False
        else:
            print("\n💬 Start chatting (type your messages, Ctrl+C to exit):")
        
        # Chat loop with STT integration
        def keyboard_input_thread():
            """Handle keyboard input in a separate thread."""
            while True:
                try:
                    user_input = input().strip() if not stt_enabled else input("\nType (or speak): ").strip()
                    if user_input:
                        message_queue.put(('keyboard', user_input))
                except (EOFError, KeyboardInterrupt):
                    message_queue.put(('quit', None))
                    break
        
        # Start keyboard input thread
        input_thread = threading.Thread(target=keyboard_input_thread, daemon=True)
        input_thread.start()
        
        try:
            while True:
                try:
                    # Get next message (either from STT or keyboard)
                    message_type, user_input = message_queue.get(timeout=0.1)
                    
                    if message_type == 'quit':
                        print("\n👋 Goodbye!")
                        break
                    elif message_type in ['stt', 'keyboard']:
                        # Normalize input for quit commands (remove punctuation, lowercase)
                        normalized_input = user_input.lower().strip().rstrip('.,!?;:')
                        if normalized_input in ['exit', 'quit', 'bye']:
                            print("\n👋 Goodbye!")
                            break
                        
                        if user_input:
                            # Show user input (especially important for STT)
                            if message_type == 'stt':
                                print(f"\n🎤 You (speech): {user_input}")
                            else:
                                print(f"\n⌨️  You: {user_input}")
                            
                            print("🤖 Assistant: ", end="", flush=True)
                            
                            # Pause STT during response streaming if enabled
                            if stt_instance:
                                stt_instance.pause_for_response_streaming()
                            
                            try:
                                async for chunk in chatbot.process_message(user_input):
                                    print(chunk, end="", flush=True)
                                print()  # New line after response
                            finally:
                                # Resume STT after response is complete
                                if stt_instance:
                                    stt_instance.resume_from_response_streaming()
                                    
                except queue.Empty:
                    continue
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    # Resume STT after error
                    if stt_instance:
                        stt_instance.resume_from_response_streaming()
        finally:
            # Cleanup STT
            if stt_instance:
                try:
                    stt_instance.cleanup()
                except Exception as e:
                    print(f"Warning: STT cleanup error: {e}")
                
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'chatbot' in locals():
            try:
                await chatbot.cleanup()
            except (KeyboardInterrupt, asyncio.CancelledError):
                # Ignore cleanup errors from interrupted operations
                pass
            except Exception as e:
                print(f"Warning: Cleanup error: {e}")
        
        # Additional STT cleanup if it exists
        if 'stt_instance' in locals() and stt_instance:
            try:
                stt_instance.cleanup()
            except Exception as e:
                print(f"Warning: STT cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 