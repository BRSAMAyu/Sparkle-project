"""Community strategy outcome recording API — COM-012 / GAP-P4-11."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.community_strategy_service import CommunityStrategyService

router = APIRouter(prefix="/community/strategy-outcomes", tags=["community-strategy-outcomes"])


class RecordOutcomeRequest(BaseModel):
    directive_id: str = Field(..., min_length=1, max_length=128)
    trigger_type: str = Field(..., description="cohort_mistake, partner_feedback, resource_recommendation, accountability_checkin")
    decision: str = Field(..., description="accepted, rejected, dismissed, modified, auto_expired")
    context_snapshot: dict | None = None
    user_feedback: str | None = Field(None, max_length=2000)
    time_to_decision_seconds: int | None = None
    source: str = Field(default="user_action")


class OutcomeResponse(BaseModel):
    id: str
    user_id: str
    directive_id: str
    trigger_type: str
    decision: str
    context_snapshot: dict | None = None
    user_feedback: str | None = None
    time_to_decision_seconds: int | None = None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=OutcomeResponse, status_code=201)
async def record_community_strategy_outcome(
    body: RecordOutcomeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutcomeResponse:
    """Record a user's decision on a community-derived strategy recommendation."""
    service = CommunityStrategyService(db)
    outcome = await service.record_outcome(
        user_id=str(current_user.id),
        directive_id=body.directive_id,
        trigger_type=body.trigger_type,
        decision=body.decision,
        context_snapshot=body.context_snapshot,
        user_feedback=body.user_feedback,
        time_to_decision_seconds=body.time_to_decision_seconds,
        source=body.source,
    )
    return OutcomeResponse(
        id=str(outcome.id),
        user_id=str(outcome.user_id),
        directive_id=outcome.directive_id,
        trigger_type=outcome.trigger_type,
        decision=outcome.decision,
        context_snapshot=outcome.context_snapshot,
        user_feedback=outcome.user_feedback,
        time_to_decision_seconds=outcome.time_to_decision_seconds,
        source=outcome.source,
        created_at=outcome.created_at,
    )


@router.get("", response_model=list[OutcomeResponse])
async def list_community_strategy_outcomes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trigger_type: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[OutcomeResponse]:
    """List community strategy outcomes for the current user."""
    service = CommunityStrategyService(db)
    outcomes = await service.list_outcomes(
        user_id=str(current_user.id),
        trigger_type=trigger_type,
        decision=decision,
        limit=limit,
        offset=offset,
    )
    return [
        OutcomeResponse(
            id=str(o.id),
            user_id=str(o.user_id),
            directive_id=o.directive_id,
            trigger_type=o.trigger_type,
            decision=o.decision,
            context_snapshot=o.context_snapshot,
            user_feedback=o.user_feedback,
            time_to_decision_seconds=o.time_to_decision_seconds,
            source=o.source,
            created_at=o.created_at,
        )
        for o in outcomes
    ]


@router.get("/{directive_id}", response_model=OutcomeResponse)
async def get_community_strategy_outcome(
    directive_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutcomeResponse:
    """Get a specific community strategy outcome by directive ID."""
    service = CommunityStrategyService(db)
    outcome = await service.get_by_directive(user_id=str(current_user.id), directive_id=directive_id)
    if outcome is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Outcome not found")
    return OutcomeResponse(
        id=str(outcome.id),
        user_id=str(outcome.user_id),
        directive_id=outcome.directive_id,
        trigger_type=outcome.trigger_type,
        decision=outcome.decision,
        context_snapshot=outcome.context_snapshot,
        user_feedback=outcome.user_feedback,
        time_to_decision_seconds=outcome.time_to_decision_seconds,
        source=outcome.source,
        created_at=outcome.created_at,
    )
