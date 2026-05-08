from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.user import UserDevice
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
from app.services.push_delivery_service import PushDeliveryService
from app.services.push_policy_compiler import PushDecision, PushPolicyCompiler
from app.services.user_push_opt_in_service import UserPushOptInService
from app.state_aggregator.service import StateAggregatorService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class StateDrivenPushService:
    def __init__(self, db):
        self.db = db
        self.kill_switches = AuroraStage18KillSwitchService()
        self.aggregator = StateAggregatorService(db)
        self.compiler = PushPolicyCompiler()
        self.delivery_service = PushDeliveryService(db)
        self.opt_in_service = UserPushOptInService(db)

    async def preview_decision(self, user_id: UUID, *, now: datetime | None = None) -> PushDecision | None:
        if not await self.kill_switches.is_enabled("aggregator_enabled"):
            return None
        if not await self.kill_switches.is_enabled("push_policy_enabled"):
            return None
        reference_time = now or _utcnow()
        user_state = await self.aggregator.get_user_state(
            user_id=user_id,
            required_fields=("commitment_summary", "engagement_state"),
            now=reference_time,
        )
        opt_in = await self.opt_in_service.get_or_create(user_id)
        recent_count = await self.delivery_service.recent_delivery_count_24h(user_id, now=reference_time)
        dismissal_counts = await self.delivery_service.category_dismissal_counts_7d(user_id, now=reference_time)
        dismissed_categories = {category for category, count in dismissal_counts.items() if count > 0}
        device_context = await self._active_device_context(user_id)
        return self.compiler.compile(
            user_state=user_state,
            push_opt_in=opt_in,
            recent_delivery_count_24h=recent_count,
            dismissed_categories_7d=dismissed_categories,
            category_dismissal_counts_7d=dismissal_counts,
            device_context=device_context,
            now=reference_time,
        )

    async def compile_and_deliver(self, user_id: UUID, *, now: datetime | None = None):
        decision = await self.preview_decision(user_id, now=now)
        if decision is None:
            return None
        return await self.delivery_service.deliver_decision(user_id=user_id, decision=decision)

    async def _active_device_context(self, user_id: UUID) -> dict[str, object]:
        result = await self.db.execute(
            select(UserDevice)
            .where(
                UserDevice.user_id == user_id,
                UserDevice.is_active,
            )
            .order_by(UserDevice.last_used_at.desc())
        )
        devices = list(result.scalars().all())
        if not devices:
            return {"active_device_count": 0, "platforms": []}

        platforms = sorted({str(device.platform) for device in devices if device.platform})
        last_active = devices[0]
        return {
            "active_device_count": len(devices),
            "platforms": platforms,
            "last_active_device_id": str(last_active.device_id),
            "last_active_at": last_active.last_used_at.isoformat() if last_active.last_used_at else None,
        }
