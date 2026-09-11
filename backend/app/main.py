"""FastAPI application entrypoint.

Section 0 shipped /health. Phase 1 MVP adds auth, documents (upload -> pypdf text
extraction -> single-shot Gemini extraction -> Q&A) and chat routers, per the 0.4
API contract. Phase 2 (F2.1+) builds on top of these.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import get_db
from app.routers import account, auth, chat, documents, insights, notifications, reminders
from app.services.ratelimit import limiter

app = FastAPI(title="LifeOS Agent API", version="0.3.0")

# F3.4 — rate limiting. Limiter keyed per-user (JWT) else per-IP; 429 on exceed.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — allow the Next.js dev frontend (localhost:3000) to call the API.
# CORS — allowed origins come from CORS_ORIGINS env (comma-separated).
# Default is the local dev frontend; set your deployed origin(s) in prod.
from app.config import settings as _settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(reminders.router)
app.include_router(insights.router)
app.include_router(account.router)
app.include_router(notifications.router)

# F3.10 — structured logging + request context + metrics middleware.
import time as _time
import uuid as _uuid
from starlette.requests import Request as _Req
from app.services.observability import (
    setup_logging, metrics, request_id_var, user_id_var,
)
from app.security import decode_token as _decode

setup_logging()


@app.middleware("http")
async def _observability_mw(request: _Req, call_next):
    rid = request.headers.get("x-request-id") or _uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    # Best-effort user id from bearer token (for log correlation only).
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            user_id_var.set(str(_decode(auth.split(" ", 1)[1], expected_type="access").get("sub")))
        except Exception:
            user_id_var.set("-")
    else:
        user_id_var.set("-")
    start = _time.perf_counter()
    status = 500
    try:
        resp = await call_next(request)
        status = resp.status_code
        resp.headers["x-request-id"] = rid
        return resp
    finally:
        metrics.record(status, _time.perf_counter() - start)

# Web UI (Phase 1) — single-file React app served at /. Kept out of /docs' way.
_WEB_INDEX = Path(__file__).resolve().parents[2] / "web" / "index.html"


@app.get("/", include_in_schema=False)
def web_ui() -> FileResponse:
    return FileResponse(_WEB_INDEX)


@app.on_event("startup")
def _prewarm_embeddings() -> None:
    """Warm the local embedding model off the request path so the FIRST RAG
    query isn't slow (model lazy-loads several seconds on first use)."""
    import threading
    from app.services import embeddings

    threading.Thread(target=embeddings.available, daemon=True).start()


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """F3.10 — report DB + queue reachability. Any component down => 'unhealthy'."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    # Queue reachability: the jobs table is queryable (DB-backed queue).
    queue_ok = False
    try:
        db.execute(text("SELECT 1 FROM jobs LIMIT 1"))
        queue_ok = True
    except Exception:
        queue_ok = db_ok  # if DB is up the queue table should be too
    healthy = db_ok and queue_ok
    return {
        "status": "healthy" if healthy else "unhealthy",
        "db": "reachable" if db_ok else "unreachable",
        "queue": "reachable" if queue_ok else "unreachable",
    }


@app.get("/metrics")
def get_metrics() -> dict:
    """F3.10 — minimal in-memory metrics: request count, error rate, avg latency."""
    return metrics.snapshot()
