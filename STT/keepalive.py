"""KeepAlive manager for Deepgram STT.

Handles keepalive pings during streaming responses.
"""

import asyncio
import contextlib
import logging
from typing import Any


class KeepAliveManager:
    """Manages KeepAlive functionality for Deepgram STT."""

    def __init__(self, logger: logging.Logger, stt_config: dict[str, Any]) -> None:
        self.logger = logger
        self.stt_config = stt_config
        self.keepalive_task: asyncio.Task[None] | None = None
        self.is_streaming_response = False
        self.is_running = False
        self.dg_connection: Any = None

    async def start_keepalive(self, dg_connection: Any) -> None:
        """Start KeepAlive using official Deepgram method."""
        if self.keepalive_task and not self.keepalive_task.done():
            return

        self.dg_connection = dg_connection
        self.is_streaming_response = True
        self.keepalive_task = asyncio.create_task(self._keepalive_sender())
        self.logger.debug("🔄 Started KeepAlive (official method)")

    async def stop_keepalive(self) -> None:
        """Stop KeepAlive."""
        self.is_streaming_response = False
        await self._stop_keepalive()
        self.logger.debug("⏹️ Stopped KeepAlive")

    async def _stop_keepalive(self) -> None:
        """Internal method to stop KeepAlive task."""
        if self.keepalive_task and not self.keepalive_task.done():
            self.keepalive_task.cancel()
            with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(self.keepalive_task, timeout=1.0)
            self.keepalive_task = None

    async def _keepalive_sender(self) -> None:
        """Send KeepAlive messages using official SDK method."""
        try:
            interval: int = self.stt_config.get("keepalive_interval", 3)
            while self.is_streaming_response and self.is_running:
                if self.dg_connection:
                    # Use official SDK's keep_alive method
                    await self.dg_connection.keep_alive()
                    self.logger.debug("📡 Sent KeepAlive (official SDK method)")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            self.logger.debug("KeepAlive sender cancelled")
        except Exception as e:
            self.logger.exception("Error in KeepAlive sender: %s", e)

    def set_running_state(self, is_running: bool) -> None:
        """Set running state."""
        self.is_running = is_running

    def pause_for_response_streaming(self) -> None:
        """Pause STT and start KeepAlive during response streaming."""
        if not self.is_running:
            return

        self.is_streaming_response = True
        self.logger.debug("🔄 STT paused for response streaming")

    def resume_from_response_streaming(self) -> None:
        """Resume STT processing after response streaming ends."""
        if not self.is_running:
            return

        self.is_streaming_response = False
        self.logger.debug("▶️ STT resumed from response streaming")
