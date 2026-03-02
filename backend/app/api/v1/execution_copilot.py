from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import cache_service
from app.db.session import get_db
from app.models.user import User
from app.services.execution_copilot_service import ExecutionCopilotService

router = APIRouter(prefix="/execution", tags=["execution"])


class CheckpointEventRequest(BaseModel):
    status: str = Field(pattern="^(done|skipped)$")
    task_id: str | None = None
    note: str | None = None


@router.get("/copilot/{plan_id}")
async def get_execution_copilot(
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionCopilotService(db, redis=cache_service.redis)
    data = await service.build_copilot(
        user_id=current_user.id,
        plan_id=plan_id,
        limit=3,
    )
    return {
        "success": True,
        "message": "Execution copilot generated",
        "data": data,
    }


@router.post("/copilot/{plan_id}/checkpoint")
async def post_execution_checkpoint(
    payload: CheckpointEventRequest,
    plan_id: UUID = Path(..., description="Plan ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionCopilotService(db, redis=cache_service.redis)
    result = await service.record_checkpoint_event(
        user_id=current_user.id,
        plan_id=plan_id,
        status=payload.status,
        task_id=payload.task_id,
        note=payload.note,
    )
    return {
        "success": bool(result.get("success")),
        "message": "Execution checkpoint tracked" if result.get("success") else "Execution checkpoint rejected",
        "data": result,
    }


@router.get("/copilot/{plan_id}/timeline")
async def get_execution_copilot_timeline(
    plan_id: UUID = Path(..., description="Plan ID"),
    days: int = Query(default=7, ge=7, le=14, description="Timeline window days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutionCopilotService(db, redis=cache_service.redis)
    data = await service.build_timeline(
        user_id=current_user.id,
        plan_id=plan_id,
        days=days,
    )
    return {
        "success": True,
        "message": "Execution timeline generated",
        "data": data,
    }
