"""F2.7 — Insights endpoint. GET /insights sorted by severity. RULE 4 scoped."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Insight, User
from app.schemas import InsightResponse
from app.services.insights import regenerate_insights

router = APIRouter(prefix="/insights", tags=["insights"])

_SEVERITY_ORDER = case(
    {"high": 0, "medium": 1, "low": 2}, value=Insight.severity, else_=3
)


@router.get("", response_model=list[InsightResponse])
def list_insights(
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Insight]:
    if refresh:
        regenerate_insights(db, current_user.id)
    return (
        db.query(Insight)
        .filter(Insight.user_id == current_user.id)  # RULE 4
        .order_by(_SEVERITY_ORDER, Insight.created_at.desc())
        .all()
    )
