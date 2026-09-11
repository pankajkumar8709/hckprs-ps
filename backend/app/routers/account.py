"""F2.9 — Premium plan stub. GET /account/plan, POST /account/upgrade."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    AuditLog, Conversation, Document, DocumentChunk, ExtractedField, Insight,
    Message, Reminder, ShareGrant, User,
)
from app.schemas import AuditLogResponse, PlanResponse
from app.services import audit

router = APIRouter(prefix="/account", tags=["account"])

_FREE_TIER_DOC_LIMIT = 10


def _plan(user: User) -> PlanResponse:
    return PlanResponse(
        plan_tier=user.plan_tier,
        document_limit=None if user.plan_tier == "premium" else _FREE_TIER_DOC_LIMIT,
    )


@router.get("/plan", response_model=PlanResponse)
def get_plan(current_user: User = Depends(get_current_user)) -> PlanResponse:
    return _plan(current_user)


@router.post("/upgrade", response_model=PlanResponse)
def upgrade(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanResponse:
    current_user.plan_tier = "premium"
    db.commit()
    db.refresh(current_user)
    return _plan(current_user)


@router.get("/audit-log", response_model=list[AuditLogResponse])
def audit_log(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLog]:
    """F3.7 — the user's own audit trail (login, document access, shares, etc.)."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)  # RULE 4
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )


@router.delete("", status_code=204, response_class=Response)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """F3.8 — right-to-be-forgotten. Cascade-delete EVERYTHING for this user:
    storage files on disk, vector embeddings (document_chunks), documents,
    extracted fields, reminders, insights, conversations, messages, share grants,
    audit logs — then the user row. Verified by tests that the vector rows are
    actually gone, not just the Postgres user row."""
    import os
    uid = current_user.id

    # Audit the deletion BEFORE we remove the user's rows (best-effort).
    audit.log_audit(db, uid, audit.ACCOUNT_DELETE, resource_type="account", resource_id=uid)

    # 1) Delete storage files on disk (encrypted blobs).
    docs = db.query(Document).filter(Document.user_id == uid).all()
    for d in docs:
        if d.storage_path:
            try:
                os.remove(d.storage_path)
            except OSError:
                pass  # already gone / inaccessible

    # 2) Explicitly delete every user-owned table (vector embeddings FIRST —
    # the part teams usually fake). synchronize_session=False for bulk delete.
    db.query(DocumentChunk).filter(DocumentChunk.user_id == uid).delete(synchronize_session=False)
    db.query(ExtractedField).filter(ExtractedField.user_id == uid).delete(synchronize_session=False)
    db.query(Message).filter(Message.user_id == uid).delete(synchronize_session=False)
    db.query(Reminder).filter(Reminder.user_id == uid).delete(synchronize_session=False)
    db.query(Insight).filter(Insight.user_id == uid).delete(synchronize_session=False)
    db.query(Conversation).filter(Conversation.user_id == uid).delete(synchronize_session=False)
    db.query(ShareGrant).filter(
        (ShareGrant.owner_user_id == uid) | (ShareGrant.shared_with_user_id == uid)
    ).delete(synchronize_session=False)
    db.query(Document).filter(Document.user_id == uid).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.user_id == uid).delete(synchronize_session=False)

    # 3) Finally the user row.
    db.query(User).filter(User.id == uid).delete(synchronize_session=False)
    db.commit()
    return Response(status_code=204)
