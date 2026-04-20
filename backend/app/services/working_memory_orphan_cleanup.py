from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.working_memory.service import WorkingMemoryService


class WorkingMemoryOrphanCleanupService:
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.working_memory = WorkingMemoryService(redis_client)

    async def run_once(self) -> int:
        result = await self.db.execute(select(ChatSession.id).where(ChatSession.is_active.is_(True)))
        active_session_ids = {str(item) for item in result.scalars().all()}
        return await self.working_memory.cleanup_orphaned_namespaces(active_session_ids=active_session_ids)
