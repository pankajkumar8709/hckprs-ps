"""F2.3 — Reminders endpoints. GET /reminders (filter+sort), PATCH /reminders/{id}.

RULE 4: every query filters by current_user.id.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Reminder, User
from app.schemas import ReminderCreateRequest, ReminderResponse, ReminderUpdateRequest
from app.services.insights import regenerate_insights
from app.services.ics import reminder_to_ics, safe_filename
from app.services.scoped import scoped_get

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(
    body: ReminderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reminder:
    """Manual task/reminder creation (user-authored, not document-derived)."""
    reminder = Reminder(
        user_id=current_user.id,  # RULE 4
        document_id=None,
        title=body.title,
        due_date=body.due_date,
        status="pending",
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    regenerate_insights(db, current_user.id)  # a new dated task may create a clash
    return reminder


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
    reminder = scoped_get(db, Reminder, reminder_id, current_user.id,
                          not_found_detail="Reminder not found")
    reminder.status = body.status
    db.commit()
    db.refresh(reminder)
    # F2.7 — insights depend on pending reminders; refresh after a status change.
    regenerate_insights(db, current_user.id)
    return reminder


@router.get("/{reminder_id}/calendar.ics")
def reminder_ics(
    reminder_id: uuid.UUID,
    alarm_days: int = Query(default=7, ge=0, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Download an .ics for this reminder with an alarm `alarm_days` before the
    due date, so the user's calendar notifies them ahead of the deadline."""
    reminder = scoped_get(db, Reminder, reminder_id, current_user.id,
                          not_found_detail="Reminder not found")
    ics = reminder_to_ics(reminder, alarm_days_before=alarm_days)
    fname = safe_filename(reminder.title)
    return Response(
        content=ics,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
