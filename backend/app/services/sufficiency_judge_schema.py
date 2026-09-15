from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


ScoreBucket = Literal[0.0, 0.5, 1.0]


@dataclass(frozen=True)
class SufficiencyScore:
    score: float
    missing_dimensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SufficiencyJudgment:
    task_sufficiency: SufficiencyScore
    context_sufficiency: SufficiencyScore
    computed_at: datetime = field(default_factory=_utcnow)
    judge_version: str = "v1"


@dataclass(frozen=True)
class CurrentTurnParseResult:
    intent: str
    intent_confidence: float
    information_sufficient: bool
    target_object_resolved: bool
    constraint_explicit: bool
