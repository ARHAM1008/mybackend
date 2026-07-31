"""
Pydantic schemas for AI chat endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=50_000)
    model: Optional[str] = None
    conversation_id: Optional[int] = None
    history: Optional[list[ChatMessageIn]] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096, ge=64, le=16384)
    persist: bool = True


class ChatResponse(BaseModel):
    response: str
    model: str
    conversation_id: Optional[int] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class RegenerateRequest(BaseModel):
    conversation_id: int
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=4096, ge=64, le=16384)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    model: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    title: str
    model: Optional[str] = None
    pinned: bool = False
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationListResponse(BaseModel):
    conversations: list[ConversationOut]
    total: int


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    pinned: Optional[bool] = None
