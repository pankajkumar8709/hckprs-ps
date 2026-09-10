"""F2.9 — Premium plan stub. GET /account/plan, POST /account/upgrade."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import PlanResponse

router = APIRouter(prefix="/account", tags=["account"])

_FREE_TIER_DOC_LIMIT = 10


def _plan(user: User) -> PlanResponse:
    return PlanResponse(
        plan_tier=user.plan_tier,
        document_limit=None if user.plan_tier == "premium" else _FREE_TIER_DOC_LIMIT,
    )


@router.get("/plan", response_model=PlanResponse)
def get_plan(current_user: User = Depends(get_current_user)) -> PlanResponse:
    return _plan(current_user)


@router.post("/upgrade", response_model=PlanResponse)
def upgrade(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlanResponse:
    current_user.plan_tier = "premium"
    db.commit()
    db.refresh(current_user)
    return _plan(current_user)
