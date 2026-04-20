from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID


T = TypeVar("T")
UserStateFieldName = Literal[
    "commitment_summary",
    "recent_person_mentions",
    "engagement_state",
    "learning_state",
]


@dataclass(frozen=True)
class StateFieldEnvelope(Generic[T]):
    value: T
    computed_at: datetime
    source_snapshot_ids: tuple[str, ...]
    freshness_seconds: int


@dataclass(frozen=True)
class CommitmentSummaryValue:
    overdue_count: int
    next_due_at: datetime | None
    pending_commitment_ids: tuple[str, ...]


@dataclass(frozen=True)
class SocialMentionValue:
    summary: str
    occurred_at: datetime


@dataclass(frozen=True)
class RecentPersonMentionsValue:
    mentions: tuple[SocialMentionValue, ...]
    relationship_count: int


@dataclass(frozen=True)
class EngagementStateValue:
    last_active_at: datetime | None
    session_count_7d: int
    streak: int


@dataclass(frozen=True)
class LearningStateValue:
    within_category_preference: dict[str, Any] | None


@dataclass(frozen=True)
class UserStateV1:
    user_id: UUID
    schema_version: str = "user_state.v1"
    commitment_summary: StateFieldEnvelope[CommitmentSummaryValue] | None = None
    recent_person_mentions: StateFieldEnvelope[RecentPersonMentionsValue] | None = None
    engagement_state: StateFieldEnvelope[EngagementStateValue] | None = None
    learning_state: StateFieldEnvelope[LearningStateValue] | None = None
    emotion_hint: StateFieldEnvelope[None] | None = None

