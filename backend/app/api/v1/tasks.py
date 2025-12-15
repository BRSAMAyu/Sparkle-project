"""
Tasks API Endpoints
"""
from typing import Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCompleteRequest, TaskDetail

router = APIRouter()

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
    
    # 返回数据
    return {
        "success": True,
        "data": {
            "task": TaskDetail.model_validate(task),
            # Mock update data for MVP
            "flame_update": {
                "level_before": 3,
                "level_after": 3,
                "brightness_change": 5
            },
            "stats_update": {
                "today_completed": 5,
                "streak_days": 7
            }
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
