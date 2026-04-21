from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID


T = TypeVar("T")
UserStateFieldName = Literal[
    "commitment_summary",
    "pending_policies",
    "recent_reflections",
    "recent_scenes",
    "foresight_hint",
    "recent_person_mentions",
    "engagement_state",
    "learning_state",
    "working_memory_snapshot",
    "task_sufficiency_summary",
    "context_sufficiency_summary",
    "active_skills_summary",
    "achievement_summary",
    "calendar_context",
    "traits_prior",
    "srl_phase",
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
class PendingPoliciesSummaryValue:
    count: int
    next_trigger_at: datetime | None
    policy_ids: tuple[str, ...]


@dataclass(frozen=True)
class RecentReflectionsSummaryValue:
    count: int
    last_category: str | None
    last_at: datetime | None


@dataclass(frozen=True)
class RecentSceneItemValue:
    scene_id: str
    title: str
    time_start: datetime
    time_end: datetime
    member_count: int
    quality_score: float


@dataclass(frozen=True)
class RecentScenesSummaryValue:
    items: tuple[RecentSceneItemValue, ...]


@dataclass(frozen=True)
class ForesightConfidenceItemValue:
    dim: str
    confidence: float


@dataclass(frozen=True)
class ForesightHintSummaryValue:
    hint_text: str | None
    generated_at: datetime | None
    deviation_count: int
    attractor_confidences: tuple[ForesightConfidenceItemValue, ...]


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
class WorkingMemorySnapshotValueItem:
    summary: str
    subject_type: str
    mention_count: int
    consolidated: bool
    last_seen_at: datetime


@dataclass(frozen=True)
class WorkingMemorySnapshotValue:
    active_session_id: str | None
    items: tuple[WorkingMemorySnapshotValueItem, ...]


@dataclass(frozen=True)
class SufficiencySummaryValue:
    score: float
    top_missing_dimensions: tuple[str, ...]


@dataclass(frozen=True)
class ActiveSkillSummaryItemValue:
    skill_id: str
    name: str
    activation_match_score: float


@dataclass(frozen=True)
class ActiveSkillsSummaryValue:
    items: tuple[ActiveSkillSummaryItemValue, ...]


@dataclass(frozen=True)
class AchievementUnlockSummaryItemValue:
    achievement_id: str
    name: str
    rarity: str
    unlocked_at: datetime


@dataclass(frozen=True)
class AchievementProgressSummaryItemValue:
    achievement_id: str
    name: str
    progress: float


@dataclass(frozen=True)
class AchievementSummaryValue:
    recent_unlocks: tuple[AchievementUnlockSummaryItemValue, ...]
    in_progress_achievements: tuple[AchievementProgressSummaryItemValue, ...]
    total_achievement_score: float


@dataclass(frozen=True)
class CalendarDeadlineItemValue:
    title: str
    start_time: datetime
    end_time: datetime
    source: str


@dataclass(frozen=True)
class CalendarTimeBlockItemValue:
    start: str
    end: str


@dataclass(frozen=True)
class CalendarContextValue:
    upcoming_deadlines: tuple[CalendarDeadlineItemValue, ...]
    time_blocks_today: tuple[CalendarTimeBlockItemValue, ...]
    workload_density: str
    exam_urgency: dict[str, Any] | None


@dataclass(frozen=True)
class TraitPriorDimensionValue:
    dim: str
    value: float
    confidence: float
    source: str


@dataclass(frozen=True)
class TraitsPriorSummaryValue:
    items: tuple[TraitPriorDimensionValue, ...]


@dataclass(frozen=True)
class SRLPhaseSummaryValue:
    current_phase: str
    phase_started_at: datetime | None
    confidence: float
    source: str


@dataclass(frozen=True)
class UserStateV1:
    user_id: UUID
    schema_version: str = "user_state.v1.10"
    commitment_summary: StateFieldEnvelope[CommitmentSummaryValue] | None = None
    pending_policies: StateFieldEnvelope[PendingPoliciesSummaryValue] | None = None
    recent_reflections: StateFieldEnvelope[RecentReflectionsSummaryValue] | None = None
    recent_scenes: StateFieldEnvelope[RecentScenesSummaryValue] | None = None
    foresight_hint: StateFieldEnvelope[ForesightHintSummaryValue] | None = None
    recent_person_mentions: StateFieldEnvelope[RecentPersonMentionsValue] | None = None
    engagement_state: StateFieldEnvelope[EngagementStateValue] | None = None
    learning_state: StateFieldEnvelope[LearningStateValue] | None = None
    working_memory_snapshot: StateFieldEnvelope[WorkingMemorySnapshotValue] | None = None
    task_sufficiency_summary: StateFieldEnvelope[SufficiencySummaryValue] | None = None
    context_sufficiency_summary: StateFieldEnvelope[SufficiencySummaryValue] | None = None
    active_skills_summary: StateFieldEnvelope[ActiveSkillsSummaryValue] | None = None
    achievement_summary: StateFieldEnvelope[AchievementSummaryValue] | None = None
    calendar_context: StateFieldEnvelope[CalendarContextValue] | None = None
    traits_prior: StateFieldEnvelope[TraitsPriorSummaryValue] | None = None
    srl_phase: StateFieldEnvelope[SRLPhaseSummaryValue] | None = None
    emotion_hint: StateFieldEnvelope[None] | None = None
