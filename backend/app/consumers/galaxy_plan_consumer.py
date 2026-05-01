from __future__ import annotations

from sqlalchemy import func, select

from app.consumers.journey_consumer_base import JourneyEventConsumerBase, JourneyPayloadSecurityError
from app.db.session import AsyncSessionLocal
from app.models.galaxy import UserNodeStatus
from app.models.plan import Plan
from app.services.galaxy_bootstrap_service import GalaxyBootstrapService


class GalaxyPlanConsumer(JourneyEventConsumerBase):
    GROUP_NAME = "galaxy_plan_consumer"
    EVENT_TYPE = "plan.created"
    CONSUMER_NAME_PREFIX = "galaxy-plan"
    CONSUMER_LABEL = "GalaxyPlanConsumer"

    async def _process_event(self, event: dict, user_id) -> None:
        plan_id = event.get("plan_id")
        async with AsyncSessionLocal() as db:
            plan = await db.get(Plan, plan_id)
            if plan is None:
                raise JourneyPayloadSecurityError("plan_not_found")
            if plan.user_id != user_id:
                raise JourneyPayloadSecurityError("cross_user_plan_payload")

            existing_status_count = (
                await db.execute(
                    select(func.count()).select_from(UserNodeStatus).where(UserNodeStatus.user_id == user_id)
                )
            ).scalar_one()
            if int(existing_status_count or 0) > 0:
                return

            await GalaxyBootstrapService(db).seed_from_goal(
                user_id=user_id,
                learning_goal=plan.name,
                goal_type=getattr(plan.type, "value", plan.type),
            )
