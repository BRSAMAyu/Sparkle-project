
from uuid import UUID
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanType
from app.models.user import User

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
        
        # Get weather
        weather = await self._calculate_weather(user_id, user, sprint)
        
        # Get next actions
        next_actions = await self._get_next_actions(user_id)

        return {
            "weather": weather,
            "flame": {
                "level": user.flame_level,
                "brightness": user.flame_brightness,
                "today_focus_minutes": 0 # TODO: Calculate from StudyRecords
            },
            "sprint": sprint,
            "next_actions": next_actions,
            "cognitive": {
                "weekly_pattern": "Planning Fallacy", # Placeholder
                "status": "active"
            }
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

    async def _calculate_weather(self, user_id: UUID, user: User, sprint: Optional[Dict]) -> Dict:
        """
        Calculate inner weather based on rules.
        """
        # Default
        weather = "sunny"
        condition = "Ready to Spark"

        # 1. Check Sprint Status
        if sprint:
            if sprint["days_left"] < 3 and sprint["progress"] < 0.5:
                 weather = "rainy"
                 condition = "Deadline Pressure"
            elif sprint["progress"] < 0.2 and sprint["days_left"] < 7:
                 weather = "cloudy"
                 condition = "Falling Behind"
            elif sprint["progress"] > 0.8:
                 weather = "sunny"
                 condition = "Momentum High"

        # 2. TODO: Check recent study records (if no study for 2 days -> cloudy)
        
        # 3. TODO: Check cognitive fragments (if recent anxiety > threshold -> rainy)

        return {
            "type": weather, # sunny, cloudy, rainy, meteor
            "condition": condition
        }
