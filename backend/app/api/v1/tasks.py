"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

Tasks API Endpoints
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _zh, get_current_user
from app.core.cache import cache_service
from app.core.exceptions import NotFoundError
from app.core.metrics import observe_product_loop_latency, record_product_loop_event
from app.db.session import get_db
from app.models.file_storage import StoredFile
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.task_resources import TaskResourceLink, TaskResourceType
from app.models.user import User
from app.schemas.task import (
    SubTaskDetail,
    TaskAbandon,
    TaskBoundSourceInfo,
    TaskCompleteRequest,
    TaskCreate,
    TaskDetail,
    TaskDocumentInfo,
    TaskDocumentLinkCreate,
    TaskDocumentSuggestion,
    TaskDocumentUnlinkRequest,
    TaskPause,
    TaskQuickActionRequest,
    TaskRecommendationResponse,
    TaskReorderRequest,
    TaskResourceLinkCreate,
    TaskResourceLinkInfo,
    TaskSnoozeRequest,
    TaskStuckRequest,
    TaskSuggestionRequest,
    TaskSuggestionResponse,
    TaskUpdate,
)
from app.schemas.task_feedback import (
    NextActionSelectionCreate,
    ReflectionAnswerCreate,
    ReflectionAnswerResponse,
    TaskFeedbackCreate,
    TaskFeedbackResponse,
    TaskFeedbackSubmitResponse,
)
from app.services.daily_task_selection_service import DailyTaskSelectionService
from app.services.feedback_service import feedback_service
from app.services.focus_context_service import focus_context_service
from app.services.intelligent_task_service import IntelligentTaskService
from app.services.seed_library_service import SeedLibraryService
from app.services.task_document_service import task_document_service
from app.services.task_guide_service import task_guide_service
from app.services.task_priority_service import TaskPriorityService
from app.services.task_service import TaskService
from app.task_guidance import TaskGuidance, TaskGuidanceAudience

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _serialize_task_guidance(guidance: TaskGuidance) -> dict[str, Any]:
    return guidance.model_dump(mode="json")


def _serialize_task_document(link, file_record) -> TaskDocumentInfo:
    return TaskDocumentInfo(
        id=link.id,
        created_at=link.created_at,
        updated_at=link.updated_at,
        deleted_at=link.deleted_at,
        task_id=link.task_id,
        file_id=file_record.id,
        file_name=file_record.file_name,
        mime_type=file_record.mime_type,
        file_size=int(file_record.file_size or 0),
        status=file_record.status,
        linked_by=link.linked_by,
        document_quality_score=float(file_record.document_quality_score or 0.0),
    )


def _serialize_source_asset(
    *,
    file_record: StoredFile,
    linked_by: str | None,
    reason: str | None = None,
) -> TaskBoundSourceInfo:
    return TaskBoundSourceInfo(
        id=file_record.id,
        title=file_record.file_name,
        lifecycle_status=file_record.lifecycle_status or "active",
        source_type="file",
        linked_by=linked_by,
        reason=reason,
        status=file_record.status,
        lifecycle_reason=file_record.lifecycle_reason,
        updated_at=file_record.updated_at,
    )


async def _load_bound_sources_for_tasks(
    db: AsyncSession,
    *,
    task_ids: list[UUID],
    user_id: UUID,
) -> dict[UUID, list[TaskBoundSourceInfo]]:
    """Return task-bound source assets, including archived/revoked/orphaned files."""
    if not task_ids:
        return {}

    sources_by_task: dict[UUID, list[TaskBoundSourceInfo]] = {task_id: [] for task_id in task_ids}
    seen_by_task: dict[UUID, set[UUID]] = {task_id: set() for task_id in task_ids}

    document_rows = (
        await db.execute(
            select(TaskDocument, StoredFile)
            .join(StoredFile, StoredFile.id == TaskDocument.file_id)
            .join(Task, Task.id == TaskDocument.task_id)
            .where(TaskDocument.task_id.in_(task_ids))
            .where(Task.user_id == user_id)
            .where(TaskDocument.deleted_at.is_(None))
            .where(StoredFile.deleted_at.is_(None))
            .order_by(TaskDocument.created_at.asc(), StoredFile.file_name.asc())
        )
    ).all()

    for link, file_record in document_rows:
        if file_record.id in seen_by_task[link.task_id]:
            continue
        seen_by_task[link.task_id].add(file_record.id)
        sources_by_task[link.task_id].append(
            _serialize_source_asset(
                file_record=file_record,
                linked_by=link.linked_by,
                reason=link.source_reason,
            )
        )

    resource_rows = (
        await db.execute(
            select(TaskResourceLink, StoredFile)
            .join(StoredFile, StoredFile.id == TaskResourceLink.resource_id)
            .join(Task, Task.id == TaskResourceLink.task_id)
            .where(TaskResourceLink.task_id.in_(task_ids))
            .where(TaskResourceLink.resource_type == TaskResourceType.FILE.value)
            .where(Task.user_id == user_id)
            .where(TaskResourceLink.deleted_at.is_(None))
            .where(StoredFile.deleted_at.is_(None))
            .order_by(TaskResourceLink.order_index.asc(), TaskResourceLink.created_at.asc())
        )
    ).all()

    for link, file_record in resource_rows:
        if file_record.id in seen_by_task[link.task_id]:
            continue
        seen_by_task[link.task_id].add(file_record.id)
        sources_by_task[link.task_id].append(
            _serialize_source_asset(
                file_record=file_record,
                linked_by="resource",
                reason=link.summary,
            )
        )

    return sources_by_task


async def _load_bound_sources_for_task(
    db: AsyncSession,
    *,
    task_id: UUID,
    user_id: UUID,
) -> list[TaskBoundSourceInfo]:
    return (await _load_bound_sources_for_tasks(db, task_ids=[task_id], user_id=user_id)).get(task_id, [])


def _serialize_task_detail(
    task: Task,
    *,
    bound_sources: list[TaskBoundSourceInfo] | None = None,
) -> dict[str, Any]:
    payload = TaskDetail.model_validate(task).model_dump(mode="json")
    payload["bound_sources"] = [source.model_dump(mode="json") for source in (bound_sources or [])]
    return payload


async def _get_user_task_or_404(db: AsyncSession, task_id: UUID, user_id: UUID) -> Task:
    task = await db.get(Task, task_id)
    if not task or task.user_id != user_id:
        raise NotFoundError(message="Task not found")
    return task


async def _find_today_focus_task(
    db: AsyncSession,
    *,
    user_id: UUID,
    exclude_task_id: UUID,
) -> Task | None:
    today = date.today()
    result = await db.execute(
        select(Task)
        .where(
            Task.user_id == user_id,
            Task.id != exclude_task_id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.STUCK]),
            (Task.due_date.is_(None)) | (Task.due_date <= today),
        )
        .order_by(Task.order_index.asc(), desc(Task.priority), desc(Task.updated_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


def _action_response(
    *,
    action: str,
    message: str,
    task: Task,
    subtasks: list[Any] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {"task": TaskDetail.model_validate(task)}
    if subtasks is not None:
        data["subtasks"] = [SubTaskDetail.model_validate(item) for item in subtasks]
    return {
        "success": True,
        "action": action,
        "message": message,
        "data": data,
    }


async def _resolve_task_resource_defaults(
    db: AsyncSession,
    payload: TaskResourceLinkCreate,
    user_id: UUID,
) -> tuple[str | None, str | None, dict | None]:
    title = payload.title
    summary = payload.summary
    metadata = dict(payload.resource_metadata or {})
    seed_service = SeedLibraryService()

    if payload.resource_type == TaskResourceType.SEED_LIBRARY.value:
        if not payload.resource_id:
            raise HTTPException(status_code=400, detail="seed_library resource_id is required")
        library = await seed_service.get_library_for_user(db, payload.resource_id, user_id)
        if not library:
            raise HTTPException(status_code=404, detail="Seed library not found")
        title = title or library.name
        summary = summary or library.description
        metadata.setdefault("category", library.category)
        metadata.setdefault("visibility", library.visibility)
        metadata.setdefault("language", library.language)
    elif payload.resource_type == TaskResourceType.SEED_ITEM.value:
        if not payload.resource_id:
            raise HTTPException(status_code=400, detail="seed_item resource_id is required")
        item = await seed_service.get_item_for_user(db, payload.resource_id, user_id)
        if not item:
            raise HTTPException(status_code=404, detail="Seed item not found")
        title = title or item.title or "Seed Item"
        summary = summary or item.content
        metadata.setdefault("item_type", item.item_type)
        metadata.setdefault("subject", item.subject)
        metadata.setdefault("library_id", str(item.library_id))
    elif payload.resource_type == TaskResourceType.KNOWLEDGE_NODE.value:
        if not payload.resource_id:
            raise HTTPException(status_code=400, detail="knowledge_node resource_id is required")
    elif payload.resource_type == TaskResourceType.EXTERNAL_URL.value:
        if not payload.url:
            raise HTTPException(status_code=400, detail="external_url requires url")
    elif payload.resource_type == TaskResourceType.FILE.value:
        if not payload.resource_id:
            raise HTTPException(status_code=400, detail="file resource_id is required")
    elif payload.resource_type == TaskResourceType.NOTE.value:
        if not (title or summary):
            raise HTTPException(status_code=400, detail="note requires title or summary")

    return title, summary, metadata or None


# route-tier: authed
@router.get("", response_model=dict[str, Any])
async def list_tasks(
    status: TaskStatus | None = Query(None, description="Filter by status"),
    type: TaskType | None = Query(None, description="Filter by type"),
    plan_id: UUID | None = Query(None, description="Filter by plan ID"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    due_date_start: date | None = Query(None, description="Filter by due date start (inclusive)"),
    due_date_end: date | None = Query(None, description="Filter by due date end (inclusive)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List tasks with filtering and pagination
    """
    query = select(Task).where(Task.user_id == current_user.id)

    # Filters
    if status:
        query = query.where(Task.status == status)
    if type:
        query = query.where(Task.type == type)
    if plan_id:
        query = query.where(Task.plan_id == plan_id)
    if tags:
        # Check if task tags contain any of the filter tags (OR logic)
        # Uses JSONB @> operator for PostgreSQL, falls back to LIKE for SQLite
        tag_conditions = []
        for tag in tags:
            # PostgreSQL: tags @> '["tag"]' checks if array contains the tag
            # Using contains for JSONB array
            tag_conditions.append(Task.tags.op("@>")(f'["{tag}"]'))
        query = query.where(or_(*tag_conditions))
    if due_date_start:
        query = query.where(Task.due_date >= due_date_start)
    if due_date_end:
        query = query.where(Task.due_date <= due_date_end)

    # Persisted display order with created_at fallback
    query = query.order_by(Task.order_index.asc(), desc(Task.created_at))

    # Pagination
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()
    bound_sources = await _load_bound_sources_for_tasks(
        db,
        task_ids=[task.id for task in tasks],
        user_id=current_user.id,
    )

    return {
        "data": [_serialize_task_detail(t, bound_sources=bound_sources.get(t.id, [])) for t in tasks],
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


# route-tier: authed
@router.post("", response_model=dict[str, Any])
async def create_task(
    task_in: TaskCreate,
    generate_guide: bool = Query(False, description="Whether to auto-generate guide"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new task
    """
    task = await TaskService.create(db, task_in, current_user.id)

    linked_documents = [
        _serialize_task_document(link, file_record)
        for link, file_record in await task_document_service.list_task_documents(
            db,
            task_id=task.id,
            user_id=current_user.id,
        )
    ]
    document_suggestions = [
        TaskDocumentSuggestion.model_validate(item)
        for item in await task_document_service.suggest_documents_for_task(db, task=task)
    ]

    if generate_guide and not task.guide_content:
        guidance = await task_guide_service.generate_task_guidance(
            task,
            current_user,
            db,
            audience=TaskGuidanceAudience.HUMAN,
        )
        task.guide_content = guidance.content
        db.add(task)
        await db.commit()
        await db.refresh(task)

    # Get Nudge suggestions based on user behavior patterns
    nudges = []
    try:
        nudge_service = IntelligentTaskService(db)
        nudges = await nudge_service.get_task_nudges(
            db, current_user.id, {"estimated_minutes": task_in.estimated_minutes, **task_in.model_dump()}
        )
    except Exception as e:
        logger.warning(f"Failed to get task nudges: {e}")

    return {
        "data": _serialize_task_detail(
            task,
            bound_sources=await _load_bound_sources_for_task(db, task_id=task.id, user_id=current_user.id),
        ),
        "nudges": nudges,
        "linked_documents": linked_documents,
        "document_suggestions": document_suggestions,
    }


# route-tier: authed
@router.post("/reorder", response_model=dict[str, Any])
async def reorder_tasks(
    request: TaskReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist the display order of tasks for the current user."""
    try:
        tasks = await TaskService.reorder_tasks(
            db,
            user_id=current_user.id,
            ordered_task_ids=request.task_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "data": [TaskDetail.model_validate(task) for task in tasks],
    }


# route-tier: authed
@router.post("/suggestions", response_model=TaskSuggestionResponse)
async def get_task_suggestions(
    request: TaskSuggestionRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    获取任务创建建议 (LLM 驱动)
    """
    service = IntelligentTaskService(db)
    return await service.get_suggestions(current_user.id, request.input_text)


# route-tier: authed
@router.get("/recommendations/micro", response_model=list[TaskRecommendationResponse])
async def get_micro_task_recommendations(
    context: str | None = Query(None, description="上下文: commute, lunch, evening"),
    limit: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取碎片时间微任务推荐
    """
    from app.services.personalization import get_personalization_engine
    from app.services.task_recommendation_service import TaskRecommendationService

    engine = get_personalization_engine(db, cache_service.redis)
    service = TaskRecommendationService(db, engine)

    recommendations = await service.get_recommendations(
        user_id=current_user.id,
        limit=limit * 2,
        context=context,
    )

    micro_tasks = [r for r in recommendations if r.estimated_minutes <= 15]
    return [TaskRecommendationResponse(**r.__dict__) for r in micro_tasks[:limit]]


# route-tier: authed
@router.get("/today", response_model=list[TaskDetail])
async def get_today_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return tasks relevant for today."""
    selections = await DailyTaskSelectionService(db, cache_service.redis).select_tasks(
        user_id=current_user.id,
        limit=50,
        include_completed_today=True,
        only_today_relevant=True,
    )
    tasks = [selection.task for selection in selections]
    bound_sources = await _load_bound_sources_for_tasks(
        db,
        task_ids=[task.id for task in tasks],
        user_id=current_user.id,
    )
    return [_serialize_task_detail(task, bound_sources=bound_sources.get(task.id, [])) for task in tasks]


# route-tier: authed
@router.get("/recommended", response_model=list[TaskDetail])
async def get_recommended_tasks(
    limit: int = Query(5, ge=1, le=20, description="Recommendation count"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a lightweight recommendation list for the dashboard."""
    selections = await DailyTaskSelectionService(db, cache_service.redis).select_tasks(
        user_id=current_user.id,
        limit=limit,
        include_completed_today=False,
    )
    tasks = [selection.task for selection in selections]
    bound_sources = await _load_bound_sources_for_tasks(
        db,
        task_ids=[task.id for task in tasks],
        user_id=current_user.id,
    )
    return [_serialize_task_detail(task, bound_sources=bound_sources.get(task.id, [])) for task in tasks]


# route-tier: authed
@router.get("/{task_id}", response_model=dict[str, Any])
async def get_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get task details
    """
    task = await _get_user_task_or_404(db, task_id, current_user.id)

    return {
        "data": _serialize_task_detail(
            task,
            bound_sources=await _load_bound_sources_for_task(db, task_id=task_id, user_id=current_user.id),
        )
    }


# route-tier: authed
@router.get("/{task_id}/card-protocol", response_model=dict[str, Any])
async def get_task_card_protocol(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    TASK-001: Return the structured TaskCardProtocol for a task.

    Surfaces the protocol fields (why_this_task, materials_protocol,
    stuck_protocol, success_criteria, minimum_output, updates_after_completion,
    fallback_if_failed) that the Flutter task guide panel needs to render the
    "why am I doing this" / "what materials do I need" / "what if I fail"
    sections.

    The protocol is built on demand from the task's existing fields plus any
    cached SkillDirective / RetrievalDirective hints from the Spine
    orchestrator. Falls back to sane defaults if no Spine context is cached.
    """
    from app.signals.task_card_protocol import TaskCardBuilder
    from app.signals.types import StuckProtocol, WhyThisTask

    task = await _get_user_task_or_404(db, task_id, current_user.id)

    # Try to read cached Spine task-card-protocol payload first
    cached_payload: dict[str, Any] | None = None
    if cache_service.redis is not None:
        try:
            raw = await cache_service.redis.get(f"spine:task_card_protocol:{task.id}")
            if raw:
                import json as _json

                cached_payload = _json.loads(raw if isinstance(raw, str) else raw.decode())
        except Exception:  # noqa: BLE001
            cached_payload = None

    if cached_payload is not None:
        return {"data": cached_payload}

    # Build a default protocol from task fields. Map task type → builder.
    bound_nodes: list[str] = []
    if getattr(task, "knowledge_node_id", None):
        bound_nodes.append(str(task.knowledge_node_id))

    builder_map = {
        TaskType.LEARNING: TaskCardBuilder.for_study,
        TaskType.TRAINING: TaskCardBuilder.for_practice,
        TaskType.ERROR_FIX: TaskCardBuilder.for_practice,
        TaskType.REFLECTION: TaskCardBuilder.for_study,
    }
    builder = builder_map.get(task.task_type, TaskCardBuilder.for_study)

    protocol = builder(
        goal_id=str(task.plan_id) if task.plan_id else "",
        bound_nodes=bound_nodes,
        why=WhyThisTask(
            primary_signal=(task.description or task.title)[:200],
            user_visible_reason=task.title,
        ),
        steps=[],
        stuck_protocol=StuckProtocol(
            escalation_after_min=15,
            hint_strategy="worked_example",
        ),
    )
    # Override task_id to match the live DB row
    protocol.task_id = str(task.id)
    return {"data": protocol.to_dict()}


async def _compute_priority_reasoning_background(
    service: TaskPriorityService,
    *,
    user_id: UUID,
    task_id: UUID,
) -> None:
    try:
        await service.generate_and_cache(user_id=user_id, task_id=task_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to compute priority reasoning for task {}: {}", task_id, exc)


# route-tier: authed
@router.get("/{task_id}/priority-reasoning", response_model=dict[str, Any])
async def get_task_priority_reasoning(
    background_tasks: BackgroundTasks,
    task_id: UUID = Path(..., description="Task ID"),
    refresh: bool = Query(False, description="Force synchronous recomputation"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return structured transparent reasoning for why this task is recommended today."""
    task = await _get_user_task_or_404(db, task_id, current_user.id)
    service = TaskPriorityService(db, cache_service)

    if not refresh:
        cached = await service.get_cached_reasoning(user_id=current_user.id, task=task)
        if cached is not None:
            return {"data": cached}

        background_tasks.add_task(
            _compute_priority_reasoning_background,
            service,
            user_id=current_user.id,
            task_id=task_id,
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "calculating",
                "task_id": str(task_id),
                "retry_after_seconds": 1,
            },
        )

    reasoning = await service.generate_and_cache(user_id=current_user.id, task_id=task_id)
    return {"data": reasoning.model_dump(mode="json")}


# route-tier: authed
@router.get("/{task_id}/documents", response_model=dict[str, Any])
async def list_task_documents(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents explicitly linked to a task."""
    await _get_user_task_or_404(db, task_id, current_user.id)
    links = await task_document_service.list_task_documents(
        db,
        task_id=task_id,
        user_id=current_user.id,
    )
    return {"data": [_serialize_task_document(link, file_record) for link, file_record in links]}


# route-tier: authed
@router.post("/{task_id}/documents", response_model=dict[str, Any])
async def attach_task_document(
    payload: TaskDocumentLinkCreate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach a study document to a task."""
    task = await _get_user_task_or_404(db, task_id, current_user.id)
    try:
        link = await task_document_service.attach_document(
            db,
            task=task,
            file_id=payload.file_id,
            linked_by=payload.linked_by,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await db.commit()
    await focus_context_service.invalidate_for_task(user_id=current_user.id, task_id=task_id)
    links = await task_document_service.list_task_documents(
        db,
        task_id=task_id,
        user_id=current_user.id,
    )
    attached = next((item for item in links if item[0].id == link.id), None)
    if attached is None:
        raise HTTPException(status_code=500, detail="Linked document could not be loaded")
    return {"data": _serialize_task_document(attached[0], attached[1])}


# route-tier: authed
@router.delete("/{task_id}/documents", response_model=dict[str, Any])
async def detach_task_document(
    payload: TaskDocumentUnlinkRequest,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detach a study document from a task."""
    await _get_user_task_or_404(db, task_id, current_user.id)
    removed = await task_document_service.detach_document(
        db,
        task_id=task_id,
        file_id=payload.file_id,
        user_id=current_user.id,
    )
    if not removed:
        raise NotFoundError(message="Task document not found")
    await db.commit()
    await focus_context_service.invalidate_for_task(user_id=current_user.id, task_id=task_id)
    return {"success": True, "task_id": str(task_id), "file_id": str(payload.file_id)}


# route-tier: authed
@router.get("/{task_id}/resources", response_model=dict[str, Any])
async def list_task_resources(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List resources attached to a task."""
    await _get_user_task_or_404(db, task_id, current_user.id)
    result = await db.execute(
        select(TaskResourceLink)
        .where(TaskResourceLink.task_id == task_id, TaskResourceLink.deleted_at.is_(None))
        .order_by(TaskResourceLink.order_index.asc(), TaskResourceLink.created_at.asc())
    )
    resources = result.scalars().all()
    return {"data": [TaskResourceLinkInfo.model_validate(link) for link in resources]}


# route-tier: authed
@router.post("/{task_id}/resources", response_model=dict[str, Any])
async def attach_task_resource(
    payload: TaskResourceLinkCreate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach a seed resource or external reference to a task."""
    await _get_user_task_or_404(db, task_id, current_user.id)
    title, summary, metadata = await _resolve_task_resource_defaults(db, payload, current_user.id)

    order_index = payload.order_index
    if order_index is None:
        max_order_result = await db.execute(
            select(func.max(TaskResourceLink.order_index)).where(
                TaskResourceLink.task_id == task_id,
                TaskResourceLink.deleted_at.is_(None),
            )
        )
        order_index = (max_order_result.scalar() or -1) + 1

    link = TaskResourceLink(
        task_id=task_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        title=title,
        url=payload.url,
        summary=summary,
        resource_metadata=metadata,
        order_index=order_index,
        is_primary=payload.is_primary,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return {"data": TaskResourceLinkInfo.model_validate(link)}


# route-tier: authed
@router.delete("/{task_id}/resources/{link_id}", status_code=204)
async def delete_task_resource(
    task_id: UUID = Path(..., description="Task ID"),
    link_id: UUID = Path(..., description="Task resource link ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an attached resource from a task."""
    await _get_user_task_or_404(db, task_id, current_user.id)
    link = await db.get(TaskResourceLink, link_id)
    if not link or link.task_id != task_id or link.deleted_at is not None:
        raise NotFoundError(message="Task resource not found")
    await link.delete(db, soft=True)
    await db.commit()
    return None


# route-tier: authed
@router.put("/{task_id}", response_model=dict[str, Any])
async def update_task(
    task_in: TaskUpdate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    return {"data": TaskDetail.model_validate(task)}


# route-tier: authed
@router.post("/{task_id}/generate-guide", response_model=dict[str, Any])
async def generate_task_guide(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate or regenerate AI guide for an existing task using fast LLM tier.
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    guidance = await task_guide_service.generate_task_guidance(
        task,
        current_user,
        db,
        audience=TaskGuidanceAudience.HUMAN,
    )
    task.guide_content = guidance.content
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {"data": TaskDetail.model_validate(task)}


# route-tier: authed
@router.get("/{task_id}/guidance", response_model=dict[str, Any])
async def get_task_guidance(
    task_id: UUID = Path(..., description="Task ID"),
    audience: TaskGuidanceAudience = Query(
        default=TaskGuidanceAudience.HUMAN,
        description="Which TaskGuidance sidecar audience to fetch",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a TaskGuidance sidecar object for the requested audience.
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    guidance = await task_guide_service.get_task_guidance(
        task,
        current_user,
        audience=audience,
    )
    if guidance is None:
        raise HTTPException(status_code=404, detail="Task guidance not found")
    return {"data": _serialize_task_guidance(guidance)}


# route-tier: authed
@router.post("/{task_id}/guidance", response_model=dict[str, Any])
async def create_or_refresh_task_guidance(
    task_id: UUID = Path(..., description="Task ID"),
    audience: TaskGuidanceAudience = Query(
        default=TaskGuidanceAudience.HUMAN,
        description="Which TaskGuidance sidecar audience to generate",
    ),
    regenerate: bool = Query(
        default=False,
        description="Whether to force regeneration when a TaskGuidance sidecar already exists",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or regenerate a TaskGuidance sidecar object.
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    if not regenerate:
        existing = await task_guide_service.get_task_guidance(
            task,
            current_user,
            audience=audience,
        )
        if existing is not None:
            return {"data": _serialize_task_guidance(existing)}

    guidance = await task_guide_service.generate_task_guidance(
        task,
        current_user,
        db,
        audience=audience,
    )
    if audience is TaskGuidanceAudience.HUMAN and task.guide_content != guidance.content:
        task.guide_content = guidance.content
        db.add(task)
        await db.commit()
        await db.refresh(task)

    return {"data": _serialize_task_guidance(guidance)}


# route-tier: authed
@router.post("/{task_id}/snooze", response_model=dict[str, Any])
async def snooze_task(
    request: TaskSnoozeRequest | None = None,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    req: Request = None,  # injected by FastAPI for locale detection
):
    """Push one task to a later date without changing the plan structure."""
    task = await _get_user_task_or_404(db, task_id, current_user.id)
    target_date = (request.target_date if request else None) or (
        date.today() + timedelta(days=(request.days if request else 1))
    )
    task.due_date = target_date
    tags = list(task.tags or [])
    if "snoozed" not in tags:
        tags.append("snoozed")
    task.tags = tags
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return _action_response(
        action="snooze",
        message="已推迟到明天，今天先把节奏放轻一点。" if _zh(req) else "Snoozed till tomorrow. Take it easy today.",
        task=task,
    )


# route-tier: authed
@router.post("/{task_id}/stuck", response_model=dict[str, Any])
async def mark_task_stuck(
    request: TaskStuckRequest | None = None,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as stuck and return Aurora's current-context diagnosis."""
    task = await _get_user_task_or_404(db, task_id, current_user.id)
    payload = request or TaskStuckRequest()
    try:
        updated_task, diagnosis = await TaskService.mark_stuck(
            db,
            task,
            stuck_point=payload.stuck_point,
            recent_steps=payload.recent_steps,
            current_step_index=payload.current_step_index,
            elapsed_seconds=payload.elapsed_seconds,
            trigger=payload.trigger,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "success": True,
        "action": "stuck",
        "message": "Aurora 已根据当前任务状态给出诊断。",
        "data": {
            "task": TaskDetail.model_validate(updated_task),
            "diagnosis": diagnosis,
        },
    }


# route-tier: authed
@router.post("/{task_id}/too-hard", response_model=dict[str, Any])
# route-tier: authed
@router.post(
    "/{task_id}/too_hard",
    response_model=dict[str, Any],
    include_in_schema=False,
)
async def mark_task_too_hard(
    request: TaskQuickActionRequest | None = None,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    req: Request = None,  # injected by FastAPI for locale detection
):
    """Break a task into smaller subtasks when the current card feels too hard."""
    task = await _get_user_task_or_404(db, task_id, current_user.id)
    from app.orchestration.adaptive_replanner import AdaptiveReplanner

    replanner = AdaptiveReplanner(db, cache_service.redis)
    subtasks = await replanner.break_down_single_task_for_too_hard(
        user_id=current_user.id,
        task_id=task.id,
        feedback_text=request.reason if request else None,
    )
    await db.commit()
    await db.refresh(task)
    for subtask in subtasks:
        await db.refresh(subtask)

    if subtasks:
        message = (
            f"我把它拆成 {len(subtasks)} 小步了，先做「{subtasks[0].title}」。"
            if _zh(req)
            else f"I broke it into {len(subtasks)} smaller steps. Start with「{subtasks[0].title}」."
        )
    else:
        message = (
            "我知道这张有点硬，先别硬扛；可以直接找 AI 一起拆卡点。"
            if _zh(req)
            else "This one is tough. Don't push through alone — let AI help you break it down."
        )
    return _action_response(
        action="too_hard",
        message=message,
        task=task,
        subtasks=subtasks,
    )


# route-tier: authed
@router.post("/{task_id}/skip", response_model=dict[str, Any])
async def skip_task(
    request: TaskQuickActionRequest | None = None,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hide a task from active surfaces by marking it abandoned as a quick skip."""
    reason = (request.reason if request else None) or "quick_action_skip"
    task = await TaskService.abandon_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
        reason=reason,
    )
    # Note: abandon_task already commits internally. The user_note is set via
    # the reason parameter, avoiding a second commit that would double-transact.
    if task:
        task.user_note = task.user_note or "Skipped from quick action"
    return _action_response(
        action="skip",
        message="已跳过，这张卡不会再挤在今天了。" if _zh(req) else "Skipped — this card won't crowd today anymore.",
        task=task,
    )


# route-tier: authed
@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    await TaskService.delete(db, task)

    return {"success": True}


# route-tier: authed
@router.post("/{task_id}/start", response_model=dict[str, Any])
async def start_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start task (v2.2 修复 - 调用服务层)

    调用 TaskService.start_task() 确保状态同步逻辑被执行
    """
    task = await TaskService.start_task(db=db, task_id=task_id, user_id=current_user.id)

    return {"data": TaskDetail.model_validate(task)}


# route-tier: authed
@router.post("/{task_id}/pause", response_model=dict[str, Any])
async def pause_task(
    task_id: UUID = Path(..., description="Task ID"),
    request: TaskPause | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause task without counting it as success or failure."""
    reason = request.reason if request else None
    try:
        task = await TaskService.pause_task(db=db, task_id=task_id, user_id=current_user.id, reason=reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": TaskDetail.model_validate(task)}


# route-tier: authed
@router.post("/{task_id}/resume", response_model=dict[str, Any])
async def resume_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused or stuck task back to IN_PROGRESS."""
    try:
        task = await TaskService.resume_task(db=db, task_id=task_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"data": TaskDetail.model_validate(task)}


# route-tier: authed
@router.post("/{task_id}/abandon", response_model=dict[str, Any])
async def abandon_task(
    task_id: UUID = Path(..., description="Task ID"),
    request: TaskAbandon | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Abandon task (v2.2 修复 - 发布事件)

    调用 TaskService.abandon_task() 确保:
    - 状态同步
    - 发布 task.abandoned 事件 (用于认知分析)
    """
    reason = request.reason if request else None
    task = await TaskService.abandon_task(db=db, task_id=task_id, user_id=current_user.id, reason=reason)

    try:
        from app.services.task_reflection_service import TaskReflectionService

        time_spent = None
        if task.started_at and task.completed_at:
            time_spent = int((task.completed_at - task.started_at).total_seconds() / 60)
        reflection_service = TaskReflectionService(db, cache_service.redis)
        await reflection_service.create_abandon_feedback_and_prompt(
            user_id=current_user.id,
            task=task,
            reason=reason,
            time_spent_minutes=time_spent,
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to enqueue abandon reflection prompt: {e}")

    return {"data": TaskDetail.model_validate(task)}


# route-tier: authed
@router.post("/{task_id}/complete", response_model=dict[str, Any])
async def complete_task(
    request: TaskCompleteRequest,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
):
    """
    完成任务 (v2.2 增强 - 修复事件发布)

    调用 TaskService.complete_task() 确保以下功能完整执行:
    - 任务状态更新
    - 计划进度更新 (PlanService.update_progress)
    - 任务状态同步 (TaskStateSyncService)
    - 发布 task.completed 事件 (触发 AdaptiveReplanner)
    - Galaxy Spark 点亮
    """
    start_time = time.perf_counter()

    # 幂等性检查: 查询任务当前状态
    existing_task = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
    task = existing_task.scalar_one_or_none()

    if not task:
        record_product_loop_event("task_execution", "task_complete", "not_found", "missing_task")
        observe_product_loop_latency("task_execution", "task_complete", "not_found", time.perf_counter() - start_time)
        raise NotFoundError(message="Task not found")

    if task.status == TaskStatus.COMPLETED:
        record_product_loop_event("task_execution", "task_complete", "already_completed", "idempotent")
        observe_product_loop_latency(
            "task_execution", "task_complete", "already_completed", time.perf_counter() - start_time
        )
        return {
            "success": True,
            "data": {
                "task": TaskDetail.model_validate(task),
            },
            "message": "Task already completed",
            "retry_token": x_idempotency_key or "generated-token",
        }

    # 🔥 关键修复: 调用 TaskService.complete_task() 而非直接操作数据库
    # 这确保了 task.completed 事件被发布，从而触发 AdaptiveReplanner
    actual_minutes = request.actual_minutes or task.estimated_minutes or 15
    task = await TaskService.complete_task(
        db=db, task_id=task_id, user_id=current_user.id, actual_minutes=actual_minutes, note=request.note
    )

    # 以下逻辑由 TaskService.complete() 已处理，无需重复:
    # - plan_update (已包含在 TaskService.complete 中)
    # - galaxy spark (已包含在 TaskService.complete 中)
    # - task completion event (已发布)

    feedback = {}
    try:
        feedback = await feedback_service.generate_feedback(task, current_user, db)
    except Exception as e:
        logger.warning(f"Failed to generate feedback: {e}")

    # 获取 galaxy update 信息 (TaskService.complete 中已执行 spark，这里查询结果)
    galaxy_update = None
    if task.knowledge_node_id:
        try:
            from app.models.knowledge import UserNodeStatus
            from app.services.galaxy_service import GalaxyService

            GalaxyService(db)
            node_status = await db.execute(
                select(UserNodeStatus).where(
                    UserNodeStatus.user_id == current_user.id, UserNodeStatus.node_id == task.knowledge_node_id
                )
            )
            status_obj = node_status.scalar_one_or_none()
            if status_obj:
                galaxy_update = {
                    "node_id": str(task.knowledge_node_id),
                    "new_mastery": status_obj.mastery_level,
                    "next_review_at": status_obj.next_review_at.isoformat() if status_obj.next_review_at else None,
                }
        except Exception as e:
            logger.warning(f"Failed to get galaxy update: {e}")

    # Generate Next Steps
    next_actions = []
    try:
        from app.services.next_step_service import next_step_service

        next_actions = await next_step_service.suggest_next_actions(completed_task=task, user=current_user, db=db)
    except Exception as e:
        logger.warning(f"Failed to generate next actions: {e}")

    # ========== Achievement Integration ==========
    unlocked_achievements = []
    try:
        from app.services.achievement_engine import AchievementEngine, AchievementEvent

        achievement_engine = AchievementEngine(db)
        unlocked = await achievement_engine.process_event(
            user_id=str(current_user.id),
            event_type=AchievementEvent.TASK_COMPLETED,
            task_id=str(task.id),
            actual_minutes=actual_minutes,
            estimated_minutes=task.estimated_minutes,
            difficulty=task.difficulty if hasattr(task, "difficulty") else None,
        )

        if unlocked:
            unlocked_achievements = unlocked
            next_actions.append({"type": "achievement_unlocked", "achievements": unlocked})
            logger.info(f"User {current_user.id} unlocked {len(unlocked)} achievements on task completion")
    except Exception as e:
        logger.warning(f"Achievement processing failed: {e}")
    # ============================================

    # ========== Contract Progress Integration ==========
    try:
        from app.services.achievement_engine import ContractService

        contract_service = ContractService(db)
        await contract_service.update_daily_progress(
            str(current_user.id),
            actual_minutes,
        )
    except Exception as e:
        logger.warning(f"Contract progress update failed: {e}")
    # ============================================

    record_product_loop_event("task_execution", "task_complete", "completed", "user_action")
    observe_product_loop_latency("task_execution", "task_complete", "completed", time.perf_counter() - start_time)

    # 返回数据
    return {
        "success": True,
        "data": {
            "task": TaskDetail.model_validate(task),
            # Mock update data for MVP
            "flame_update": {
                "level_before": 3,
                "level_after": 3,
                "brightness_change": 5 + feedback.get("flame_bonus", 0),
            },
            "stats_update": {"today_completed": 5, "streak_days": 7},
            "feedback": feedback.get("content"),
            "plan_update": None,  # TaskService.complete 中已处理，无需重复返回
            "galaxy_update": galaxy_update or feedback.get("galaxy_update"),
            "unlocked_achievements": unlocked_achievements,
        },
        "next_actions": [action.model_dump() if hasattr(action, "model_dump") else action for action in next_actions],
        # 🆕 v2.1: 重试令牌 (在这里简单返回 key 或 生成一个新的 token)
        "retry_token": x_idempotency_key or "generated-token",
    }


# route-tier: authed
@router.post("/confirm-batch/{tool_result_id}", response_model=dict[str, Any])
async def confirm_generated_tasks(
    tool_result_id: str = Path(..., description="Tool result ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    确认 AI 生成的一批任务 (P0.1 修复)
    """
    from app.services.task_service import TaskService

    tasks = await TaskService.confirm_tasks_by_tool_result(db, tool_result_id, current_user.id)
    return {"success": True, "count": len(tasks), "data": [TaskDetail.model_validate(t) for t in tasks]}


# ========== Task Feedback Endpoints ==========


# route-tier: authed
@router.post("/{task_id}/feedback", response_model=TaskFeedbackSubmitResponse)
async def submit_task_feedback(
    feedback_in: TaskFeedbackCreate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    提交任务反馈（v2.1 增强）

    - 验证任务所有权
    - 验证任务状态（必须是COMPLETED）
    - 支持重复提交（更新现有反馈）
    - 自动推断并更新用户偏好
    - 返回偏好更新详情
    """
    from app.services.task_feedback_service import TaskFeedbackService

    service = TaskFeedbackService(db, cache_service.redis)

    try:
        feedback, reflection_prompt = await service.submit_feedback(
            user_id=current_user.id,
            task_id=task_id,
            completion_quality=feedback_in.completion_quality,
            feedback_text=feedback_in.feedback_text,
            category=feedback_in.category,
            stuck_point=feedback_in.stuck_point,
            effective_method=feedback_in.effective_method,
            adjustment_intention=feedback_in.adjustment_intention,
        )

        # 构建偏好更新详情
        preference_updates = None
        if feedback.inferred_depth_delta is not None or feedback.inferred_difficulty_delta is not None:
            preference_updates = {
                "depth_preference": feedback.inferred_depth_delta,
                "difficulty_preference": feedback.inferred_difficulty_delta,
            }

        return TaskFeedbackSubmitResponse(
            success=True,
            message="偏好已更新" if preference_updates else "反馈已提交",
            data=TaskFeedbackResponse.model_validate(feedback),
            preference_updates=preference_updates,
            reflection_prompt=reflection_prompt,
            reflection_payload=feedback.reflection_payload,
            ai_response=(
                feedback.reflection_payload.get("ai_response")
                if isinstance(feedback.reflection_payload, dict)
                else None
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post(
    "/feedback/{feedback_id}/reflection",
    response_model=ReflectionAnswerResponse,
)
async def submit_task_reflection_answer(
    reflection_in: ReflectionAnswerCreate,
    feedback_id: UUID = Path(..., description="Task feedback ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交任务反思答案，并回流认知棱镜。"""
    from app.services.task_reflection_service import TaskReflectionService

    service = TaskReflectionService(db, cache_service.redis)
    try:
        reflection_payload = await service.submit_reflection_answer(
            user_id=current_user.id,
            feedback_id=feedback_id,
            selected_option=reflection_in.selected_option,
            free_text=reflection_in.free_text,
            stuck_point=reflection_in.stuck_point,
            effective_method=reflection_in.effective_method,
            adjustment_intention=reflection_in.adjustment_intention,
        )
        await db.commit()
        return ReflectionAnswerResponse(
            success=True,
            message=reflection_payload.get("ai_response") or "谢谢你的反馈，我会据此优化后续计划。",
            reflection_payload=reflection_payload,
            ai_response=reflection_payload.get("ai_response"),
            memory_id=reflection_payload.get("memory_id"),
            linked_knowledge_nodes=reflection_payload.get("linked_knowledge_nodes"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# route-tier: authed
@router.get("/{task_id}/feedback", response_model=dict[str, Any])
async def get_task_feedback(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务的反馈历史

    返回该任务的所有反馈记录（按创建时间倒序）
    """
    from app.services.task_feedback_service import TaskFeedbackService

    # 验证任务所有权
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError(message="Task not found")

    service = TaskFeedbackService(db)
    feedbacks = await service.get_task_feedbacks(task_id)

    return {
        "success": True,
        "data": [TaskFeedbackResponse.model_validate(f) for f in feedbacks],
        "total": len(feedbacks),
    }


# route-tier: authed
@router.get("/feedback/stats", response_model=dict[str, Any])
async def get_user_feedback_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取当前用户的任务反馈统计

    Returns:
        - total_feedbacks: 总反馈数
        - avg_completion_quality: 平均完成质量评分
        - category_distribution: 反馈分类分布
        - recent_feedbacks: 最近的反馈记录
    """
    from app.services.task_feedback_service import TaskFeedbackService

    service = TaskFeedbackService(db)
    stats = await service.get_user_task_feedback_stats(current_user.id)

    return {
        "success": True,
        "data": {
            "total_feedbacks": stats["total_feedbacks"],
            "avg_completion_quality": stats["avg_completion_quality"],
            "category_distribution": stats["category_distribution"],
            "recent_feedbacks": [TaskFeedbackResponse.model_validate(f) for f in stats["recent_feedbacks"]],
        },
    }


# route-tier: authed
@router.post("/{task_id}/next-action-selection", response_model=dict[str, Any])
async def record_next_action_selection(
    selection_in: NextActionSelectionCreate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    记录用户对next_action的选择行为

    用于追踪用户对next_action建议的交互，从而学习用户偏好。

    Args:
        task_id: 任务ID
        selection_in: 选择数据

    Returns:
        记录结果
    """
    from app.services.next_action_selection_service import NextActionSelectionService

    # 验证task_id匹配
    if selection_in.task_id != task_id:
        raise HTTPException(status_code=400, detail="task_id in path does not match task_id in body")

    service = NextActionSelectionService(db, cache_service.redis)

    try:
        selection = await service.record_selection(
            user_id=current_user.id,
            task_id=selection_in.task_id,
            action_type=selection_in.action_type,
            action_title=selection_in.action_title,
            selected=selection_in.selected,
            skipped=selection_in.skipped,
            display_position=selection_in.display_position,
            displayed_actions_count=selection_in.displayed_actions_count,
            context=selection_in.context,
        )
        return {"success": True, "data": selection.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
