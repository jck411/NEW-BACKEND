#!/usr/bin/env python3
"""
Deepgram SDK Speech-to-Text integration.
Uses the current supported methods (asyncwebsocket) with proper KeepAlive support.
"""
import os
import asyncio
import threading
import logging
from typing import Callable
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

# Load environment variables from .env file
load_dotenv()


class DeepgramSTT:
    """
    Deepgram SDK-based Speech-to-Text integration.
    Following the patterns from the official documentation.
    """
    
    def __init__(self, stt_config: dict, utterance_callback: Callable[[str], None]):
        self.stt_config = stt_config
        self.utterance_callback = utterance_callback
        self.logger = logging.getLogger(__name__)
        
        # Get API key
        api_key_env = stt_config.get('api_key_env', 'DEEPGRAM_API_KEY')
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Deepgram API key not found: {api_key_env}")
        
        self.deepgram = DeepgramClient(api_key)
        self.dg_connection = None
        self.microphone = None
        self.is_final_transcript = []
        self.is_running = False
        self.is_streaming_response = False
        self.keepalive_task = None
        
        # Create a dedicated event loop for Deepgram tasks
        self.dg_loop = asyncio.new_event_loop()
        self.dg_thread = threading.Thread(target=self._run_dg_loop, daemon=True)
        self.dg_thread.start()

    def _run_dg_loop(self):
        """Run the dedicated asyncio event loop for Deepgram operations."""
        import threading
        asyncio.set_event_loop(self.dg_loop)
        self.dg_loop.run_forever()

    async def start_live_transcription(self):
        """Start live transcription following official SDK patterns."""
        try:
            # Create live connection (current working method - asynclive is deprecated in v4.0.0+)
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Set up all event handlers first (official pattern)
            self.dg_connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.Metadata, self._on_metadata)
            self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, self._on_speech_started)
            self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self._on_close)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self._on_error)
            
            # Configure options (official settings)
            options = LiveOptions(
                model=self.stt_config.get('model', 'nova-2'),
                language=self.stt_config.get('language', 'en-US'),
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms=self.stt_config.get('utterance_end_ms', 1000),
                vad_events=True,
            )
            
            # Start connection with official method
            started = await self.dg_connection.start(options)
            if not started:
                raise Exception("Failed to start Deepgram connection")
                
            # Set up microphone (official SDK way)
            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()
            
            self.is_running = True
            self.logger.info("🎤 Deepgram live transcription started (official SDK)")
            
        except Exception as e:
            self.logger.error(f"Error starting live transcription: {e}")
            raise

    async def _on_open(self, client, open, **kwargs):
        """Connection opened callback (official SDK style)."""
        self.logger.info("🔗 Deepgram connection opened")

    async def _on_transcript(self, client, result, **kwargs):
        """Transcript received callback - only show important events."""
        try:
            self.logger.debug(f"🎵 Raw result received: {result}")  # Keep as debug
            
            # Skip processing during KeepAlive mode, but start KeepAlive if needed
            if self.is_streaming_response:
                # Start KeepAlive if not already running
                if not self.keepalive_task or self.keepalive_task.done():
                    self.keepalive_task = asyncio.create_task(self._keepalive_sender())
                return
                
            transcript = result.channel.alternatives[0].transcript
            if transcript.strip():
                if result.is_final:
                    confidence = getattr(result.channel.alternatives[0], "confidence", "N/A")
                    self.logger.debug(f"✔️ FINAL: {transcript} (Confidence: {confidence})")  # Changed to DEBUG
                    self.is_final_transcript.append(transcript)
                else:
                    self.logger.debug(f"⚡ INTERIM: {transcript}")  # Changed to DEBUG
            else:
                self.logger.debug("🔇 Empty transcript received")  # Keep as debug
                    
        except Exception as e:
            self.logger.error(f"Error processing transcript: {e}")
            self.logger.debug(f"🐛 Full result object: {result}")  # Changed to DEBUG

    async def _on_metadata(self, client, metadata, **kwargs):
        """Metadata received callback - quiet unless debugging."""
        self.logger.debug(f"📊 Metadata: {metadata}")  # Changed to DEBUG

    async def _on_speech_started(self, client, speech_started, **kwargs):
        """Speech started callback - quiet unless debugging."""
        self.logger.debug(f"🗣️ Speech started: {speech_started}")  # Changed to DEBUG

    async def _on_utterance_end(self, client, utterance_end, **kwargs):
        """Utterance end callback - only show the final submitted utterance."""
        try:
            self.logger.debug(f"🔚 Utterance end: {utterance_end}")  # Changed to DEBUG
            
            # Skip processing during KeepAlive mode
            if self.is_streaming_response:
                return
                
            if self.is_final_transcript:
                complete_utterance = " ".join(self.is_final_transcript)
                self.logger.info(f"🎯 COMPLETE UTTERANCE: {complete_utterance}")  # Keep this visible
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

    async def _on_close(self, client, close, **kwargs):
        """Connection closed callback (official SDK style)."""
        self.logger.info("❌ Deepgram connection closed")
        self.is_running = False
        await self._stop_keepalive()

    async def _on_error(self, client, error, **kwargs):
        """Error callback (official SDK style)."""
        self.logger.error(f"❌ Deepgram error: {error}")
        self.is_running = False
        await self._stop_keepalive()

    async def start_keepalive(self):
        """Start KeepAlive using official Deepgram method."""
        if self.keepalive_task and not self.keepalive_task.done():
            return
            
        self.is_streaming_response = True
        self.keepalive_task = asyncio.create_task(self._keepalive_sender())
        self.logger.debug("🔄 Started KeepAlive (official method)")

    async def stop_keepalive(self):
        """Stop KeepAlive."""
        self.is_streaming_response = False
        await self._stop_keepalive()
        self.logger.debug("⏹️ Stopped KeepAlive")

    async def _stop_keepalive(self):
        """Internal method to stop KeepAlive task."""
        if self.keepalive_task and not self.keepalive_task.done():
            self.keepalive_task.cancel()
            try:
                await asyncio.wait_for(self.keepalive_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            self.keepalive_task = None

    async def _keepalive_sender(self):
        """Send KeepAlive messages using official SDK method."""
        try:
            interval = self.stt_config.get('keepalive_interval', 3)
            while self.is_streaming_response and self.is_running:
                if self.dg_connection:
                    # Use official SDK's keep_alive method
                    await self.dg_connection.keep_alive()
                    self.logger.debug("📡 Sent KeepAlive (official SDK method)")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.debug("KeepAlive sender cancelled")
        except Exception as e:
            self.logger.error(f"Error in KeepAlive sender: {e}")

    async def finish_transcription(self):
        """Finish transcription using official SDK method."""
        try:
            self.is_running = False
            await self._stop_keepalive()
            
            # Stop microphone first with error handling
            if self.microphone:
                try:
                    self.microphone.finish()
                except Exception:
                    pass  # Ignore microphone cleanup errors
                self.microphone = None
                
            # Close connection gracefully with timeout
            if self.dg_connection:
                try:
                    await asyncio.wait_for(self.dg_connection.finish(), timeout=2.0)
                except (asyncio.TimeoutError, Exception):
                    pass  # Ignore connection cleanup errors
                self.dg_connection = None
                
            self.logger.info("🛑 Live transcription finished")
            
        except Exception as e:
            self.logger.debug(f"Error finishing transcription (ignoring): {e}")  # Make this debug level

    # Public methods for integration with chatbot
    def pause_for_response_streaming(self):
        """Pause STT and start KeepAlive during response streaming."""
        if not self.is_running:
            return
        
        self.is_streaming_response = True
        self.logger.debug("🔄 STT paused for response streaming")

    def resume_from_response_streaming(self):
        """Resume STT processing after response streaming ends."""
        if not self.is_running:
            return
        
        self.is_streaming_response = False
        self.logger.debug("▶️ STT resumed from response streaming")

    # Sync wrapper methods using dedicated event loop
    def start(self):
        """Start the STT service."""
        if self.is_running:
            self.logger.warning("STT is already running")
            return
            
        self.logger.info("Starting live transcription...")
        future = asyncio.run_coroutine_threadsafe(self.start_live_transcription(), self.dg_loop)
        try:
            future.result(timeout=10)  # Wait up to 10 seconds for start
        except Exception as e:
            self.logger.error(f"Failed to start STT: {e}")

    def stop(self):
        """Stop the STT service."""
        if not self.is_running:
            return  # Silently return if already stopped
            
        self.logger.info("Stopping live transcription...")
        future = asyncio.run_coroutine_threadsafe(self.finish_transcription(), self.dg_loop)
        try:
            future.result(timeout=3)  # Shorter timeout for faster shutdown
        except Exception as e:
            self.logger.debug(f"Stop error (ignoring): {e}")  # Make this debug level

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, '_cleanup_done') and self._cleanup_done:
            return  # Prevent duplicate cleanup
            
        self.logger.info("Cleaning up official STT...")
        self._cleanup_done = True
        
        if self.is_running:
            self.stop()
            
        # Stop the event loop
        if hasattr(self, 'dg_loop') and self.dg_loop.is_running():
            try:
                self.dg_loop.call_soon_threadsafe(self.dg_loop.stop)
            except RuntimeError:
                pass  # Loop might already be stopped
            if hasattr(self, 'dg_thread'):
                self.dg_thread.join(timeout=2.0)
            
        self.logger.info("STT cleanup complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup() 