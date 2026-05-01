from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.common import AuroraSchemaBase
from app.aurora.runtime_v1.models import AuroraDecisionTelemetry, AuroraScheduledWake, AuroraStateSnapshot
from app.aurora.runtime_v1.state import (
    ActivityProfile,
    AuroraCognitiveSnapshot,
    AuroraIntent,
    AuroraState,
    InformationalTension,
    LatentThread,
    ScheduledWake,
)
from app.config import settings

AuroraStateSnapshotRecord = AuroraStateSnapshot
AuroraScheduledWakeRecord = AuroraScheduledWake
AuroraDecisionTelemetryRecord = AuroraDecisionTelemetry


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _coerce_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class PersistedScheduledWake(AuroraSchemaBase):
    user_id: str
    surface: str
    conversation_id: str
    runtime_session_id: str | None = None
    wake: ScheduledWake
    suppressed_reason: str | None = None
    executed_at: datetime | None = None
    metadata_payload: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class AuroraPersistenceStore:
    def __init__(self, db: AsyncSession, *, enabled: bool | None = None) -> None:
        self.db = db
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_AURORA_RUNTIME_V1 if self._enabled is None else bool(self._enabled)

    async def save_cognitive_snapshot(
        self,
        state: AuroraState,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> AuroraCognitiveSnapshot | None:
        if not self.enabled:
            return None

        latest = await self._load_latest_snapshot_record(state.user_id)
        version = int(getattr(latest, "snapshot_version", 0) or 0) + 1
        now = _utcnow()

        record = AuroraStateSnapshotRecord(
            user_id=_coerce_uuid(state.user_id),
            surface=state.surface,
            conversation_id=state.conversation_id,
            runtime_session_id=state.runtime_session_id,
            snapshot_version=version,
            snapshot_at=now,
            user_model_snapshot=state.user_model_snapshot,
            informational_tensions=[item.model_dump(mode="json") for item in state.informational_tensions],
            current_intent=state.current_intent.model_dump(mode="json") if state.current_intent else None,
            latent_threads=[item.model_dump(mode="json") for item in state.latent_threads],
            activity_profile=state.activity_profile.model_dump(mode="json"),
            last_decision_at=state.last_decision_at,
            runtime_metadata=dict(metadata or {}),
        )
        self.db.add(record)

        await self.db.commit()
        await self.db.refresh(record)
        return self._snapshot_from_record(record)

    async def load_cognitive_snapshot(self, user_id: UUID | str) -> AuroraCognitiveSnapshot | None:
        if not self.enabled:
            return None
        record = await self._load_latest_snapshot_record(user_id)
        if record is None:
            return None
        return self._snapshot_from_record(record)

    async def save_scheduled_wake(
        self,
        *,
        user_id: UUID | str,
        surface: str,
        conversation_id: str,
        wake: ScheduledWake,
        runtime_session_id: str | None = None,
        suppressed_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        executed_at: datetime | None = None,
    ) -> PersistedScheduledWake | None:
        if not self.enabled:
            return None

        result = await self.db.execute(
            select(AuroraScheduledWakeRecord).where(
                AuroraScheduledWakeRecord.wake_id == wake.wake_id,
                AuroraScheduledWakeRecord.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = AuroraScheduledWakeRecord(
                wake_id=wake.wake_id,
                user_id=_coerce_uuid(user_id),
            )
            self.db.add(record)

        payload = dict(getattr(record, "payload", {}) or {})
        payload.update(dict(metadata or {}))
        payload["wake_id"] = wake.wake_id

        record.surface = surface
        record.conversation_id = conversation_id
        record.runtime_session_id = runtime_session_id
        record.scheduled_at = wake.scheduled_at
        record.executed_at = executed_at
        record.status = wake.status
        record.reason = wake.reason
        record.planned_action = wake.planned_action
        record.payload = payload
        record.runtime_metadata = dict(metadata or {})
        record.suppression_reason = suppressed_reason
        if getattr(record, "urgency_score", None) is None:
            record.urgency_score = 0.5
        record.updated_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(record)
        return self._persisted_wake_from_record(record)

    async def load_scheduled_wake(self, wake_id: str) -> PersistedScheduledWake | None:
        if not self.enabled:
            return None

        result = await self.db.execute(
            select(AuroraScheduledWakeRecord).where(
                AuroraScheduledWakeRecord.wake_id == wake_id,
                AuroraScheduledWakeRecord.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return self._persisted_wake_from_record(record)

    async def list_pending_wakes(
        self,
        *,
        due_before: datetime | None = None,
        user_id: UUID | str | None = None,
        limit: int = 100,
    ) -> list[PersistedScheduledWake]:
        if not self.enabled:
            return []

        query = select(AuroraScheduledWakeRecord).where(
            AuroraScheduledWakeRecord.status == "pending",
            AuroraScheduledWakeRecord.deleted_at.is_(None),
        )
        if due_before is not None:
            query = query.where(AuroraScheduledWakeRecord.scheduled_at <= due_before)
        if user_id is not None:
            query = query.where(AuroraScheduledWakeRecord.user_id == _coerce_uuid(user_id))
        query = query.order_by(AuroraScheduledWakeRecord.scheduled_at.asc()).limit(max(1, limit))

        result = await self.db.execute(query)
        return [self._persisted_wake_from_record(item) for item in result.scalars().all()]

    async def mark_wake_status(
        self,
        wake_id: str,
        *,
        status: str,
        suppressed_reason: str | None = None,
        executed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PersistedScheduledWake | None:
        if not self.enabled:
            return None

        result = await self.db.execute(
            select(AuroraScheduledWakeRecord).where(
                AuroraScheduledWakeRecord.wake_id == wake_id,
                AuroraScheduledWakeRecord.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        record.status = status
        record.executed_at = executed_at
        record.suppression_reason = suppressed_reason
        if metadata is not None:
            payload = dict(getattr(record, "payload", {}) or {})
            payload.update(dict(metadata))
            record.payload = payload
            record.runtime_metadata = dict(metadata)
        record.updated_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(record)
        return self._persisted_wake_from_record(record)

    async def _load_latest_snapshot_record(self, user_id: UUID | str) -> AuroraStateSnapshotRecord | None:
        result = await self.db.execute(
            select(AuroraStateSnapshotRecord)
            .where(
                AuroraStateSnapshotRecord.user_id == _coerce_uuid(user_id),
                AuroraStateSnapshotRecord.deleted_at.is_(None),
            )
            .order_by(
                AuroraStateSnapshotRecord.snapshot_at.desc(),
                AuroraStateSnapshotRecord.created_at.desc(),
            )
        )
        return result.scalars().first()

    def _snapshot_from_record(self, record: AuroraStateSnapshotRecord) -> AuroraCognitiveSnapshot:
        runtime_metadata = dict(getattr(record, "runtime_metadata", {}) or {})
        return AuroraCognitiveSnapshot(
            user_id=str(record.user_id),
            user_model_snapshot=dict(record.user_model_snapshot or {}),
            informational_tensions=[
                InformationalTension.model_validate(item)
                for item in (record.informational_tensions or [])
                if isinstance(item, dict)
            ],
            current_intent=AuroraIntent.model_validate(record.current_intent) if isinstance(record.current_intent, dict) else None,
            latent_threads=[
                LatentThread.model_validate(item)
                for item in (record.latent_threads or [])
                if isinstance(item, dict)
            ],
            activity_profile=ActivityProfile.model_validate(record.activity_profile or {}),
            last_surface=record.surface,
            last_conversation_id=record.conversation_id,
            last_runtime_session_id=record.runtime_session_id,
            last_decision_at=record.last_decision_at,
            updated_at=record.snapshot_at,
            snapshot_version=int(record.snapshot_version or runtime_metadata.get("snapshot_version") or 1),
        )

    def _persisted_wake_from_record(self, record: AuroraScheduledWakeRecord) -> PersistedScheduledWake:
        payload = dict(getattr(record, "payload", {}) or {})
        wake_id = str(getattr(record, "wake_id", None) or payload.get("wake_id") or record.id)
        return PersistedScheduledWake(
            user_id=str(record.user_id),
            surface=record.surface,
            conversation_id=record.conversation_id,
            runtime_session_id=getattr(record, "runtime_session_id", None),
            wake=ScheduledWake(
                wake_id=wake_id,
                scheduled_at=record.scheduled_at,
                reason=record.reason,
                planned_action=record.planned_action,
                status=record.status,
            ),
            suppressed_reason=getattr(record, "suppression_reason", None),
            executed_at=record.executed_at,
            metadata_payload=payload,
            updated_at=record.updated_at,
        )
