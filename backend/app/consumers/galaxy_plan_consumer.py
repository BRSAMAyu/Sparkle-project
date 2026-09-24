from __future__ import annotations

import asyncio

from loguru import logger
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
            plan = None
            for attempt in range(3):
                plan = await db.get(Plan, plan_id)
                if plan is not None:
                    break
                logger.warning(
                    "GalaxyPlanConsumer: plan not found, retrying (attempt={}/3, plan_id={})",
                    attempt + 1, plan_id,
                )
                await asyncio.sleep(0.1 * (attempt + 1))
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
                logger.debug(
                    "GalaxyPlanConsumer skipped: user already seeded",
                    extra={"user_id": str(user_id), "existing_nodes": existing_status_count},
                )
                return

            # WT337：播种 learning_goal 不吃「TOUR 冲刺 {run}」token 名
            # （纯 token → 按创建日兜底命名，播种链路保持可用）。
            from app.services.galaxy.title_sanitizer import clean_display_plan_name, sprint_plan_fallback_name

            await GalaxyBootstrapService(db).seed_from_goal(
                user_id=user_id,
                learning_goal=clean_display_plan_name(plan.name) or sprint_plan_fallback_name(plan.created_at),
                goal_type=getattr(plan.type, "value", plan.type),
            )
