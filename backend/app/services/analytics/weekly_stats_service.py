from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.galaxy import StudyRecord, KnowledgeNode, UserNodeStatus
from app.models.focus import FocusSession, FocusStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.error_book import ErrorRecord

class WeeklyStatsService:
    """
    Weekly Statistics Aggregation Service
    Aggregates data for the weekly learning report.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_weekly_summary(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get high-level weekly summary stats.
        """
        # 1. Study Time
        total_study_minutes = await self._get_total_study_time(user_id, start_date, end_date)
        
        # 2. Focus Sessions
        focus_stats = await self._get_focus_stats(user_id, start_date, end_date)
        
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

    async def _get_total_study_time(self, user_id: str, start_date: datetime, end_date: datetime) -> int:
        """Calculate total study minutes from study records."""
        query = select(func.sum(StudyRecord.study_minutes)).where(
            StudyRecord.user_id == user_id,
            StudyRecord.created_at >= start_date,
            StudyRecord.created_at <= end_date
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_focus_stats(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, int]:
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

    async def _get_mastery_stats(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
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

    async def get_daily_activity_trend(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
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
