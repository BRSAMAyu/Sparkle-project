"""
PlanHealthEventConsumer — Lightweight consumer for plan.health.alerted events.

职责:
  - 记录信号到日志
  - 生成系统更新 (但不与断点1已有的 plan_adjustment_applied 重复)
  - 供后续断点4接行为触发推送

Design rules:
  - action_taken in {"incremental_adjustment_applied", "full_replan_triggered"} 时,
    不额外给用户弹第二条 visible update (断点1 的 PlanAdjustmentApplier 已经做了)
  - 只有当 action_taken 是 cooldown 状态或 none 时才生成系统提醒
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger

from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.services.system_update_service import SystemUpdateService, build_system_update

# Actions where断点1 already handles user-facing notification
_ALREADY_NOTIFIED_ACTIONS = frozenset({
    "incremental_adjustment_applied",
    "full_replan_triggered",
})


class PlanHealthEventConsumer:
    """Consumes plan.health.alerted events and generates appropriate system updates."""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "plan_health_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False

    async def start(self):
        """Start consuming events."""
        await self.event_bus.connect()
        self._running = True

        logger.info(f"PlanHealthEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"plan-health-{id(self)}",
                    callback=self._handle_event,
                )
                break
            except Exception as e:
                logger.error(f"PlanHealthEventConsumer error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop consuming events."""
        self._running = False

    async def _handle_event(self, event: dict):
        """Route events by type."""
        event_type = event.get("event_type")

        if event_type == "plan.health.alerted":
            await self._handle_plan_health_alerted(event)

    async def _handle_plan_health_alerted(self, event: dict):
        """Process plan health alert event."""
        try:
            user_id = event.get("user_id")
            plan_id = event.get("plan_id")
            action_taken = event.get("action_taken", "none")
            severity = event.get("severity", "unknown")

            if not user_id:
                return

            logger.info(
                "PlanHealthAlert consumed: user={}, plan={}, severity={}, action={}",
                user_id, plan_id, severity, action_taken,
            )

            async with AsyncSessionLocal() as db:
                should_generate_visible_update = action_taken not in _ALREADY_NOTIFIED_ACTIONS
                if not should_generate_visible_update:
                    logger.debug(
                        "PlanHealthAlert: skipping visible update (action={} already notified by断点1)",
                        action_taken,
                    )

                # Only generate visible update for cooldown situations
                if should_generate_visible_update and action_taken.endswith("_cooldown_active"):
                    message = self._build_cooldown_message(severity, event.get("reasons", []))
                    update = build_system_update(
                        update_type="plan_health_signal",
                        category="plan_health",
                        title="计划状态观察中",
                        description=message,
                        priority="low" if severity == "warning" else "medium",
                        metadata={
                            "plan_id": plan_id,
                            "severity": severity,
                            "action_taken": action_taken,
                            "silent": True,
                        },
                    )
                    await SystemUpdateService().enqueue(
                        user_id=UUID(user_id),
                        payload=update,
                    )

                # --- Card protocol: create InterventionRecord (breakpoint 3 fix) ---
                try:
                    from app.services.card_protocol.health_intervention_bridge import PlanHealthInterventionBridge
                    bridge = PlanHealthInterventionBridge(db, self.event_bus)
                    record = await bridge.on_plan_health_signal(
                        user_id=UUID(user_id),
                        plan_id=UUID(plan_id),
                        severity=severity,
                        reasons=event.get("reasons", []),
                        action_taken=action_taken,
                        context=event.get("context"),
                    )
                    if record:
                        await db.commit()

                        # --- Delivery Step ---
                        from app.models.card_protocol import DeliveryChannel
                        if record.delivery_channel == DeliveryChannel.IN_APP:
                            update = build_system_update(
                                update_type="intervention_record",
                                category="plan_health",
                                title="系统检测到需要调整",
                                description="您的学习计划存在较大偏差或阻力，系统已生成调整建议。",
                                priority="high" if severity == "critical" else "medium",
                                metadata={
                                    "intervention_id": str(record.id),
                                    "payload": record.diagnosis_payload
                                },
                            )
                            await SystemUpdateService().enqueue(
                                user_id=UUID(user_id),
                                payload=update,
                            )
                        elif record.delivery_channel == DeliveryChannel.PUSH:
                            from app.core.celery_tasks import schedule_push_notification
                            schedule_push_notification.delay(
                                user_id=str(user_id),
                                intervention_id=str(record.id),
                                payload=record.diagnosis_payload or {}
                            )

                except Exception as bridge_exc:
                    await db.rollback()
                    logger.warning("PlanHealth→InterventionRecord bridge failed (non-fatal): {}", bridge_exc)

        except Exception as e:
            logger.error(f"PlanHealthEventConsumer failed: {e}")

    @staticmethod
    def _build_cooldown_message(severity: str, reasons: list[str]) -> str:
        """Build a lightweight message for cooldown state."""
        if severity == "critical":
            return "检测到学习节奏较大偏差，系统正在评估最佳调整方案。"
        return "学习节奏有波动，系统在观察中。"
