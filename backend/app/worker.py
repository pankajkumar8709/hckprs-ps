"""F3.9 — standalone async worker process.

Run alongside the API to process the document pipeline off the request thread:
  cd backend && .venv\\Scripts\\python.exe -m app.worker

Loops forever, claiming and processing jobs with retry/backoff/dead-letter.
Kill it (Ctrl+C) mid-job: the claimed job's attempt is recorded, and on the next
run it is retried (or dead-lettered once attempts hit max) — never lost.
"""
from __future__ import annotations

import time

from app.database import SessionLocal
from app.services.jobs import process_one


def main() -> None:
    print("[worker] started; polling for jobs…")
    while True:
        db = SessionLocal()
        try:
            outcome = process_one(db, worker_id="worker-main")
        except Exception as exc:  # never let the loop die
            outcome = None
            print(f"[worker] loop error: {exc}")
        finally:
            db.close()
        if outcome is None:
            time.sleep(1.0)
        else:
            print(f"[worker] job -> {outcome}")


if __name__ == "__main__":
    main()
