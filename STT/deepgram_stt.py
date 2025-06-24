#!/usr/bin/env python3
"""
Deepgram SDK Speech-to-Text integration.
Refactored following 2025 best practices with proper separation of concerns
"""
import os
import asyncio
import logging
from typing import Callable
from dotenv import load_dotenv

from backend.exceptions import DeepgramSTTError, STTError, wrap_exception
from .handlers import STTEventHandlers
from .connection import DeepgramConnectionManager
from .keepalive import KeepAliveManager

# Load environment variables from .env file
load_dotenv()


class DeepgramSTT:
    """
    Refactored Deepgram SDK-based Speech-to-Text integration.
    Following 2025 best practices with proper separation of concerns.
    """
    
    def __init__(self, stt_config: dict, utterance_callback: Callable[[str], None]):
        self.stt_config = stt_config
        self.utterance_callback = utterance_callback
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        
        # Get API key
        api_key_env = stt_config.get('api_key_env', 'DEEPGRAM_API_KEY')
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise DeepgramSTTError(f"Deepgram API key not found: {api_key_env}")
        
        # Initialize components with proper separation of concerns
        self.event_handlers = STTEventHandlers(self.logger, utterance_callback)
        self.connection_manager = DeepgramConnectionManager(api_key, stt_config, self.logger)
        self.keepalive_manager = KeepAliveManager(self.logger, stt_config)

    async def start_live_transcription(self):
        """Start live transcription using modular components"""
        try:
            # Start connection through connection manager
            dg_connection = await self.connection_manager.start_connection(self.event_handlers)
            
            # Update state across components
            self.is_running = True
            self.event_handlers.set_running_state(True)
            self.keepalive_manager.set_running_state(True)
            
            self.logger.info("🎤 Deepgram live transcription started (modular)")
            
        except Exception as e:
            self.logger.error(f"Error starting live transcription: {e}")
            wrapped_error = wrap_exception(e, DeepgramSTTError, "Failed to start transcription",
                                         error_code="STT_START_FAILED")
            raise wrapped_error

    async def finish_transcription(self):
        """Finish transcription using modular components"""
        try:
            self.is_running = False
            self.event_handlers.set_running_state(False)
            self.keepalive_manager.set_running_state(False)
            
            # Stop keepalive first
            await self.keepalive_manager.stop_keepalive()
            
            # Finish connection
            await self.connection_manager.finish_connection()
                
            self.logger.info("🛑 Live transcription finished")
            
        except Exception as e:
            self.logger.debug(f"Error finishing transcription (ignoring): {e}")

    # Public methods for integration with chatbot
    def pause_for_response_streaming(self):
        """Pause STT and start KeepAlive during response streaming"""
        if not self.is_running:
            return
        
        self.event_handlers.set_streaming_response(True)
        self.keepalive_manager.pause_for_response_streaming()
        
        # Start keepalive with current connection
        dg_connection = self.connection_manager.get_connection()
        if dg_connection:
            asyncio.run_coroutine_threadsafe(
                self.keepalive_manager.start_keepalive(dg_connection), 
                self.connection_manager.dg_loop
            )

    def resume_from_response_streaming(self):
        """Resume STT processing after response streaming ends"""
        if not self.is_running:
            return
        
        self.event_handlers.set_streaming_response(False)
        self.keepalive_manager.resume_from_response_streaming()

    # Sync wrapper methods using dedicated event loop
    def start(self):
        """Start the STT service"""
        if self.is_running:
            self.logger.warning("STT is already running")
            return
            
        self.logger.info("Starting live transcription...")
        future = asyncio.run_coroutine_threadsafe(
            self.start_live_transcription(), 
            self.connection_manager.dg_loop
        )
        try:
            future.result(timeout=10)  # Wait up to 10 seconds for start
        except Exception as e:
            wrapped_error = wrap_exception(e, DeepgramSTTError, "Failed to start STT service",
                                         error_code="STT_SERVICE_START_FAILED")
            raise wrapped_error

    def stop(self):
        """Stop the STT service"""
        if not self.is_running:
            return  # Silently return if already stopped
            
        self.logger.info("Stopping live transcription...")
        future = asyncio.run_coroutine_threadsafe(
            self.finish_transcription(), 
            self.connection_manager.dg_loop
        )
        try:
            future.result(timeout=3)  # Shorter timeout for faster shutdown
        except Exception as e:
            self.logger.debug(f"Stop error (ignoring): {e}")

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, '_cleanup_done') and self._cleanup_done:
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

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup() 