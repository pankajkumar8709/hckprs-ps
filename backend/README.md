# backend/ — LifeOS Agent API

FastAPI (Python 3.11+) + SQLAlchemy 2.0 + Alembic, PostgreSQL on Supabase (pgvector).

## Section 0 setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env          # Windows  (cp on *nix)
# Fill DATABASE_URL (Supabase -> Database -> Connection string -> "Session pooler")
# and JWT_SECRET.

# Enable pgvector on the Supabase project once (SQL editor):  CREATE EXTENSION vector;
# (the migration also runs CREATE EXTENSION IF NOT EXISTS vector)

alembic upgrade head            # creates all 9 tables
python scripts/check_db.py      # proves connection + lists tables
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# GET http://127.0.0.1:8000/health  -> {"status":"healthy","db":"reachable"}
```

## Layout
```
backend/
  app/
    __init__.py
    config.py       # .env settings (0.5)
    database.py     # engine + session + Base
    models.py       # core data model (0.3) — LOCKED
    main.py         # FastAPI app + /health
  migrations/       # Alembic (0001_initial creates the schema)
  scripts/check_db.py
  requirements.txt
  alembic.ini
  .env.example
```

Feature routers are added per the build order (F2.1 → …). Section 0 ships only `/health`.
