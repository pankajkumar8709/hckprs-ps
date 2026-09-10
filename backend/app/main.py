"""FastAPI application entrypoint (Section 0).

Only /health exists at Section 0. Feature routers are added per the build order
starting at F2.1. /health checks DB reachability — the connection proof for
Section 0's definition of done, and the basis for F3.10 observability.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

app = FastAPI(title="LifeOS Agent API", version="0.1.0")


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
