"""Pydantic v2 request/response schemas for the Phase 1 MVP endpoints.

Kept separate from SQLAlchemy models. Response models use from_attributes so
they can be built directly from ORM rows.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    plan_tier: str
    created_at: datetime


# ---------- Documents ----------
class ExtractedFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    field_name: str
    field_value: str | None
    field_type: str
    source_span: dict | None
    confidence: float | None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    doc_type: str
    upload_status: str
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    ocr_text: str | None
    extracted_fields: list[ExtractedFieldResponse] = []
    agent_trace: list[dict] = []  # F2.2 — "How this was extracted"


# ---------- Reminders (F2.3) ----------
class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID | None
    title: str
    due_date: datetime | None
    status: str
    created_at: datetime


class ReminderUpdateRequest(BaseModel):
    status: str = Field(pattern="^(pending|done|dismissed)$")


class ReminderCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    due_date: datetime | None = None


# ---------- Insights (F2.7) ----------
class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    description: str | None
    related_reminder_ids: list[uuid.UUID] | None
    severity: str
    created_at: datetime


# ---------- Sharing (F2.8) ----------
class ShareRequest(BaseModel):
    shared_with_email: EmailStr
    permission: str = Field(default="view", pattern="^(view|edit)$")
    expires_at: datetime | None = None


class ShareGrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    shared_with_user_id: uuid.UUID
    permission: str
    expires_at: datetime | None
    created_at: datetime


# ---------- Account / Premium (F2.9) ----------
class PlanResponse(BaseModel):
    plan_tier: str
    document_limit: int | None  # None = unlimited


# ---------- Chat ----------
class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=8000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: str
    content: str | None
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message: MessageResponse
    intent: str = "question"  # F2.5 router intent
    citations: list[dict] = []  # F2.4 [{document_id, filename}]


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str | None
    created_at: datetime
