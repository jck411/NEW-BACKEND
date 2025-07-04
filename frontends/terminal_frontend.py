#!/usr/bin/env python3
"""Standalone Terminal Frontend for ChatBot Backend.

A simple terminal-based frontend that connects to the FastAPI backend via WebSocket.
Supports real-time streaming chat and optional Speech-to-Text.
"""

import asyncio
import contextlib
import json
import logging
import queue
import threading
import uuid
from typing import TYPE_CHECKING, Any

import websockets
import websockets.exceptions

if TYPE_CHECKING:
    from stt import DeepgramSTT

# Set up module logger
logger = logging.getLogger(__name__)

# Import backend config to get backend connection details and STT config
try:
    from backend.connection_config import ConnectionConfig
    from stt import DeepgramSTT

    client_config = ConnectionConfig()
    backend_config = client_config.get_backend_config()
    websocket_uri = f"ws://{backend_config['host']}:{backend_config['port']}/ws/chat"
    stt_available = True
except (ImportError, AttributeError, KeyError) as e:
    logger.warning("Failed to load backend config: %s", e)
    websocket_uri = "ws://localhost:8000/ws/chat"
    stt_available = False
    DeepgramSTT = None  # type: ignore[assignment]


class TerminalChatClient:
    """Terminal-based chat client."""

    def __init__(self) -> None:
        """Initialize the terminal chat client."""
        self.websocket: Any | None = (
            None  # Using Any to handle websocket type variations
        )
        self.connection_status = "Disconnected"
        self.current_message_id: str | None = None
        self.message_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self.stt_instance: Any | None = (
            None  # Using Any since DeepgramSTT might not be available
        )
        self.stt_enabled = False
        self._last_user_message: str | None = None

    async def connect(self) -> bool:
        """Connect to the backend WebSocket."""
        try:
            self.websocket = await websockets.connect(websocket_uri)
        except (websockets.exceptions.WebSocketException, OSError):
            logger.exception("Failed to connect to WebSocket")
            return False
        else:
            self.connection_status = "Connected"
            return True

    async def listen_for_messages(self) -> None:
        """Listen for incoming WebSocket messages."""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.handle_message(data)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse WebSocket message: %s", e)
        except websockets.exceptions.ConnectionClosed:
            self.connection_status = "Disconnected"
        except Exception:
            logger.exception("WebSocket listening error")
            self.connection_status = "Error"

    def handle_message(self, data: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")

        if msg_type == "message_start":
            # Start of new message
            self.current_message_id = data.get("id")
            user_message = data.get("user_message", "")

            # Show user message if not already displayed
            if user_message and (
                not hasattr(self, "_last_user_message")
                or self._last_user_message != user_message
            ):
                self._last_user_message = user_message

        elif msg_type == "text_chunk":
            # Streaming text chunk
            data.get("content", "")

        elif msg_type == "message_complete":
            # Message finished
            self.current_message_id = None

            # Resume STT if it was paused
            if self.stt_instance:
                self.stt_instance.resume_from_response_streaming()

        elif msg_type == "error":
            data.get("error", "Unknown error")

        elif msg_type == "connection_established":
            data.get("client_id", "unknown")

    async def send_message(self, message: str) -> None:
        """Send a message to the backend."""
        if not self.websocket:
            return

        # Check if connection is still open
        try:
            # Try to check connection state - websockets 12+ uses different attributes
            if (hasattr(self.websocket, "closed") and self.websocket.closed) or (
                hasattr(self.websocket, "state")
                and self.websocket.state.name == "CLOSED"
            ):
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
            "content": message,
        }

        try:
            await self.websocket.send(json.dumps(message_data))
        except (websockets.exceptions.WebSocketException, OSError):
            logger.exception("Failed to send message")
            # Resume STT on error
            if self.stt_instance:
                self.stt_instance.resume_from_response_streaming()

    def setup_stt(self) -> bool:
        """Setup Speech-to-Text if available and enabled."""
        if not stt_available or DeepgramSTT is None:
            return False

        try:
            stt_config = client_config.get_stt_config()
            if not stt_config.get("enabled", False):
                return False

            def utterance_callback(utterance: str) -> None:
                """Handle complete utterances from STT."""
                self.message_queue.put(("stt", utterance))

            self.stt_instance = DeepgramSTT(stt_config, utterance_callback)
            self.stt_instance.start()
            self.stt_enabled = True
        except (ImportError, AttributeError, KeyError):
            logger.exception("Failed to setup STT")
            return False
        else:
            return True

    def keyboard_input_thread(self) -> None:
        """Handle keyboard input in a separate thread."""
        while True:
            try:
                if self.stt_enabled:
                    user_input: str = input("\nType (or speak): ").strip()
                else:
                    user_input: str = input("> ").strip()

                if user_input:
                    self.message_queue.put(("keyboard", user_input))
            except (EOFError, KeyboardInterrupt):
                self.message_queue.put(("quit", None))
                break

    def _process_user_input(self, message_type: str, user_input: str | None) -> bool:
        """Process user input and return True if should continue, False if should quit."""
        if message_type == "quit":
            return False
        if message_type in ["stt", "keyboard"] and user_input:
            # Normalize input for quit commands
            normalized_input: str = user_input.lower().strip().rstrip(".,!?;:")
            if normalized_input in ["exit", "quit", "bye"]:
                return False

            if user_input:
                # Show user input (especially important for STT)
                if message_type == "stt":
                    pass

                # Store reference to avoid dangling task
                task = asyncio.create_task(self.send_message(user_input))
                # Keep reference to prevent garbage collection
                setattr(self, f"_send_task_{id(task)}", task)
        return True

    async def _main_loop(self) -> None:
        """Main message processing loop."""
        while True:
            try:
                # Get next message (either from STT or keyboard)
                message_type: str
                user_input: str | None
                message_type, user_input = self.message_queue.get(timeout=0.1)

                if not self._process_user_input(message_type, user_input):
                    break

            except queue.Empty:
                # Allow the event loop to process other tasks
                await asyncio.sleep(0.1)
                continue
            except KeyboardInterrupt:
                break
            except Exception:
                logger.exception("Error in main loop")
                # Resume STT after error
                if self.stt_instance:
                    self.stt_instance.resume_from_response_streaming()

    async def run(self) -> None:
        """Main chat loop."""
        # Connect to backend
        if not await self.connect():
            return

        # Setup STT if available
        stt_setup_success = self.setup_stt()
        if stt_setup_success:
            logger.info("STT enabled")
        else:
            logger.info("STT disabled")

        # Start keyboard input thread
        input_thread = threading.Thread(target=self.keyboard_input_thread, daemon=True)
        input_thread.start()

        # Start message listener
        listen_task = asyncio.create_task(self.listen_for_messages())
        self._listen_task = listen_task  # Store reference

        try:
            await self._main_loop()
        finally:
            # Cleanup
            listen_task.cancel()
            if self.websocket:
                await self.websocket.close()
            if self.stt_instance:
                with contextlib.suppress(Exception):
                    self.stt_instance.cleanup()


async def main() -> None:
    """Main entry point."""
    client = TerminalChatClient()
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("Terminal frontend interrupted")
    except Exception:
        logger.exception("Terminal frontend error")


if __name__ == "__main__":
    asyncio.run(main())
