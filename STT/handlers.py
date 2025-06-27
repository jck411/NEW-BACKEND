"""Deepgram STT Event Handlers
Following 2025 best practices for event handling with proper separation of concerns
"""
import asyncio
import logging
from collections.abc import Callable


class STTEventHandlers:
    """Event handlers for Deepgram STT"""

    def __init__(self, logger: logging.Logger, utterance_callback: Callable[[str], None]):
        self.logger = logger
        self.utterance_callback = utterance_callback
        self.is_final_transcript: list[str] = []
        self.is_streaming_response = False
        self.is_running = False

    async def on_open(self, client, open, **kwargs):
        """Connection opened callback"""
        self.logger.info("🔗 Deepgram connection opened")

    async def on_transcript(self, client, result, **kwargs):
        """Transcript received callback - main processing logic"""
        try:
            self.logger.debug(f"🎵 Raw result received: {result}")

            # Skip processing during KeepAlive mode
            if self.is_streaming_response:
                return

            transcript = result.channel.alternatives[0].transcript
            if transcript.strip():
                if result.is_final:
                    confidence = getattr(result.channel.alternatives[0], "confidence", "N/A")
                    self.logger.debug(f"✔️ FINAL: {transcript} (Confidence: {confidence})")
                    self.is_final_transcript.append(transcript)
                else:
                    self.logger.debug(f"⚡ INTERIM: {transcript}")
            else:
                self.logger.debug("🔇 Empty transcript received")

        except Exception as e:
            self.logger.error(f"Error processing transcript: {e}")
            self.logger.debug(f"🐛 Full result object: {result}")

    async def on_metadata(self, client, metadata, **kwargs):
        """Metadata received callback"""
        self.logger.debug(f"📊 Metadata: {metadata}")

    async def on_speech_started(self, client, speech_started, **kwargs):
        """Speech started callback"""
        self.logger.debug(f"🗣️ Speech started: {speech_started}")

    async def on_utterance_end(self, client, utterance_end, **kwargs):
        """Utterance end callback - triggers final processing"""
        try:
            self.logger.debug(f"🔚 Utterance end: {utterance_end}")

            # Skip processing during KeepAlive mode
            if self.is_streaming_response:
                return

            if self.is_final_transcript:
                complete_utterance = " ".join(self.is_final_transcript)
                self.logger.info(f"🎯 COMPLETE UTTERANCE: {complete_utterance}")
                self.is_final_transcript = []

                # Trigger callback with complete utterance
                if self.utterance_callback:
                    try:
                        if asyncio.iscoroutinefunction(self.utterance_callback):
                            await self.utterance_callback(complete_utterance)
                        else:
                            self.utterance_callback(complete_utterance)
                    except Exception as cb_e:
                        self.logger.error(f"Error in utterance callback: {cb_e}")

        except Exception as e:
            self.logger.error(f"Error processing utterance end: {e}")

    async def on_close(self, client, close, **kwargs):
        """Connection closed callback"""
        self.logger.info("❌ Deepgram connection closed")
        self.is_running = False

    async def on_error(self, client, error, **kwargs):
        """Error callback"""
        self.logger.error(f"❌ Deepgram error: {error}")
        self.is_running = False

    def set_streaming_response(self, is_streaming: bool):
        """Set streaming response state"""
        self.is_streaming_response = is_streaming

    def set_running_state(self, is_running: bool):
        """Set running state"""
        self.is_running = is_running
