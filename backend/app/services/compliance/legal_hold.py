from __future__ import annotations
from datetime import timezone, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import LegalHold


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LegalHoldService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_hold_active(self, user_id: UUID) -> bool:
        stmt = select(LegalHold).where(
            LegalHold.user_id == user_id,
            LegalHold.is_active
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_hold(self, user_id: UUID, admin_id: UUID, case_ref: str, reason: str | None = None) -> LegalHold:
        hold = LegalHold(
            user_id=user_id,
            admin_id=admin_id,
            case_ref=case_ref,
            reason=reason,
            is_active=True
        )
        self.db.add(hold)
        await self.db.commit()
        await self.db.refresh(hold)
        return hold

    async def release_hold(self, hold: LegalHold, released_by: UUID) -> LegalHold:
        hold.is_active = False
        hold.released_by = released_by
        hold.released_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(hold)
        return hold
