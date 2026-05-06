from __future__ import annotations

import asyncio

from loguru import logger

from app.consumers.journey_consumer_base import JourneyEventConsumerBase, JourneyPayloadSecurityError
from app.db.session import AsyncSessionLocal
from app.models.plan import Plan, PlanType
from app.services.achievement_engine import AchievementEngine, AchievementEvent


class AchievementPlanConsumer(JourneyEventConsumerBase):
    GROUP_NAME = "achievement_plan_consumer"
    EVENT_TYPE = "plan.created"
    CONSUMER_NAME_PREFIX = "achievement-plan"
    CONSUMER_LABEL = "AchievementPlanConsumer"

    async def _process_event(self, event: dict, user_id) -> None:
        plan_id = event.get("plan_id")
        async with AsyncSessionLocal() as db:
            plan = None
            for attempt in range(3):
                plan = await db.get(Plan, plan_id)
                if plan is not None:
                    break
                logger.warning(
                    "AchievementPlanConsumer: plan not found, retrying (attempt={}/3, plan_id={})",
                    attempt + 1, plan_id,
                )
                await asyncio.sleep(0.1 * (attempt + 1))
            if plan is None:
                raise JourneyPayloadSecurityError("plan_not_found")
            if plan.user_id != user_id:
                raise JourneyPayloadSecurityError("cross_user_plan_payload")

            engine = AchievementEngine(db)
            await engine.process_event(
                user_id=str(user_id),
                event_type=AchievementEvent.PLAN_CREATED,
                plan_id=str(plan.id),
                plan_type=str(getattr(plan.type, "value", plan.type) or ""),
            )
            if plan.type == PlanType.SPRINT:
                await engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.SPRINT_STARTED,
                    plan_id=str(plan.id),
                    plan_type=str(getattr(plan.type, "value", plan.type) or ""),
                )
