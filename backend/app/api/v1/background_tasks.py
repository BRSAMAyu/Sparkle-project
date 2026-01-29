"""
Background Tasks API Endpoints
"""
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.background_task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType
from app.models.user import User

router = APIRouter()


@router.get("", response_model=dict[str, Any])
async def get_background_tasks(
    status: BackgroundTaskStatus | None = Query(None, description="Filter by status"),
    task_type: BackgroundTaskType | None = Query(None, description="Filter by task type"),
    limit: int = Query(20, ge=1, le=100, description="Limit results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get background tasks for the current user
    """
    query = select(BackgroundTask).where(BackgroundTask.user_id == current_user.id)

    if status:
        query = query.where(BackgroundTask.status == status)
    if task_type:
        query = query.where(BackgroundTask.task_type == task_type)

    # Order by created_at desc, limit to recent tasks
    query = query.order_by(desc(BackgroundTask.created_at)).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "data": [task.to_dict() for task in tasks],
        "count": len(tasks),
    }


@router.get("/{task_id}", response_model=dict[str, Any])
async def get_background_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific background task
    """
    result = await db.execute(
        select(BackgroundTask).where(
            and_(
                BackgroundTask.id == task_id,
                BackgroundTask.user_id == current_user.id
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Background task not found")

    return {"data": task.to_dict()}


@router.post("/{task_id}/retry", response_model=dict[str, Any])
async def retry_background_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry a failed background task
    """
    result = await db.execute(
        select(BackgroundTask).where(
            and_(
                BackgroundTask.id == task_id,
                BackgroundTask.user_id == current_user.id
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Background task not found")

    if task.status != BackgroundTaskStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail="Only failed tasks can be retried"
        )

    # Reset the task status to pending
    task.status = BackgroundTaskStatus.PENDING
    task.error_message = None
    task.progress = 0.0

    await db.commit()
    await db.refresh(task)

    # TODO: Trigger the actual retry logic here (e.g., re-queue to Celery)

    return {
        "data": task.to_dict(),
        "message": "Task has been queued for retry"
    }


@router.post("/{task_id}/cancel", response_model=dict[str, Any])
async def cancel_background_task(
    task_id: UUID = Path(..., description="Task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running or pending background task
    """
    result = await db.execute(
        select(BackgroundTask).where(
            and_(
                BackgroundTask.id == task_id,
                BackgroundTask.user_id == current_user.id
            )
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Background task not found")

    if task.status not in [BackgroundTaskStatus.PENDING, BackgroundTaskStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail="Only pending or running tasks can be cancelled"
        )

    # Update task status
    task.status = BackgroundTaskStatus.CANCELLED
    task.progress_message = "Task was cancelled by user"

    await db.commit()
    await db.refresh(task)

    # TODO: If task has external_task_id, cancel the external job (e.g., Celery)

    return {
        "data": task.to_dict(),
        "message": "Task cancelled successfully"
    }


@router.get("/stats/summary", response_model=dict[str, Any])
async def get_background_task_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics of background tasks
    """
    # Count tasks by status
    stats = {}

    for status in BackgroundTaskStatus:
        await db.execute(
            select(BackgroundTask)
            .where(
                and_(
                    BackgroundTask.user_id == current_user.id,
                    BackgroundTask.status == status
                )
            ).count()
        )
        count = await db.scalar(select(BackgroundTask).where(
            and_(
                BackgroundTask.user_id == current_user.id,
                BackgroundTask.status == status
            )
        ).count())
        stats[status.value] = count

    # Get recently completed tasks (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_result = await db.execute(
        select(BackgroundTask)
        .where(
            and_(
                BackgroundTask.user_id == current_user.id,
                BackgroundTask.status == BackgroundTaskStatus.COMPLETED,
                BackgroundTask.completed_at >= yesterday
            )
        ).count()
    )
    recent_completed = recent_result.scalar() or 0

    return {
        "stats": stats,
        "recent_completed_24h": recent_completed,
    }
