"""
统计数据 API
Statistics API
"""
from datetime import timezone, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.achievement import UserAchievement
from app.models.galaxy import UserNodeStatus
from app.models.task import Task
from app.models.user import User

router = APIRouter()


@router.get("/daily")
async def get_daily_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取今日统计数据
    Get daily statistics for current user
    """
    user_id = current_user.id
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    # Tasks completed today
    completed_query = select(func.count(Task.id)).where(
        and_(
            Task.user_id == user_id,
            Task.status == "COMPLETED",
            Task.completed_at >= today_start
        )
    )
    completed_result = await db.execute(completed_query)
    tasks_completed = completed_result.scalar() or 0

    # Study minutes today (based on estimated_minutes of completed tasks)
    time_query = select(func.sum(Task.estimated_minutes)).where(
        and_(
            Task.user_id == user_id,
            Task.status == "COMPLETED",
            Task.completed_at >= today_start
        )
    )
    time_result = await db.execute(time_query)
    study_minutes = time_result.scalar() or 0

    # Total tasks today (created or due)
    total_today_query = select(func.count(Task.id)).where(
        and_(
            Task.user_id == user_id,
            Task.due_date == today_start.date()
        )
    )
    total_today_result = await db.execute(total_today_query)
    total_today = total_today_result.scalar() or 0

    return {
        "tasks_completed": tasks_completed,
        "study_minutes": study_minutes,
        "total_tasks_today": total_today,
        "focus_sessions": 0,  # TRACKED(TD-008): integrate with focus_sessions table when available
    }


@router.get("/overview")
async def get_stats_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户统计概览
    Get user statistics overview
    """
    user_id = current_user.id

    # 获取任务统计
    total_tasks_query = select(func.count(Task.id)).where(
        Task.user_id == user_id
    )
    total_result = await db.execute(total_tasks_query)
    total_tasks = total_result.scalar() or 0

    completed_tasks_query = select(func.count(Task.id)).where(
        and_(
            Task.user_id == user_id,
            Task.status == "COMPLETED"
        )
    )
    completed_result = await db.execute(completed_tasks_query)
    completed_tasks = completed_result.scalar() or 0

    # 获取成就统计
    achievements_query = select(func.count(UserAchievement.id)).where(
        UserAchievement.user_id == user_id
    )
    achievements_result = await db.execute(achievements_query)
    total_achievements = achievements_result.scalar() or 0

    # 获取知识节点统计
    nodes_query = select(func.count(UserNodeStatus.node_id)).where(
        UserNodeStatus.user_id == user_id
    )
    nodes_result = await db.execute(nodes_query)
    knowledge_nodes = nodes_result.scalar() or 0

    # 计算学习天数
    first_task_query = select(Task.created_at).where(
        Task.user_id == user_id
    ).order_by(Task.created_at.asc()).limit(1)
    first_task_result = await db.execute(first_task_query)
    first_task_date = first_task_result.scalar_one_or_none()

    study_days = 0
    if first_task_date:
        # Use naive UTC to match DB TIMESTAMP WITHOUT TIME ZONE
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        first_naive = first_task_date.replace(tzinfo=None) if first_task_date.tzinfo else first_task_date
        delta = now_naive - first_naive
        study_days = delta.days + 1

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": total_tasks - completed_tasks,
        "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
        "total_achievements": total_achievements,
        "knowledge_nodes": knowledge_nodes,
        "study_days": study_days,
        "flame_level": current_user.flame_level or 1,
        "flame_brightness": current_user.flame_brightness or 0,
        "streak_days": current_user.flame_level or 0,  # Using flame_level as proxy
    }


@router.get("/learning-summary")
async def get_learning_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compatibility summary endpoint for acceptance and legacy clients."""
    overview = await get_stats_overview(current_user=current_user, db=db)
    weekly = await get_weekly_stats(current_user=current_user, db=db)
    return {
        "overview": overview,
        "weekly": weekly,
    }


@router.get("/weekly")
async def get_weekly_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取周统计数据
    Get weekly statistics
    """
    user_id = current_user.id
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)

    # 周内完成任务
    completed_query = select(func.count(Task.id)).where(
        and_(
            Task.user_id == user_id,
            Task.status == "COMPLETED",
            Task.completed_at >= week_ago
        )
    )
    completed_result = await db.execute(completed_query)
    weekly_completed = completed_result.scalar() or 0

    # 周内学习时间（基于任务预估）
    time_query = select(func.sum(Task.estimated_minutes)).where(
        and_(
            Task.user_id == user_id,
            Task.status == "COMPLETED",
            Task.completed_at >= week_ago
        )
    )
    time_result = await db.execute(time_query)
    weekly_minutes = time_result.scalar() or 0

    return {
        "week_start": week_ago.isoformat(),
        "week_end": now.isoformat(),
        "tasks_completed": weekly_completed,
        "total_study_minutes": weekly_minutes,
        "average_daily_minutes": round(weekly_minutes / 7, 1) if weekly_minutes else 0,
    }


@router.get("/flame")
async def get_flame_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取火花等级统计
    Get flame level statistics
    """
    return {
        "flame_level": current_user.flame_level or 1,
        "flame_brightness": current_user.flame_brightness or 0,
        "depth_preference": current_user.depth_preference or 0.5,
        "curiosity_preference": current_user.curiosity_preference or 0.5,
    }
