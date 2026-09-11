# LifeOS Agent — Architecture

## Overview
LifeOS is a personal AI document-management platform. A user uploads documents;
the system extracts structured information, tracks deadlines, and answers
questions grounded only in that user's own documents. Every layer enforces
per-user isolation.

## Components

```
                         ┌────────────────────────┐
   Browser (Next.js) ───▶│  FastAPI API (uvicorn) │
   web/ (App Router,     │  app/main.py            │
   Tailwind, TS)         │                         │
                         │  Middleware:            │
                         │   - CORS (locked origins)│
                         │   - Rate limit (slowapi) │
                         │   - Observability (JSON  │
                         │     logs, request_id,    │
                         │     metrics)             │
                         └───────────┬─────────────┘
                                     │
          ┌──────────────────────────┼───────────────────────────┐
          ▼                          ▼                           ▼
   Auth (JWT/bcrypt)        Routers (documents, chat,     LLM service (Groq,
   deps.get_current_user    reminders, insights, share,   openai/gpt-oss-120b)
   scoped_to_user (F3.2)    account, notifications)       + local embeddings
                                     │                    (all-MiniLM-L6-v2)
                                     ▼
                    ┌────────────────────────────────┐
                    │ PostgreSQL (Supabase) + pgvector│
                    │  users, documents,             │
                    │  extracted_fields, reminders,  │
                    │  insights, conversations,      │
                    │  messages, share_grants,       │
                    │  audit_logs, document_chunks,  │
                    │  jobs, failed_jobs             │
                    └────────────────────────────────┘
                                     ▲
                    encrypted files  │  (Fernet at rest)
                    backend/storage/<user>/<uuid>.enc
```

## Tech stack
- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic migrations.
- **DB:** PostgreSQL 17 (Supabase) with the `pgvector` extension (384-dim
  embeddings from `all-MiniLM-L6-v2`, run locally — Groq has no embeddings API).
- **LLM:** Groq (`openai/gpt-oss-120b`), OpenAI-compatible SDK. No CrewAI — the
  "agents" (classification, extraction, validator, router, insight) are plain
  orchestrated Groq calls in `app/services/llm.py`, with a visible
  `agent_trace`.
- **Auth:** JWT (python-jose) + bcrypt (passlib), access + refresh tokens.
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, framer-motion.

## Document pipeline (F2.1/F2.2)
`upload → text extraction (pypdf, OCR fallback) → ClassificationAgent →
ExtractionAgent → ValidatorAgent → persist ExtractedField rows + agent_trace →
auto-create reminders (F2.3) → regenerate cross-document insights (F2.7) →
chunk + embed into pgvector (F2.4)`. The ValidatorAgent verifies every extracted
date/amount appears verbatim in the source text before it is stored.

## Async processing (F3.9)
Heavy pipeline work can run off the request thread via a **DB-backed job queue**
(`jobs` table) drained by a worker (`app/worker.py`): atomic claim
(`FOR UPDATE SKIP LOCKED`), **retry with exponential backoff**, and a
**dead-letter table** (`failed_jobs`) after `max_attempts`. Opt-in via
`ASYNC_INGEST`.

**Production note:** the queue is DB-backed rather than Celery+Redis (Redis was
not available in the build environment; the plan permits RQ/equivalent). The job
lifecycle is identical; migrating to Celery+Redis means pointing `enqueue_ingest`
at a Celery task and running `celery worker` against `REDIS_URL` — the
`failed_jobs` dead-letter and retry semantics carry over unchanged.

## Observability (F3.10)
- Structured **JSON logs** with `request_id` + `user_id` (contextvars, set by an
  HTTP middleware).
- `GET /health` — reports DB **and** queue reachability; returns `unhealthy` if
  either is down.
- `GET /metrics` — in-memory request count, error rate, average latency.

## Scalability approach (not all implemented; design intent)
- **DB indexing:** every user-owned table is indexed on `user_id`; hot queries
  (jobs by `status,next_run_at`; reminders/insights by user) are indexed.
- **Read scaling:** Supabase supports read replicas; read-heavy endpoints
  (document/reminder lists) could be routed to a replica.
- **Queue scaling:** move from the DB-backed queue to Celery+Redis; partition by
  `job_type`; run N workers (the atomic claim already supports concurrent
  workers safely).
- **Rate-limit storage:** slowapi currently uses in-memory storage (per-process);
  a multi-worker deploy needs Redis-backed limits storage (`REDIS_URL` reserved).
- **Metrics:** replace the in-memory counter with a Prometheus exporter.
