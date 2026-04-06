from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.user_insight_state import InsightSignalEvidence


@dataclass(frozen=True)
class InsightSignalSpec:
    signal_id: str
    family: str
    label: str
    source: str
    surfaces: list[str] = field(default_factory=list)
    description: str = ""
    default_confidence: float = 0.7
    default_freshness: str = "medium"


INSIGHT_SIGNAL_REGISTRY: dict[str, InsightSignalSpec] = {
    "error_summary": InsightSignalSpec(
        signal_id="error_summary",
        family="learning_pain",
        label="Recent error pressure",
        source="error_book",
        surfaces=["orchestration", "planning"],
        description="Summarizes recent error burden and weak-subject distribution.",
        default_confidence=0.9,
        default_freshness="high",
    ),
    "recent_errors": InsightSignalSpec(
        signal_id="recent_errors",
        family="learning_pain",
        label="Recent concrete errors",
        source="error_book",
        surfaces=["orchestration", "planning"],
        description="Concrete recent mistakes that should shape immediate help.",
        default_confidence=0.9,
        default_freshness="high",
    ),
    "recent_mastery_changes": InsightSignalSpec(
        signal_id="recent_mastery_changes",
        family="learning_progress",
        label="Recent mastery wins",
        source="knowledge_progress",
        surfaces=["orchestration", "planning"],
        description="Recent mastery gains that should shape reinforcement and pacing.",
        default_confidence=0.85,
        default_freshness="high",
    ),
    "achievement_motivation_response": InsightSignalSpec(
        signal_id="achievement_motivation_response",
        family="achievement",
        label="Achievement motivation response",
        source="achievement_signals",
        surfaces=["orchestration", "planning", "transparency", "personalization"],
        description="Which achievement framing appears to motivate the user best.",
        default_confidence=0.78,
    ),
    "achievement_pace_style": InsightSignalSpec(
        signal_id="achievement_pace_style",
        family="achievement",
        label="Achievement pace style",
        source="achievement_signals",
        surfaces=["orchestration", "planning", "transparency", "personalization"],
        description="Whether the user tends to sustain steady or sprint-like progress.",
        default_confidence=0.74,
    ),
    "achievement_peak_hours": InsightSignalSpec(
        signal_id="achievement_peak_hours",
        family="achievement",
        label="Achievement peak hours",
        source="achievement_signals",
        surfaces=["orchestration", "planning", "transparency", "scheduling"],
        description="Hours where achievement unlocks tend to cluster.",
        default_confidence=0.73,
    ),
    "achievement_reward_sensitivity": InsightSignalSpec(
        signal_id="achievement_reward_sensitivity",
        family="achievement",
        label="Achievement reward sensitivity",
        source="achievement_signals",
        surfaces=["orchestration", "planning", "transparency", "personalization"],
        description="How sensitive the user appears to be to reward framing.",
        default_confidence=0.72,
    ),
    "calendar_density": InsightSignalSpec(
        signal_id="calendar_density",
        family="calendar",
        label="Calendar density",
        source="calendar_events",
        surfaces=["orchestration", "planning", "scheduling"],
        description="How compressed the user's recent calendar has been.",
        default_confidence=0.76,
    ),
    "calendar_recurring_windows": InsightSignalSpec(
        signal_id="calendar_recurring_windows",
        family="calendar",
        label="Recurring calendar windows",
        source="calendar_events",
        surfaces=["orchestration", "planning", "scheduling"],
        description="Repeated class-like or routine time windows inferred from calendar history.",
        default_confidence=0.79,
    ),
    "exam_urgency": InsightSignalSpec(
        signal_id="exam_urgency",
        family="calendar",
        label="Exam urgency",
        source="preferences",
        surfaces=["orchestration", "planning", "scheduling"],
        description="Explicit or inferred exam pressure that should affect planning urgency.",
        default_confidence=0.82,
    ),
    "peak_focus_hours": InsightSignalSpec(
        signal_id="peak_focus_hours",
        family="calendar",
        label="Peak focus hours",
        source="focus_sessions",
        surfaces=["orchestration", "planning", "scheduling", "transparency"],
        description="Hours where focus completion is strongest.",
        default_confidence=0.85,
    ),
    "inactive_push_hours": InsightSignalSpec(
        signal_id="inactive_push_hours",
        family="calendar",
        label="Inactive push hours",
        source="push_feedback",
        surfaces=["orchestration", "planning", "scheduling", "transparency"],
        description="Hours that are repeatedly low-response or interruption-unfriendly.",
        default_confidence=0.8,
    ),
    "workflow_tool_affinity": InsightSignalSpec(
        signal_id="workflow_tool_affinity",
        family="workflow",
        label="Workflow tool affinity",
        source="tool_history",
        surfaces=["orchestration", "planning"],
        description="Tools the user repeatedly succeeds with and returns to.",
        default_confidence=0.77,
    ),
    "workflow_tool_reliability": InsightSignalSpec(
        signal_id="workflow_tool_reliability",
        family="workflow",
        label="Workflow reliability",
        source="tool_history",
        surfaces=["orchestration", "planning"],
        description="How reliable the user's recent tool-mediated workflow has been.",
        default_confidence=0.74,
    ),
    "capsule_depth_preference": InsightSignalSpec(
        signal_id="capsule_depth_preference",
        family="content",
        label="Capsule depth preference",
        source="capsule_favorites",
        surfaces=["orchestration", "planning"],
        description="Depth level the user repeatedly saves for later.",
        default_confidence=0.7,
    ),
    "capsule_subject_affinity": InsightSignalSpec(
        signal_id="capsule_subject_affinity",
        family="content",
        label="Capsule subject affinity",
        source="capsule_favorites",
        surfaces=["orchestration", "planning"],
        description="Subjects the user repeatedly favorites in capsule form.",
        default_confidence=0.72,
    ),
    "accountability_support": InsightSignalSpec(
        signal_id="accountability_support",
        family="community",
        label="Accountability support",
        source="accountability",
        surfaces=["orchestration", "planning", "transparency"],
        description="Whether the user currently has a live accountability support loop.",
        default_confidence=0.75,
    ),
    "accountability_rhythm": InsightSignalSpec(
        signal_id="accountability_rhythm",
        family="community",
        label="Accountability rhythm",
        source="accountability",
        surfaces=["orchestration", "planning", "transparency"],
        description="How actively the user is engaging in accountability check-ins.",
        default_confidence=0.7,
    ),
}


def build_signal_evidence(
    signal_id: str,
    *,
    value: Any,
    confidence: float | None = None,
    freshness: str | None = None,
    status: str = "live",
    explanation: str | None = None,
) -> InsightSignalEvidence:
    spec = INSIGHT_SIGNAL_REGISTRY[signal_id]
    return InsightSignalEvidence(
        signal_id=signal_id,
        family=spec.family,
        label=spec.label,
        source=spec.source,
        value=value,
        confidence=float(confidence if confidence is not None else spec.default_confidence),
        freshness=str(freshness or spec.default_freshness),
        surfaces=list(spec.surfaces),
        status=status,
        explanation=explanation or spec.description,
    )
