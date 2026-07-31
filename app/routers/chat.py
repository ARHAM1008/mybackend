"""
AI Chat Router: Streaming chat with Groq, conversation management, and model selection.

Endpoints:
  GET    /api/ai/models
  POST   /api/ai/chat
  POST   /api/ai/chat/stream
  POST   /api/ai/chat/regenerate
  GET    /api/ai/chat/history
  GET    /api/ai/chat/history/{conversation_id}
  PATCH  /api/ai/chat/history/{conversation_id}
  DELETE /api/ai/chat/{conversation_id}

Also exposes aliases under /api/chat/* for the requested API surface.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.database.connection import get_db
from app.models.chat import ChatMessage, Conversation
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationListResponse,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
    RegenerateRequest,
)
from app.services.groq_service import (
    GroqServiceError,
    chat_completion_with_usage,
    list_models,
    resolve_model,
    stream_chat,
)


router = APIRouter(tags=["AI Chat"])

# Simple in-memory rate limit buckets: user_id -> list[timestamps]
_rate_buckets: dict[int, list[float]] = {}


def _enforce_chat_rate_limit(user_id: int) -> None:
    max_requests = settings.CHAT_RATE_LIMIT_PER_MINUTE or 30
    window = 60
    now = time.time()
    bucket = [t for t in _rate_buckets.get(user_id, []) if now - t < window]
    if len(bucket) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests. Please slow down.",
        )
    bucket.append(now)
    _rate_buckets[user_id] = bucket


def _sanitize_message(text: str) -> str:
    """Basic input sanitization — strip null bytes and extreme whitespace."""
    return (text or "").replace("\x00", "").strip()


def _title_from_message(message: str) -> str:
    clean = " ".join(message.split())
    return (clean[:45] + "…") if len(clean) > 45 else (clean or "New Conversation")


def _get_user_conversation(db: Session, user_id: int, conversation_id: int) -> Conversation:
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _history_dicts(history) -> list[dict]:
    if not history:
        return []
    out = []
    for item in history:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        elif isinstance(item, dict):
            out.append(item)
    return out


def _ensure_conversation(
    db: Session,
    user: User,
    conversation_id: Optional[int],
    message: str,
    model: str,
    persist: bool,
) -> Optional[Conversation]:
    if not persist:
        return None
    if conversation_id:
        return _get_user_conversation(db, user.id, conversation_id)

    conv = Conversation(
        user_id=user.id,
        title=_title_from_message(message),
        model=model,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _save_message(
    db: Session,
    conversation: Optional[Conversation],
    *,
    role: str,
    content: str,
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> None:
    if conversation is None:
        return
    msg = ChatMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    conversation.updated_at = datetime.now(timezone.utc)
    if model:
        conversation.model = model
    db.add(msg)
    db.commit()


def _conversation_out(conv: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        pinned=bool(conv.pinned),
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages) if conv.messages is not None else 0,
    )


# ─── Models ───────────────────────────────────────────────────────────────────

@router.get("/ai/models")
@router.get("/chat/models")
def get_models():
    """Get available Groq models."""
    return {"models": list_models(), "default": resolve_model()}


# ─── Non-streaming chat ───────────────────────────────────────────────────────

@router.post("/ai/chat", response_model=ChatResponse)
@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a non-streaming chat response from Groq."""
    _enforce_chat_rate_limit(current_user.id)
    message = _sanitize_message(data.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    model = resolve_model(data.model)
    conv = _ensure_conversation(db, current_user, data.conversation_id, message, model, data.persist)
    _save_message(db, conv, role="user", content=message, model=model)

    history = _history_dicts(data.history)
    if not history and conv is not None:
        history = [{"role": m.role, "content": m.content} for m in conv.messages if m.role in ("user", "assistant")]
        # Exclude the user message we just saved from being duplicated if client also sent history
        if history and history[-1]["role"] == "user" and history[-1]["content"] == message:
            history = history[:-1]

    try:
        result = await chat_completion_with_usage(
            message=message,
            model=model,
            history=history,
            system_prompt=data.system_prompt,
            temperature=data.temperature or 0.7,
            max_tokens=data.max_tokens or 4096,
        )
    except GroqServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.user_message) from exc

    _save_message(
        db,
        conv,
        role="assistant",
        content=result["content"],
        model=result["model"],
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
    )

    return ChatResponse(
        response=result["content"],
        model=result["model"],
        conversation_id=conv.id if conv else None,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        total_tokens=result["total_tokens"],
    )


# ─── Streaming chat ───────────────────────────────────────────────────────────

@router.post("/ai/chat/stream")
@router.post("/chat/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a chat response from Groq (SSE)."""
    _enforce_chat_rate_limit(current_user.id)
    message = _sanitize_message(data.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    model = resolve_model(data.model)
    conv = _ensure_conversation(db, current_user, data.conversation_id, message, model, data.persist)
    _save_message(db, conv, role="user", content=message, model=model)

    history = _history_dicts(data.history)
    if not history and conv is not None:
        history = [{"role": m.role, "content": m.content} for m in conv.messages if m.role in ("user", "assistant")]
        if history and history[-1]["role"] == "user" and history[-1]["content"] == message:
            history = history[:-1]

    conversation_id = conv.id if conv else None
    logger.info(
        f"Chat stream user={current_user.id} model={model} conv={conversation_id} len={len(message)}"
    )

    async def event_generator():
        collected: list[str] = []
        try:
            async for chunk in stream_chat(
                message=message,
                model=model,
                history=history,
                system_prompt=data.system_prompt,
                temperature=data.temperature or 0.7,
                max_tokens=data.max_tokens or 4096,
            ):
                # Extract token text for persistence
                if chunk.startswith("data: ") and "[DONE]" not in chunk:
                    try:
                        import json

                        payload = json.loads(chunk[6:].strip())
                        token = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if token:
                            collected.append(token)
                    except Exception:
                        pass
                yield chunk
        finally:
            full = "".join(collected).strip()
            if full and conversation_id is not None:
                # Fresh session for post-stream write
                from app.database.connection import SessionLocal

                session = SessionLocal()
                try:
                    c = session.query(Conversation).filter(Conversation.id == conversation_id).first()
                    if c:
                        session.add(
                            ChatMessage(
                                conversation_id=c.id,
                                role="assistant",
                                content=full,
                                model=model,
                            )
                        )
                        c.updated_at = datetime.now(timezone.utc)
                        c.model = model
                        session.commit()
                except Exception as exc:
                    logger.error(f"Failed to persist streamed message: {exc}")
                finally:
                    session.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": str(conversation_id or ""),
        },
    )


# ─── Regenerate ───────────────────────────────────────────────────────────────

@router.post("/ai/chat/regenerate")
@router.post("/chat/regenerate")
async def regenerate(
    data: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate the last assistant reply for a conversation (streaming)."""
    _enforce_chat_rate_limit(current_user.id)
    conv = _get_user_conversation(db, current_user.id, data.conversation_id)

    # Drop trailing assistant messages
    while conv.messages and conv.messages[-1].role == "assistant":
        db.delete(conv.messages[-1])
        db.commit()
        db.refresh(conv)

    last_user = next((m for m in reversed(conv.messages) if m.role == "user"), None)
    if not last_user:
        raise HTTPException(status_code=400, detail="No user message to regenerate from")

    model = resolve_model(data.model or conv.model)
    history = [{"role": m.role, "content": m.content} for m in conv.messages if m.role in ("user", "assistant")]
    # Exclude last user message from history (it is the prompt)
    if history and history[-1]["role"] == "user":
        prompt = history[-1]["content"]
        history = history[:-1]
    else:
        prompt = last_user.content

    conversation_id = conv.id

    async def event_generator():
        collected: list[str] = []
        try:
            async for chunk in stream_chat(
                message=prompt,
                model=model,
                history=history,
                temperature=data.temperature or 0.7,
                max_tokens=data.max_tokens or 4096,
            ):
                if chunk.startswith("data: ") and "[DONE]" not in chunk:
                    try:
                        import json

                        payload = json.loads(chunk[6:].strip())
                        token = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if token:
                            collected.append(token)
                    except Exception:
                        pass
                yield chunk
        finally:
            full = "".join(collected).strip()
            if full:
                from app.database.connection import SessionLocal

                session = SessionLocal()
                try:
                    c = session.query(Conversation).filter(Conversation.id == conversation_id).first()
                    if c:
                        session.add(
                            ChatMessage(
                                conversation_id=c.id,
                                role="assistant",
                                content=full,
                                model=model,
                            )
                        )
                        c.updated_at = datetime.now(timezone.utc)
                        c.model = model
                        session.commit()
                except Exception as exc:
                    logger.error(f"Failed to persist regenerated message: {exc}")
                finally:
                    session.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": str(conversation_id),
        },
    )


# ─── History ──────────────────────────────────────────────────────────────────

@router.get("/ai/chat/history", response_model=ConversationListResponse)
@router.get("/chat/history", response_model=ConversationListResponse)
def list_history(
    q: Optional[str] = Query(default=None, description="Search conversations by title"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's conversations."""
    query = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.user_id == current_user.id)
    )
    if q:
        query = query.filter(Conversation.title.ilike(f"%{q.strip()}%"))
    convs = query.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()).all()
    return ConversationListResponse(
        conversations=[_conversation_out(c) for c in convs],
        total=len(convs),
    )


@router.get("/ai/chat/history/{conversation_id}", response_model=ConversationDetail)
@router.get("/chat/history/{conversation_id}", response_model=ConversationDetail)
def get_history_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a conversation with all messages."""
    conv = _get_user_conversation(db, current_user.id, conversation_id)
    return ConversationDetail(
        **_conversation_out(conv).model_dump(),
        messages=[MessageOut.model_validate(m) for m in conv.messages],
    )


@router.patch("/ai/chat/history/{conversation_id}", response_model=ConversationOut)
@router.patch("/chat/history/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename or pin/unpin a conversation."""
    conv = _get_user_conversation(db, current_user.id, conversation_id)
    if data.title is not None:
        conv.title = data.title.strip()
    if data.pinned is not None:
        conv.pinned = data.pinned
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conv)
    return _conversation_out(conv)


@router.delete("/ai/chat/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/chat/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and all of its messages."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return None
