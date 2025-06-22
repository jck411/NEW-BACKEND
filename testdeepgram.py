#!/usr/bin/env python3
import os
import asyncio
import threading
import logging
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")

if not DEEPGRAM_API_KEY:
    print("❌ Error: DEEPGRAM_API_KEY not found in .env file")
    print("Please check your .env file contains: DEEPGRAM_API_KEY=your_api_key_here")
    exit(1)

print(f"✅ Loaded API key from .env: {DEEPGRAM_API_KEY[:8]}..." if len(DEEPGRAM_API_KEY) > 8 else "✅ API key loaded")

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
        """Set up the Deepgram WebSocket connection and event handlers (WORKING METHOD)."""
        self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")

        async def on_open(client, open, **kwargs):
            logger.info("🔗 Deepgram connection established (OFFICIAL SDK)")
            print(f"📊 Connection opened with metadata: {open}")

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
                print(f"🎵 Raw result received: {result}")  # Debug output
                transcript = result.channel.alternatives[0].transcript
                if transcript.strip():
                    if result.is_final:
                        confidence = getattr(result.channel.alternatives[0], "confidence", "N/A")
                        print(f"✔️ FINAL: {transcript} (Confidence: {confidence})")
                        self.is_final_transcript.append(transcript)
                    else:
                        print(f"⚡ INTERIM: {transcript}")
                else:
                    print("🔇 Empty transcript received")
            except Exception as e:
                logger.error(f"Error processing transcript: {e}")
                print(f"🐛 Full result object: {result}")

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)

        async def on_metadata(client, metadata, **kwargs):
            print(f"📊 Metadata: {metadata}")

        self.dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)

        async def on_speech_started(client, speech_started, **kwargs):
            print(f"🗣️ Speech started: {speech_started}")

        self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)

        async def on_utterance_end(client, utterance_end, **kwargs):
            print(f"🔚 Utterance end: {utterance_end}")
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
            
            # Start connection with official method
            started = await self.dg_connection.start(options)
            if not started:
                raise Exception("Failed to start Deepgram connection")
                
            print("🔗 Official SDK connection started successfully!")
                
            # Use Deepgram's Microphone class for audio input
            print("🎤 Setting up microphone...")
            try:
                # Try to list available audio devices
                import pyaudio
                p = pyaudio.PyAudio()
                print("🔊 Available audio devices:")
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        print(f"  Device {i}: {info['name']} (inputs: {info['maxInputChannels']})")
                p.terminate()
            except Exception as e:
                print(f"Could not list audio devices: {e}")
            
            self.microphone = Microphone(self.dg_connection.send)
            print("📡 Starting microphone stream...")
            self.microphone.start()
            
            self.is_running = True
            logger.info("🎤 STT started with OFFICIAL SDK - speak into your microphone!")
            print("🔊 Microphone should now be listening...")
            
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
    print("🎙️  Deepgram Speech-to-Text Terminal (WORKING VERSION)")
    print("=" * 52)
    print("Using asyncwebsocket.v('1') - Current working method")
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