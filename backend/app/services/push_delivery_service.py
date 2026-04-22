from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.push_delivery_record import PushDeliveryRecord
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
from app.services.notification_push_service import NotificationPushService
from app.services.push_policy_compiler import PushDecision, PushPolicyCompiler
from app.services.user_push_opt_in_service import UserPushOptInService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PushChannel:
    async def deliver(self, *, user_id: UUID, decision: PushDecision) -> PushDeliveryRecord:
        raise NotImplementedError


class WebSocketPushChannel(PushChannel):
    def __init__(self, db: AsyncSession):
        self.db = db
        self.push_service = NotificationPushService(db)

    async def deliver(self, *, user_id: UUID, decision: PushDecision) -> PushDeliveryRecord:
        notification = await self.push_service.create_and_push(
            user_id=user_id,
            title=decision.title,
            content=decision.body,
            notification_type="aurora_push",
            data={
                "source_type": "push",
                "policy_id": decision.policy_id,
                "category": decision.category,
                "evidence_token": decision.evidence_token,
                "message_template_id": decision.message_template_id,
                "delivery_channel": "websocket",
                "context_variables": decision.metadata,
            },
            priority="high",
        )
        record = PushDeliveryRecord(
            user_id=user_id,
            notification_id=notification.id,
            policy_id=decision.policy_id,
            category=decision.category,
            message_template_id=decision.message_template_id,
            title=decision.title,
            body=decision.body,
            evidence_token=decision.evidence_token,
            delivery_channel="websocket",
            status="sent",
            scheduled_send_at=decision.scheduled_send_at,
            sent_at=_utcnow(),
            retractable_until=_utcnow() + timedelta(hours=24),
            metadata_payload=decision.metadata,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        notification.data = {
            **(notification.data or {}),
            "delivery_record_id": str(record.id),
            "retractable_until": record.retractable_until.isoformat() if record.retractable_until else None,
        }
        await self.db.commit()
        return record


class PushDeliveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kill_switches = AuroraStage18KillSwitchService()
        self.opt_in_service = UserPushOptInService(db)
        self.channel = WebSocketPushChannel(db)

    async def recent_delivery_count_24h(self, user_id: UUID, *, now: datetime | None = None) -> int:
        reference_time = now or _utcnow()
        result = await self.db.execute(
            select(func.count(PushDeliveryRecord.id)).where(
                PushDeliveryRecord.user_id == user_id,
                PushDeliveryRecord.sent_at.is_not(None),
                PushDeliveryRecord.sent_at >= reference_time - timedelta(hours=24),
                PushDeliveryRecord.retracted_at.is_(None),
            )
        )
        return int(result.scalar() or 0)

    async def dismissed_categories_7d(self, user_id: UUID, *, now: datetime | None = None) -> set[str]:
        reference_time = now or _utcnow()
        result = await self.db.execute(
            select(PushDeliveryRecord.category).where(
                PushDeliveryRecord.user_id == user_id,
                PushDeliveryRecord.dismissed_at.is_not(None),
                PushDeliveryRecord.dismissed_at >= reference_time - timedelta(days=7),
            )
        )
        return {str(value) for value in result.scalars().all()}

    async def deliver_decision(self, *, user_id: UUID, decision: PushDecision) -> PushDeliveryRecord | None:
        if not await self.kill_switches.is_live("push_delivery_enabled"):
            return None
        if not await self._passes_delivery_guards(user_id=user_id, decision=decision):
            return None
        return await self.channel.deliver(user_id=user_id, decision=decision)

    async def list_active_records(self, user_id: UUID) -> list[PushDeliveryRecord]:
        result = await self.db.execute(
            select(PushDeliveryRecord)
            .where(
                PushDeliveryRecord.user_id == user_id,
                PushDeliveryRecord.deleted_at.is_(None),
                PushDeliveryRecord.retracted_at.is_(None),
                PushDeliveryRecord.created_at >= _utcnow() - timedelta(days=30),
            )
            .order_by(desc(PushDeliveryRecord.created_at))
        )
        return list(result.scalars().all())

    async def apply_action(self, *, user_id: UUID, notification_id: UUID, action: str) -> PushDeliveryRecord | None:
        result = await self.db.execute(
            select(PushDeliveryRecord).where(
                PushDeliveryRecord.user_id == user_id,
                PushDeliveryRecord.notification_id == notification_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        now = _utcnow()
        if action == "seen":
            record.read_at = now
            record.status = "read"
        elif action == "dismissed":
            record.dismissed_at = now
            record.status = "dismissed"
            record.deleted_at = now
        elif action == "acted":
            record.acted_at = now
            record.status = "acted"
        elif action == "retract":
            record.retracted_at = now
            record.status = "retracted"
            record.deleted_at = now
        elif action == "disable_category":
            record.category_disabled = True
            await self.opt_in_service.disable_category(user_id, record.category)
            record.status = "dismissed"
            record.dismissed_at = now
            record.deleted_at = now

        notification = await self.db.get(Notification, record.notification_id) if record.notification_id else None
        if notification is not None:
            if action in {"seen", "dismissed", "acted", "disable_category"}:
                notification.is_read = True
                notification.read_at = now
            if action in {"dismissed", "disable_category", "retract"}:
                notification.deleted_at = now
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def _passes_delivery_guards(self, *, user_id: UUID, decision: PushDecision) -> bool:
        opt_in = await self.opt_in_service.get_or_create(user_id)
        if not getattr(opt_in, "enabled", False):
            return False
        if decision.category == "commitment_follow_up" and not getattr(opt_in, "allow_commitment_follow_up", False):
            return False
        if decision.category == "engagement_recovery" and not getattr(opt_in, "allow_engagement_recovery", False):
            return False

        now = _utcnow()
        if await self.recent_delivery_count_24h(user_id, now=now) >= PushPolicyCompiler.DAILY_CAP:
            return False
        if decision.scheduled_send_at > now:
            return False
        if self._is_in_quiet_hours(now=now, quiet_start=opt_in.quiet_hours_start, quiet_end=opt_in.quiet_hours_end):
            return False
        return True

    @staticmethod
    def _is_in_quiet_hours(*, now: datetime, quiet_start: str, quiet_end: str) -> bool:
        start_hour, start_minute = (int(part) for part in quiet_start.split(":"))
        end_hour, end_minute = (int(part) for part in quiet_end.split(":"))
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        return current_minutes >= start_minutes or current_minutes < end_minutes
