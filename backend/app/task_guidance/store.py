"""Cache-backed persistence skeleton for TaskGuidance sidecar objects."""

from __future__ import annotations

from typing import Final
from uuid import UUID

from app.core.cache import cache_service
from app.task_guidance.schemas import TaskGuidance, TaskGuidanceAudience

_GUIDANCE_TTL_SECONDS: Final[int] = 60 * 60 * 24 * 30


class CacheBackedTaskGuidanceStore:
    """Persist TaskGuidance sidecars in the existing cache substrate."""

    RECORD_PREFIX: Final[str] = "stage4:task_guidance:record"
    TASK_AUDIENCE_PREFIX: Final[str] = "stage4:task_guidance:task"

    @classmethod
    def _record_key(cls, guidance_id: UUID) -> str:
        return f"{cls.RECORD_PREFIX}:{guidance_id}"

    @classmethod
    def _task_audience_key(cls, task_id: UUID, audience: TaskGuidanceAudience) -> str:
        return f"{cls.TASK_AUDIENCE_PREFIX}:{task_id}:{audience.value}"

    async def get(self, guidance_id: UUID) -> TaskGuidance | None:
        payload = await cache_service.get(self._record_key(guidance_id))
        if not payload:
            return None
        return TaskGuidance.model_validate(payload)

    async def get_for_task(self, task_id: UUID, audience: TaskGuidanceAudience) -> TaskGuidance | None:
        guidance_id = await cache_service.get(self._task_audience_key(task_id, audience))
        if not guidance_id:
            return None
        return await self.get(UUID(str(guidance_id)))

    async def upsert(self, guidance: TaskGuidance) -> TaskGuidance:
        payload = guidance.model_dump(mode="json")
        await cache_service.set(
            self._record_key(guidance.id),
            payload,
            ttl=_GUIDANCE_TTL_SECONDS,
        )
        await cache_service.set(
            self._task_audience_key(guidance.task_id, guidance.audience),
            str(guidance.id),
            ttl=_GUIDANCE_TTL_SECONDS,
        )
        return guidance
