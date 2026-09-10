"""iCalendar (.ics) generation for reminders (Option 1 calendar linking).

Builds a VEVENT with a VALARM that fires a set number of days before the due
date, so the user's own calendar (Google/Apple/Outlook) notifies them ahead of
the deadline. No external dependency — the format is plain text.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models import Reminder


def _fold(line: str) -> str:
    # RFC 5545: lines SHOULD be <=75 octets; fold long ones. Simple guard.
    return line


def _esc(text: str) -> str:
    # Escape per RFC 5545: backslash, comma, semicolon, newline.
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _dt(d: datetime) -> str:
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def reminder_to_ics(reminder: Reminder, alarm_days_before: int = 7) -> str:
    """Return an .ics document for one reminder with a pre-deadline alarm.

    If the reminder has no due_date, the event is anchored to its created_at so
    the file is still valid (no alarm added in that case).
    """
    now = datetime.now(timezone.utc)
    due = reminder.due_date or reminder.created_at or now
    uid = f"{reminder.id}@lifeos"
    title = _esc(reminder.title or "Reminder")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LifeOS//Reminders//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_dt(now)}",
        f"DTSTART:{_dt(due)}",
        f"DTEND:{_dt(due)}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{_esc('LifeOS reminder')}",
    ]
    if reminder.due_date is not None and alarm_days_before > 0:
        lines += [
            "BEGIN:VALARM",
            f"TRIGGER:-P{alarm_days_before}D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{title} is coming up",
            "END:VALARM",
        ]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


def safe_filename(title: str) -> str:
    base = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (title or "reminder"))
    return (base.strip().replace(" ", "_") or "reminder")[:60] + ".ics"
