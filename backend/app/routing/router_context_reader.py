from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.routing.social_context_provider import FrozenSocialMention, FrozenSocialSnapshot, SocialContextProvider
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RouterContextReader(SocialContextProvider):
    """Stage 17 prompt-only social snapshot reader.

    This data is prompt context only, not a routing decision signal. Any
    if/switch logic based on it requires Stage 19B Sufficiency Judge
    acceptance.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)

    async def fetch(self, user_id: UUID, scope_hint: str | None = None) -> FrozenSocialSnapshot:
        del scope_hint
        seven_days_ago = _utcnow() - timedelta(days=7)
        recent_social = await self.memory_service.list_recent_episodic(
            user_id=user_id,
            limit=12,
            start=seven_days_ago,
            subject_types=["person_mention", "relationship"],
        )
        mentions = [
            FrozenSocialMention(summary=record.summary, occurred_at=record.occurred_at)
            for record in recent_social
            if record.subject_type == "person_mention"
        ][:3]
        relationship_count = sum(1 for record in recent_social if record.subject_type == "relationship")
        pending_commitments = await self.memory_service.list_pending_commitments(user_id)
        return FrozenSocialSnapshot(
            recent_person_mentions=mentions,
            pending_commitments_count=len(pending_commitments),
            relationship_count=relationship_count,
        )

    async def fetch_social_snapshot(self, user_id: UUID) -> FrozenSocialSnapshot:
        return await self.fetch(user_id=user_id, scope_hint="router_prompt")
