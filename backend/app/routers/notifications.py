"""Notifications (Option A) — DERIVED, no schema change.

Surfaces what already exists: pending reminders due within a window, plus
high/medium insights. Read-only; unread state is tracked client-side via a
last-seen timestamp. RULE 4: everything filters by current_user.id.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Insight, Reminder, User

router = APIRouter(prefix="/notifications", tags=["notifications"])

_DUE_WINDOW_DAYS = 14


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc)
    items: list[dict] = []

    # --- Reminders due within the window, still pending ---
    reminders = (
        db.query(Reminder)
        .filter(
            Reminder.user_id == current_user.id,  # RULE 4
            Reminder.status == "pending",
            Reminder.due_date.isnot(None),
        )
        .order_by(Reminder.due_date.asc())
        .all()
    )
    for r in reminders:
        due = r.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days = (due - now).days
        if days > _DUE_WINDOW_DAYS:
            continue
        if days < 0:
            label = f"{r.title} was due {abs(days)} day(s) ago"
            severity = "high"
        elif days == 0:
            label = f"{r.title} is due today"
            severity = "high"
        else:
            label = f"{r.title} is due in {days} day(s)"
            severity = "high" if days <= 7 else "medium"
        items.append({
            "id": f"reminder:{r.id}",
            "kind": "reminder",
            "title": r.title,
            "message": label,
            "severity": severity,
            "link": "/reminders",
            "created_at": (r.created_at.isoformat() if r.created_at else now.isoformat()),
            "sort_ts": due.isoformat(),
        })

    # --- Insights (high/medium) ---
    insights = (
        db.query(Insight)
        .filter(
            Insight.user_id == current_user.id,  # RULE 4
            Insight.severity.in_(["high", "medium"]),
        )
        .order_by(Insight.created_at.desc())
        .all()
    )
    for ins in insights:
        items.append({
            "id": f"insight:{ins.id}",
            "kind": "insight",
            "title": ins.type.replace("_", " ").title(),
            "message": ins.description or "",
            "severity": ins.severity,
            "link": "/insights",
            "created_at": (ins.created_at.isoformat() if ins.created_at else now.isoformat()),
            "sort_ts": (ins.created_at.isoformat() if ins.created_at else now.isoformat()),
        })

    # High first, then by soonest/most-recent.
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: (sev_rank.get(x["severity"], 3), x["sort_ts"]))

    return {"items": items, "count": len(items)}
