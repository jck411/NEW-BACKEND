"""Deepgram STT Event Handlers.

Following 2025 best practices for event handling with proper separation of concerns.
"""

import logging
from collections.abc import Callable
from typing import Any


class STTEventHandlers:
    """Event handlers for Deepgram STT."""

    def __init__(
        self, logger: logging.Logger, utterance_callback: Callable[[str], None]
    ) -> None:
        """Initialize STT event handlers.

        Args:
            logger: Logger instance for event logging
            utterance_callback: Callback function to handle complete utterances
        """
        self.logger = logger
        self.utterance_callback = utterance_callback
        self.is_final_transcript: list[str] = []
        self.is_streaming_response = False
        self.is_running = False

    async def on_open(self, _client: Any, _open: Any) -> None:  # noqa: ANN401
        """Connection opened callback."""
        self.logger.info("🔗 Deepgram connection opened")

    async def on_transcript(self, _client: Any, result: Any) -> None:  # noqa: ANN401
        """Transcript received callback - main processing logic."""
        try:
            self.logger.debug("🎵 Raw result received: %s", result)

            # Skip processing during KeepAlive mode
            if self.is_streaming_response:
                return

            # Handle unknown object types safely
            if hasattr(result, "channel") and hasattr(result.channel, "alternatives"):
                transcript = result.channel.alternatives[0].transcript
                if transcript.strip():
                    if hasattr(result, "is_final") and result.is_final:
                        confidence = getattr(
                            result.channel.alternatives[0], "confidence", "N/A"
                        )
                        self.logger.debug(
                            "✔️ FINAL: %s (Confidence: %s)", transcript, confidence
                        )
                        self.is_final_transcript.append(transcript)
                    else:
                        self.logger.debug("⚡ INTERIM: %s", transcript)
                else:
                    self.logger.debug("🔇 Empty transcript received")
            else:
                self.logger.debug("🔇 Invalid result structure received")

        except Exception:
            self.logger.exception("Error processing transcript")
            self.logger.debug("🐛 Full result object: %s", result)

    async def on_metadata(self, _client: Any, metadata: Any) -> None:  # noqa: ANN401
        """Metadata received callback."""
        self.logger.debug("📊 Metadata: %s", metadata)

    async def on_speech_started(
        self, _client: Any, speech_started: Any  # noqa: ANN401
    ) -> None:
        """Speech started callback."""
        self.logger.debug("🗣️ Speech started: %s", speech_started)

    async def on_utterance_end(
        self, _client: Any, utterance_end: Any  # noqa: ANN401
    ) -> None:
        """Utterance end callback - triggers final processing."""
        try:
            self.logger.debug("🔚 Utterance end: %s", utterance_end)

            # Skip processing during KeepAlive mode
            if self.is_streaming_response:
                return

            if len(self.is_final_transcript) > 0:
                complete_utterance = " ".join(self.is_final_transcript)
                self.logger.info("🎯 COMPLETE UTTERANCE: %s", complete_utterance)
                self.is_final_transcript = []

                # Trigger callback with complete utterance
                try:
                    self.utterance_callback(complete_utterance)
                except Exception:
                    self.logger.exception("Error in utterance callback")

        except Exception:
            self.logger.exception("Error processing utterance end")

    async def on_close(self, _client: Any, _close: Any) -> None:  # noqa: ANN401
        """Connection closed callback."""
        self.logger.info("❌ Deepgram connection closed")
        self.is_running = False

    async def on_error(self, _client: Any, error: Any) -> None:  # noqa: ANN401
        """Error callback."""
        self.logger.error("❌ Deepgram error: %s", error)
        self.is_running = False

    def set_streaming_response(self, *, is_streaming: bool) -> None:
        """Set streaming response state."""
        self.is_streaming_response = is_streaming

    def set_running_state(self, *, is_running: bool) -> None:
        """Set running state."""
        self.is_running = is_running
