"""F3.7 — audit logging for sensitive actions.

A single `log_audit()` writes an AuditLog row (action, resource, ip, user).
Resilient: an audit-write failure must never break the underlying action, so
it swallows errors after a rollback. Actions are short stable strings so the
audit-log view and tests can match them.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog

# Stable action names (used by the log view and tests).
LOGIN = "login"
DOC_UPLOAD = "document.upload"
DOC_ACCESS = "document.access"
DOC_DELETE = "document.delete"
DOC_DOWNLOAD = "document.download"
SHARE_CREATE = "share.create"
ACCOUNT_DELETE = "account.delete"
# Blocked / security events (F3.5 / F3.6) — probing leaves a trail.
SECURITY_UPLOAD_BLOCKED = "security.upload_blocked"
SECURITY_INJECTION_BLOCKED = "security.injection_blocked"


def log_audit(
    db: Session,
    user_id: uuid.UUID,
    action: str,
    *,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> None:
    """Write one audit row. Never raises — a logging failure must not break the
    action being audited."""
    try:
        db.add(AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
        ))
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
