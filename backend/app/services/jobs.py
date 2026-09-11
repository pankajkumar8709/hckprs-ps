"""F3.9 — async job queue + worker (DB-backed, no external broker needed).

Moves the heavy document pipeline (OCR -> extraction -> reminders -> insights ->
embedding) off the request thread. A worker claims queued jobs atomically,
processes them, retries with exponential backoff on failure, and dead-letters a
job (row in failed_jobs) once it exhausts max_attempts — so a failure is
recorded and inspectable, never lost silently.

Swap to Celery+Redis in prod by pointing enqueue at a Celery task; the job
lifecycle (retry/backoff/dead-letter) and the failed_jobs view stay identical.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Document, ExtractedField, FailedJob, Job


def enqueue_ingest(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> Job:
    job = Job(user_id=user_id, document_id=document_id, job_type="ingest",
              status="queued", attempts=0, max_attempts=3)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _backoff_seconds(attempts: int) -> int:
    return min(60, 2 ** attempts)  # 2s, 4s, 8s ... capped


def claim_next_job(db: Session, worker_id: str) -> Job | None:
    """Atomically claim one due queued job (row-level lock, skip locked) so
    multiple workers never grab the same job."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(Job)
        .filter(Job.status == "queued", Job.next_run_at <= now)
        .order_by(Job.next_run_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if row is None:
        return None
    row.status = "running"
    row.locked_by = worker_id
    row.attempts += 1
    db.commit()
    db.refresh(row)
    return row


def _run_ingest(db: Session, job: Job) -> None:
    """The actual heavy work — mirrors the synchronous upload pipeline."""
    from app.services import llm, rag
    from app.services.reminders import create_reminders_for_document
    from app.services.insights import regenerate_insights

    doc = db.query(Document).filter(Document.id == job.document_id).first()
    if doc is None:
        return  # document deleted; nothing to do
    ocr_text = doc.ocr_text or ""
    result = llm.ingest_document(ocr_text)
    doc.doc_type = result["doc_type"]
    doc.agent_trace_json = {"steps": result["agent_trace"]}
    # Clear any prior fields (idempotent re-run).
    db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).delete()
    for f in result["fields"]:
        db.add(ExtractedField(document_id=doc.id, user_id=job.user_id,
                              field_name=f["field_name"], field_value=f.get("field_value"),
                              field_type=f["field_type"], confidence=f.get("confidence")))
    doc.upload_status = result["status"]
    db.commit()
    create_reminders_for_document(db, job.user_id, doc.id)
    regenerate_insights(db, job.user_id)
    try:
        rag.index_document(db, job.user_id, doc.id, ocr_text)
    except Exception:
        db.rollback()


def process_one(db: Session, worker_id: str = "worker-1") -> str | None:
    """Claim + process a single job. Returns the job status, or None if idle.
    On failure: retry-with-backoff until max_attempts, then dead-letter."""
    job = claim_next_job(db, worker_id)
    if job is None:
        return None
    try:
        _run_ingest(db, job)
        job.status = "done"
        job.last_error = None
        db.commit()
        return "done"
    except Exception as exc:  # retry or dead-letter
        db.rollback()
        job = db.query(Job).filter(Job.id == job.id).first()
        job.last_error = str(exc)[:2000]
        if job.attempts >= job.max_attempts:
            # Dead-letter.
            db.add(FailedJob(user_id=job.user_id, document_id=job.document_id,
                             job_type=job.job_type, attempts=job.attempts,
                             error=str(exc)[:2000]))
            job.status = "failed"
            db.commit()
            return "failed"
        # Retry with backoff.
        job.status = "queued"
        job.locked_by = None
        job.next_run_at = datetime.now(timezone.utc) + timedelta(
            seconds=_backoff_seconds(job.attempts))
        db.commit()
        return "retry"


def run_worker(max_idle_polls: int = 3, poll_sleep: float = 0.5, worker_id: str = "worker-1") -> dict:
    """Drain the queue: process jobs until idle for max_idle_polls in a row.
    Returns counts. Used by the standalone worker process and tests."""
    import time
    counts = {"done": 0, "failed": 0, "retry": 0}
    idle = 0
    while idle < max_idle_polls:
        db = SessionLocal()
        try:
            outcome = process_one(db, worker_id)
        finally:
            db.close()
        if outcome is None:
            idle += 1
            time.sleep(poll_sleep)
        else:
            idle = 0
            counts[outcome] = counts.get(outcome, 0) + 1
    return counts
