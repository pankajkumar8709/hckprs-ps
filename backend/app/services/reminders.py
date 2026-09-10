"""F2.3 — Reminders service. Converts extracted `date` fields into Reminder rows.

Pure service logic, no LLM. Runs after extraction completes. Every row is scoped
to the owning user (Rule 4).
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ExtractedField, Reminder

# Accept a few common date shapes the extractor emits.
_DATE_PATTERNS = [
    ("%Y-%m-%d", r"\b(\d{4}-\d{2}-\d{2})\b"),
    ("%d/%m/%Y", r"\b(\d{2}/\d{2}/\d{4})\b"),
    ("%m/%d/%Y", r"\b(\d{2}/\d{2}/\d{4})\b"),
    ("%d %B %Y", r"\b(\d{1,2} [A-Za-z]+ \d{4})\b"),
    ("%B %d, %Y", r"\b([A-Za-z]+ \d{1,2}, \d{4})\b"),
    ("%B %d %Y", r"\b([A-Za-z]+ \d{1,2} \d{4})\b"),
]


def _parse_due_date(value: str) -> datetime | None:
    if not value:
        return None
    for fmt, pat in _DATE_PATTERNS:
        m = re.search(pat, value)
        if m:
            try:
                return datetime.strptime(m.group(1), fmt)
            except ValueError:
                continue
    return None


def create_reminders_for_document(
    db: Session, user_id: uuid.UUID, document_id: uuid.UUID
) -> list[Reminder]:
    """Create Reminder rows from this document's `date` ExtractedField rows.

    Idempotent-ish: skips date fields that already produced a reminder
    (matched by source_field_id).
    """
    date_fields = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.document_id == document_id,
            ExtractedField.user_id == user_id,  # RULE 4
            ExtractedField.field_type == "date",
        )
        .all()
    )
    existing_src = {
        r.source_field_id
        for r in db.query(Reminder)
        .filter(Reminder.user_id == user_id, Reminder.document_id == document_id)
        .all()
        if r.source_field_id is not None
    }

    created: list[Reminder] = []
    for f in date_fields:
        if f.id in existing_src:
            continue
        due = _parse_due_date(f.field_value or "")
        title = (f.field_name or "Important date").strip().title()
        reminder = Reminder(
            user_id=user_id,
            document_id=document_id,
            title=title,
            due_date=due,
            status="pending",
            source_field_id=f.id,
        )
        db.add(reminder)
        created.append(reminder)
    if created:
        db.commit()
        for r in created:
            db.refresh(r)
    return created
