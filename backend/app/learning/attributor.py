"""Attribution detection for successful strategy trajectories."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class AttributionSignalBundle:
    """Signals indicating a candidate successful trajectory."""

    user_id: UUID
    scenario_pack_id: str
    goal_achieved: bool
    task_completion_streak: int
    positive_feedback_score: float
    behavioral_improvement_score: float
    outcome_summary: str
    interventions: list[str] = field(default_factory=list)
    context_excerpt: str = ""
    subject_tags: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AttributionCandidate:
    """Detected attribution event ready for distillation."""

    user_id: UUID
    scenario_pack_id: str
    detected_at: datetime
    success_score: float
    outcome_summary: str
    interventions: tuple[str, ...]
    context_excerpt: str
    subject_tags: tuple[str, ...]
    source_refs: tuple[str, ...]


def detect_successful_attribution(bundle: AttributionSignalBundle) -> AttributionCandidate | None:
    """Detect high-signal success trajectories that should enter distillation."""

    streak_score = min(1.0, bundle.task_completion_streak / 5.0)
    success_score = round(
        (0.4 if bundle.goal_achieved else 0.0)
        + (0.25 * streak_score)
        + (0.2 * max(0.0, min(bundle.positive_feedback_score, 1.0)))
        + (0.15 * max(0.0, min(bundle.behavioral_improvement_score, 1.0))),
        3,
    )
    if not bundle.goal_achieved:
        return None
    if bundle.task_completion_streak < 3:
        return None
    if bundle.positive_feedback_score < 0.6:
        return None
    if bundle.behavioral_improvement_score < 0.5:
        return None
    return AttributionCandidate(
        user_id=bundle.user_id,
        scenario_pack_id=bundle.scenario_pack_id,
        detected_at=_utcnow(),
        success_score=success_score,
        outcome_summary=bundle.outcome_summary.strip(),
        interventions=tuple(item.strip() for item in bundle.interventions if item.strip()),
        context_excerpt=bundle.context_excerpt.strip(),
        subject_tags=tuple(item.strip() for item in bundle.subject_tags if item.strip()),
        source_refs=tuple(item.strip() for item in bundle.source_refs if item.strip()),
    )
