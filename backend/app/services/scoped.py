"""F3.2 — tenant isolation as a hard layer.

A single, reusable scoping mechanism that FORCES `user_id` filtering on every
query touching a user-owned table (Document, Reminder, Insight, Message,
ExtractedField, Conversation, ShareGrant, DocumentChunk). Endpoints must fetch
user-owned rows through these helpers instead of building raw queries, so an
endpoint physically cannot forget the filter.

Cross-user access returns 404 (not 403) — we do not confirm the resource exists
to a user who may not see it (no existence leak), matching the isolation tests.
"""
from __future__ import annotations

import uuid
from typing import Type, TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Query, Session

from app.models import (
    Conversation, Document, DocumentChunk, ExtractedField, Insight, Message,
    Reminder, ShareGrant,
)

# Tables that MUST always be user-scoped. A model not in this set is refused,
# so a new user-owned table added later cannot silently skip scoping.
_USER_SCOPED_MODELS = {
    Document, Reminder, Insight, Message, ExtractedField,
    Conversation, ShareGrant, DocumentChunk,
}

T = TypeVar("T")


def scoped_query(db: Session, model: Type[T], user_id: uuid.UUID) -> Query:
    """Return a Query already filtered to `user_id`. Refuses models that are not
    registered as user-scoped (prevents accidental unscoped access)."""
    if model not in _USER_SCOPED_MODELS:
        raise RuntimeError(
            f"{model.__name__} is not a registered user-scoped model; refusing "
            "to build an unscoped query."
        )
    return db.query(model).filter(model.user_id == user_id)  # forced user_id filter


def scoped_get(
    db: Session, model: Type[T], resource_id: uuid.UUID, user_id: uuid.UUID,
    *, not_found_detail: str = "Not found",
) -> T:
    """Fetch one row by id, scoped to user_id. Raises 404 if it does not exist
    OR belongs to another user (no existence leak — cross-tenant reads 404)."""
    row = scoped_query(db, model, user_id).filter(model.id == resource_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return row
