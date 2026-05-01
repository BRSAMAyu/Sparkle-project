"""
统计数据 API
Statistics API
"""
from datetime import date, datetime, timedelta, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.achievement import UserAchievement
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.focus import FocusSession, FocusStatus
from app.models.task import Task, TaskStatus
from app.models.user import User

router = APIRouter()


async def _count_today_focus_sessions(db: AsyncSession, user_id: UUID, today_start: datetime) -> int:
    """Count completed focus sessions started today."""
    tomorrow_start = today_start + timedelta(days=1)
    query = select(func.count(FocusSession.id)).where(
        and_(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= today_start,
            FocusSession.start_time < tomorrow_start,
            FocusSession.status == FocusStatus.COMPLETED,
        )
    )
    result = await db.execute(query)
    return result.scalar() or 0


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
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

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
        "focus_sessions": await _count_today_focus_sessions(db, user_id, today_start),
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
        now_naive = datetime.now(UTC).replace(tzinfo=None)
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
    now = datetime.now(UTC).replace(tzinfo=None)
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


def _day_key(value: date | str | datetime) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _resolve_heatmap_user_id(current_user: User, requested_user_id: UUID | None) -> UUID:
    if requested_user_id is None or requested_user_id == current_user.id:
        return current_user.id
    if current_user.is_superuser:
        return requested_user_id
    raise HTTPException(status_code=403, detail="Not authorized to view another user's activity heatmap")


@router.get("/activity/heatmap")
async def get_learning_heatmap(
    days: int = Query(default=90, ge=1, le=365),
    user_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    学习热力图（GitHub 风格贡献图）
    Returns one entry per day, including today.

    Minutes are sourced from:
    1. `study_records` written by galaxy/task learning updates
    2. completed tasks without a linked study record as a fallback

    Response: [{date: "2026-04-01", minutes: 45, tasks_completed: 3}, ...]
    """
    target_user_id = _resolve_heatmap_user_id(current_user, user_id)
    today = datetime.now(UTC).replace(tzinfo=None).date()
    start_day = today - timedelta(days=days - 1)
    range_start = datetime.combine(start_day, datetime.min.time())
    range_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

    study_query = (
        select(
            func.date(StudyRecord.created_at).label("day"),
            func.coalesce(func.sum(StudyRecord.study_minutes), 0).label("study_minutes"),
        )
        .where(
            StudyRecord.user_id == target_user_id,
            StudyRecord.created_at >= range_start,
            StudyRecord.created_at < range_end,
        )
        .group_by(func.date(StudyRecord.created_at))
    )
    study_result = await db.execute(study_query)
    study_minutes_by_day = {
        _day_key(row.day): float(row.study_minutes or 0)
        for row in study_result
    }

    task_has_study_record = select(StudyRecord.id).where(StudyRecord.task_id == Task.id).exists()
    task_minutes_query = (
        select(
            func.date(Task.completed_at).label("day"),
            func.coalesce(
                func.sum(func.coalesce(Task.actual_minutes, Task.estimated_minutes, 0)),
                0,
            ).label("task_minutes"),
        )
        .where(
            Task.user_id == target_user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at.is_not(None),
            Task.completed_at >= range_start,
            Task.completed_at < range_end,
            ~task_has_study_record,
        )
        .group_by(func.date(Task.completed_at))
    )
    task_minutes_result = await db.execute(task_minutes_query)
    fallback_task_minutes_by_day = {
        _day_key(row.day): float(row.task_minutes or 0)
        for row in task_minutes_result
    }

    task_count_query = (
        select(
            func.date(Task.completed_at).label("day"),
            func.count(Task.id).label("task_count"),
        )
        .where(
            Task.user_id == target_user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at.is_not(None),
            Task.completed_at >= range_start,
            Task.completed_at < range_end,
        )
        .group_by(func.date(Task.completed_at))
    )
    task_count_result = await db.execute(task_count_query)
    tasks_completed_by_day = {
        _day_key(row.day): int(row.task_count or 0)
        for row in task_count_result
    }

    result: list[dict[str, str | int | float]] = []
    for offset in range(days):
        current_day = start_day + timedelta(days=offset)
        day_key = current_day.isoformat()
        total_minutes = study_minutes_by_day.get(day_key, 0.0) + fallback_task_minutes_by_day.get(day_key, 0.0)
        result.append(
            {
                "date": day_key,
                "minutes": round(total_minutes, 1),
                "tasks_completed": tasks_completed_by_day.get(day_key, 0),
            }
        )

    return result


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
