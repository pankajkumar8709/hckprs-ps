"""F3.9 — async processing checklist.

- A job that fails is RETRIED with backoff, then DEAD-LETTERED after max_attempts
  (simulating a worker dying / erroring mid-job — the job is never lost silently).
- Multiple queued jobs all drain (5 uploads process without blocking).

Run: cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_jobs.py -v -s
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import FailedJob, Job, User
from app.security import hash_password
from app.services import jobs as jobsvc


def _user(db) -> uuid.UUID:
    u = User(email=f"job_{uuid.uuid4().hex[:8]}@t.com", password_hash=hash_password("x"*8))
    db.add(u); db.commit(); db.refresh(u)
    return u.id


def test_failure_retries_then_dead_letters(monkeypatch):
    db = SessionLocal()
    uid = _user(db)
    job = Job(user_id=uid, document_id=None, job_type="ingest",
              status="queued", attempts=0, max_attempts=3,
              next_run_at=datetime.now(timezone.utc))
    db.add(job); db.commit(); db.refresh(job)
    job_id = job.id
    db.close()

    # Force the work to always fail (simulates a crashing/killed job).
    def boom(_db, _job):
        raise RuntimeError("simulated worker failure mid-job")
    monkeypatch.setattr(jobsvc, "_run_ingest", boom)

    # Make backoff instant so the test doesn't wait.
    monkeypatch.setattr(jobsvc, "_backoff_seconds", lambda a: 0)

    outcomes = []
    for _ in range(5):
        d = SessionLocal()
        try:
            outcomes.append(jobsvc.process_one(d, "test-worker"))
        finally:
            d.close()
    print("outcomes:", outcomes)

    # Expect: retry, retry, failed (3 attempts = max), then idle (None).
    assert outcomes[:3] == ["retry", "retry", "failed"], outcomes
    assert outcomes[3] is None  # dead-lettered, no longer queued

    d = SessionLocal()
    j = d.query(Job).filter(Job.id == job_id).first()
    dead = d.query(FailedJob).filter(FailedJob.document_id.is_(None),
                                     FailedJob.user_id == uid).count()
    d.close()
    assert j.status == "failed", f"job status {j.status}"
    assert j.attempts == 3
    assert dead >= 1, "job not dead-lettered into failed_jobs"


def test_five_jobs_all_drain(monkeypatch):
    db = SessionLocal()
    uid = _user(db)
    for _ in range(5):
        db.add(Job(user_id=uid, document_id=None, job_type="ingest",
                   status="queued", attempts=0, max_attempts=3,
                   next_run_at=datetime.now(timezone.utc)))
    db.commit(); db.close()

    # Make each job succeed instantly (no real doc needed).
    monkeypatch.setattr(jobsvc, "_run_ingest", lambda _db, _job: None)

    counts = jobsvc.run_worker(max_idle_polls=2, poll_sleep=0.01, worker_id="drain")
    print("drain counts:", counts)
    assert counts["done"] >= 5, f"not all jobs drained: {counts}"
