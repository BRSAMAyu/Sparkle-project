from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.services.plan_state_service import PlanStateService


class PlanScopeProvider:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.plan_state_service = PlanStateService(db, redis)

    async def get_scope(self, user_id: UUID, plan_id: UUID) -> dict[str, Any]:
        """Fetch plan-specific context"""
        # Get dynamic state
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)

        # Get static info (title, type)
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()

        if not state or not plan:
            return {}

        return {
            "plan_id": str(plan_id),
            "title": plan.name,
            "type": plan.type.value,
            "facts": state.facts,
            "milestones": state.milestones,
            "task_index": state.task_index,
            "constraints": state.constraints,
            "version": state.version,
            "feedback_log": state.feedback_log[-5:] if state.feedback_log else []
        }
