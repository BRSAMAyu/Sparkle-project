"""Chat Schemas - Chat messages, sessions, etc."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import MessageRole
from app.schemas.common import BaseSchema

# ========== Request Schemas ==========

class ChatMessageSend(BaseModel):
    """Send message"""
    content: str = Field(min_length=1, description="Message content")
    session_id: UUID | None = Field(default=None, description="Session ID (create new if not provided)")
    task_id: UUID | None = Field(default=None, description="Related task ID")
    context: dict | None = Field(default=None, description="Context information")
    # 🆕 v2.1: 客户端生成的消息 ID（用于幂等）
    message_id: str | None = Field(default=None, description="Client generated message ID for idempotency")

class ChatSessionCreate(BaseModel):
    """Create session"""
    task_id: UUID | None = Field(default=None, description="Related task ID")
    initial_message: str | None = Field(default=None, description="Initial message")

# ========== Response Schemas ==========

class ChatMessageBase(BaseSchema):
    """Chat message basic information"""
    session_id: UUID = Field(description="Session ID")
    role: MessageRole = Field(description="Message role")
    content: str = Field(description="Message content")

class ChatMessageDetail(ChatMessageBase):
    """Chat message detailed information"""
    user_id: UUID = Field(description="User ID")
    task_id: UUID | None = Field(description="Related task ID")
    actions: list[Any] | None = Field(description="AI actions")
    tokens_used: int | None = Field(description="Tokens used")
    model_name: str | None = Field(description="Model name")

class ChatSession(BaseModel):
    """Chat session information"""
    session_id: UUID = Field(description="Session ID")
    user_id: UUID = Field(description="User ID")
    task_id: UUID | None = Field(description="Related task ID")
    message_count: int = Field(description="Message count")
    created_at: datetime = Field(description="Created time")
    last_message_at: datetime = Field(description="Last message time")

    model_config = ConfigDict(from_attributes=True)

class ChatHistory(BaseModel):
    """Chat history"""
    session_id: UUID = Field(description="Session ID")
    messages: list[ChatMessageDetail] = Field(description="Messages list")
    total_messages: int = Field(description="Total messages")

class AIResponse(BaseModel):
    """AI response"""
    message_id: UUID = Field(description="Message ID")
    session_id: UUID = Field(description="Session ID")
    content: str = Field(description="AI reply content")
    actions: list[Any] | None = Field(default=None, description="AI actions")
    suggestions: list[str] | None = Field(default=None, description="Suggestions list")
    created_at: datetime = Field(description="Created time")

    model_config = ConfigDict(from_attributes=True)
