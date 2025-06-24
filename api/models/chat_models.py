"""
Pydantic models for chat API
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message model"""
    type: str = Field(..., description="Message type (e.g., 'text_message')")
    content: str = Field(..., description="Message content")
    id: Optional[str] = Field(None, description="Message ID for tracking")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ChatResponse(BaseModel):
    """Chat response model"""
    type: str = Field(..., description="Response type")
    content: Optional[str] = Field(None, description="Response content")
    id: Optional[str] = Field(None, description="Message ID reference")
    full_content: Optional[str] = Field(None, description="Complete response content")


class ErrorResponse(BaseModel):
    """Error response model"""
    type: str = Field(default="error", description="Response type")
    error: str = Field(..., description="Error message")
    id: Optional[str] = Field(None, description="Message ID reference")


class HistoryRequest(BaseModel):
    """Request for conversation history"""
    type: str = Field(default="get_history", description="Request type")


class HistoryResponse(BaseModel):
    """Conversation history response"""
    type: str = Field(default="history", description="Response type")
    data: List[Dict[str, Any]] = Field(..., description="Conversation history")


class ConfigRequest(BaseModel):
    """Request for configuration"""
    type: str = Field(default="get_config", description="Request type")


class ConfigResponse(BaseModel):
    """Configuration response"""
    type: str = Field(default="config", description="Response type")
    data: Dict[str, Any] = Field(..., description="Configuration data")


class PingMessage(BaseModel):
    """Ping message for connection health check"""
    type: str = Field(default="ping", description="Message type")


class PongMessage(BaseModel):
    """Pong response to ping"""
    type: str = Field(default="pong", description="Response type")


class MessageStartResponse(BaseModel):
    """Response when message processing starts"""
    type: str = Field(default="message_start", description="Response type")
    id: str = Field(..., description="Message ID")
    user_message: str = Field(..., description="Original user message")


class TextChunkResponse(BaseModel):
    """Streaming text chunk response"""
    type: str = Field(default="text_chunk", description="Response type")
    id: str = Field(..., description="Message ID")
    content: str = Field(..., description="Text chunk content")


class MessageCompleteResponse(BaseModel):
    """Response when message processing is complete"""
    type: str = Field(default="message_complete", description="Response type")
    id: str = Field(..., description="Message ID")
    full_content: str = Field(..., description="Complete response content") 