"""F2.3 — Reminders endpoints. GET /reminders (filter+sort), PATCH /reminders/{id}.

RULE 4: every query filters by current_user.id.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Reminder, User
from app.schemas import ReminderResponse, ReminderUpdateRequest
from app.services.insights import regenerate_insights

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderResponse])
def list_reminders(
    status: str | None = Query(default=None, pattern="^(pending|done|dismissed)$"),
    sort: str = Query(default="due_date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Reminder]:
    q = db.query(Reminder).filter(Reminder.user_id == current_user.id)  # RULE 4
    if status:
        q = q.filter(Reminder.status == status)
    if sort == "due_date":
        q = q.order_by(Reminder.due_date.asc().nullslast())
    else:
        q = q.order_by(Reminder.created_at.desc())
    return q.all()


@router.patch("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reminder:
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id)  # RULE 4
        .first()
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder.status = body.status
    db.commit()
    db.refresh(reminder)
    # F2.7 — insights depend on pending reminders; refresh after a status change.
    regenerate_insights(db, current_user.id)
    return reminder
