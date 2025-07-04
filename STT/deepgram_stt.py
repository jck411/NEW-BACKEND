#!/usr/bin/env python3
"""Deepgram SDK Speech-to-Text integration.

Refactored following 2025 best practices with proper separation of concerns.
"""
import asyncio
import logging
import os
import types
from collections.abc import Callable
from typing import Any

from dotenv import load_dotenv

from backend.exceptions import DeepgramSTTError
from backend.utils import log_and_wrap_error

from .connection import DeepgramConnectionManager
from .handlers import STTEventHandlers
from .keepalive import KeepAliveManager

# Load environment variables from .env file
load_dotenv()


class DeepgramSTT:
    """Refactored Deepgram SDK-based Speech-to-Text integration.
    Following 2025 best practices with proper separation of concerns.
    """

    def __init__(
        self, stt_config: dict[str, Any], utterance_callback: Callable[[str], None]
    ) -> None:
        self.stt_config = stt_config
        self.utterance_callback = utterance_callback
        self.logger = logging.getLogger(__name__)
        self.is_running = False

        # Securely get API key from environment
        api_key_env: str = stt_config.get("api_key_env", "DEEPGRAM_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            msg = f"Deepgram API key not found: {api_key_env}"
            raise DeepgramSTTError(msg)

        # Initialize components with proper separation of concerns
        # Note: API key is passed to connection manager but not stored long-term
        self.event_handlers = STTEventHandlers(self.logger, utterance_callback)
        self.connection_manager = DeepgramConnectionManager(
            api_key, stt_config, self.logger
        )
        self.keepalive_manager = KeepAliveManager(self.logger, stt_config)

    async def start_live_transcription(self) -> None:
        """Start live transcription using modular components."""
        try:
            # Start connection through connection manager
            await self.connection_manager.start_connection(self.event_handlers)

            # Update state across components
            self.is_running = True
            self.event_handlers.set_running_state(True)
            self.keepalive_manager.set_running_state(True)

            self.logger.info("🎤 Deepgram live transcription started (modular)")

        except (RuntimeError, OSError, ConnectionError, ValueError) as e:
            wrapped_error = log_and_wrap_error(
                e,
                DeepgramSTTError,
                "Failed to start transcription",
                error_code="STT_START_FAILED",
                logger=self.logger,
            )
            raise wrapped_error

    async def finish_transcription(self) -> None:
        """Finish transcription using modular components."""
        try:
            self.is_running = False
            self.event_handlers.set_running_state(False)
            self.keepalive_manager.set_running_state(False)

            # Stop keepalive first
            await self.keepalive_manager.stop_keepalive()

            # Finish connection
            await self.connection_manager.finish_connection()

            self.logger.info("🛑 Live transcription finished")

        except (RuntimeError, OSError, ConnectionError, ValueError) as e:
            self.logger.debug("Error finishing transcription (ignoring): %s", e)

    # Public methods for integration with chatbot
    def pause_for_response_streaming(self) -> None:
        """Pause STT and start KeepAlive during response streaming."""
        if not self.is_running:
            return

        self.event_handlers.set_streaming_response(True)
        self.keepalive_manager.pause_for_response_streaming()

        # Start keepalive with current connection
        dg_connection = self.connection_manager.get_connection()
        if dg_connection:
            asyncio.run_coroutine_threadsafe(
                self.keepalive_manager.start_keepalive(dg_connection),
                self.connection_manager.dg_loop,
            )

    def resume_from_response_streaming(self) -> None:
        """Resume STT processing after response streaming ends."""
        if not self.is_running:
            return

        self.event_handlers.set_streaming_response(False)
        self.keepalive_manager.resume_from_response_streaming()

    # Sync wrapper methods using dedicated event loop
    def start(self) -> None:
        """Start the STT service."""
        if self.is_running:
            self.logger.warning("STT is already running")
            return

        self.logger.info("Starting live transcription...")
        future = asyncio.run_coroutine_threadsafe(
            self.start_live_transcription(), self.connection_manager.dg_loop
        )
        try:
            future.result(timeout=10)  # Wait up to 10 seconds for start
        except (RuntimeError, OSError, ConnectionError, ValueError, TimeoutError) as e:
            wrapped_error = log_and_wrap_error(
                e,
                DeepgramSTTError,
                "Failed to start STT service",
                error_code="STT_SERVICE_START_FAILED",
                logger=self.logger,
            )
            raise wrapped_error

    def stop(self) -> None:
        """Stop the STT service."""
        if not self.is_running:
            return  # Silently return if already stopped

        self.logger.info("Stopping live transcription...")
        future = asyncio.run_coroutine_threadsafe(
            self.finish_transcription(), self.connection_manager.dg_loop
        )
        try:
            future.result(timeout=3)  # Shorter timeout for faster shutdown
        except (RuntimeError, OSError, ConnectionError, ValueError, TimeoutError) as e:
            self.logger.debug("Stop error (ignoring): %s", e)

    def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self, "_cleanup_done") and self._cleanup_done:
            return  # Prevent duplicate cleanup

        self.logger.info("Cleaning up STT...")
        self._cleanup_done = True

        if self.is_running:
            self.stop()

        # Clean up connection manager
        self.connection_manager.cleanup()

        self.logger.info("STT cleanup complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ):
        self.cleanup()
