from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import TrackingEvent
from app.models.user_state import UserStateSnapshot


class EventRetentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def prune_events(self, days: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            update(TrackingEvent)
            .where(TrackingEvent.deleted_at.is_(None))
            .where(TrackingEvent.received_at < cutoff)
            .values(
                deleted_at=datetime.utcnow(),
                payload=None,
                entities=None,
            )
        )
        await self.db.commit()
        return result.rowcount or 0

    async def prune_state_snapshots(self, days: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            update(UserStateSnapshot)
            .where(UserStateSnapshot.deleted_at.is_(None))
            .where(UserStateSnapshot.snapshot_at < cutoff)
            .values(deleted_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount or 0
