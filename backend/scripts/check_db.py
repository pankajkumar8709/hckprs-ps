"""Standalone DB connection check (Section 0 definition of done).

Run from backend/ after filling in .env:
    python scripts/check_db.py

Prints the Postgres version, whether the `vector` extension is present, and
lists the created tables. Exit code 0 = healthy.
"""
from __future__ import annotations

import sys

from sqlalchemy import text

# Allow running as `python scripts/check_db.py` from backend/.
sys.path.insert(0, ".")

from app.database import engine  # noqa: E402


def main() -> int:
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar_one()
            has_vector = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")
            ).scalar_one()
            tables = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' ORDER BY table_name"
                )
            ).scalars().all()
    except Exception as exc:  # noqa: BLE001
        print(f"DB CONNECTION FAILED: {exc}")
        return 1

    print("DB connection OK")
    print(f"  {version}")
    print(f"  vector extension enabled: {has_vector}")
    print(f"  public tables ({len(tables)}): {', '.join(tables) or '(none — run alembic upgrade head)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
