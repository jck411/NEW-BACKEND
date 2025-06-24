#!/usr/bin/env python3
"""
Standalone Terminal Frontend for ChatBot Backend

A simple terminal-based frontend that connects to the FastAPI backend via WebSocket.
Supports real-time streaming chat and optional Speech-to-Text.
"""

import asyncio
import json
import uuid
import threading
import queue
import sys
from typing import Optional, Dict, Any

import websockets
import websockets.exceptions

# Import backend config to get backend connection details and STT config
try:
    from backend.connection_config import ConnectionConfig
    from STT import DeepgramSTT
    
    client_config = ConnectionConfig()
    backend_config = client_config.get_backend_config()
    WEBSOCKET_URI = f"ws://{backend_config['host']}:{backend_config['port']}/ws/chat"
    STT_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not load backend config or STT, using defaults: {e}")
    WEBSOCKET_URI = "ws://localhost:8000/ws/chat"
    STT_AVAILABLE = False


class TerminalChatClient:
    """Terminal-based chat client"""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connection_status = "Disconnected"
        self.current_message_id: Optional[str] = None
        self.message_queue = queue.Queue()
        self.stt_instance = None
        self.stt_enabled = False
        
    async def connect(self):
        """Connect to the backend WebSocket"""
        try:
            print(f"🔌 Connecting to backend: {WEBSOCKET_URI}")
            self.websocket = await websockets.connect(WEBSOCKET_URI)
            self.connection_status = "Connected"
            print("✅ Connected to ChatBot backend!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.handle_message(data)
                except Exception as e:
                    print(f"\n❌ Message handling error: {e}")
        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 Connection lost")
            self.connection_status = "Disconnected"
        except Exception as e:
            print(f"\n❌ Listen error: {e}")
            self.connection_status = "Error"
    
    def handle_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        msg_type = data.get("type")
        
        if msg_type == "message_start":
            # Start of new message
            self.current_message_id = data.get("id")
            user_message = data.get("user_message", "")
            
            # Show user message if not already displayed
            if user_message and (not hasattr(self, '_last_user_message') or self._last_user_message != user_message):
                print(f"\n⌨️  You: {user_message}")
                self._last_user_message = user_message
            
            print("🤖 Assistant: ", end="", flush=True)
            
        elif msg_type == "text_chunk":
            # Streaming text chunk
            content = data.get("content", "")
            print(content, end="", flush=True)
            
        elif msg_type == "message_complete":
            # Message finished
            print()  # New line after response
            self.current_message_id = None
            
            # Resume STT if it was paused
            if self.stt_instance:
                self.stt_instance.resume_from_response_streaming()
                
        elif msg_type == "error":
            error_msg = data.get("error", "Unknown error")
            print(f"\n❌ Error: {error_msg}")
            
        elif msg_type == "connection_established":
            client_id = data.get("client_id", "unknown")
            print(f"🔌 Connected as client: {client_id}")
    
    async def send_message(self, message: str):
        """Send a message to the backend"""
        if not self.websocket:
            print("❌ Not connected to server")
            return
        
        # Check if connection is still open
        try:
            # Try to check connection state - websockets 12+ uses different attributes
            if hasattr(self.websocket, 'closed') and self.websocket.closed:
                print("❌ Connection closed")
                return
            elif hasattr(self.websocket, 'state') and self.websocket.state.name == 'CLOSED':
                print("❌ Connection closed")
                return
        except AttributeError:
            # If we can't check the state, we'll try to send and handle errors
            pass
        
        # Pause STT during message sending
        if self.stt_instance:
            self.stt_instance.pause_for_response_streaming()
        
        message_data = {
            "type": "text_message",
            "id": str(uuid.uuid4()),
            "content": message
        }
        
        try:
            await self.websocket.send(json.dumps(message_data))
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            # Resume STT on error
            if self.stt_instance:
                self.stt_instance.resume_from_response_streaming()
    
    def setup_stt(self):
        """Setup Speech-to-Text if available and enabled"""
        if not STT_AVAILABLE:
            return False
        
        try:
            stt_config = client_config.get_stt_config()
            if not stt_config.get('enabled', False):
                return False
            
            def utterance_callback(utterance: str):
                """Handle complete utterances from STT."""
                self.message_queue.put(('stt', utterance))
            
            self.stt_instance = DeepgramSTT(stt_config, utterance_callback)
            self.stt_instance.start()
            self.stt_enabled = True
            return True
            
        except Exception as e:
            print(f"⚠️  STT initialization failed: {e}")
            return False
    
    def keyboard_input_thread(self):
        """Handle keyboard input in a separate thread"""
        while True:
            try:
                if self.stt_enabled:
                    user_input = input("\nType (or speak): ").strip()
                else:
                    user_input = input("> ").strip()
                    
                if user_input:
                    self.message_queue.put(('keyboard', user_input))
            except (EOFError, KeyboardInterrupt):
                self.message_queue.put(('quit', None))
                break
    
    async def run(self):
        """Main chat loop"""
        # Connect to backend
        if not await self.connect():
            return
        
        # Setup STT if available
        stt_setup_success = self.setup_stt()
        if stt_setup_success:
            print("🎤 Speech-to-Text enabled - speak into your microphone!")
            print("💬 You can also type messages or say 'exit', 'quit', or 'bye' to stop")
        else:
            print("\n💬 Start chatting (type your messages, Ctrl+C to exit):")
        
        # Start keyboard input thread
        input_thread = threading.Thread(target=self.keyboard_input_thread, daemon=True)
        input_thread.start()
        
        # Start message listener
        listen_task = asyncio.create_task(self.listen_for_messages())
        
        try:
            while True:
                try:
                    # Get next message (either from STT or keyboard)
                    message_type, user_input = self.message_queue.get(timeout=0.1)
                    
                    if message_type == 'quit':
                        print("\n👋 Goodbye!")
                        break
                    elif message_type in ['stt', 'keyboard']:
                        # Normalize input for quit commands
                        normalized_input = user_input.lower().strip().rstrip('.,!?;:')
                        if normalized_input in ['exit', 'quit', 'bye']:
                            print("\n👋 Goodbye!")
                            break
                        
                        if user_input:
                            # Show user input (especially important for STT)
                            if message_type == 'stt':
                                print(f"\n🎤 You (speech): {user_input}")
                            
                            await self.send_message(user_input)
                            
                except queue.Empty:
                    # Allow the event loop to process other tasks
                    await asyncio.sleep(0.1)
                    continue
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    # Resume STT after error
                    if self.stt_instance:
                        self.stt_instance.resume_from_response_streaming()
        finally:
            # Cleanup
            listen_task.cancel()
            if self.websocket:
                await self.websocket.close()
            if self.stt_instance:
                try:
                    self.stt_instance.cleanup()
                except Exception as e:
                    print(f"Warning: STT cleanup error: {e}")


async def main():
    """Main entry point"""
    print("💬 Starting Terminal ChatBot Frontend...")
    print(f"   Connecting to: {WEBSOCKET_URI}")
    
    client = TerminalChatClient()
    try:
        await client.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 