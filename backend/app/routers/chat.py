"""Chat endpoints (Section 0.4): POST /chat, list conversations, list messages.

Basic Q&A (Phase 1 MVP): grounds the answer in the user's own ExtractedField rows,
persists the user + assistant messages, returns the assistant reply.

RULE 4: every query filters by current_user.id.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Conversation, ExtractedField, Message, User
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services import llm

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_context(db: Session, user_id: uuid.UUID) -> str:
    fields = (
        db.query(ExtractedField)
        .filter(ExtractedField.user_id == user_id)  # RULE 4
        .order_by(ExtractedField.created_at.desc())
        .limit(100)
        .all()
    )
    if not fields:
        return ""
    return "\n".join(
        f"- {f.field_name} ({f.field_type}): {f.field_value}" for f in fields
    )


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    # Resolve or create the conversation, scoped to this user.
    if body.conversation_id is not None:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == body.conversation_id,
                Conversation.user_id == current_user.id,  # RULE 4
            )
            .first()
        )
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(
            user_id=current_user.id,
            title=body.message[:60],
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    db.add(
        Message(
            conversation_id=conv.id,
            user_id=current_user.id,
            role="user",
            content=body.message,
        )
    )
    db.commit()

    context = _build_context(db, current_user.id)
    answer = llm.answer_question(body.message, context)

    assistant_msg = Message(
        conversation_id=conv.id,
        user_id=current_user.id,
        role="assistant",
        content=answer,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(conversation_id=conv.id, message=assistant_msg)


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)  # RULE 4
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conv_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Message]:
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conv_id,
            Conversation.user_id == current_user.id,  # RULE 4
        )
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return (
        db.query(Message)
        .filter(
            Message.conversation_id == conv_id,
            Message.user_id == current_user.id,  # RULE 4
        )
        .order_by(Message.created_at.asc())
        .all()
    )
