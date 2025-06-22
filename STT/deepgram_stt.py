#!/usr/bin/env python3
import os
import asyncio
import threading
import logging
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]

class DeepgramSTT:
    def __init__(self, api_key: str = DEEPGRAM_API_KEY):
        self.deepgram = DeepgramClient(api_key)
        self.dg_connection = None
        self.microphone = None
        self.is_final_transcript = []
        self.is_running = False
        
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
            logger.info("🔗 Deepgram connection established")

        self.dg_connection.on(LiveTranscriptionEvents.Open, on_open)

        async def on_close(client, *args, **kwargs):
            logger.info("❌ Deepgram connection closed")
            self.is_running = False

        self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)

        async def on_error(client, error, **kwargs):
            logger.error(f"❌ Deepgram error: {error}")
            self.is_running = False

        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        async def on_transcript(client, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                if transcript.strip():
                    if result.is_final:
                        confidence = getattr(result.channel.alternatives[0], "confidence", "N/A")
                        print(f"✔️ FINAL: {transcript} (Confidence: {confidence})")
                        self.is_final_transcript.append(transcript)
                    else:
                        print(f"⚡ INTERIM: {transcript}")
            except Exception as e:
                logger.error(f"Error processing transcript: {e}")

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)

        async def on_utterance_end(client, *args, **kwargs):
            if self.is_final_transcript:
                complete_utterance = " ".join(self.is_final_transcript)
                print(f"🎯 COMPLETE UTTERANCE: {complete_utterance}")
                print("-" * 60)
                self.is_final_transcript = []

        self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)

    async def _async_start(self):
        """Start the STT service asynchronously."""
        try:
            self.setup_connection()
            
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms="1000",
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
            logger.info("🎤 STT started - speak into your microphone!")
            
        except Exception as e:
            logger.error(f"Error starting STT: {e}")
            self.is_running = False

    async def _async_stop(self):
        """Stop the STT service asynchronously."""
        try:
            self.is_running = False
            
            if self.microphone:
                self.microphone.finish()
                self.microphone = None
                
            if self.dg_connection:
                await asyncio.sleep(0.1)  # Brief pause before finishing
                await self.dg_connection.finish()
                self.dg_connection = None
                
            logger.info("🛑 STT stopped")
            
        except Exception as e:
            logger.error(f"Error stopping STT: {e}")

    def start(self):
        """Start the STT service."""
        if self.is_running:
            logger.warning("STT is already running")
            return
            
        logger.info("Starting STT...")
        future = asyncio.run_coroutine_threadsafe(self._async_start(), self.dg_loop)
        try:
            future.result(timeout=10)  # Wait up to 10 seconds for start
        except Exception as e:
            logger.error(f"Failed to start STT: {e}")

    def stop(self):
        """Stop the STT service."""
        if not self.is_running:
            logger.warning("STT is not running")
            return
            
        logger.info("Stopping STT...")
        future = asyncio.run_coroutine_threadsafe(self._async_stop(), self.dg_loop)
        try:
            future.result(timeout=5)  # Wait up to 5 seconds for stop
        except Exception as e:
            logger.error(f"Failed to stop STT: {e}")

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up DeepgramSTT...")
        
        if self.is_running:
            self.stop()
            
        # Stop the event loop
        if self.dg_loop.is_running():
            self.dg_loop.call_soon_threadsafe(self.dg_loop.stop)
            self.dg_thread.join(timeout=2.0)
            
        logger.info("Cleanup complete")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def main():
    """Main function to run the STT service."""
    print("🎙️  Deepgram Speech-to-Text Terminal")
    print("=" * 40)
    print("Press Ctrl+C to stop")
    print()
    
    stt = DeepgramSTT()
    
    try:
        with stt:
            # Keep the main thread alive
            while stt.is_running:
                try:
                    import time
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()