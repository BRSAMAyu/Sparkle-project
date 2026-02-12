"""
Subtasks API Endpoints
"""
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.task import SubTask, SubTaskStatus, Task
from app.models.user import User
from app.schemas.task import SubTaskCreate, SubTaskDetail, SubTaskReorderRequest, SubTaskUpdate

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _verify_task_ownership(task_id: UUID, user_id: int, db: AsyncSession) -> Task:
    """Verify that the task exists and belongs to the user"""
    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.user_id == user_id
            )
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError(message="Task not found")
    return task


@router.get("/tasks/{task_id}/subtasks", response_model=list[SubTaskDetail])
async def get_subtasks(
    task_id: UUID = Path(..., description="Parent task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all subtasks for a task
    """
    # Verify task ownership
    await _verify_task_ownership(task_id, current_user.id, db)

    # Get subtasks ordered by order field
    result = await db.execute(
        select(SubTask)
        .where(SubTask.parent_task_id == task_id)
        .order_by(SubTask.order)
    )
    subtasks = result.scalars().all()

    return [SubTaskDetail.model_validate(st) for st in subtasks]


@router.post("/tasks/{task_id}/subtasks", response_model=dict[str, Any])
async def create_subtask(
    subtask_in: SubTaskCreate,
    task_id: UUID = Path(..., description="Parent task ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subtask
    """
    # Verify task ownership
    task = await _verify_task_ownership(task_id, current_user.id, db)

    # Get the next order value if not provided
    if subtask_in.order is None or subtask_in.order == 0:
        result = await db.execute(
            select(SubTask)
            .where(SubTask.parent_task_id == task_id)
            .order_by(desc(SubTask.order))
            .limit(1)
        )
        last_subtask = result.scalar_one_or_none()
        next_order = (last_subtask.order + 1) if last_subtask else 0
    else:
        next_order = subtask_in.order

    subtask = SubTask(
        parent_task_id=task_id,
        title=subtask_in.title,
        description=subtask_in.description,
        order=next_order,
        status=SubTaskStatus.PENDING
    )

    db.add(subtask)
    await db.commit()
    await db.refresh(subtask)

    return {
        "data": SubTaskDetail.model_validate(subtask),
        "parent_task_subtotals": {
            "total": task.subtasks_total,
            "completed": task.subtasks_completed
        }
    }


@router.put("/subtasks/{subtask_id}", response_model=dict[str, Any])
async def update_subtask(
    subtask_in: SubTaskUpdate,
    subtask_id: UUID = Path(..., description="Subtask ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a subtask
    """
    # Get subtask
    result = await db.execute(
        select(SubTask).where(SubTask.id == subtask_id)
    )
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise NotFoundError(message="Subtask not found")

    # Verify parent task ownership
    await _verify_task_ownership(subtask.parent_task_id, current_user.id, db)

    # Update fields
    update_data = subtask_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subtask, field, value)

    # Set completed_at when status changes to COMPLETED
    if subtask_in.status == SubTaskStatus.COMPLETED and subtask.completed_at is None:
        subtask.completed_at = _utcnow()
    elif subtask_in.status and subtask_in.status != SubTaskStatus.COMPLETED:
        subtask.completed_at = None

    await db.commit()
    await db.refresh(subtask)

    # Get updated parent task for subtotals
    parent_result = await db.execute(
        select(Task).where(Task.id == subtask.parent_task_id)
    )
    parent_task = parent_result.scalar_one()

    return {
        "data": SubTaskDetail.model_validate(subtask),
        "parent_task_subtotals": {
            "total": parent_task.subtasks_total,
            "completed": parent_task.subtasks_completed
        }
    }


@router.delete("/subtasks/{subtask_id}")
async def delete_subtask(
    subtask_id: UUID = Path(..., description="Subtask ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a subtask
    """
    # Get subtask
    result = await db.execute(
        select(SubTask).where(SubTask.id == subtask_id)
    )
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise NotFoundError(message="Subtask not found")

    # Store parent task ID for response
    parent_task_id = subtask.parent_task_id

    # Verify parent task ownership
    task = await _verify_task_ownership(parent_task_id, current_user.id, db)

    await db.delete(subtask)
    await db.commit()

    return {
        "success": True,
        "parent_task_subtotals": {
            "total": task.subtasks_total,
            "completed": task.subtasks_completed
        }
    }


@router.post("/subtasks/reorder", response_model=dict[str, Any])
async def reorder_subtasks(
    request: SubTaskReorderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reorder subtasks in bulk
    """
    # Get all subtask IDs from request
    subtask_ids = [item.get("subtask_id") for item in request.subtask_orders]

    # Verify all subtasks exist and belong to the same user
    subtasks_result = await db.execute(
        select(SubTask).where(SubTask.id.in_(subtask_ids))
    )
    subtasks = subtasks_result.scalars().all()

    if len(subtasks) != len(subtask_ids):
        raise HTTPException(status_code=400, detail="One or more subtasks not found")

    # Verify all subtasks belong to the same parent task owned by user
    parent_task_id = subtasks[0].parent_task_id
    for subtask in subtasks:
        if subtask.parent_task_id != parent_task_id:
            raise HTTPException(status_code=400, detail="Subtasks must belong to the same parent task")

    await _verify_task_ownership(parent_task_id, current_user.id, db)

    # Update order for each subtask
    for item in request.subtask_orders:
        subtask_id = item.get("subtask_id")
        new_order = item.get("order")
        if subtask_id and new_order is not None:
            # Find the subtask in our fetched list
            for subtask in subtasks:
                if subtask.id == subtask_id:
                    subtask.order = new_order
                    break

    await db.commit()

    return {"success": "Subtasks reordered successfully"}
