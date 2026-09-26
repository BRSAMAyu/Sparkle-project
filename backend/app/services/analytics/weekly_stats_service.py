from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import time_utils
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus
from app.models.user import PushPreference


class WeeklyStatsService:
    """
    Weekly Statistics Aggregation Service
    Aggregates data for the weekly learning report.

    Active dependency: weekly_digest_service and weekly_synthesis_service use
    this for user-facing weekly summaries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_weekly_summary(self, user_id: str, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        """
        Get high-level weekly stats.
        """
        # V3-FIX-211 按列定钟：start/end 是调用方传入的 UTC 滚动瞬间（无跨钟
        # 地服务 StudyRecord.created_at / Task.updated_at）；FocusSession.start_time
        # 是墙上钟列，focus 查询端点换算成同一真实区间的用户本地墙上 naive。
        focus_start, focus_end = await self._wall_window(user_id, start_date, end_date)
        # 1. Study Time
        total_study_minutes = await self._get_total_study_time(user_id, start_date, end_date)

        # 2. Focus Sessions
        focus_stats = await self._get_focus_stats(user_id, focus_start, focus_end)

        # 3. Tasks Completed
        tasks_completed = await self._get_tasks_completed_count(user_id, start_date, end_date)

        # 4. Knowledge Mastery
        mastery_stats = await self._get_mastery_stats(user_id, start_date, end_date)

        # 5. Active Days
        active_days = await self._get_active_days(user_id, start_date, end_date)

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_study_minutes": total_study_minutes,
            "focus_sessions_count": focus_stats["count"],
            "focus_duration_minutes": focus_stats["duration"],
            "tasks_completed": tasks_completed,
            "mastery_gain": mastery_stats["gain"],
            "nodes_learned": mastery_stats["nodes_count"],
            "active_days": active_days
        }

    async def _wall_window(self, user_id: str, start_date: datetime, end_date: datetime) -> tuple[datetime, datetime]:
        """调用方 UTC 瞬间窗口 → 用户本地墙上钟域（FocusSession.start_time 列域，V3-FIX-211）。

        定界：本服务窗口端点由调用方传入（weekly_digest_service /
        weekly_synthesis_service 均为 ``_utcnow()`` 派生的 UTC 滚动瞬间）。
        同一端点直比 StudyRecord.created_at / Task.updated_at（UTC 存储列）
        无跨钟，而 FocusSession.start_time 存客户端本地墙上时间 naive——不
        换算时专注计数随市场时区漂移 ±8h。此处把端点换算成同一真实区间的
        用户本地墙上 naive（周期语义零改动）；如产品要把周窗对齐本地日界
        （local_midnight_wall），需连同调用方周期语义一起拍板，非本卡面。
        """
        tz_name = await self.db.scalar(select(PushPreference.timezone).where(PushPreference.user_id == user_id))
        tz = ZoneInfo(time_utils.valid_timezone_name(tz_name))
        return (
            start_date.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None),
            end_date.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None),
        )

    async def _get_total_study_time(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        """Calculate total study minutes from study records."""
        query = select(func.sum(StudyRecord.study_minutes)).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= start_date,
            StudyRecord.created_at <= end_date
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_focus_stats(self, user_id: str, start_date: datetime, end_date: datetime) -> dict[str, int]:
        """Get focus session count and total duration."""
        query = select(
            func.count(FocusSession.id),
            func.sum(FocusSession.duration_minutes)
        ).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= start_date,
            FocusSession.start_time <= end_date,
            FocusSession.status == FocusStatus.COMPLETED
        )
        result = await self.db.execute(query)
        count, duration = result.one()
        return {"count": count or 0, "duration": duration or 0}

    async def _get_tasks_completed_count(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        """Get number of tasks completed."""
        query = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.updated_at >= start_date,
            Task.updated_at <= end_date,
            Task.status == TaskStatus.COMPLETED
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_mastery_stats(self, user_id: str, start_date: datetime, end_date: datetime) -> dict[str, Any]:
        """Calculate total mastery points gained and unique nodes learned."""
        # Mastery Gain
        query_gain = select(func.sum(StudyRecord.mastery_delta)).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= start_date,
            StudyRecord.created_at <= end_date
        )
        result_gain = await self.db.execute(query_gain)
        gain = result_gain.scalar() or 0.0

        # Unique Nodes Learned
        query_nodes = select(func.count(func.distinct(StudyRecord.node_id))).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= start_date,
            StudyRecord.created_at <= end_date
        )
        result_nodes = await self.db.execute(query_nodes)
        nodes_count = result_nodes.scalar() or 0

        return {"gain": round(gain, 2), "nodes_count": nodes_count}

    async def _get_active_days(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        """Count distinct days with any study activity."""
        # Check StudyRecords and FocusSessions
        # This is a simplified check; ideally check created_at::date

        # Using a set of dates in python to aggregate from different sources might be easier if volume is low,
        # but SQL is better.

        # Group by date(created_at)
        query = select(func.count(func.distinct(func.date(StudyRecord.created_at)))).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= start_date,
            StudyRecord.created_at <= end_date
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_daily_activity_trend(self, user_id: str, start_date: datetime, end_date: datetime) -> list[dict[str, Any]]:
        """
        Get daily breakdown of study time and tasks for charts.
        """
        # Generate all dates in range
        delta = end_date - start_date
        dates = [(start_date + timedelta(days=i)).date() for i in range(delta.days + 1)]

        # Query DB grouping by date
        # (Simplified: Iterate and query or single sophisticated query. For MVP, iteration is fine for 7 days)
        trend = []
        for d in dates:
            day_start = datetime.combine(d, datetime.min.time())
            day_end = datetime.combine(d, datetime.max.time())

            study_min = await self._get_total_study_time(user_id, day_start, day_end)
            tasks = await self._get_tasks_completed_count(user_id, day_start, day_end)

            trend.append({
                "date": d.isoformat(),
                "study_minutes": study_min,
                "tasks_completed": tasks
            })

        return trend
