"""
统计数据 API
Statistics API
"""

from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core import time_utils
from app.models.achievement import UserAchievement
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import StudyRecord, UserNodeStatus
from app.models.task import Task, TaskStatus
from app.models.user import User

router = APIRouter()


def _utcnow() -> datetime:
    """Canonical naive-UTC clock (app.core.time_utils); module-level so tests can freeze it."""
    return time_utils.utcnow()


async def _count_today_focus_sessions(db: AsyncSession, user_id: UUID, today_start: datetime) -> int:
    """Count completed focus sessions started today.

    ``today_start`` 必须与 FocusSession.start_time 的存储钟同源——该列存客户端
    本地墙上时间 naive（V3-FIX-37 定界），故传入本地墙上零点 naive。
    """
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
async def get_daily_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取今日统计数据
    Get daily statistics for current user
    """
    user_id = current_user.id
    # ── 「今日」口径（V3-FIX-37 定界 + V3-FIX-197 收口）──
    # - due_date 口径：沿 goal_today_view SSOT 的「今日任务」基座；SSOT 调用方
    #   （experience_readouts._next_task / goal_router._todays_next_task）已随
    #   V3-FIX-197 切用户本地日，本分母同步用本地日，三面同钟。
    # - FocusSession.start_time：存客户端本地墙上时间 naive（mobile 发本地 ISO 串、
    #   无时区后缀）→ 窗口必须用同一墙钟的本地日界；修前用 naive-UTC 日界，
    #   UTC+8 本地 00:00–08:00 的晨间会话被切进「昨天」（focus_sessions 计 0）。
    tz_name = time_utils.user_timezone_name(current_user)
    today = time_utils.local_date(_utcnow(), tz_name)
    focus_today_start = time_utils.local_midnight_wall(today)

    # ── H7 口径声明（对齐 SSOT app/services/goal_today_view.py 的「今日任务」基座）──
    # 基座：due_date == today（用户本地日，V3-FIX-197）且 deleted_at IS NULL；
    # 状态：ABANDONED 已被 SSOT 排除出「今日任务」→ 不计分母；COMPLETED 保留（分子母集）；
    # 时间轴：分子分母统一到 due_date（修前分子按 completed_at 异轴，逾期补完成
    # 计入分子却不在分母，完成率可 >1）——逾期任务补完成计入其实际到期日。
    today_scope = and_(
        Task.user_id == user_id,
        Task.deleted_at.is_(None),
        Task.due_date == today,
        Task.status != "ABANDONED",
    )

    # Tasks completed today：分母同基座上的已完成子集（分子 ⊆ 分母）
    completed_query = select(func.count(Task.id)).where(and_(today_scope, Task.status == "COMPLETED"))
    completed_result = await db.execute(completed_query)
    tasks_completed = completed_result.scalar() or 0

    # Study minutes today：与分子同集合（今日到期且已完成任务的预计时长），避免同屏两口径
    time_query = select(func.sum(Task.estimated_minutes)).where(and_(today_scope, Task.status == "COMPLETED"))
    time_result = await db.execute(time_query)
    study_minutes = time_result.scalar() or 0

    # Total tasks today：今日到期 + 未软删 + 未放弃（声明口径见上）
    total_today_query = select(func.count(Task.id)).where(today_scope)
    total_today_result = await db.execute(total_today_query)
    total_today = total_today_result.scalar() or 0

    return {
        "tasks_completed": tasks_completed,
        "study_minutes": study_minutes,
        "total_tasks_today": total_today,
        "focus_sessions": await _count_today_focus_sessions(db, user_id, focus_today_start),
    }


@router.get("/overview")
async def get_stats_overview(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取用户统计概览
    Get user statistics overview
    """
    user_id = current_user.id

    # 获取任务统计
    total_tasks_query = select(func.count(Task.id)).where(Task.user_id == user_id)
    total_result = await db.execute(total_tasks_query)
    total_tasks = total_result.scalar() or 0

    completed_tasks_query = select(func.count(Task.id)).where(and_(Task.user_id == user_id, Task.status == "COMPLETED"))
    completed_result = await db.execute(completed_tasks_query)
    completed_tasks = completed_result.scalar() or 0

    # 获取成就统计
    achievements_query = select(func.count(UserAchievement.id)).where(UserAchievement.user_id == user_id)
    achievements_result = await db.execute(achievements_query)
    total_achievements = achievements_result.scalar() or 0

    # 获取知识节点统计
    nodes_query = select(func.count(UserNodeStatus.node_id)).where(UserNodeStatus.user_id == user_id)
    nodes_result = await db.execute(nodes_query)
    knowledge_nodes = nodes_result.scalar() or 0

    # 计算学习天数
    first_task_query = select(Task.created_at).where(Task.user_id == user_id).order_by(Task.created_at.asc()).limit(1)
    first_task_result = await db.execute(first_task_query)
    first_task_date = first_task_result.scalar_one_or_none()

    study_days = 0
    if first_task_date:
        # Use naive UTC to match DB TIMESTAMP WITHOUT TIME ZONE
        now_naive = _utcnow()
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
async def get_weekly_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    获取周统计数据
    Get weekly statistics
    """
    user_id = current_user.id
    now = _utcnow()
    week_ago = now - timedelta(days=7)

    # 周内完成任务
    completed_query = select(func.count(Task.id)).where(
        and_(Task.user_id == user_id, Task.status == "COMPLETED", Task.completed_at >= week_ago)
    )
    completed_result = await db.execute(completed_query)
    weekly_completed = completed_result.scalar() or 0

    # 周内学习时间（基于任务预估）
    time_query = select(func.sum(Task.estimated_minutes)).where(
        and_(Task.user_id == user_id, Task.status == "COMPLETED", Task.completed_at >= week_ago)
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


def _resolve_heatmap_user_id(current_user: User, requested_user_id: UUID | None) -> UUID:
    if requested_user_id is None or requested_user_id == current_user.id:
        return cast("UUID", (current_user.id))
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
    Returns one entry per user-local day, including today.

    Minutes are sourced from:
    1. `study_records` written by galaxy/task learning updates
    2. completed tasks without a linked study record as a fallback

    Response: [{date: "2026-04-01", minutes: 45, tasks_completed: 3}, ...]

    时区口径（V3-FIX-37）：两源列均存 naive-UTC（服务端 utcnow），但日界与
    标注按用户本地日切——窗口边界由本地零点换算回 UTC naive 瞬间，归属在
    应用层把 UTC 瞬时转回用户本地日（修前窗口与 func.date 分桶都用 UTC 日，
    UTC+8 本地 00:00–08:00 的记录被上界整段排除/错标到前一日）。
    """
    target_user_id = _resolve_heatmap_user_id(current_user, user_id)
    tz_name = time_utils.user_timezone_name(current_user)
    today = time_utils.local_date(_utcnow(), tz_name)
    start_day = today - timedelta(days=days - 1)
    range_start = time_utils.local_midnight_as_utc_naive(start_day, tz_name)
    range_end = time_utils.local_midnight_as_utc_naive(today + timedelta(days=1), tz_name)

    # 按行取回后在应用层按用户本地日分桶（SQL func.date 只能取 UTC 日，
    # 跨方言的可移植本地日偏移无统一表达式；单用户 ≤365 天行数量级可接受）。
    study_query = select(StudyRecord.created_at, StudyRecord.study_minutes).where(
        StudyRecord.user_id == target_user_id,
        StudyRecord.created_at >= range_start,
        StudyRecord.created_at < range_end,
    )
    study_result = await db.execute(study_query)
    study_minutes_by_day: dict[str, float] = {}
    for created_at, row_minutes in study_result:
        day_key = time_utils.local_date(created_at, tz_name).isoformat()
        study_minutes_by_day[day_key] = study_minutes_by_day.get(day_key, 0.0) + float(row_minutes or 0)

    task_has_study_record = select(StudyRecord.id).where(StudyRecord.task_id == Task.id).exists()
    task_minutes_query = select(Task.completed_at, func.coalesce(Task.actual_minutes, Task.estimated_minutes, 0)).where(
        Task.user_id == target_user_id,
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at.is_not(None),
        Task.completed_at >= range_start,
        Task.completed_at < range_end,
        ~task_has_study_record,
    )
    task_minutes_result = await db.execute(task_minutes_query)
    fallback_task_minutes_by_day: dict[str, float] = {}
    for completed_at, row_minutes in task_minutes_result:
        day_key = time_utils.local_date(completed_at, tz_name).isoformat()
        fallback_task_minutes_by_day[day_key] = fallback_task_minutes_by_day.get(day_key, 0.0) + float(row_minutes or 0)

    task_count_query = select(Task.completed_at).where(
        Task.user_id == target_user_id,
        Task.status == TaskStatus.COMPLETED,
        Task.completed_at.is_not(None),
        Task.completed_at >= range_start,
        Task.completed_at < range_end,
    )
    task_count_result = await db.execute(task_count_query)
    tasks_completed_by_day: dict[str, int] = {}
    for (completed_at,) in task_count_result:
        day_key = time_utils.local_date(completed_at, tz_name).isoformat()
        tasks_completed_by_day[day_key] = tasks_completed_by_day.get(day_key, 0) + 1

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
async def get_flame_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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
