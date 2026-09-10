"""F2.7 — Cross-document Insights engine (the differentiator). No LLM.

Scans a user's PENDING reminders and generates Insight rows:
- date_clash:   2+ due dates within a 7-day window (across any documents).
- renewal_risk: a reminder due within 14 days (from now) still pending.

Regenerated on demand: existing insights for the user are cleared and rebuilt so
the list always reflects current reminder state (an insight disappears once its
clashing reminders are resolved). Scoped to the user (Rule 4).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Insight, Reminder

_CLASH_WINDOW_DAYS = 7
_RENEWAL_WINDOW_DAYS = 14


def regenerate_insights(db: Session, user_id: uuid.UUID) -> list[Insight]:
    # Clear old insights for this user (Rule 4) — we rebuild from current state.
    db.query(Insight).filter(Insight.user_id == user_id).delete()
    db.commit()

    reminders = (
        db.query(Reminder)
        .filter(
            Reminder.user_id == user_id,  # RULE 4
            Reminder.status == "pending",
            Reminder.due_date.isnot(None),
        )
        .order_by(Reminder.due_date.asc())
        .all()
    )

    insights: list[Insight] = []
    now = datetime.now(timezone.utc)

    # --- date_clash: any pair within 7 days ---
    for i in range(len(reminders)):
        for j in range(i + 1, len(reminders)):
            a, b = reminders[i], reminders[j]
            delta = abs((b.due_date - a.due_date).days)
            if delta <= _CLASH_WINDOW_DAYS:
                insights.append(
                    Insight(
                        user_id=user_id,
                        type="date_clash",
                        description=(
                            f"'{a.title}' ({a.due_date.date()}) and "
                            f"'{b.title}' ({b.due_date.date()}) fall within "
                            f"{delta} day(s) of each other."
                        ),
                        related_reminder_ids=[a.id, b.id],
                        severity="high" if delta <= 3 else "medium",
                    )
                )
            else:
                break  # sorted; no later reminder can be within window of a

    # --- renewal_risk: due within 14 days from now ---
    for r in reminders:
        due = r.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days_out = (due - now).days
        if 0 <= days_out <= _RENEWAL_WINDOW_DAYS:
            insights.append(
                Insight(
                    user_id=user_id,
                    type="renewal_risk",
                    description=(
                        f"'{r.title}' is due on {due.date()} "
                        f"({days_out} day(s) away) and is still pending."
                    ),
                    related_reminder_ids=[r.id],
                    severity="high" if days_out <= 7 else "medium",
                )
            )

    for ins in insights:
        db.add(ins)
    if insights:
        db.commit()
        for ins in insights:
            db.refresh(ins)
    return insights
