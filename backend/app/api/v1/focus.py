"""
专注模式 API
Focus API - 番茄钟、统计、LLM辅助
"""
from __future__ import annotations
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.focus import FocusStatus, FocusType
from app.models.user import User
from app.services.focus_service import focus_service

router = APIRouter()

# ============ Schemas ============

class FocusSessionLog(BaseModel):
    task_id: UUID | None = None
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    focus_type: str = "pomodoro"
    status: str = "completed"

class FocusStats(BaseModel):
    total_minutes: int
    pomodoro_count: int
    today_date: str

class LLMGuideRequest(BaseModel):
    task_id: UUID | None = None
    task_context: str
    user_input: str

class LLMBreakdownRequest(BaseModel):
    task_title: str
    task_description: str | None = ""

# ============ Endpoints ============

@router.post("/sessions", summary="记录专注会话")
async def log_focus_session(
    data: FocusSessionLog,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    客户端完成专注（或中断）后调用此接口记录数据，并获取奖励反馈（火苗增长）
    """
    try:
        result = await focus_service.log_session(
            db,
            current_user.id,
            data.task_id,
            data.start_time,
            data.end_time,
            data.duration_minutes,
            FocusType(data.focus_type),
            FocusStatus(data.status)
        )

        rewards = result["rewards"]

        return {
            "success": True,
            "id": result["session_id"],
            "rewards": rewards, # {flame_earned, leveled_up, new_level}
            "unlocked_achievements": result.get("unlocked_achievements", []),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats", response_model=FocusStats, summary="获取今日专注统计")
async def get_focus_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await focus_service.get_today_stats(db, current_user.id)

@router.post("/llm/guide", summary="获取LLM方法论指导")
async def get_llm_guide(
    data: LLMGuideRequest,
    current_user: User = Depends(get_current_user),
):
    """
    User asks for help/hint during focus mode.
    """
    response = await focus_service.get_methodological_guidance(
        data.task_context,
        data.user_input
    )
    return {"content": response}

@router.post("/llm/breakdown", summary="获取任务拆解建议")
async def get_llm_breakdown(
    data: LLMBreakdownRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Break down a task into subtasks
    """
    subtasks = await focus_service.breakdown_task_via_llm(
        data.task_title,
        data.task_description
    )
    return {"subtasks": subtasks}


# ============ Statistics Endpoints ============

@router.get("/stats/weekly", summary="获取本周专注统计")
async def get_weekly_focus_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get focus statistics for the current week"""
    return await focus_service.get_weekly_stats(db, current_user.id)


@router.get("/stats/monthly", summary="获取本月专注统计")
async def get_monthly_focus_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get focus statistics for the current month"""
    return await focus_service.get_monthly_stats(db, current_user.id)


@router.get("/sessions/history", summary="获取专注会话历史")
async def get_focus_session_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated history of focus sessions"""
    return await focus_service.get_session_history(
        db, current_user.id, limit, offset
    )


@router.get("/stats/heatmap", summary="获取专注热力图数据")
async def get_focus_heatmap(
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get heatmap data for the last N days"""
    return await focus_service.get_heatmap_data(db, current_user.id, days)


@router.get("/sessions", summary="获取专注会话列表")
async def get_focus_sessions(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of focus sessions (alias for /sessions/history)"""
    return await focus_service.get_session_history(
        db, current_user.id, limit, offset
    )
