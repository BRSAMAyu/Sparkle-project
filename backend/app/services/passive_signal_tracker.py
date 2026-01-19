"""Passive signal tracking for intervention feedback loops."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention_adaptive import PassiveSignal


class PassiveSignalTracker:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        user_id: UUID,
        signal_type: str,
        intervention_id: Optional[UUID] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[Any] = None,
    ) -> PassiveSignal:
        signal = PassiveSignal(
            user_id=user_id,
            signal_type=signal_type,
            intervention_id=intervention_id,
            context=context,
        )
        if timestamp is not None:
            signal.timestamp = timestamp
        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)
        return signal
