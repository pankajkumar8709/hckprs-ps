"""Core data model — Section 0.3. LOCKED. Do not redesign mid-phase.

Conventions (Section 0.2):
- Every user-data table has: id (UUID PK), user_id (UUID FK, indexed, NOT NULL),
  created_at, updated_at.
- snake_case columns. Enum-ish string columns use CHECK constraints so the DB,
  not just the app, enforces the allowed values.

Schema decisions made in Section 0 (flagged to the user, not in the plan verbatim):
- ExtractedField.source_span -> JSONB (e.g. {"start": 120, "end": 168}).
- Insight.related_reminder_ids -> ARRAY(UUID).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    plan_tier: Mapped[str] = mapped_column(String(20), default="free", nullable=False)

    __table_args__ = (
        CheckConstraint("plan_tier IN ('free', 'premium')", name="ck_users_plan_tier"),
    )


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(32), default="other", nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024))
    ocr_text: Mapped[str | None] = mapped_column(Text)
    upload_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    agent_trace_json: Mapped[dict | None] = mapped_column(JSONB)  # F2.2

    __table_args__ = (
        Index("ix_documents_user_id", "user_id"),
        CheckConstraint(
            "doc_type IN ('lease','insurance','loan_emi','subscription','medical','other')",
            name="ck_documents_doc_type",
        ),
        CheckConstraint(
            "upload_status IN ('pending','processing','done','failed')",
            name="ck_documents_upload_status",
        ),
    )


class ExtractedField(Base, TimestampMixin):
    __tablename__ = "extracted_fields"

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text)
    field_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_span: Mapped[dict | None] = mapped_column(JSONB)  # {"start": int, "end": int}
    confidence: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("ix_extracted_fields_user_id", "user_id"),
        Index("ix_extracted_fields_document_id", "document_id"),
        CheckConstraint(
            "field_type IN ('date','amount','text','party')",
            name="ck_extracted_fields_field_type",
        ),
    )


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    source_field_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extracted_fields.id", ondelete="SET NULL")
    )

    __table_args__ = (
        Index("ix_reminders_user_id", "user_id"),
        CheckConstraint(
            "status IN ('pending','done','dismissed')", name="ck_reminders_status"
        ),
    )


class Insight(Base, TimestampMixin):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    related_reminder_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True))
    )
    severity: Mapped[str] = mapped_column(String(16), default="low", nullable=False)

    __table_args__ = (
        Index("ix_insights_user_id", "user_id"),
        CheckConstraint(
            "type IN ('date_clash','renewal_risk','unused_subscription')",
            name="ck_insights_type",
        ),
    )


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(512))

    __table_args__ = (Index("ix_conversations_user_id", "user_id"),)


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    agent_trace_json: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_messages_user_id", "user_id"),
        Index("ix_messages_conversation_id", "conversation_id"),
        CheckConstraint("role IN ('user','assistant')", name="ck_messages_role"),
    )


class ShareGrant(Base, TimestampMixin):
    __tablename__ = "share_grants"

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission: Mapped[str] = mapped_column(String(8), default="view", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_share_grants_owner_user_id", "owner_user_id"),
        Index("ix_share_grants_shared_with_user_id", "shared_with_user_id"),
        Index("ix_share_grants_document_id", "document_id"),
        CheckConstraint(
            "permission IN ('view','edit')", name="ck_share_grants_permission"
        ),
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (Index("ix_audit_logs_user_id", "user_id"),)
