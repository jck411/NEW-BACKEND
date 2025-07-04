"""Deepgram STT Connection Manager

Following 2025 best practices for connection management.
"""

import asyncio
import logging
import threading

from deepgram import (
    DeepgramClient,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone,
)


class DeepgramConnectionManager:
    """Manages Deepgram STT connections and lifecycle."""

    def __init__(self, api_key: str, stt_config: dict, logger: logging.Logger) -> None:
        # Don't store API key as instance variable for security
        self.stt_config = stt_config
        self.logger = logger

        # Initialize Deepgram client (API key not stored)
        self.deepgram = DeepgramClient(api_key)
        self.dg_connection = None
        self.microphone = None

        # Event loop management
        self.dg_loop = asyncio.new_event_loop()
        self.dg_thread = threading.Thread(target=self._run_dg_loop, daemon=True)
        self.dg_thread.start()

    def _run_dg_loop(self) -> None:
        """Run the dedicated asyncio event loop for Deepgram operations."""
        asyncio.set_event_loop(self.dg_loop)
        self.dg_loop.run_forever()

    async def start_connection(self, event_handlers: object):
        """Start live transcription connection."""
        try:
            # Create live connection
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")

            # Set up event handlers
            self.dg_connection.on(LiveTranscriptionEvents.Open, event_handlers.on_open)
            self.dg_connection.on(
                LiveTranscriptionEvents.Transcript, event_handlers.on_transcript
            )
            self.dg_connection.on(
                LiveTranscriptionEvents.Metadata, event_handlers.on_metadata
            )
            self.dg_connection.on(
                LiveTranscriptionEvents.SpeechStarted, event_handlers.on_speech_started
            )
            self.dg_connection.on(
                LiveTranscriptionEvents.UtteranceEnd, event_handlers.on_utterance_end
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
            started = await self.dg_connection.start(options)
            if not started:
                msg = "Failed to start Deepgram connection"
                raise Exception(msg)

            # Set up microphone
            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()

            self.logger.info("🎤 Deepgram live transcription started")
            return self.dg_connection

        except Exception:
            self.logger.exception("Error starting live transcription")
            raise

    async def finish_connection(self) -> None:
        """Finish transcription and cleanup connections."""
        try:
            # Stop microphone first
            if self.microphone:
                try:
                    self.microphone.finish()
                except (RuntimeError, OSError, AttributeError):
                    pass  # Ignore microphone cleanup errors
                self.microphone = None

            # Close connection gracefully
            if self.dg_connection:
                try:
                    await asyncio.wait_for(self.dg_connection.finish(), timeout=2.0)
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
            try:
                self.dg_loop.call_soon_threadsafe(self.dg_loop.stop)
            except RuntimeError:
                pass  # Loop might already be stopped
            if hasattr(self, "dg_thread"):
                self.dg_thread.join(timeout=2.0)

        self.logger.info("Connection cleanup complete")

    def get_connection(self):
        """Get the current Deepgram connection."""
        return self.dg_connection
