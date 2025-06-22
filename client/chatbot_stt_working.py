#!/usr/bin/env python3
"""
Clean, working Deepgram STT integration for ChatBot.
Based on proven working patterns with asyncwebsocket and proper KeepAlive.
"""
import os
import asyncio
import logging
import json
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


class ChatBotSTTWorking:
    """
    Clean, working STT integration using proven patterns.
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

    def setup_connection(self):
        """Set up the Deepgram WebSocket connection and event handlers."""
        # Use the working method (not deprecated asynclive)
        self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")

        async def on_open(client, open, **kwargs):
            self.logger.info("🔗 Deepgram connection established")

        self.dg_connection.on(LiveTranscriptionEvents.Open, on_open)

        async def on_close(client, close, **kwargs):
            self.logger.info("❌ Deepgram connection closed")
            self.is_running = False

        self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)

        async def on_error(client, error, **kwargs):
            self.logger.error(f"❌ Deepgram error: {error}")
            self.is_running = False

        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        async def on_transcript(client, result, **kwargs):
            try:
                # Skip processing during KeepAlive mode but start KeepAlive if needed
                if self.is_streaming_response:
                    if not self.keepalive_task or self.keepalive_task.done():
                        self.keepalive_task = asyncio.create_task(self._keepalive_sender())
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

        async def on_utterance_end(client, utterance_end, **kwargs):
            try:
                if self.is_streaming_response:
                    return
                    
                if self.is_final_transcript:
                    complete_utterance = " ".join(self.is_final_transcript)
                    self.logger.info(f"🎯 COMPLETE UTTERANCE: {complete_utterance}")
                    self.is_final_transcript = []
                    
                    # Call the callback with the complete utterance
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

        self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)

    async def start_live_transcription(self):
        """Start live transcription."""
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
                utterance_end_ms=self.stt_config.get('utterance_end_ms', 1000),
                vad_events=True,
                endpointing=300,
            )
            
            started = await self.dg_connection.start(options)
            if not started:
                raise Exception("Failed to start Deepgram connection")
                
            # Set up microphone
            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()
            
            self.is_running = True
            self.logger.info("🎤 Deepgram live transcription started")
            
        except Exception as e:
            self.logger.error(f"Error starting live transcription: {e}")
            raise

    async def finish_transcription(self):
        """Finish transcription."""
        try:
            self.is_running = False
            
            if self.keepalive_task and not self.keepalive_task.done():
                self.keepalive_task.cancel()
                try:
                    await self.keepalive_task
                except asyncio.CancelledError:
                    pass
            
            if self.microphone:
                self.microphone.finish()
                self.microphone = None
                
            if self.dg_connection:
                await self.dg_connection.finish()
                self.dg_connection = None
                
            self.logger.info("🛑 Live transcription finished")
            
        except Exception as e:
            self.logger.error(f"Error finishing transcription: {e}")

    async def _keepalive_sender(self):
        """Send KeepAlive messages using manual JSON method."""
        try:
            interval = self.stt_config.get('keepalive_interval', 3)
            while self.is_streaming_response and self.is_running:
                if self.dg_connection:
                    # Send KeepAlive as JSON message
                    keepalive_msg = json.dumps({"type": "KeepAlive"})
                    await self.dg_connection.send(keepalive_msg)
                    self.logger.debug("📡 Sent KeepAlive")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.debug("KeepAlive sender cancelled")
        except Exception as e:
            self.logger.error(f"Error in KeepAlive sender: {e}")

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

    # Sync wrapper methods
    def start(self):
        """Start the STT service (sync wrapper)."""
        if self.is_running:
            self.logger.warning("STT is already running")
            return
            
        self.logger.info("Starting live transcription...")
        import concurrent.futures
        
        def run_async_start():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.start_live_transcription())
            finally:
                loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_start)
            future.result(timeout=10)

    def stop(self):
        """Stop the STT service (sync wrapper)."""
        if not self.is_running:
            self.logger.warning("STT is not running")
            return
            
        self.logger.info("Stopping live transcription...")
        import concurrent.futures
        
        def run_async_stop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.finish_transcription())
            finally:
                loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_stop)
            future.result(timeout=5)

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up STT...")
        if self.is_running:
            self.stop()
        self.logger.info("STT cleanup complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup() 