"""Goal creation API."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.schemas.task import TaskCreate, coerce_task_type
from app.services.goal_decomposition_service import goal_decomposition_service
from app.services.task_service import TaskService
from app.signals.multi_goal_arbitration import MultiGoalArbitrator

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
    first_task_id: str | None = None
    warning: str | None = None


# route-tier: authed
@router.get("", response_model=list[GoalResponse])
@router.get("/", response_model=list[GoalResponse])
async def list_goals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GoalResponse]:
    from app.models.goal import Goal
    stmt = select(Goal).where(Goal.user_id == current_user.id, Goal.deleted_at.is_(None)).order_by(Goal.created_at.desc())
    result = await db.execute(stmt)
    goals = result.scalars().all()
    return [
        GoalResponse(
            id=str(g.id),
            title=g.title,
            goal_type=g.goal_type,
            description=g.description,
            status=g.status,
            target_date=g.target_date,
            metadata=g.metadata_payload,
            minimum_acceptance_criteria=g.minimum_acceptance_criteria,
        )
        for g in goals
    ]


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
    # Soft warning: check for active goals with the same title for this user.
    from app.models.goal import Goal as GoalModel
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    warning: str | None = None
    try:
        dup_stmt = select(GoalModel).where(
            GoalModel.user_id == current_user.id,
            GoalModel.title == payload.title.strip(),
            GoalModel.status == "active",
            GoalModel.deleted_at.is_(None),
        )
        dup_result = await db.execute(dup_stmt)
        if dup_result.scalars().first() is not None:
            warning = "duplicate_title"
            _logger.info(
                "Duplicate goal title warning for user=%s title=%r",
                current_user.id, payload.title,
            )
    except Exception:
        pass  # non-critical; never block creation

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
    await db.flush()
    await db.refresh(goal)

    # Auto-assign matching scenario pack based on goal_type.
    from app.signals.goal_type_adapter import _normalize_goal_type
    normalized_type = _normalize_goal_type(payload.goal_type)
    _auto_assign_scenario_pack(goal, normalized_type, str(current_user.id))

    # Plan B: create the first task from the first milestone so the wizard
    # can navigate directly to /tasks/{id}/execute after creation.
    first_task_id: str | None = None
    if milestones:
        first = milestones[0]
        try:
            task = await TaskService.create(
                db,
                TaskCreate(
                    title=first.get("title", f"{payload.title} — 第一步"),
                    type=coerce_task_type("learning"),
                    estimated_minutes=25,
                    energy_cost=2,
                    tags=["goal_first_step"],
                    guide_content=first.get("description"),
                ),
                user_id=current_user.id,
            )
            await db.flush()
            await db.refresh(task)
            first_task_id = str(task.id)
        except Exception:
            first_task_id = None

    await db.commit()
    return GoalResponse(
        id=str(goal.id),
        title=goal.title,
        goal_type=goal.goal_type,
        description=goal.description,
        status=goal.status,
        target_date=goal.target_date,
        metadata=goal.metadata_payload,
        minimum_acceptance_criteria=goal.minimum_acceptance_criteria,
        first_task_id=first_task_id,
        warning=warning,
    )


# ── Multi-Goal Arbitration ────────────────────────────────────────────────────


class GoalArbitrationResponse(BaseModel):
    primary_goal_id: str
    reason: str
    priority_scores: dict[str, float]
    suggested_time_split: dict[str, float]
    conflicts: list[str]
    active_goal_count: int


# route-tier: authed
@router.get("/arbitrate", response_model=GoalArbitrationResponse)
async def arbitrate_goals(
    current_user: User = Depends(get_current_user),
) -> GoalArbitrationResponse:
    """Return the current multi-goal arbitration result.

    Reads active goals from the spine Redis store and runs the
    MultiGoalArbitrator to produce a recommended primary goal, time
    split, and any detected conflicts.
    """
    arbitrator = MultiGoalArbitrator(cache_service.redis)
    goals = await arbitrator.get_active_goals(str(current_user.id))
    result = arbitrator.arbitrate(goals)

    if result is None:
        return GoalArbitrationResponse(
            primary_goal_id="",
            reason="no_active_goals",
            priority_scores={},
            suggested_time_split={},
            conflicts=[],
            active_goal_count=0,
        )

    return GoalArbitrationResponse(
        primary_goal_id=result.primary_goal_id,
        reason=result.reason,
        priority_scores=result.priority_scores,
        suggested_time_split=result.suggested_time_split,
        conflicts=result.conflicts,
        active_goal_count=len(goals),
    )


# ── Scenario Pack Auto-Assignment ─────────────────────────────────────────

_GOAL_TYPE_PACK_MAP: dict[str, str] = {
    "exam": "exam_prep_14d@v1.0",
    "project": "project_sprint_7d@v1.0",
    "job_search": "job_search_14d@v1.0",
    "fitness": "fitness_foundation_14d@v1.0",
    "startup": "career_pivot_30d@v1.0",
}


def _auto_assign_scenario_pack(goal: Any, goal_type: str, user_id: str) -> None:
    """Assign the best matching scenario pack to a newly created goal."""
    pack_id = _GOAL_TYPE_PACK_MAP.get(goal_type)
    if pack_id is None:
        return
    goal.domain_pack_id = pack_id
    goal.source_metadata = {
        **(goal.source_metadata or {}),
        "scenario_pack_auto_assigned": True,
        "scenario_pack_assigned_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write initial journey state to Redis.
    try:
        from app.scenario_packs.registry import load_default_registry
        registry = load_default_registry()
        manifest = registry.get_by_id(pack_id)
        if manifest is not None:
            first_node = manifest.backbone_nodes[0].node_id if manifest.backbone_nodes else ""
            state_key = f"spine:scenario_journey:{user_id}:{goal.id}"
            import asyncio
            asyncio.ensure_future(cache_service.redis.set(
                state_key,
                json.dumps({
                    "pack_id": pack_id,
                    "current_node": first_node,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "is_on_backbone": True,
                }),
                ex=90 * 24 * 3600,
            ))
    except Exception:
        pass
