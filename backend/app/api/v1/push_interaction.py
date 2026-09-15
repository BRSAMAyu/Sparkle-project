"""
Push interaction API - record push open/dismiss/ignore events.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.core.metrics import record_product_loop_event
from app.db.session import get_db
from app.models.user import User
from app.services.push_feedback_service import PushFeedbackService

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PushInteractionPayload(BaseModel):
    push_id: UUID
    action: str
    timestamp: datetime | None = None


@router.post("/push/interaction", summary="记录推送交互")
async def record_push_interaction(
    payload: PushInteractionPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    action = payload.action.strip().lower()
    if action not in {"opened", "dismissed", "ignored", "wrong", "not_useful", "too_much", "bad_timing"}:
        record_product_loop_event("push_judgment", "push_interaction", "invalid", "bad_action")
        raise HTTPException(status_code=400, detail="Invalid action")

    service = PushFeedbackService(db, cache_service.redis)
    await service.process_interaction(
        user_id=current_user.id,
        push_id=payload.push_id,
        action=action,
        timestamp=payload.timestamp or _utcnow(),
    )
    reason = (
        "positive"
        if action == "opened"
        else "negative"
        if action in {"dismissed", "ignored", "wrong", "not_useful", "too_much", "bad_timing"}
        else "neutral"
    )
    record_product_loop_event("push_judgment", "push_interaction", action, reason)
    return {"success": True}
