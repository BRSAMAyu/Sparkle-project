"""Cache-backed sidecar store for dormant injection sets and outcomes."""

from __future__ import annotations

from typing import Final
from uuid import UUID

from app.core.cache import cache_service
from app.task_assistant.schemas import AssistantOutcome, DormantInjection

_TTL_SECONDS: Final[int] = 60 * 60 * 24 * 7  # 7 days for dormant sidecars
_OUTCOME_TTL_SECONDS: Final[int] = 60 * 60 * 24 * 30  # 30 days for outcomes


class CacheBackedDormantStore:
    """Persist DormantInjection sidecars + AssistantOutcome records in cache."""

    INJECTION_PREFIX: Final[str] = "stage4:ws-d:injection"
    OUTCOME_PREFIX: Final[str] = "stage4:ws-d:outcome"

    @classmethod
    def _injection_key(cls, task_id: UUID, user_id: UUID) -> str:
        return f"{cls.INJECTION_PREFIX}:{user_id}:{task_id}"

    @classmethod
    def _outcome_key(cls, outcome_id: UUID) -> str:
        return f"{cls.OUTCOME_PREFIX}:{outcome_id}"

    # -- injection --

    async def get_injection(
        self, task_id: UUID, user_id: UUID,
    ) -> DormantInjection | None:
        payload = await cache_service.get(self._injection_key(task_id, user_id))
        if not payload:
            return None
        return DormantInjection.model_validate(payload)

    async def save_injection(self, injection: DormantInjection) -> DormantInjection:
        payload = injection.model_dump(mode="json")
        await cache_service.set(
            self._injection_key(injection.task_id, injection.user_id),
            payload,
            ttl=_TTL_SECONDS,
        )
        return injection

    # -- outcome --

    async def save_outcome(self, outcome: AssistantOutcome) -> AssistantOutcome:
        payload = outcome.model_dump(mode="json")
        await cache_service.set(
            self._outcome_key(outcome.id),
            payload,
            ttl=_OUTCOME_TTL_SECONDS,
        )
        return outcome

    async def get_outcome(self, outcome_id: UUID) -> AssistantOutcome | None:
        payload = await cache_service.get(self._outcome_key(outcome_id))
        if not payload:
            return None
        return AssistantOutcome.model_validate(payload)
