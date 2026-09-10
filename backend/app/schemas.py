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


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str | None
    created_at: datetime
