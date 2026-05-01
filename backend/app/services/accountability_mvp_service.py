from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import EpisodicMemory
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class PendingCommitment:
    id: str
    summary: str
    due_at: datetime
    subject_type: str
    evidence_token: str | None
    resolved_at: datetime | None


class AccountabilityMvpService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)

    async def list_pending_commitments(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> list[PendingCommitment]:
        records = await self.memory_service.list_pending_commitments(user_id, now=now or _utcnow())
        return [self._serialize(record) for record in records]

    async def resolve_commitment(
        self,
        *,
        user_id: UUID,
        memory_id: UUID,
    ) -> PendingCommitment | None:
        record = await self.memory_service.resolve_commitment(user_id=user_id, memory_id=memory_id)
        if record is None:
            return None
        return self._serialize(record)

    @staticmethod
    def _serialize(record: EpisodicMemory) -> PendingCommitment:
        return PendingCommitment(
            id=str(record.id),
            summary=record.summary,
            due_at=record.due_at or record.occurred_at,
            subject_type=record.subject_type,
            evidence_token=record.evidence_token,
            resolved_at=record.resolved_at,
        )
