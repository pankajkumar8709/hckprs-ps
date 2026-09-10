# Architecture

> Section 0 stub. Full component diagram + description lands in F3.11.

## Components (as of Section 0)
- **backend/** — FastAPI (Python 3.11+), SQLAlchemy 2.0 ORM, Alembic migrations.
- **Primary DB** — PostgreSQL on Supabase (free tier), `vector` extension enabled for pgvector (F2.4).
- **android/** — Kotlin + Jetpack Compose client (built from F2.1 onward).
- **web/** — optional Next.js dashboard, built LAST only if time remains.

## Data model
See `Project-plan.md` Section 0.3 and `backend/app/models.py`. Every user-data table carries
`id (UUID)`, `user_id (UUID, FK, indexed, NOT NULL)`, `created_at`, `updated_at`, and **every query
against user data filters by `user_id`** (Section 0.2).
