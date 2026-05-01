from __future__ import annotations

import inspect
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from app.aurora.runtime_v1.control_surface import ControlSurfaceService
from app.aurora.runtime_v1.persistence import AuroraPersistenceStore, PersistedScheduledWake
from app.aurora.runtime_v1.state import ScheduledWake
from app.config import settings


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AuroraWakeScheduler:
    WAKE_QUEUE_KEY = "aurora:wake_queue"

    def __init__(
        self,
        db,
        redis=None,
        *,
        persistence_store: AuroraPersistenceStore | None = None,
        control_surface_service: ControlSurfaceService | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.persistence_store = persistence_store or AuroraPersistenceStore(db, enabled=enabled)
        self.control_surface_service = control_surface_service or ControlSurfaceService(db, redis, enabled=enabled)
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return settings.ENABLE_AURORA_RUNTIME_V1 if self._enabled is None else bool(self._enabled)

    async def schedule_wake(
        self,
        user_id: UUID | str,
        *,
        surface: str,
        conversation_id: str,
        wake: ScheduledWake,
        runtime_session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PersistedScheduledWake | None:
        if not self.enabled:
            return None

        reading = await self.control_surface_service.read_control_surface(user_id)
        status = wake.status
        suppressed_reason: str | None = None

        if reading.hard_bounds.is_action_disabled("proactive_follow_up") or reading.hard_bounds.is_action_disabled(
            wake.planned_action
        ):
            status = "suppressed"
            suppressed_reason = "disabled_action"
        elif reading.hard_bounds.is_within_dnd(wake.scheduled_at):
            status = "suppressed"
            suppressed_reason = "dnd_window"

        persisted = await self.persistence_store.save_scheduled_wake(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
            runtime_session_id=runtime_session_id,
            wake=wake.model_copy(update={"status": status}),
            suppressed_reason=suppressed_reason,
            metadata=metadata,
        )
        if persisted is None:
            return None

        if persisted.wake.status == "pending":
            await self._enqueue(persisted)
        else:
            await self._dequeue(persisted.wake.wake_id)
        return persisted

    async def list_due_wakes(
        self,
        *,
        due_before: datetime | None = None,
        user_id: UUID | str | None = None,
        limit: int = 100,
    ) -> list[PersistedScheduledWake]:
        if not self.enabled:
            return []
        return await self.persistence_store.list_pending_wakes(
            due_before=due_before or _utcnow(),
            user_id=user_id,
            limit=limit,
        )

    async def mark_executed(
        self,
        wake_id: str,
        *,
        executed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PersistedScheduledWake | None:
        if not self.enabled:
            return None
        persisted = await self.persistence_store.mark_wake_status(
            wake_id,
            status="executed",
            executed_at=executed_at or _utcnow(),
            metadata=metadata,
        )
        if persisted is not None:
            await self._dequeue(wake_id)
        return persisted

    async def cancel_wake(
        self,
        wake_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> PersistedScheduledWake | None:
        if not self.enabled:
            return None
        persisted = await self.persistence_store.mark_wake_status(
            wake_id,
            status="cancelled",
            metadata=metadata,
        )
        if persisted is not None:
            await self._dequeue(wake_id)
        return persisted

    async def _enqueue(self, wake: PersistedScheduledWake) -> None:
        if self.redis is None:
            return
        await self._redis_call(
            "zadd",
            self.WAKE_QUEUE_KEY,
            {wake.wake.wake_id: wake.wake.scheduled_at.timestamp()},
        )

    async def _dequeue(self, wake_id: str) -> None:
        if self.redis is None:
            return
        await self._redis_call("zrem", self.WAKE_QUEUE_KEY, wake_id)

    async def _redis_call(self, method_name: str, *args, **kwargs):
        method = getattr(self.redis, method_name, None)
        if method is None:
            return None
        result = method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result
