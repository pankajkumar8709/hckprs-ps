"""F3.9 — jobs + failed_jobs (async queue + dead-letter)

Revision ID: 0003_jobs
Revises: 0002_document_chunks
Create Date: 2026-09-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_jobs"
down_revision: Union[str, None] = "0002_document_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("job_type", sa.String(32), nullable=False, server_default="ingest"),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_run_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_by", sa.String(64), nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('queued','running','done','failed')", name="ck_jobs_status"),
    )
    op.create_index("ix_jobs_status_next_run", "jobs", ["status", "next_run_at"])
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])

    op.create_table(
        "failed_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("document_id", UUID, nullable=True),
        sa.Column("job_type", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_failed_jobs_user_id", "failed_jobs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_failed_jobs_user_id", table_name="failed_jobs")
    op.drop_table("failed_jobs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_index("ix_jobs_status_next_run", table_name="jobs")
    op.drop_table("jobs")
