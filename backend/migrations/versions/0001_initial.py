"""initial schema — Section 0.3 core data model

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-10

Creates all 9 tables from Section 0.3 with the 0.2 conventions (UUID id, user_id
FK+index NOT NULL, created_at/updated_at), CHECK constraints for enum columns,
and enables the pgvector extension (needed from F2.4; enabling now keeps the
schema single-sourced).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # pgvector — used from F2.4. Requires the extension to be available on the
    # Supabase project (enable "vector" in Database -> Extensions if this errors).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("plan_tier", sa.String(20), nullable=False, server_default="free"),
        *_timestamps(),
        sa.CheckConstraint("plan_tier IN ('free','premium')", name="ck_users_plan_tier"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("doc_type", sa.String(32), nullable=False, server_default="other"),
        sa.Column("storage_path", sa.String(1024)),
        sa.Column("ocr_text", sa.Text()),
        sa.Column("upload_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("agent_trace_json", postgresql.JSONB()),
        *_timestamps(),
        sa.CheckConstraint(
            "doc_type IN ('lease','insurance','loan_emi','subscription','medical','other')",
            name="ck_documents_doc_type",
        ),
        sa.CheckConstraint(
            "upload_status IN ('pending','processing','done','failed')",
            name="ck_documents_upload_status",
        ),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "extracted_fields",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(128), nullable=False),
        sa.Column("field_value", sa.Text()),
        sa.Column("field_type", sa.String(16), nullable=False),
        sa.Column("source_span", postgresql.JSONB()),
        sa.Column("confidence", sa.Float()),
        *_timestamps(),
        sa.CheckConstraint(
            "field_type IN ('date','amount','text','party')",
            name="ck_extracted_fields_field_type",
        ),
    )
    op.create_index("ix_extracted_fields_user_id", "extracted_fields", ["user_id"])
    op.create_index("ix_extracted_fields_document_id", "extracted_fields", ["document_id"])

    op.create_table(
        "reminders",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("due_date", TS),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("source_field_id", UUID, sa.ForeignKey("extracted_fields.id", ondelete="SET NULL")),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending','done','dismissed')", name="ck_reminders_status"
        ),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])

    op.create_table(
        "insights",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("related_reminder_ids", postgresql.ARRAY(UUID)),
        sa.Column("severity", sa.String(16), nullable=False, server_default="low"),
        *_timestamps(),
        sa.CheckConstraint(
            "type IN ('date_clash','renewal_risk','unused_subscription')",
            name="ck_insights_type",
        ),
    )
    op.create_index("ix_insights_user_id", "insights", ["user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512)),
        *_timestamps(),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("agent_trace_json", postgresql.JSONB()),
        *_timestamps(),
        sa.CheckConstraint("role IN ('user','assistant')", name="ck_messages_role"),
    )
    op.create_index("ix_messages_user_id", "messages", ["user_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "share_grants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_with_user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(8), nullable=False, server_default="view"),
        sa.Column("expires_at", TS),
        *_timestamps(),
        sa.CheckConstraint("permission IN ('view','edit')", name="ck_share_grants_permission"),
    )
    op.create_index("ix_share_grants_owner_user_id", "share_grants", ["owner_user_id"])
    op.create_index("ix_share_grants_shared_with_user_id", "share_grants", ["shared_with_user_id"])
    op.create_index("ix_share_grants_document_id", "share_grants", ["document_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64)),
        sa.Column("resource_id", UUID),
        sa.Column("ip_address", sa.String(64)),
        *_timestamps(),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("share_grants")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("insights")
    op.drop_table("reminders")
    op.drop_table("extracted_fields")
    op.drop_table("documents")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
