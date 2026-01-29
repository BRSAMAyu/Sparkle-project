from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_pack import ContextPackRun


class ContextPackTelemetryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_run(
        self,
        *,
        user_id: UUID,
        intent: str,
        budgets: dict[str, Any],
        token_usage: dict[str, Any],
        memory_counts: dict[str, Any],
        evidence_score_avg: float | None,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> UUID:
        record = ContextPackRun(
            user_id=user_id,
            intent=intent,
            budgets=budgets,
            token_usage=token_usage,
            memory_counts=memory_counts,
            evidence_score_avg=evidence_score_avg,
            request_id=request_id,
            trace_id=trace_id,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record.id
