from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WorkingMemoryEntry:
    entry_id: str
    user_id: str
    session_id: str
    text: str
    semantic_key: str
    salience_score: float
    mention_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    source_turn_ids: tuple[str, ...]
    subject_type: str
    confidence: float
    evidence_token: str
    occurred_at: datetime
    due_at: datetime | None = None
    source_lane: str = "working_memory"
    confirmation_status: str = "none"
    consolidated_to_l1_id: str | None = None
    rejected: bool = False


@dataclass(frozen=True)
class WorkingMemorySnapshotItem:
    summary: str
    subject_type: str
    salience_score: float
    mention_count: int
    last_seen_at: datetime
    consolidated: bool = False
