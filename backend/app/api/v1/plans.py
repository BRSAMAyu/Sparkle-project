"""
Plans API Endpoints - Full CRUD operations
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.core.exceptions import QuotaExceededError
from app.db.session import get_db
from app.models.plan import Plan, PlanType
from app.models.plan_state import PlanStateStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.plan import (
    PlanCreate,
    PlanDetail,
    PlanPriorityUpdate,
    PlanProgress,
    PlanQuotaStatus,
    PlanUpdate,
    SetPrimaryPlanRequest,
)
from app.services.plan_quota_service import PlanQuotaService
from app.services.plan_service import PlanService
from app.services.plan_state_service import PlanStateService
from app.services.state_notification_service import state_notification_service

router = APIRouter()


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

    # Enrich with task counts
    plans_data = []
    for plan in plans:
        task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
        task_count = (await db.execute(task_query)).scalar() or 0

        completed_query = select(func.count(Task.id)).where(
            and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
        )
        completed_count = (await db.execute(completed_query)).scalar() or 0

        plan_dict = {
            "id": plan.id,
            "name": plan.name,
            "type": plan.type.value,
            "description": plan.description,
            "subject": plan.subject,
            "target_date": plan.target_date,
            "progress": plan.progress,
            "mastery_level": plan.mastery_level,
            "is_active": plan.is_active,
            "priority": plan.priority.value if plan.priority else "normal",
            "is_primary": plan.is_primary if hasattr(plan, "is_primary") else False,
            "task_count": task_count,
            "completed_task_count": completed_count,
            "created_at": plan.created_at,
        }
        plans_data.append(plan_dict)

    return {
        "data": plans_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


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

    return {
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
        "plan_stage": plan.plan_stage.value if plan.plan_stage else "daily",
        "priority": plan.priority.value if plan.priority else "normal",
        "is_primary": plan.is_primary if hasattr(plan, "is_primary") else False,
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": 0,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


@router.get("/{plan_id}", response_model=PlanDetail)
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

    # Get task counts
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0

    completed_query = select(func.count(Task.id)).where(
        and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
    )
    completed_count = (await db.execute(completed_query)).scalar() or 0

    return {
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
        "plan_stage": plan.plan_stage.value if plan.plan_stage else "daily",
        "priority": plan.priority.value if plan.priority else "normal",
        "is_primary": plan.is_primary if hasattr(plan, "is_primary") else False,
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": completed_count,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


@router.patch("/{plan_id}", response_model=PlanDetail)
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

    return {
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
        "plan_stage": plan.plan_stage.value if plan.plan_stage else "daily",
        "priority": plan.priority.value if plan.priority else "normal",
        "is_primary": plan.is_primary if hasattr(plan, "is_primary") else False,
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": completed_count,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.post("/{plan_id}/archive", response_model=dict[str, Any])
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
        daily_first_reward = None
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


@router.post("/{plan_id}/restore", response_model=dict[str, Any])
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


@router.get("/{plan_id}/progress", response_model=PlanProgress)
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
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "type": plan.type.value,
            "description": plan.description,
            "subject": plan.subject,
            "target_date": plan.target_date,
            "progress": plan.progress,
            "priority": plan.priority.value if plan.priority else "normal",
            "is_primary": True,
            "task_count": task_count,
            "completed_task_count": completed_count,
            "created_at": plan.created_at,
        }
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


@router.patch("/{plan_id}/priority", response_model=dict[str, Any])
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

    plans_data = []
    for plan in plans:
        task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
        task_count = (await db.execute(task_query)).scalar() or 0

        completed_query = select(func.count(Task.id)).where(
            and_(Task.plan_id == plan.id, Task.status == TaskStatus.COMPLETED)
        )
        completed_count = (await db.execute(completed_query)).scalar() or 0

        plans_data.append(
            {
                "id": plan.id,
                "name": plan.name,
                "type": plan.type.value,
                "description": plan.description,
                "subject": plan.subject,
                "target_date": plan.target_date,
                "progress": plan.progress,
                "priority": plan.priority.value if plan.priority else "normal",
                "task_count": task_count,
                "completed_task_count": completed_count,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
            }
        )

    return {"data": plans_data, "total": len(plans_data), "page": page, "page_size": page_size}


@router.get("/{plan_id}/learning-path-progress")
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

    from app.models.galaxy import KnowledgeNode, UserNodeStatus
    from sqlalchemy import or_

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
                "mastery": mastery_score,
                "is_target": is_target,
            }
        )

    overall_progress = mastered_count / len(path_node_ids) if path_node_ids else 0.0

    target_node_data = None
    if target_node_id:
        target_node = nodes.get(str(target_node_id))
        target_status = user_statuses.get(str(target_node_id))
        if target_node:
            target_node_data = {
                "id": str(target_node_id),
                "name": target_node.name,
                "mastery": target_status.mastery_score if target_status else 0,
            }

    return {
        "target_node": target_node_data,
        "nodes": nodes_progress,
        "overall_progress": overall_progress,
    }
