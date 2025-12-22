"""
Tasks API Endpoints
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path, Header, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskDetail, TaskCompleteRequest, 
    TaskStart, TaskAbandon, TaskSummary
)
from app.services.task_guide_service import task_guide_service
from app.services.feedback_service import feedback_service

router = APIRouter()

@router.get("", response_model=Dict[str, Any])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    type: Optional[TaskType] = Query(None, description="Filter by type"),
    plan_id: Optional[UUID] = Query(None, description="Filter by plan ID"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
        pass # Tag filtering implementation pending DB specific JSON operators

    # Order by created_at desc
    query = query.order_by(desc(Task.created_at))
    
    # Pagination
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "data": [TaskDetail.model_validate(t) for t in tasks],
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }

@router.post("", response_model=Dict[str, Any])
async def create_task(
    task_in: TaskCreate,
    generate_guide: bool = Query(False, description="Whether to auto-generate guide"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task
    """
    task = Task(
        user_id=current_user.id,
        title=task_in.title,
        type=task_in.type,
        plan_id=task_in.plan_id,
        tags=task_in.tags,
        estimated_minutes=task_in.estimated_minutes,
        difficulty=task_in.difficulty,
        energy_cost=task_in.energy_cost,
        priority=task_in.priority,
        due_date=task_in.due_date,
        guide_content=task_in.guide_content,
        status=TaskStatus.PENDING
    )
    
    if generate_guide and not task.guide_content:
        # Call guide generation service
        guide = await task_guide_service.generate_guide(task, current_user, db)
        task.guide_content = guide
        
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task details
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return {"data": TaskDetail.model_validate(task)}

@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_in: TaskUpdate,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await db.delete(task)
    await db.commit()
    
    return {"success": True}

@router.post("/{task_id}/start", response_model=Dict[str, Any])
async def start_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = TaskStatus.IN_PROGRESS
    task.started_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.post("/{task_id}/abandon", response_model=Dict[str, Any])
async def abandon_task(
    request: TaskAbandon,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Abandon task
    """
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = TaskStatus.ABANDONED
    task.user_note = request.reason # Store reason in user_note or separate field if available
    
    await db.commit()
    await db.refresh(task)
    
    return {"data": TaskDetail.model_validate(task)}

@router.post("/{task_id}/complete", response_model=Dict[str, Any])
async def complete_task(
    request: TaskCompleteRequest,
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key")
):
    """
    完成任务 (v2.1 增强)
    """
    # 查找任务
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 更新状态
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    task.actual_minutes = request.actual_minutes
    task.user_note = request.note
    # request.completion_quality is used for stats, ignored in model for now if not in schema
    
    await db.commit()
    await db.refresh(task)
    
    # 🆕 Generate AI Feedback
    feedback = await feedback_service.generate_feedback(task, current_user, db)

    # 返回数据
    return {
        "success": True,
        "data": {
            "task": TaskDetail.model_validate(task),
            # Mock update data for MVP
            "flame_update": {
                "level_before": 3,
                "level_after": 3,
                "brightness_change": 5 + feedback.get("flame_bonus", 0)
            },
            "stats_update": {
                "today_completed": 5,
                "streak_days": 7
            },
            "feedback": feedback.get("content"),
            "galaxy_update": feedback.get("galaxy_update")
        },
        # 🆕 v2.1: 重试令牌 (在这里简单返回 key 或 生成一个新的 token)
        "retry_token": x_idempotency_key or "generated-token"
    }

# Skeleton for other endpoints
@router.get("", response_model=Dict[str, Any])
async def list_tasks():
    return {"data": []}

@router.post("", response_model=Dict[str, Any])
async def create_task():
    return {"data": {}}
