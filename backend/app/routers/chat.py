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
from app.models import Conversation, Document, ExtractedField, Message, Reminder, User
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services import llm, rag

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_context(db: Session, user_id: uuid.UUID) -> str:
    fields = (
        db.query(ExtractedField)
        .filter(ExtractedField.user_id == user_id)  # RULE 4
        .order_by(ExtractedField.created_at.desc())
        .limit(100)
        .all()
    )
    parts: list[str] = []
    if fields:
        parts.append("Extracted fields from the user's documents:")
        parts.extend(
            f"- {f.field_name} ({f.field_type}): {f.field_value}" for f in fields
        )

    # Fall back to (and augment with) the raw document text so ANY uploaded
    # document is answerable, not just those with financial-style fields.
    docs = (
        db.query(Document)
        .filter(Document.user_id == user_id)  # RULE 4
        .order_by(Document.created_at.desc())
        .limit(5)
        .all()
    )
    for d in docs:
        if d.ocr_text:
            parts.append(f"\n--- Document: {d.filename} ---\n{d.ocr_text[:6000]}")

    return "\n".join(parts).strip()


def _reminders_summary(db: Session, user_id: uuid.UUID) -> str:
    reminders = (
        db.query(Reminder)
        .filter(Reminder.user_id == user_id, Reminder.status == "pending")  # RULE 4
        .order_by(Reminder.due_date.asc().nullslast())
        .limit(20)
        .all()
    )
    if not reminders:
        return "You have no pending reminders."
    lines = ["Your pending reminders:"]
    for r in reminders:
        due = r.due_date.date().isoformat() if r.due_date else "no date"
        lines.append(f"- {r.title} (due {due})")
    return "\n".join(lines)


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

    # F2.5 — Router Agent classifies intent, dispatch to the right path.
    intent = llm.route_intent(body.message)
    citations: list[dict] = []

    if intent == "show_reminders":
        answer = _reminders_summary(db, current_user.id)
    elif intent == "upload_help":
        answer = ("To add a document, use the upload panel (or POST /documents/"
                  "upload). PDF, TXT, MD and images are supported.")
    else:
        # question / show_insights / general -> ground in the user's documents.
        # F2.4 — try user-scoped RAG retrieval first; fall back to whole-text.
        rag_context, citations = rag.search(db, current_user.id, body.message, k=5)
        context = rag_context or _build_context(db, current_user.id)
        answer = llm.answer_question(body.message, context)

    assistant_msg = Message(
        conversation_id=conv.id,
        user_id=current_user.id,
        role="assistant",
        content=answer,
        agent_trace_json={"intent": intent, "citations": citations},
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conv.id,
        message=assistant_msg,
        intent=intent,
        citations=citations,
    )


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
