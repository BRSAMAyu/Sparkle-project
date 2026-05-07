
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.insight_copy import (
    present_pattern_description,
    present_pattern_name,
    present_pattern_solution,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class DashboardService:
    DASHBOARD_CACHE_TTL_SECONDS = 300

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def _dashboard_cache_key(cls, user_id: UUID) -> str:
        return f"dashboard:status:{user_id}"

    async def generate_daily_report(self) -> dict[str, Any]:
        """
        Build a lightweight system-wide daily report for Celery beat.

        This report is used as an operational heartbeat, so it should stay fast
        and deterministic even when no user-facing dashboard context is present.
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        active_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.is_active.is_(True))
        )
        completed_tasks_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= today_start,
                )
            )
        )
        created_tasks_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.created_at >= today_start)
        )
        active_plans_result = await self.db.execute(
            select(func.count(Plan.id)).where(Plan.is_active.is_(True))
        )

        return {
            "date": today_start.date().isoformat(),
            "active_users": active_users_result.scalar() or 0,
            "tasks_created_today": created_tasks_result.scalar() or 0,
            "tasks_completed_today": completed_tasks_result.scalar() or 0,
            "active_plans": active_plans_result.scalar() or 0,
            "generated_at": _utcnow().isoformat(),
        }

    async def get_dashboard_status(self, user_id: UUID) -> dict[str, Any]:
        """
        Get all data for the dashboard
        """
        cache_key = self._dashboard_cache_key(user_id)
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return cached

        user = await self._get_user(user_id)

        # Get active sprint
        sprint = await self._get_active_sprint(user_id)

        # Get active growth plan
        growth = await self._get_active_growth(user_id)

        # Get weather (now includes cognitive data check)
        weather = await self._calculate_weather(user_id, user, sprint)

        # Get next actions
        next_actions = await self._get_next_actions(user_id)

        # Get cognitive data
        cognitive = await self._get_cognitive_summary(user_id)

        # Calculate today's focus minutes from completed tasks
        today_focus_minutes = await self._get_today_focus_minutes(user_id)
        tasks_completed_today = await self._get_today_completed_tasks(user_id)
        growth_dashboard = await GrowthDashboardService(self.db).build_snapshot(user_id, user=user)

        payload = {
            "weather": weather,
            "flame": {
                "level": user.flame_level,
                "brightness": user.flame_brightness,
                "today_focus_minutes": today_focus_minutes,
                "tasks_completed": tasks_completed_today,
            },
            "sprint": sprint,
            "growth": growth,
            "next_actions": next_actions,
            "cognitive": cognitive,
            "growth_status": growth_dashboard.get("growth_status"),
            "most_important_task": growth_dashboard.get("most_important_task"),
            "growth_signal": growth_dashboard.get("growth_signal"),
            "active_plan_progress": growth_dashboard.get("active_plan_progress"),
        }

        # T4.1: Spine/Aurora status integration
        spine_data = await self._get_spine_status(user_id)
        if spine_data:
            payload["spine"] = spine_data
        await cache_service.set(
            cache_key,
            payload,
            ttl=self.DASHBOARD_CACHE_TTL_SECONDS,
        )
        return payload

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _get_next_actions(self, user_id: UUID) -> list[dict]:
        """Top 3 pending tasks"""
        query = (
            select(Task)
            .where(and_(Task.user_id == user_id, Task.status == TaskStatus.PENDING))
            .order_by(desc(Task.priority), Task.due_date, Task.created_at) # Sort by priority then due date
            .limit(3)
        )
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "estimated_minutes": t.estimated_minutes,
                "priority": t.priority,
                "type": t.type
            } for t in tasks
        ]

    async def _get_active_sprint(self, user_id: UUID) -> dict | None:
        """Get first active sprint plan"""
        query = (
            select(Plan)
            .where(and_(
                Plan.user_id == user_id,
                Plan.is_active,
                Plan.type == PlanType.SPRINT
            ))
            .order_by(Plan.target_date) # Closest deadline
            .limit(1)
        )
        result = await self.db.execute(query)
        plan = result.scalar_one_or_none()

        if plan:
            days_left = (plan.target_date - datetime.now().date()).days if plan.target_date else 0
            return {
                "id": str(plan.id),
                "name": plan.name,
                "progress": plan.progress,
                "days_left": max(0, days_left),
                "total_estimated_hours": plan.total_estimated_hours
            }
        return None

    async def _get_active_growth(self, user_id: UUID) -> dict | None:
        """Get first active growth plan"""
        query = (
            select(Plan)
            .where(and_(
                Plan.user_id == user_id,
                Plan.is_active,
                Plan.type == PlanType.GROWTH
            ))
            .order_by(Plan.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        plan = result.scalar_one_or_none()

        if plan:
            return {
                "id": str(plan.id),
                "name": plan.name,
                "progress": plan.progress,
                "mastery_level": plan.mastery_level,
            }
        return None

    async def _get_today_focus_minutes(self, user_id: UUID) -> int:
        """Calculate today's focus time from completed tasks"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = select(func.coalesce(func.sum(Task.actual_minutes), 0)).where(
            and_(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= today_start
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_today_completed_tasks(self, user_id: UUID) -> int:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count(Task.id)).where(
            and_(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= today_start,
            )
        )
        result = await self.db.execute(query)
        return int(result.scalar() or 0)

    async def _get_cognitive_summary(self, user_id: UUID) -> dict:
        """Get cognitive prism summary for dashboard"""
        # Get the latest active behavior pattern
        pattern_query = (
            select(BehaviorPattern)
            .where(
                and_(
                    BehaviorPattern.user_id == user_id,
                    BehaviorPattern.is_archived.is_(False),
                )
            )
            .order_by(desc(BehaviorPattern.created_at))
            .limit(1)
        )
        result = await self.db.execute(pattern_query)
        latest_pattern = result.scalar_one_or_none()

        # Check if there are new patterns created in last 24 hours
        yesterday = _utcnow() - timedelta(days=1)
        new_pattern_query = select(func.count(BehaviorPattern.id)).where(
            and_(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.created_at >= yesterday,
                BehaviorPattern.is_archived.is_(False),
            )
        )
        new_count_result = await self.db.execute(new_pattern_query)
        has_new_pattern = (new_count_result.scalar() or 0) > 0

        if latest_pattern:
            return {
                "weekly_pattern": present_pattern_name(latest_pattern.pattern_name),
                "pattern_type": latest_pattern.pattern_type,
                "description": present_pattern_description(
                    latest_pattern.pattern_name,
                    latest_pattern.description,
                ),
                "solution_text": present_pattern_solution(
                    latest_pattern.pattern_name,
                    latest_pattern.solution_text,
                ),
                "status": "new" if has_new_pattern else "active",
                "has_new_insight": has_new_pattern
            }

        return {
            "weekly_pattern": None,
            "pattern_type": None,
            "description": None,
            "solution_text": None,
            "status": "empty",
            "has_new_insight": False
        }

    async def _get_recent_anxiety_level(self, user_id: UUID) -> float:
        """Check recent cognitive fragments for anxiety"""
        two_days_ago = _utcnow() - timedelta(days=2)

        total_query = select(func.count(CognitiveFragment.id)).where(
            and_(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.created_at >= two_days_ago
            )
        )
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        if total_count == 0:
            return 0.0

        anxiety_query = select(func.count(CognitiveFragment.id)).where(
            and_(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.created_at >= two_days_ago,
                CognitiveFragment.sentiment == "anxious",
            )
        )
        anxiety_result = await self.db.execute(anxiety_query)
        anxiety_count = anxiety_result.scalar() or 0
        return anxiety_count / total_count

    async def _calculate_weather(self, user_id: UUID, user: User, sprint: dict | None) -> dict:
        """
        Calculate inner weather based on rules.
        """
        weather = "sunny"
        condition = "心境晴朗"

        # 1. Check Sprint Status
        if sprint:
            if sprint["days_left"] < 3 and sprint["progress"] < 0.5:
                weather = "rainy"
                condition = "临近截止日"
            elif sprint["progress"] < 0.2 and sprint["days_left"] < 7:
                weather = "cloudy"
                condition = "进度落后"
            elif sprint["progress"] > 0.8:
                weather = "meteor"
                condition = "势头正旺"

        # 2. Check recent study records (if no task completed for 2 days -> cloudy)
        two_days_ago = _utcnow() - timedelta(days=2)
        recent_task_query = select(func.count(Task.id)).where(
            and_(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= two_days_ago
            )
        )
        result = await self.db.execute(recent_task_query)
        recent_completed = result.scalar() or 0

        if recent_completed == 0 and weather == "sunny":
            weather = "cloudy"
            condition = "需要动起来"

        # 3. Check cognitive fragments (if recent anxiety > 50% -> rainy)
        anxiety_level = await self._get_recent_anxiety_level(user_id)
        if anxiety_level > 0.5:
            weather = "rainy"
            condition = "检测到焦虑"

        return {
            "type": weather,  # sunny, cloudy, rainy, meteor
            "condition": condition
        }

    async def _get_spine_status(self, user_id: UUID) -> dict | None:
        """Fetch Spine/Aurora status band for dashboard integration (T4.1)."""
        try:
            redis_client = cache_service.redis
            if redis_client is None:
                return None

            from app.signals.spine_orchestrator import get_spine_orchestrator

            orchestrator = get_spine_orchestrator(redis_client=redis_client)
            summary = await orchestrator.get_status_band_summary(str(user_id))
            return {
                "band_status": summary.get("band_status", "sensing"),
                "band_label": summary.get("band_label", ""),
                "band_summary": summary.get("band_summary", ""),
                "band_severity": summary.get("band_severity", "none"),
                "band_energy": summary.get("band_energy", "L0"),
                "active_claims": summary.get("active_claims", []),
                "correction_options": summary.get("correction_options", []),
            }
        except Exception as e:
            logger.warning("Dashboard spine status fetch failed for user {}: {}", user_id, e)
            return None
