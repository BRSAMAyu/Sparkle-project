from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.core.cache import cache_service
from app.learning.prompt_bandit import PromptBandit
from app.services.response_feedback_service import ResponseFeedbackService

router = APIRouter(prefix="/admin", tags=["Admin Feedback"], dependencies=[Depends(get_current_active_superuser)])


def _parse_window(value: str) -> timedelta:
    if not value:
        return timedelta(hours=24)
    value = value.strip().lower()
    try:
        if value.endswith("h"):
            return timedelta(hours=float(value[:-1]))
        if value.endswith("m"):
            return timedelta(minutes=float(value[:-1]))
        if value.endswith("d"):
            return timedelta(days=float(value[:-1]))
        return timedelta(hours=float(value))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid window") from exc


@router.get("/feedback/summary")
async def feedback_summary(
    window: str = Query("24h"),
    db: AsyncSession = Depends(get_db),
):
    service = ResponseFeedbackService(db, redis_client=cache_service.redis)
    summary = await service.get_summary(_parse_window(window))
    return summary


@router.get("/bandit/prompt")
async def bandit_prompt_state(
    workflow_id: str = Query(..., min_length=1),
    arms: str | None = Query(None, description="Comma-separated list of prompt versions"),
):
    arm_list = [a.strip() for a in (arms or "v1,v2").split(",") if a.strip()]
    bandit = PromptBandit(redis_client=cache_service.redis)
    return await bandit.get_debug_state(workflow_id, arm_list)
