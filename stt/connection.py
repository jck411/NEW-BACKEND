"""Deepgram STT Connection Manager.

Following 2025 best practices for connection management.
"""

import asyncio
import contextlib
import logging
import threading
from typing import Any, Protocol

from deepgram import (
    DeepgramClient,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone,
)

# Type aliases for Deepgram SDK types that don't have proper stubs
DeepgramConnection = Any
DeepgramEventHandler = Any
STTConfig = dict[str, Any]


class DeepgramConnectionError(Exception):
    """Custom exception for Deepgram connection errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(message)
        self.message = message


class EventHandlersProtocol(Protocol):
    """Protocol for event handlers object."""

    async def on_open(self, _client: Any, _open: Any) -> None: ...  # noqa: ANN401
    async def on_transcript(
        self, _client: Any, result: Any  # noqa: ANN401
    ) -> None: ...
    async def on_metadata(
        self, _client: Any, metadata: Any  # noqa: ANN401
    ) -> None: ...
    async def on_speech_started(
        self, _client: Any, speech_started: Any  # noqa: ANN401
    ) -> None: ...
    async def on_utterance_end(
        self, _client: Any, utterance_end: Any  # noqa: ANN401
    ) -> None: ...
    async def on_close(self, _client: Any, _close: Any) -> None: ...  # noqa: ANN401
    async def on_error(self, _client: Any, error: Any) -> None: ...  # noqa: ANN401


class DeepgramConnectionManager:
    """Manages Deepgram STT connections and lifecycle."""

    def __init__(
        self, api_key: str, stt_config: STTConfig, logger: logging.Logger
    ) -> None:
        """Initialize the Deepgram connection manager.

        Args:
            api_key: Deepgram API key (not stored as instance variable for security)
            stt_config: Configuration dictionary for STT settings
            logger: Logger instance for this connection manager
        """
        # Don't store API key as instance variable for security
        self.stt_config: STTConfig = stt_config
        self.logger: logging.Logger = logger

        # Initialize Deepgram client (API key not stored)
        self.deepgram: DeepgramClient = DeepgramClient(api_key)
        self.dg_connection: DeepgramConnection | None = None
        self.microphone: Microphone | None = None

        # Event loop management
        self.dg_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self.dg_thread: threading.Thread = threading.Thread(
            target=self._run_dg_loop, daemon=True
        )
        self.dg_thread.start()

        # Cleanup state
        self._cleanup_done: bool = False

    def _run_dg_loop(self) -> None:
        """Run the dedicated asyncio event loop for Deepgram operations."""
        asyncio.set_event_loop(self.dg_loop)
        self.dg_loop.run_forever()

    def _raise_connection_error(self, message: str) -> None:
        """Raise a connection error with the given message."""
        raise DeepgramConnectionError(message)

    async def start_connection(
        self, event_handlers: EventHandlersProtocol
    ) -> DeepgramConnection:
        """Start live transcription connection."""
        try:
            # Create live connection
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")

            # Set up event handlers
            if self.dg_connection:
                self.dg_connection.on(
                    LiveTranscriptionEvents.Open, event_handlers.on_open
                )
                self.dg_connection.on(
                    LiveTranscriptionEvents.Transcript, event_handlers.on_transcript
                )
                self.dg_connection.on(
                    LiveTranscriptionEvents.Metadata, event_handlers.on_metadata
                )
                self.dg_connection.on(
                    LiveTranscriptionEvents.SpeechStarted,
                    event_handlers.on_speech_started,
                )
                self.dg_connection.on(
                    LiveTranscriptionEvents.UtteranceEnd,
                    event_handlers.on_utterance_end,
                )
                self.dg_connection.on(
                    LiveTranscriptionEvents.Close, event_handlers.on_close
                )
                self.dg_connection.on(
                    LiveTranscriptionEvents.Error, event_handlers.on_error
                )

            # Configure options
            options = LiveOptions(
                model=self.stt_config.get("model", "nova-2"),
                language=self.stt_config.get("language", "en-US"),
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms=self.stt_config.get("utterance_end_ms", 1000),
                vad_events=True,
            )

            # Start connection
            if not self.dg_connection:
                self._raise_connection_error("Failed to create Deepgram connection")

            started: bool | asyncio.Future[bool] = await self.dg_connection.start(  # type: ignore[attr-defined]
                options
            )
            if not started:
                self._raise_connection_error("Failed to start Deepgram connection")

            # Set up microphone
            if self.dg_connection:
                self.microphone = Microphone(self.dg_connection.send)  # type: ignore[attr-defined]
            if self.microphone:
                self.microphone.start()

            self.logger.info("🎤 Deepgram live transcription started")

        except Exception:
            self.logger.exception("Error starting live transcription")
            raise
        else:
            return self.dg_connection

    async def finish_connection(self) -> None:
        """Finish transcription and cleanup connections."""
        try:
            # Stop microphone first
            if self.microphone:
                with contextlib.suppress(RuntimeError, OSError, AttributeError):
                    self.microphone.finish()
                self.microphone = None

            # Close connection gracefully
            if self.dg_connection:
                try:
                    finish_result: bool | asyncio.Future[bool] = (
                        self.dg_connection.finish()
                    )
                    if isinstance(finish_result, asyncio.Future):
                        await asyncio.wait_for(finish_result, timeout=2.0)
                    # If it's a bool, no need to await
                except (TimeoutError, RuntimeError, OSError, AttributeError):
                    pass  # Ignore connection cleanup errors
                self.dg_connection = None

            self.logger.info("🛑 Live transcription finished")

        except (RuntimeError, OSError, ConnectionError, ValueError) as e:
            self.logger.debug("Error finishing transcription (ignoring): %s", e)

    def cleanup(self) -> None:
        """Clean up connection resources."""
        if hasattr(self, "_cleanup_done") and self._cleanup_done:
            return

        self.logger.info("Cleaning up connection...")
        self._cleanup_done = True

        # Stop the event loop
        if hasattr(self, "dg_loop") and self.dg_loop.is_running():
            with contextlib.suppress(RuntimeError):
                self.dg_loop.call_soon_threadsafe(self.dg_loop.stop)
            if hasattr(self, "dg_thread"):
                self.dg_thread.join(timeout=2.0)

        self.logger.info("Connection cleanup complete")

    def get_connection(self) -> DeepgramConnection | None:
        """Get the current Deepgram connection."""
        return self.dg_connection
