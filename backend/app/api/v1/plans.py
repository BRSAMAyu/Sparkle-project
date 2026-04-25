"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Plans API Endpoints - Full CRUD operations
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.core.event_bus import event_bus
from app.core.exceptions import QuotaExceededError
from app.db.session import get_db
from app.models.card_protocol import ArtifactType
from app.models.plan import Plan, PlanType
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.orchestration.discovery_manager import (
    PHASE_DESIGN_WORKFLOW_STATE,
    PHASE_SKETCH_REVIEW_WORKFLOW_STATE,
    DiscoveryManager,
)
from app.orchestration.phase_sketch_service import PhaseSketchService
from app.orchestration.task_guide_enricher import TaskGuideEnricher
from app.schemas.plan import (
    PlanCreate,
    PlanDetail,
    PlanPriorityUpdate,
    PlanProgress,
    PlanQuotaStatus,
    PlanUpdate,
    SetPrimaryPlanRequest,
)
from app.schemas.task import TaskDetail
from app.services.card_protocol.feedback_gate_engine import FeedbackGateEngine
from app.services.card_protocol.global_compass_manager import GlobalCompassManager
from app.services.card_protocol.phase_design_service import PhaseDesignService
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.planning_memory_service import PlanningMemoryService
from app.services.plan_quota_service import PlanQuotaService
from app.services.plan_service import PlanService, _sync_plan_card_projection
from app.services.plan_state_service import PlanStateService
from app.services.planning_artifact_service import PlanningArtifactService
from app.services.state_notification_service import state_notification_service
from app.tools.plan_tools import GenerateTasksForPlanTool
from app.tools.schemas import GenerateTasksForPlanParams

router = APIRouter()
_task_guide_enricher = TaskGuideEnricher()


class GenerateTasksRequest(BaseModel):
    count: int | None = Field(default=None, ge=1, le=20)


class PhaseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phase_index: int = Field(ge=1)
    estimated_start: date | None = None
    estimated_end: date | None = None
    entry_criteria: list[str] | None = None
    exit_criteria: list[str] | None = None
    feedback_gate_required: bool = True
    phase_weight: float | None = Field(default=None, gt=0)
    objective: str | None = None


class PhaseReorderRequest(BaseModel):
    ordered_phase_ids: list[UUID] = Field(min_length=1)


class PhaseFeedbackRequest(BaseModel):
    rating: float | None = Field(default=None, ge=1, le=5)
    reflection: str | None = None
    blocked: bool = False
    life_changed: bool = False
    request_compass_review: bool = False
    structured_answers: dict[str, Any] | None = None


class PhaseRegenerateScheduleRequest(BaseModel):
    from_date: date | None = None


class DiscoveryStartRequest(BaseModel):
    initial_message: str = Field(min_length=1, max_length=5000)


class DiscoveryTurnRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=5000)


class DiscoveryFinalizeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: PlanType | None = None
    description: str | None = None
    subject: str | None = Field(default=None, max_length=100)
    target_date: date | None = None
    daily_available_minutes: int | None = Field(default=None, ge=1)
    total_estimated_hours: float | None = Field(default=None, ge=0)


class CompassApproveRequest(BaseModel):
    edits: dict[str, Any] | None = None


class PhaseSketchGenerateRequest(BaseModel):
    compass_artifact_id: UUID | None = None
    dossier_artifact_id: UUID | None = None


class FeedbackGateAnswerRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=5000)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_plan(
    plan: Plan,
    *,
    task_count: int,
    completed_task_count: int,
    tasks: list[Task] | None = None,
    user_display_name: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": plan.id,
        "name": plan.name,
        "type": plan.type.value,
        "description": plan.description,
        "subject": plan.subject,
        "target_date": plan.target_date,
        "progress": plan.progress,
        "mastery_level": plan.mastery_level,
        "daily_available_minutes": plan.daily_available_minutes,
        "total_estimated_hours": plan.total_estimated_hours,
        "is_active": plan.is_active,
        "priority": plan.priority.value if plan.priority else "normal",
        "is_primary": bool(getattr(plan, "is_primary", False)),
        "plan_stage": plan.plan_stage.value if plan.plan_stage else "daily",
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": completed_task_count,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "source": plan.source,
        "source_metadata": plan.source_metadata,
    }
    if tasks is not None:
        task_payloads = [_serialize_task_for_plan_detail(task, subject=plan.subject) for task in tasks]
        payload["tasks"] = task_payloads
        payload["day_highlights"] = _build_day_highlights(
            plan=plan,
            task_payloads=task_payloads,
            user_display_name=user_display_name,
        )
    return payload


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _serialize_task_for_plan_detail(task: Task, *, subject: str | None) -> dict[str, Any]:
    payload = TaskDetail.model_validate(task).model_dump(mode="json")
    guide_json = payload.get("guide_json")
    guide = dict(guide_json) if isinstance(guide_json, dict) else {}
    if not _strip(guide.get("why_now")):
        task_kind = _strip(guide.get("task_kind")) or _task_kind_from_tags(payload.get("tags")) or "retrieval_drill"
        focus = (
            _strip(guide.get("focus_cue"))
            or _strip(guide.get("objective"))
            or _strip(payload.get("guide_content"))
            or _strip(payload.get("title"))
        )
        guide["why_now"] = _task_guide_enricher.build_rule_based_why_now(
            task_kind=task_kind,
            subject=_strip(subject) or "当前科目",
            focus=focus,
            guide_json=guide,
        )
    payload["guide_json"] = guide
    return payload


def _task_kind_from_tags(tags: Any) -> str:
    if not isinstance(tags, list):
        return ""
    known_kinds = {
        "diagnostic_triage",
        "retrieval_triage",
        "retrieval_drill",
        "retrieval_repair",
        "mock_review",
        "diagnostic_map",
        "closed_book_map",
        "deep_learn_retrieval",
        "spaced_retrieval",
        "integration_retrieval",
        "stage_mock",
    }
    for tag in tags:
        text = _strip(tag)
        if text in known_kinds:
            return text
    return ""


def _task_day_from_payload(task_payload: dict[str, Any]) -> int:
    order_index = task_payload.get("order_index")
    try:
        order_value = int(order_index or 0)
    except (TypeError, ValueError):
        order_value = 0
    if order_value >= 1000:
        return max(1, order_value // 1000)
    tags = task_payload.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            text = _strip(tag)
            if text.startswith("day:"):
                try:
                    return max(1, int(text.split(":", 1)[1]))
                except ValueError:
                    continue
    return 1


def _stored_day_recommendation(plan: Plan, day: int) -> str:
    metadata = plan.source_metadata if isinstance(plan.source_metadata, dict) else {}
    highlights = metadata.get("day_highlights")
    if not isinstance(highlights, dict):
        return ""
    try:
        stored_day = int(highlights.get("day") or 0)
    except (TypeError, ValueError):
        stored_day = 0
    if stored_day == day:
        return _strip(highlights.get("recommendation") or highlights.get("ai_recommendation"))
    keyed = highlights.get(str(day))
    if isinstance(keyed, dict):
        return _strip(keyed.get("recommendation") or keyed.get("ai_recommendation"))
    return ""


def _build_day_recommendation(
    *,
    plan: Plan,
    day: int,
    task_payloads: list[dict[str, Any]],
    user_display_name: str | None,
) -> str:
    stored = _stored_day_recommendation(plan, day)
    display_name = _strip(user_display_name)
    if stored:
        if display_name and len(display_name) <= 12 and not stored.startswith(f"{display_name}，"):
            return f"{display_name}，{stored}"
        return stored
    name_prefix = f"{display_name}，" if display_name and len(display_name) <= 12 else ""
    task_count = max(1, len(task_payloads))
    thing_label = f"这 {task_count} 件事" if task_count > 1 else "这 1 件事"
    subject_tail = f"{_strip(plan.subject)} 的第一步就稳下来了" if _strip(plan.subject) else "你已经走在正确路上了"
    if day == 1:
        return f"{name_prefix}今天先做好{thing_label}，{subject_tail}。"
    return f"{name_prefix}先看 Day {day} 的{thing_label}，把节奏稳稳接上。"


def _build_day_highlights(
    *,
    plan: Plan,
    task_payloads: list[dict[str, Any]],
    user_display_name: str | None,
) -> dict[str, Any] | None:
    if not task_payloads:
        return None

    day_groups: dict[int, list[dict[str, Any]]] = {}
    for task_payload in task_payloads:
        day = _task_day_from_payload(task_payload)
        day_groups.setdefault(day, []).append(task_payload)

    highlight_day = 1 if day_groups.get(1) else min(day_groups)
    highlight_tasks = sorted(
        day_groups[highlight_day],
        key=lambda task: (int(task.get("order_index") or 0), _strip(task.get("created_at"))),
    )
    return {
        "day": highlight_day,
        "recommendation": _build_day_recommendation(
            plan=plan,
            day=highlight_day,
            task_payloads=highlight_tasks,
            user_display_name=user_display_name,
        ),
        "tasks": highlight_tasks,
    }


async def _get_plan_card_or_500(db: AsyncSession, plan: Plan, user_id: UUID):
    await _sync_plan_card_projection(db, plan)
    service = PhaseService(db, event_bus)
    plan_card = await service.get_plan_card_by_legacy_plan(plan.id, user_id)
    if not plan_card:
        raise HTTPException(status_code=500, detail="Plan card projection unavailable")
    return plan_card


async def _get_latest_artifact_for_plan(
    db: AsyncSession,
    *,
    plan_card_id: UUID,
    artifact_type: ArtifactType,
):
    history = await PlanningArtifactService(db, event_bus).get_artifact_history(plan_card_id, artifact_type)
    return history[0] if history else None


@router.get("", response_model=dict[str, Any])
async def list_plans(
    type: PlanType | None = Query(None, description="Filter by plan type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all plans with optional filtering and pagination
    """
    query = select(Plan).where(Plan.user_id == current_user.id)

    # Apply filters
    if type:
        query = query.where(Plan.type == type)
    if is_active is not None:
        query = query.where(Plan.is_active == is_active)

    # Count total
    count_query = select(func.count(Plan.id)).where(Plan.user_id == current_user.id)
    if type:
        count_query = count_query.where(Plan.type == type)
    if is_active is not None:
        count_query = count_query.where(Plan.is_active == is_active)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Pagination and ordering
    query = query.order_by(desc(Plan.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    plans = result.scalars().all()

    # Batch task counts (replaces N+1 with single GROUP BY query)
    plan_ids = [plan.id for plan in plans]
    task_counts: dict = {}
    completed_counts: dict = {}
    if plan_ids:
        task_stats_query = (
            select(
                Task.plan_id,
                func.count(Task.id).label("total"),
                func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label("completed"),
            )
            .where(Task.plan_id.in_(plan_ids))
            .group_by(Task.plan_id)
        )
        task_stats_result = await db.execute(task_stats_query)
        for row in task_stats_result.all():
            task_counts[row.plan_id] = row.total
            completed_counts[row.plan_id] = row.completed

    # Enrich with task counts
    plans_data = []
    for plan in plans:
        plans_data.append(
            _serialize_plan(
                plan,
                task_count=task_counts.get(plan.id, 0),
                completed_task_count=completed_counts.get(plan.id, 0),
            )
        )

    return {
        "data": plans_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


# route-tier: authed
@router.post("/discovery/start", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def start_plan_discovery(
    request: DiscoveryStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = await DiscoveryManager(db, event_bus).start_discovery(
        user_id=current_user.id,
        initial_message=request.initial_message,
    )
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/discovery/{session_id}/turn", response_model=dict[str, Any])
async def continue_plan_discovery(
    request: DiscoveryTurnRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await DiscoveryManager(db, event_bus).process_discovery_turn(
            user_id=current_user.id,
            session_id=session_id,
            user_message=request.user_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/discovery/{session_id}/finalize", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def finalize_plan_discovery(
    request: DiscoveryFinalizeRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await DiscoveryManager(db, event_bus).finalize_discovery(
            user_id=current_user.id,
            session_id=session_id,
            plan_overrides=request.model_dump(exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "data": payload}


@router.post("", response_model=PlanDetail, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_in: PlanCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Create a new plan

    Checks quota before creation. Raises 403 if quota exceeded.
    """
    try:
        plan = await PlanService.create(
            db=db, obj_in=plan_in, user_id=current_user.id, skip_quota_check=False, redis_client=cache_service.redis
        )
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": e.message,
                "current_count": e.current_count,
                "max_quota": e.max_quota,
                "error_code": "QUOTA_EXCEEDED",
            },
        )

    # Get task counts
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0

    return _serialize_plan(
        plan,
        task_count=task_count,
        completed_task_count=0,
    )


# route-tier: authed
@router.get("/{plan_id:uuid}/compass/review", response_model=dict[str, Any])
async def get_compass_review(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")
    plan_card = await _get_plan_card_or_500(db, plan, current_user.id)
    try:
        payload = await GlobalCompassManager(db, event_bus).present_compass_for_review(
            plan_card_id=plan_card.id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/compass/{artifact_id}/approve", response_model=dict[str, Any])
async def approve_compass(
    request: CompassApproveRequest,
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        artifact = await GlobalCompassManager(db, event_bus).user_approve_compass(
            artifact_id=artifact_id,
            user_id=current_user.id,
            edits=request.edits,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "success": True,
        "data": {
            "workflow_state": "COMPASS_APPROVED",
            "artifact_id": str(artifact.id),
            "version": artifact.version,
            "payload": dict(artifact.payload or {}),
        },
    }


# route-tier: authed
@router.post("/{plan_id:uuid}/phase-sketch/generate", response_model=dict[str, Any])
async def generate_phase_sketch(
    request: PhaseSketchGenerateRequest,
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")
    plan_card = await _get_plan_card_or_500(db, plan, current_user.id)
    artifact_service = PlanningArtifactService(db, event_bus)
    plan_metadata = dict(plan_card.metadata_ or {})
    if plan_metadata.get("pending_global_compass_artifact_id") and request.compass_artifact_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compass review is still pending; approve the proposed compass before generating phases",
        )
    if request.compass_artifact_id:
        compass_artifact = await artifact_service.get_artifact(request.compass_artifact_id)
    else:
        compass_artifact = await artifact_service.get_approved(plan_card.id, ArtifactType.GLOBAL_COMPASS)
    dossier_artifact = (
        await artifact_service.get_artifact(request.dossier_artifact_id)
        if request.dossier_artifact_id
        else await _get_latest_artifact_for_plan(
            db,
            plan_card_id=plan_card.id,
            artifact_type=ArtifactType.DISCOVERY_DOSSIER,
        )
    )
    if not compass_artifact or not dossier_artifact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compass or discovery dossier artifact missing",
        )
    if compass_artifact.status.value != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phase sketch generation requires an APPROVED compass",
        )

    artifact = await PhaseSketchService(db, event_bus).generate_sketch(
        plan_card_id=plan_card.id,
        compass=compass_artifact,
        dossier=dossier_artifact,
        user_id=current_user.id,
    )
    return {
        "success": True,
        "data": {
            "workflow_state": PHASE_SKETCH_REVIEW_WORKFLOW_STATE,
            "artifact_id": str(artifact.id),
            "version": artifact.version,
            "payload": dict(artifact.payload or {}),
        },
    }


# route-tier: authed
@router.post("/{plan_id:uuid}/phase-sketch/{artifact_id}/materialize", response_model=dict[str, Any])
async def materialize_phase_sketch(
    plan_id: UUID = Path(..., description="Plan ID"),
    artifact_id: UUID = Path(..., description="Phase blueprint artifact ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")
    plan_card = await _get_plan_card_or_500(db, plan, current_user.id)
    artifact = await PlanningArtifactService(db, event_bus).get_artifact(artifact_id)
    if not artifact or artifact.plan_card_id != plan_card.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase sketch artifact not found")

    try:
        phases = await PhaseSketchService(db, event_bus).materialize_sketch(
            plan_card_id=plan_card.id,
            sketch=artifact,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "success": True,
        "data": {
            "workflow_state": PHASE_DESIGN_WORKFLOW_STATE,
            "phase_count": len(phases),
            "phase_ids": [str(phase.id) for phase in phases],
        },
    }


# route-tier: authed
@router.get("/{plan_id:uuid}/planning-context", response_model=dict[str, Any])
async def get_planning_context(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")
    plan_card = await _get_plan_card_or_500(db, plan, current_user.id)
    context = await PlanningMemoryService(db, event_bus).load_planning_context(
        plan_card_id=plan_card.id,
        user_id=current_user.id,
    )
    return {"success": True, "data": context.__dict__}


# route-tier: authed
@router.post("/phases/{phase_card_id}/design-tasks", response_model=dict[str, Any])
async def design_phase_tasks(
    phase_card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    phase = await PhaseService(db, event_bus)._get_owned_phase(phase_card_id, current_user.id)
    plan_card = await PhaseService(db, event_bus)._get_parent_plan(phase.id)
    if not plan_card:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phase must belong to a plan")
    created = await PhaseDesignService(db, event_bus).design_phase_tasks(
        phase_card_id=phase.id,
        plan_card_id=plan_card.id,
        user_id=current_user.id,
    )
    return {"success": True, "data": {"phase_card_id": str(phase.id), "tasks": created}}


# route-tier: authed
@router.post("/phases/{phase_card_id}/feedback-gate/start", response_model=dict[str, Any])
async def start_phase_feedback_gate(
    phase_card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await FeedbackGateEngine(db, event_bus).trigger_feedback_gate(
            phase_card_id=phase_card_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/phases/feedback-gate/{session_id}/respond", response_model=dict[str, Any])
async def respond_phase_feedback_gate(
    request: FeedbackGateAnswerRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await FeedbackGateEngine(db, event_bus).process_feedback_response(
            session_id=session_id,
            user_message=request.user_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/{plan_id:uuid}/advance-phase", response_model=dict[str, Any])
async def advance_plan_phase(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")
    plan_card = await _get_plan_card_or_500(db, plan, current_user.id)
    try:
        payload = await FeedbackGateEngine(db, event_bus).advance_to_next_phase(
            plan_card_id=plan_card.id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"success": True, "data": payload}


@router.get("/{plan_id:uuid}", response_model=PlanDetail)
async def get_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get plan details by ID
    """
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    # Get task counts and related tasks for detail view
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0

    completed_query = select(func.count(Task.id)).where(
        and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
    )
    completed_count = (await db.execute(completed_query)).scalar() or 0
    tasks_result = await db.execute(
        select(Task)
        .where(and_(Task.plan_id == plan.id, Task.user_id == current_user.id))
        .order_by(Task.order_index.asc(), Task.created_at.asc())
    )
    tasks = tasks_result.scalars().all()

    return _serialize_plan(
        plan,
        task_count=task_count,
        completed_task_count=completed_count,
        tasks=list(tasks),
        user_display_name=current_user.nickname or current_user.full_name or current_user.username,
    )


# route-tier: authed
@router.get("/{plan_id:uuid}/phases", response_model=dict[str, Any])
async def get_plan_phases(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    await _sync_plan_card_projection(db, plan)
    payload = await PhaseService(db, event_bus).get_phase_summaries_for_legacy_plan(
        legacy_plan_id=plan.id,
        user_id=current_user.id,
    )
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/{plan_id:uuid}/phases", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_plan_phase(
    request: PhaseCreateRequest,
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    await _sync_plan_card_projection(db, plan)
    service = PhaseService(db, event_bus)
    plan_card = await service.get_plan_card_by_legacy_plan(plan.id, current_user.id)
    if not plan_card:
        raise HTTPException(status_code=500, detail="Plan card projection unavailable")

    phase = await service.create_phase(
        plan_card_id=plan_card.id,
        name=request.name,
        phase_index=request.phase_index,
        user_id=current_user.id,
        estimated_start=request.estimated_start,
        estimated_end=request.estimated_end,
        entry_criteria=request.entry_criteria,
        exit_criteria=request.exit_criteria,
        feedback_gate_required=request.feedback_gate_required,
        phase_weight=request.phase_weight,
        objective=request.objective,
    )
    await db.commit()
    payload = await service.get_phase_summaries_for_legacy_plan(
        legacy_plan_id=plan.id,
        user_id=current_user.id,
    )
    summary = next((item for item in payload["phases"] if item["card_id"] == str(phase.id)), None)
    return {"success": True, "data": summary}


# route-tier: authed
@router.post("/{plan_id:uuid}/phases/reorder", response_model=dict[str, Any])
async def reorder_plan_phases(
    request: PhaseReorderRequest,
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    service = PhaseService(db, event_bus)
    plan_card = await service.get_plan_card_by_legacy_plan(plan.id, current_user.id)
    if not plan_card:
        await _sync_plan_card_projection(db, plan)
        plan_card = await service.get_plan_card_by_legacy_plan(plan.id, current_user.id)
    if not plan_card:
        raise HTTPException(status_code=500, detail="Plan card projection unavailable")

    await service.reorder_phases(
        plan_card_id=plan_card.id,
        ordered_phase_ids=request.ordered_phase_ids,
        user_id=current_user.id,
    )
    await db.commit()
    payload = await service.get_phase_summaries_for_legacy_plan(
        legacy_plan_id=plan.id,
        user_id=current_user.id,
    )
    return {"success": True, "data": payload}


# route-tier: authed
@router.post("/phases/{phase_card_id}/activate", response_model=dict[str, Any])
async def activate_phase(
    phase_card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    phase = await PhaseService(db, event_bus).activate_phase(
        phase_card_id=phase_card_id,
        user_id=current_user.id,
    )
    await db.commit()
    return {
        "success": True,
        "data": {
            "phase_card_id": str(phase.id),
            "lifecycle_status": phase.lifecycle_status.value,
        },
    }


# route-tier: authed
@router.post("/phases/{phase_card_id}/complete", response_model=dict[str, Any])
async def complete_phase(
    phase_card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await PhaseService(db, event_bus).complete_phase(
        phase_card_id=phase_card_id,
        user_id=current_user.id,
    )
    await db.commit()
    return {"success": True, "data": result.__dict__}


# route-tier: authed
@router.post("/phases/{phase_card_id}/feedback", response_model=dict[str, Any])
async def submit_phase_feedback(
    request: PhaseFeedbackRequest,
    phase_card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback_payload = request.model_dump(exclude_none=True)
    result = await PhaseService(db, event_bus).submit_phase_feedback(
        phase_card_id=phase_card_id,
        user_id=current_user.id,
        feedback=feedback_payload,
    )
    await db.commit()
    return {"success": True, "data": result.__dict__}


# route-tier: authed
@router.post("/phases/{phase_card_id}/schedule/regenerate", response_model=dict[str, Any])
async def regenerate_phase_schedule(
    request: PhaseRegenerateScheduleRequest,
    phase_card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PhaseService(db, event_bus)
    phase = await service._get_owned_phase(phase_card_id, current_user.id)
    result = await service.temporal_engine.regenerate_phase_schedule(
        phase_card_id=phase.id,
        from_date=request.from_date,
    )
    await db.commit()
    return {"success": True, "data": result}


@router.put("/{plan_id:uuid}", response_model=PlanDetail)
@router.patch("/{plan_id:uuid}", response_model=PlanDetail)
async def update_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    plan_in: PlanUpdate = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update plan details
    """
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    plan = await PlanService.update(db=db, db_obj=plan, obj_in=plan_in)

    # Get task counts
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0

    completed_query = select(func.count(Task.id)).where(
        and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
    )
    completed_count = (await db.execute(completed_query)).scalar() or 0

    return _serialize_plan(
        plan,
        task_count=task_count,
        completed_task_count=completed_count,
    )


@router.post("/{plan_id:uuid}/generate-tasks", response_model=list[TaskDetail])
async def generate_tasks_for_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    count: int = Query(5, ge=1, le=20),
    request_body: GenerateTasksRequest | None = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为计划生成任务，兼容移动端计划页调用。"""
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    requested_count = request_body.count if request_body and request_body.count is not None else count

    topic = plan.subject or plan.name
    tool = GenerateTasksForPlanTool()
    result = await tool.execute(
        GenerateTasksForPlanParams(
            plan_id=str(plan.id),
            topic=topic,
            difficulty="medium",
            task_count=requested_count,
        ),
        user_id=str(current_user.id),
        db_session=db,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error_message or "Failed to generate tasks for plan",
        )

    task_ids = []
    tasks = result.data.get("tasks", []) if isinstance(result.data, dict) else []
    for task in tasks:
        if isinstance(task, dict) and task.get("id"):
            task_ids.append(task["id"])

    created_tasks_result = await db.execute(
        select(Task)
        .where(Task.user_id == current_user.id, Task.id.in_(task_ids))
        .order_by(desc(Task.created_at))
    )
    created_tasks = created_tasks_result.scalars().all()
    return [TaskDetail.model_validate(task) for task in created_tasks]


@router.delete("/{plan_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete (archive) a plan by setting is_active to False
    """
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    # Archive instead of hard delete
    plan.is_active = False
    db.add(plan)
    await db.commit()

    # Get task count for notification
    task_result = await db.execute(select(func.count(Task.id)).where(Task.plan_id == plan_id))
    task_count_freed = task_result.scalar() or 0

    # Send state change notification
    try:
        await state_notification_service.notify_plan_deleted(
            user_id=str(current_user.id),
            plan_name=plan.name,
            plan_id=plan_id,
            task_count_freed=task_count_freed,
            memory_count_removed=0,  # Memory cleanup not implemented yet
            intervention_level="toast",
        )
    except Exception as e:
        logger.error(f"Failed to send plan_deleted notification: {e}")
        # Don't fail the request if notification fails


@router.post("/{plan_id:uuid}/archive", response_model=dict[str, Any])
async def archive_plan_state(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive plan (PlanState + Plan.is_active).

    Archiving a plan:
    - Frees up quota for new plans
    - If archived plan was primary, auto-selects new primary
    - Preserves plan data for history
    """
    # Use PlanService.archive which handles primary plan selection
    plan = await PlanService.archive(db=db, plan_id=plan_id, user_id=current_user.id, redis_client=cache_service.redis)

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    # Also update PlanState
    state_service = PlanStateService(db, cache_service.redis)
    state = await state_service.upsert_plan_state(
        user_id=current_user.id,
        plan_id=plan_id,
        patch={
            "status": PlanStateStatus.ARCHIVED.value,
            "archived_at": _utcnow(),
        },
        bump_version=False,
    )

    # Trigger sprint achievement events if this is a sprint plan
    daily_first_reward = None
    if plan.type == PlanType.SPRINT:
        from app.services.achievement_engine import AchievementEngine, AchievementEvent

        engine = AchievementEngine(db)

        # Calculate completion rate and check if ahead of schedule
        completion_rate = plan.progress or 0.0
        days_ahead = 0
        if plan.target_date:
            today = date.today()
            days_ahead = (plan.target_date - today).days if completion_rate >= 1.0 else 0

        # Check if sprint meets completion threshold (80%+)
        if completion_rate >= 0.8:
            # Check for daily first win reward
            daily_first_reward = await engine.check_daily_first(str(current_user.id), db)

            # SPRINTS_TOTAL: Count all completed sprints (both 80%+ and 100%)
            # This triggers achievements like sprint_first, sprint_5, sprint_10
            await engine.process_event(
                str(current_user.id), AchievementEvent.SPRINT_COMPLETED, completion_rate=completion_rate
            )

            if completion_rate >= 1.0:
                # 100% completion - trigger perfect completion event
                await engine.process_event(
                    str(current_user.id), AchievementEvent.SPRINT_PERFECT, completion_rate=completion_rate
                )

                if days_ahead > 0:
                    # Completed ahead of schedule
                    await engine.process_event(
                        str(current_user.id),
                        AchievementEvent.SPRINT_AHEAD,
                        completion_rate=completion_rate,
                        days_ahead=days_ahead,
                    )

            # SPRINT_STREAK: Always check streak for any completion >=80%
            await engine.process_event(
                str(current_user.id), AchievementEvent.SPRINT_STREAK, completion_rate=completion_rate
            )

    # Get new primary plan info
    quota_service = PlanQuotaService(db, cache_service.redis)
    quota_status = await quota_service.get_quota_status(current_user.id)

    # Get task and memory counts for notification
    task_count_freed = 0
    memory_count_removed = 0

    # Count tasks associated with this plan
    task_result = await db.execute(select(func.count(Task.id)).where(Task.plan_id == plan_id))
    task_count_freed = task_result.scalar() or 0

    # Get new primary plan name for notification
    new_primary_plan_name = None
    if quota_status.primary_plan_id:
        new_primary_result = await db.execute(select(Plan.name).where(Plan.id == quota_status.primary_plan_id))
        new_primary_plan_name = new_primary_result.scalar()

    # Send state change notification
    try:
        await state_notification_service.notify_plan_archived(
            user_id=str(current_user.id),
            plan_name=plan.name,
            plan_id=plan_id,
            task_count_freed=task_count_freed,
            memory_count_removed=memory_count_removed,
            new_primary_plan=new_primary_plan_name,
            intervention_level="toast" if plan.progress < 0.8 else "card",
        )
    except Exception as e:
        logger.error(f"Failed to send plan_archived notification: {e}")
        # Don't fail the request if notification fails

    response = {
        "plan_id": str(plan_id),
        "status": state.status if state else PlanStateStatus.ARCHIVED.value,
        "archived_at": state.archived_at.isoformat() if state and state.archived_at else None,
        "new_primary_plan_id": str(quota_status.primary_plan_id) if quota_status.primary_plan_id else None,
    }

    # Include daily first reward if available
    if daily_first_reward:
        response["daily_first_reward"] = daily_first_reward

    return response


@router.post("/{plan_id:uuid}/restore", response_model=dict[str, Any])
async def restore_plan_state(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore an archived plan to active.

    Restoring a plan:
    - Checks quota before restoring (raises 403 if exceeded)
    - Ensures primary plan exists after restore
    """
    try:
        # Use PlanService.restore which handles quota check
        plan = await PlanService.restore(
            db=db, plan_id=plan_id, user_id=current_user.id, skip_quota_check=False, redis_client=cache_service.redis
        )
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": e.message,
                "current_count": e.current_count,
                "max_quota": e.max_quota,
                "error_code": "QUOTA_EXCEEDED",
            },
        )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found or is already active"
        )

    # Also update PlanState
    state_service = PlanStateService(db, cache_service.redis)
    state = await state_service.upsert_plan_state(
        user_id=current_user.id,
        plan_id=plan_id,
        patch={
            "status": PlanStateStatus.ACTIVE.value,
            "archived_at": None,
        },
        bump_version=False,
    )

    # Send state change notification
    try:
        await state_notification_service.notify_plan_restored(
            user_id=str(current_user.id), plan_name=plan.name, plan_id=plan_id, intervention_level="toast"
        )
    except Exception as e:
        logger.error(f"Failed to send plan_restored notification: {e}")
        # Don't fail the request if notification fails

    return {
        "plan_id": str(plan_id),
        "status": state.status if state else PlanStateStatus.ACTIVE.value,
        "archived_at": None,
    }


@router.get("/{plan_id:uuid}/progress", response_model=PlanProgress)
async def get_plan_progress(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed progress information for a plan
    """
    plan = await PlanService.get_by_id(db=db, plan_id=plan_id, user_id=current_user.id)

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    # Get task statistics
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    total_tasks = (await db.execute(task_query)).scalar() or 0

    completed_query = select(func.count(Task.id)).where(
        and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
    )
    completed_tasks = (await db.execute(completed_query)).scalar() or 0

    return {
        "plan_id": plan.id,
        "progress": plan.progress,
        "mastery_level": plan.mastery_level,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_minutes_spent": 0,  # Would be calculated from focus sessions
        "estimated_remaining_hours": plan.total_estimated_hours or 0,
    }


@router.get("/stats/summary", response_model=dict[str, Any])
async def get_plans_summary(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get summary statistics for all user plans
    """
    total_query = select(func.count(Plan.id)).where(Plan.user_id == current_user.id)
    total = (await db.execute(total_query)).scalar() or 0

    active_query = select(func.count(Plan.id)).where(and_(Plan.user_id == current_user.id, Plan.is_active))
    active = (await db.execute(active_query)).scalar() or 0

    sprint_query = select(func.count(Plan.id)).where(
        and_(Plan.user_id == current_user.id, Plan.type == PlanType.SPRINT)
    )
    sprint_plans = (await db.execute(sprint_query)).scalar() or 0

    growth_query = select(func.count(Plan.id)).where(
        and_(Plan.user_id == current_user.id, Plan.type == PlanType.GROWTH)
    )
    growth_plans = (await db.execute(growth_query)).scalar() or 0

    return {"total": total, "active": active, "sprint_plans": sprint_plans, "growth_plans": growth_plans}


# ========== Quota Related Endpoints ==========


@router.get("/quota/status", response_model=PlanQuotaStatus)
async def get_quota_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get user's plan quota status

    Returns:
    - used: Number of active plans
    - limit: Maximum allowed active plans
    - remaining: Remaining quota (-1 if unlimited)
    - is_unlimited: Whether user has unlimited quota
    - primary_plan_id: Current primary plan ID
    """
    quota_service = PlanQuotaService(db, cache_service.redis)
    status = await quota_service.get_quota_status(current_user.id)

    return {
        "used": status.used,
        "limit": status.limit,
        "remaining": status.remaining,
        "is_unlimited": status.is_unlimited,
        "primary_plan_id": status.primary_plan_id,
    }


@router.get("/primary", response_model=dict[str, Any])
async def get_primary_plan(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Get user's current primary plan
    """
    plan = await PlanService.get_primary(db, current_user.id)

    if not plan:
        return {"plan": None, "message": "No primary plan set"}

    # Get task counts
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0

    completed_query = select(func.count(Task.id)).where(
        and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
    )
    completed_count = (await db.execute(completed_query)).scalar() or 0

    return {
        "plan": _serialize_plan(
            plan,
            task_count=task_count,
            completed_task_count=completed_count,
        )
    }


@router.post("/primary", response_model=dict[str, Any])
async def set_primary_plan(
    request: SetPrimaryPlanRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Set a plan as the primary plan

    Only one plan can be primary at a time.
    """
    quota_service = PlanQuotaService(db, cache_service.redis)
    success = await quota_service.set_primary_plan(current_user.id, request.plan_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {request.plan_id} not found or is not active"
        )

    logger.info(f"Primary plan set to {request.plan_id} for user {current_user.id}")

    return {"success": True, "primary_plan_id": str(request.plan_id), "message": "Primary plan updated successfully"}


@router.patch("/{plan_id:uuid}/priority", response_model=dict[str, Any])
async def update_plan_priority(
    plan_id: UUID = Path(..., description="Plan ID"),
    request: PlanPriorityUpdate = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update plan priority

    Priority affects automatic primary plan selection.
    """
    plan = await PlanService.update_priority(db=db, plan_id=plan_id, user_id=current_user.id, priority=request.priority)

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan {plan_id} not found")

    return {"plan_id": str(plan.id), "priority": plan.priority.value, "message": "Priority updated successfully"}


@router.get("/archived", response_model=dict[str, Any])
async def list_archived_plans(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List archived plans

    Archived plans don't count towards quota but are preserved for history.
    """
    plans = await PlanService.list_archived(db=db, user_id=current_user.id, limit=page_size)

    # Batch task counts (replaces N+1 with single GROUP BY query)
    plan_ids = [plan.id for plan in plans]
    task_counts: dict = {}
    completed_counts: dict = {}
    if plan_ids:
        task_stats_query = (
            select(
                Task.plan_id,
                func.count(Task.id).label("total"),
                func.count(case((Task.status == TaskStatus.COMPLETED, Task.id))).label("completed"),
            )
            .where(Task.plan_id.in_(plan_ids))
            .group_by(Task.plan_id)
        )
        task_stats_result = await db.execute(task_stats_query)
        for row in task_stats_result.all():
            task_counts[row.plan_id] = row.total
            completed_counts[row.plan_id] = row.completed

    plans_data = []
    for plan in plans:
        plans_data.append(
            _serialize_plan(
                plan,
                task_count=task_counts.get(plan.id, 0),
                completed_task_count=completed_counts.get(plan.id, 0),
            )
        )

    return {"data": plans_data, "total": len(plans_data), "page": page, "page_size": page_size}


@router.get("/{plan_id:uuid}/learning-path-progress")
async def get_learning_path_progress(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get learning path progress for a plan

    Returns progress information for plans created from learning paths.
    Only available for plans with source='learning_path'.
    """
    plan = await PlanService.get_by_id(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.source != "learning_path":
        raise HTTPException(status_code=400, detail="This plan was not created from a learning path")

    metadata = plan.source_metadata or {}
    path_node_ids = metadata.get("path_node_ids", [])
    target_node_id = metadata.get("target_node_id")

    if not path_node_ids:
        return {
            "target_node": None,
            "nodes": [],
            "overall_progress": 0.0,
        }

    from sqlalchemy import or_

    from app.models.galaxy import KnowledgeNode, UserNodeStatus

    nodes_result = await db.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(path_node_ids)))
    nodes = {str(n.id): n for n in nodes_result.scalars().all()}

    status_result = await db.execute(
        select(UserNodeStatus).where(
            and_(UserNodeStatus.user_id == current_user.id, UserNodeStatus.node_id.in_(path_node_ids))
        )
    )
    user_statuses = {str(s.node_id): s for s in status_result.scalars().all()}

    nodes_progress = []
    total_mastery = 0
    mastered_count = 0

    for node_id_str in path_node_ids:
        node_id = UUID(node_id_str)
        node = nodes.get(node_id_str)
        user_status = user_statuses.get(node_id_str)

        if not node:
            continue

        mastery_score = user_status.mastery_score if user_status else 0
        total_mastery += mastery_score

        if mastery_score >= 80:
            status = "mastered"
            mastered_count += 1
        elif mastery_score > 0:
            status = "unlocked"
        else:
            status = "locked"

        is_target = str(target_node_id) == node_id_str

        nodes_progress.append(
            {
                "id": node_id_str,
                "name": node.name,
                "status": status,
                "mastery": int(mastery_score),
                "is_target": is_target,
            }
        )

    overall_progress = mastered_count / len(path_node_ids) if path_node_ids else 0.0

    target_node_data = None
    if target_node_id:
        target_node = nodes.get(str(target_node_id))
        target_status = user_statuses.get(str(target_node_id))
        if target_node:
            target_mastery = target_status.mastery_score if target_status else 0
            if target_mastery >= 80:
                target_status_name = "mastered"
            elif target_mastery > 0:
                target_status_name = "unlocked"
            else:
                target_status_name = "locked"
            target_node_data = {
                "id": str(target_node_id),
                "name": target_node.name,
                "status": target_status_name,
                "mastery": int(target_mastery),
                "is_target": True,
            }

    return {
        "target_node": target_node_data,
        "nodes": nodes_progress,
        "overall_progress": overall_progress,
    }
