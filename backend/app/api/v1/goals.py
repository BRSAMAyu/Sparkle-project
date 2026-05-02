"""Goal creation API."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.goal_decomposition_service import goal_decomposition_service

router = APIRouter()


class GoalMilestonePayload(BaseModel):
    id: str | None = None
    title: str
    description: str = ""
    estimated_days: int = Field(default=14, ge=1)
    acceptance_criteria: list[str] = Field(default_factory=list)


class GoalDecomposePreviewRequest(BaseModel):
    goal_type: str
    title: str = Field(min_length=1, max_length=255)
    motivation: str = ""
    time_horizon: str = "medium"
    target_date: date | None = None


class GoalDecomposePreviewResponse(BaseModel):
    goal_type: str
    time_horizon: str
    suggested_target_date: date
    rationale: str
    milestones: list[GoalMilestonePayload]


class GoalCreateRequest(BaseModel):
    goal_type: str
    title: str = Field(min_length=1, max_length=255)
    motivation: str = ""
    time_horizon: str = "medium"
    description: str | None = None
    target_date: date | None = None
    milestones: list[GoalMilestonePayload] = Field(default_factory=list)


class GoalResponse(BaseModel):
    id: str
    title: str
    goal_type: str
    description: str | None = None
    status: str
    target_date: date | None = None
    metadata: dict[str, Any] | None = None
    minimum_acceptance_criteria: list[dict[str, Any]] | None = None


# route-tier: authed
@router.post("/decompose-preview", response_model=GoalDecomposePreviewResponse)
async def decompose_goal_preview(
    payload: GoalDecomposePreviewRequest,
    current_user: User = Depends(get_current_user),
) -> GoalDecomposePreviewResponse:
    del current_user
    preview = goal_decomposition_service.preview(
        title=payload.title,
        goal_type=payload.goal_type,
        motivation=payload.motivation,
        time_horizon=payload.time_horizon,
        target_date=payload.target_date,
    )
    return GoalDecomposePreviewResponse(**preview.to_dict())


# route-tier: authed
@router.post("", response_model=GoalResponse)
# route-tier: authed
@router.post("/", response_model=GoalResponse)
async def create_goal(
    payload: GoalCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    milestones = [milestone.model_dump() for milestone in payload.milestones]
    if not milestones:
        preview = goal_decomposition_service.preview(
            title=payload.title,
            goal_type=payload.goal_type,
            motivation=payload.motivation,
            time_horizon=payload.time_horizon,
            target_date=payload.target_date,
        )
        milestones = [milestone.to_dict() for milestone in preview.milestones]

    goal = await goal_decomposition_service.create_goal(
        db,
        user_id=current_user.id,
        title=payload.title,
        goal_type=payload.goal_type,
        motivation=payload.motivation,
        time_horizon=payload.time_horizon,
        description=payload.description,
        target_date=payload.target_date,
        milestones=milestones,
    )
    await db.commit()
    await db.refresh(goal)
    return GoalResponse(
        id=str(goal.id),
        title=goal.title,
        goal_type=goal.goal_type,
        description=goal.description,
        status=goal.status,
        target_date=goal.target_date,
        metadata=goal.metadata_payload,
        minimum_acceptance_criteria=goal.minimum_acceptance_criteria,
    )
