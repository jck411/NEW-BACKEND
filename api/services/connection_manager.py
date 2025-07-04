"""WebSocket Connection Manager
Handles multiple concurrent frontend connections.
"""

import json
import uuid

from fastapi import WebSocket

from api.config.logging import get_logger


class ConnectionManager:
    """Manages WebSocket connections from multiple frontends."""

    def __init__(self) -> None:
        # Active connections: client_id -> websocket
        self.active_connections: dict[str, WebSocket] = {}
        self.logger = get_logger(__name__)

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and return client ID."""
        await websocket.accept()
        client_id: str = str(uuid.uuid4())
        self.active_connections[client_id] = websocket

        self.logger.info(
            "New WebSocket connection established",
            client_id=client_id,
            total_connections=len(self.active_connections),
        )
        return client_id

    def disconnect(self, client_id: str) -> None:
        """Remove a client connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self.logger.info(
                "WebSocket connection disconnected",
                client_id=client_id,
                remaining_connections=len(self.active_connections),
            )

    async def send_personal_message(self, message: str, client_id: str) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                self.logger.exception(
                    "Failed to send WebSocket message",
                    client_id=client_id,
                    error=str(e),
                    exception_type=type(e).__name__,
                )
                # Remove broken connection
                self.disconnect(client_id)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        disconnected_clients: list[str] = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                self.logger.exception("Failed to broadcast to %s: %s", client_id, e)
                disconnected_clients.append(client_id)

        # Clean up broken connections
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_client_ids(self) -> set[str]:
        """Get all active client IDs."""
        return set(self.active_connections.keys())

    async def ping_all(self) -> None:
        """Send ping to all connections to check health."""
        ping_message = json.dumps({"type": "ping"})
        await self.broadcast(ping_message)

    def is_connected(self, client_id: str) -> bool:
        """Check if a client is still connected."""
        return client_id in self.active_connections
