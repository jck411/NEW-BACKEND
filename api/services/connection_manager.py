"""
WebSocket Connection Manager
Handles multiple concurrent frontend connections
"""
import uuid
import logging
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections from multiple frontends"""
    
    def __init__(self):
        # Active connections: client_id -> websocket
        self.active_connections: Dict[str, WebSocket] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept a new WebSocket connection and return client ID
        """
        await websocket.accept()
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        
        self.logger.info(f"New connection: {client_id} (total: {len(self.active_connections)})")
        return client_id
    
    def disconnect(self, client_id: str):
        """Remove a client connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self.logger.info(f"Disconnected: {client_id} (remaining: {len(self.active_connections)})")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                self.logger.error(f"Failed to send message to {client_id}: {e}")
                # Remove broken connection
                self.disconnect(client_id)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                self.logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up broken connections
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_client_ids(self) -> Set[str]:
        """Get all active client IDs"""
        return set(self.active_connections.keys())
    
    async def ping_all(self):
        """Send ping to all connections to check health"""
        import json
        ping_message = json.dumps({"type": "ping"})
        await self.broadcast(ping_message)
    
    def is_connected(self, client_id: str) -> bool:
        """Check if a client is still connected"""
        return client_id in self.active_connections 