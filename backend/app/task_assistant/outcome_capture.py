"""Outcome capture — records assistant turn outcomes for nearline optimization."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from loguru import logger

from app.task_assistant.schemas import AssistantOutcome
from app.task_assistant.store import CacheBackedDormantStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OutcomeCapture:
    """Capture task assistant turn outcomes for nearline next-turn optimization."""

    def __init__(self, store: CacheBackedDormantStore | None = None) -> None:
        self._store = store or CacheBackedDormantStore()

    async def record(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None = None,
        turn_number: int,
        injection_was_used: bool = False,
        user_engaged: bool | None = None,
        latency_ms: float | None = None,
    ) -> AssistantOutcome:
        """Record one assistant outcome for nearline consumption."""
        outcome = AssistantOutcome(
            id=uuid4(),
            task_id=task_id,
            user_id=user_id,
            conversation_id=conversation_id,
            turn_number=turn_number,
            injection_was_used=injection_was_used,
            user_engaged=user_engaged,
            latency_ms=latency_ms,
            created_at=_utcnow(),
        )
        await self._store.save_outcome(outcome)
        logger.debug(
            f"WS-D: outcome captured task={task_id} turn={turn_number} "
            f"used_injection={injection_was_used}"
        )
        return outcome
