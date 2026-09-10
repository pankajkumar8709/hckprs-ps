"""FastAPI application entrypoint.

Section 0 shipped /health. Phase 1 MVP adds auth, documents (upload -> pypdf text
extraction -> single-shot Gemini extraction -> Q&A) and chat routers, per the 0.4
API contract. Phase 2 (F2.1+) builds on top of these.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import auth, chat, documents

app = FastAPI(title="LifeOS Agent API", version="0.2.0")

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)

# Web UI (Phase 1) — single-file React app served at /. Kept out of /docs' way.
_WEB_INDEX = Path(__file__).resolve().parents[2] / "web" / "index.html"


@app.get("/", include_in_schema=False)
def web_ui() -> FileResponse:
    return FileResponse(_WEB_INDEX)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Report service + DB reachability. DB unreachable => status 'unhealthy'."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "db": "reachable" if db_ok else "unreachable",
    }
