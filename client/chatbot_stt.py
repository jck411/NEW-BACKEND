#!/usr/bin/env python3
import os
import asyncio
import threading
import logging
import json
from typing import Callable, Optional
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)


class ChatBotSTT:
    """
    Integrated Speech-to-Text for the ChatBot with KeepAlive support.
    Manages microphone input and pauses transcription during streaming responses.
    """
    
    def __init__(self, stt_config: dict, utterance_callback: Callable[[str], None]):
        """
        Initialize the ChatBot STT integration.
        
        Args:
            stt_config: STT configuration from client_config.yaml
            utterance_callback: Function to call when a complete utterance is received
        """
        self.stt_config = stt_config
        self.utterance_callback = utterance_callback
        self.logger = logging.getLogger(__name__)
        
        # Get API key from environment
        api_key_env = stt_config.get('api_key_env', 'DEEPGRAM_API_KEY')
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Deepgram API key not found in environment variable: {api_key_env}")
        
        self.deepgram = DeepgramClient(api_key)
        self.dg_connection = None
        self.microphone = None
        self.is_final_transcript = []
        self.is_running = False
        self.is_streaming_response = False  # Flag to track if chatbot is streaming response
        self.keepalive_task = None
        
        # Create a dedicated event loop for Deepgram tasks
        self.dg_loop = asyncio.new_event_loop()
        self.dg_thread = threading.Thread(target=self._run_dg_loop, daemon=True)
        self.dg_thread.start()
        
    def _run_dg_loop(self):
        """Run the dedicated asyncio event loop for Deepgram operations."""
        asyncio.set_event_loop(self.dg_loop)
        self.dg_loop.run_forever()
    
    def setup_connection(self):
        """Set up the Deepgram WebSocket connection and event handlers."""
        self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")

        async def on_open(client, *args, **kwargs):
            self.logger.info("🔗 Deepgram STT connection established")

        self.dg_connection.on(LiveTranscriptionEvents.Open, on_open)

        async def on_close(client, *args, **kwargs):
            self.logger.info("❌ Deepgram STT connection closed")
            self.is_running = False
            await self._stop_keepalive()

        self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)

        async def on_error(client, error, **kwargs):
            self.logger.error(f"❌ Deepgram STT error: {error}")
            self.is_running = False
            await self._stop_keepalive()

        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        async def on_transcript(client, result, **kwargs):
            try:
                # Skip processing if we're streaming a response (KeepAlive mode)
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
            except Exception as e:
                self.logger.error(f"Error processing transcript: {e}")

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)

        async def on_utterance_end(client, *args, **kwargs):
            try:
                # Skip processing if we're streaming a response (KeepAlive mode)
                if self.is_streaming_response:
                    return
                    
                if self.is_final_transcript:
                    complete_utterance = " ".join(self.is_final_transcript)
                    self.logger.info(f"🎯 COMPLETE UTTERANCE: {complete_utterance}")
                    self.is_final_transcript = []
                    
                    # Call the callback with the complete utterance in a thread-safe way
                    if self.utterance_callback:
                        try:
                            if asyncio.iscoroutinefunction(self.utterance_callback):
                                # Handle async callback
                                asyncio.create_task(self.utterance_callback(complete_utterance))
                            else:
                                # Handle sync callback
                                self.utterance_callback(complete_utterance)
                        except Exception as cb_e:
                            self.logger.error(f"Error in utterance callback: {cb_e}")
            except Exception as e:
                self.logger.error(f"Error processing utterance end: {e}")

        self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)

    async def _async_start(self):
        """Start the STT service asynchronously."""
        try:
            self.setup_connection()
            
            options = LiveOptions(
                model=self.stt_config.get('model', 'nova-2'),
                language=self.stt_config.get('language', 'en-US'),
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms=str(self.stt_config.get('utterance_end_ms', 1000)),
                vad_events=True,
                endpointing=300,
            )
            
            started = await self.dg_connection.start(options)
            if not started:
                raise Exception("Failed to start Deepgram connection")
                
            # Use Deepgram's Microphone class for audio input
            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()
            
            self.is_running = True
            self.logger.info("🎤 STT started - speak into your microphone!")
            
        except Exception as e:
            self.logger.error(f"Error starting STT: {e}")
            self.is_running = False
            raise

    async def _async_stop(self):
        """Stop the STT service asynchronously."""
        try:
            self.is_running = False
            await self._stop_keepalive()
            
            if self.microphone:
                self.microphone.finish()
                self.microphone = None
                
            if self.dg_connection:
                await asyncio.sleep(0.1)  # Brief pause before finishing
                await self.dg_connection.finish()
                self.dg_connection = None
                
            self.logger.info("🛑 STT stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping STT: {e}")

    async def _start_keepalive(self):
        """Start sending KeepAlive messages during response streaming."""
        if self.keepalive_task and not self.keepalive_task.done():
            return  # Already running
            
        self.keepalive_task = asyncio.create_task(self._keepalive_loop())
        self.logger.debug("Started KeepAlive messages")

    async def _stop_keepalive(self):
        """Stop sending KeepAlive messages."""
        if self.keepalive_task and not self.keepalive_task.done():
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass
            self.keepalive_task = None
            self.logger.debug("Stopped KeepAlive messages")

    async def _keepalive_loop(self):
        """Send periodic KeepAlive messages to maintain connection."""
        try:
            interval = self.stt_config.get('keepalive_interval', 3)
            while self.is_streaming_response and self.is_running:
                if self.dg_connection:
                    keepalive_msg = json.dumps({"type": "KeepAlive"})
                    await self.dg_connection.send(keepalive_msg)
                    self.logger.debug("Sent KeepAlive message")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.debug("KeepAlive loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in KeepAlive loop: {e}")

    def start(self):
        """Start the STT service."""
        if self.is_running:
            self.logger.warning("STT is already running")
            return
            
        self.logger.info("Starting STT...")
        future = asyncio.run_coroutine_threadsafe(self._async_start(), self.dg_loop)
        try:
            future.result(timeout=10)  # Wait up to 10 seconds for start
        except Exception as e:
            self.logger.error(f"Failed to start STT: {e}")
            raise

    def stop(self):
        """Stop the STT service."""
        if not self.is_running:
            self.logger.warning("STT is not running")
            return
            
        self.logger.info("Stopping STT...")
        future = asyncio.run_coroutine_threadsafe(self._async_stop(), self.dg_loop)
        try:
            future.result(timeout=5)  # Wait up to 5 seconds for stop
        except Exception as e:
            self.logger.error(f"Failed to stop STT: {e}")

    def pause_for_response_streaming(self):
        """Pause STT processing and start KeepAlive during response streaming."""
        if not self.is_running:
            return
            
        self.is_streaming_response = True
        self.logger.debug("STT paused for response streaming - switching to KeepAlive mode")
        
        # Start KeepAlive in the STT thread
        future = asyncio.run_coroutine_threadsafe(self._start_keepalive(), self.dg_loop)
        try:
            future.result(timeout=1)
        except Exception as e:
            self.logger.error(f"Failed to start KeepAlive: {e}")

    def resume_from_response_streaming(self):
        """Resume STT processing after response streaming ends."""
        if not self.is_running:
            return
            
        self.is_streaming_response = False
        self.logger.debug("STT resumed from response streaming - stopping KeepAlive mode")
        
        # Stop KeepAlive in the STT thread
        future = asyncio.run_coroutine_threadsafe(self._stop_keepalive(), self.dg_loop)
        try:
            future.result(timeout=1)
        except Exception as e:
            self.logger.error(f"Failed to stop KeepAlive: {e}")

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up ChatBotSTT...")
        
        if self.is_running:
            self.stop()
            
        # Stop the event loop
        if self.dg_loop.is_running():
            self.dg_loop.call_soon_threadsafe(self.dg_loop.stop)
            self.dg_thread.join(timeout=2.0)
            
        self.logger.info("STT cleanup complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup() 