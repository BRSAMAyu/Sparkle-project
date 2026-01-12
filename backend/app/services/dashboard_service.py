
from uuid import UUID
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func

from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanType
from app.models.user import User
from app.models.cognitive import CognitiveFragment, BehaviorPattern

class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_status(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get all data for the dashboard
        """
        user = await self._get_user(user_id)

        # Get active sprint
        sprint = await self._get_active_sprint(user_id)

        # Get weather (now includes cognitive data check)
        weather = await self._calculate_weather(user_id, user, sprint)

        # Get next actions
        next_actions = await self._get_next_actions(user_id)

        # Get cognitive data
        cognitive = await self._get_cognitive_summary(user_id)

        # Calculate today's focus minutes from completed tasks
        today_focus_minutes = await self._get_today_focus_minutes(user_id)

        return {
            "weather": weather,
            "flame": {
                "level": user.flame_level,
                "brightness": user.flame_brightness,
                "today_focus_minutes": today_focus_minutes
            },
            "sprint": sprint,
            "next_actions": next_actions,
            "cognitive": cognitive
        }

    async def _get_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()

    async def _get_next_actions(self, user_id: UUID) -> List[Dict]:
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

    async def _get_active_sprint(self, user_id: UUID) -> Optional[Dict]:
        """Get first active sprint plan"""
        query = (
            select(Plan)
            .where(and_(
                Plan.user_id == user_id, 
                Plan.is_active == True,
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

    async def _get_cognitive_summary(self, user_id: UUID) -> Dict:
        """Get cognitive prism summary for dashboard"""
        # Get the latest active behavior pattern
        pattern_query = (
            select(BehaviorPattern)
            .where(
                and_(
                    BehaviorPattern.user_id == user_id,
                    BehaviorPattern.is_archived == False
                )
            )
            .order_by(desc(BehaviorPattern.created_at))
            .limit(1)
        )
        result = await self.db.execute(pattern_query)
        latest_pattern = result.scalar_one_or_none()

        # Check if there are new patterns created in last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        new_pattern_query = select(func.count(BehaviorPattern.id)).where(
            and_(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.created_at >= yesterday
            )
        )
        new_count_result = await self.db.execute(new_pattern_query)
        has_new_pattern = (new_count_result.scalar() or 0) > 0

        if latest_pattern:
            return {
                "weekly_pattern": latest_pattern.pattern_name,
                "pattern_type": latest_pattern.pattern_type,
                "description": latest_pattern.description,
                "solution_text": latest_pattern.solution_text,
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
        two_days_ago = datetime.utcnow() - timedelta(days=2)

        query = select(CognitiveFragment).where(
            and_(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.created_at >= two_days_ago
            )
        )
        result = await self.db.execute(query)
        fragments = result.scalars().all()

        if not fragments:
            return 0.0

        anxiety_count = sum(1 for f in fragments if f.sentiment == "anxious")
        return anxiety_count / len(fragments)

    async def _calculate_weather(self, user_id: UUID, user: User, sprint: Optional[Dict]) -> Dict:
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
        two_days_ago = datetime.utcnow() - timedelta(days=2)
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
