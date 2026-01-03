"""
Plans API Endpoints - Full CRUD operations
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus
from app.schemas.plan import (
    PlanCreate, PlanUpdate, PlanDetail, PlanProgress, PlanBase
)
from app.services.plan_service import PlanService
from app.core.exceptions import NotFoundError, AuthorizationError

router = APIRouter()


@router.get("", response_model=Dict[str, Any])
async def list_plans(
    type: Optional[PlanType] = Query(None, description="Filter by plan type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
    query = query.order_by(desc(Plan.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size)

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
        "pages": (total + page_size - 1) // page_size
    }


@router.post("", response_model=PlanDetail, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_in: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new plan
    """
    plan = await PlanService.create(
        db=db,
        obj_in=plan_in,
        user_id=current_user.id
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
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": 0,
        "created_at": plan.created_at,
    }


@router.get("/{plan_id}", response_model=PlanDetail)
async def get_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get plan details by ID
    """
    plan = await PlanService.get_by_id(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

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
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": completed_count,
        "created_at": plan.created_at,
    }


@router.patch("/{plan_id}", response_model=PlanDetail)
async def update_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    plan_in: PlanUpdate = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update plan details
    """
    plan = await PlanService.get_by_id(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

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
        "user_id": plan.user_id,
        "task_count": task_count,
        "completed_task_count": completed_count,
        "created_at": plan.created_at,
    }


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (archive) a plan by setting is_active to False
    """
    plan = await PlanService.get_by_id(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

    # Archive instead of hard delete
    plan.is_active = False
    db.add(plan)
    await db.commit()


@router.get("/{plan_id}/progress", response_model=PlanProgress)
async def get_plan_progress(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed progress information for a plan
    """
    plan = await PlanService.get_by_id(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )

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


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_plans_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics for all user plans
    """
    total_query = select(func.count(Plan.id)).where(Plan.user_id == current_user.id)
    total = (await db.execute(total_query)).scalar() or 0

    active_query = select(func.count(Plan.id)).where(
        and_(Plan.user_id == current_user.id, Plan.is_active == True)
    )
    active = (await db.execute(active_query)).scalar() or 0

    sprint_query = select(func.count(Plan.id)).where(
        and_(Plan.user_id == current_user.id, Plan.type == PlanType.SPRINT)
    )
    sprint_plans = (await db.execute(sprint_query)).scalar() or 0

    growth_query = select(func.count(Plan.id)).where(
        and_(Plan.user_id == current_user.id, Plan.type == PlanType.GROWTH)
    )
    growth_plans = (await db.execute(growth_query)).scalar() or 0

    return {
        "total": total,
        "active": active,
        "sprint_plans": sprint_plans,
        "growth_plans": growth_plans
    }
