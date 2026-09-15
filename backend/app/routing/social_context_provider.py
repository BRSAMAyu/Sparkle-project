from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class FrozenSocialMention:
    summary: str
    occurred_at: datetime


@dataclass(frozen=True)
class FrozenSocialSnapshot:
    recent_person_mentions: list[FrozenSocialMention]
    pending_commitments_count: int
    relationship_count: int

    def to_prompt_payload(self) -> dict[str, object]:
        return {
            "recent_person_mentions": [
                {
                    "summary": item.summary[:48],
                    "occurred_at": item.occurred_at.isoformat(),
                }
                for item in self.recent_person_mentions[:3]
            ],
            "pending_commitments_count": self.pending_commitments_count,
            "relationship_count": self.relationship_count,
        }


class SocialContextProvider(Protocol):
    async def fetch(self, user_id: UUID, scope_hint: str | None = None) -> FrozenSocialSnapshot:
        ...

    async def fetch_social_snapshot(self, user_id: UUID) -> FrozenSocialSnapshot:
        ...
