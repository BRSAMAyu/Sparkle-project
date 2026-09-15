from __future__ import annotations

import asyncio

from loguru import logger

from app.consumers.journey_consumer_base import JourneyEventConsumerBase, JourneyPayloadSecurityError
from app.core.task_manager import task_manager
from app.db.session import AsyncSessionLocal
from app.models.plan import Plan
from app.orchestration.plan_review_service import plan_review_service


class PlanTaskGenerationConsumer(JourneyEventConsumerBase):
    GROUP_NAME = "plan_task_generation_consumer"
    EVENT_TYPE = "plan.created"
    CONSUMER_NAME_PREFIX = "plan-taskgen"
    CONSUMER_LABEL = "PlanTaskGenerationConsumer"

    async def _process_event(self, event: dict, user_id) -> None:
        plan_id = event.get("plan_id")
        async with AsyncSessionLocal() as db:
            plan = None
            for attempt in range(3):
                plan = await db.get(Plan, plan_id)
                if plan is not None:
                    break
                logger.warning(
                    "PlanTaskGenerationConsumer: plan not found, retrying (attempt={}/3, plan_id={})",
                    attempt + 1, plan_id,
                )
                await asyncio.sleep(0.1 * (attempt + 1))
            if plan is None:
                raise JourneyPayloadSecurityError("plan_not_found")
            if plan.user_id != user_id:
                raise JourneyPayloadSecurityError("cross_user_plan_payload")

        await task_manager.spawn(
            plan_review_service._generate_tasks_after_approval(
                plan_id=str(plan_id),
                user_id=str(user_id),
                action_id=f"journey-plan-created:{plan_id}",
                auto_delegate_tasks=False,
            ),
            task_name="journey_plan_task_generation",
            user_id=str(user_id),
            priority=3,
        )
