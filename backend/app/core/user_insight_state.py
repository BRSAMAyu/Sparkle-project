from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


class InsightSignalEvidence(BaseModel):
    signal_id: str
    family: str
    label: str
    source: str
    value: Any = None
    confidence: float = 0.0
    freshness: str = "medium"
    surfaces: list[str] = Field(default_factory=list)
    status: str = "live"
    explanation: str | None = None


class UserInsightState(BaseModel):
    """Canonical compiled insight state shared across orchestration and product surfaces."""

    version: str = "2.0"
    generated_at: str = Field(default_factory=_utcnow_iso)

    goals: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    readiness: dict[str, Any] = Field(default_factory=dict)

    recent_pain_points: list[dict[str, Any]] = Field(default_factory=list)
    recent_wins: list[dict[str, Any]] = Field(default_factory=list)

    stable_preferences: dict[str, Any] = Field(default_factory=dict)
    current_state: dict[str, Any] = Field(default_factory=dict)
    inferred_work_style: dict[str, Any] = Field(default_factory=dict)

    active_bottlenecks: list[dict[str, Any]] = Field(default_factory=list)
    active_contradictions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_backed_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    temporal_patterns: dict[str, Any] = Field(default_factory=dict)
    multi_span_analysis: dict[str, Any] = Field(default_factory=dict)
    prediction_summaries: dict[str, Any] = Field(default_factory=dict)
    calibration_summary: dict[str, Any] = Field(default_factory=dict)

    uncertainty_markers: list[dict[str, Any]] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_clarification: list[str] = Field(default_factory=list)

    confidence_metadata: dict[str, float] = Field(default_factory=dict)
    freshness_metadata: dict[str, str] = Field(default_factory=dict)
    signal_evidence: list[InsightSignalEvidence] = Field(default_factory=list)

    def to_prompt_context(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_legacy_projection(self) -> dict[str, Any]:
        """Project the canonical state into the legacy Phase A compiled-shape."""

        stable_traits = dict(self.stable_preferences or {})
        stable_traits.update(
            {
                key: value
                for key, value in (self.inferred_work_style or {}).items()
                if key not in stable_traits
            }
        )

        return {
            "stable_traits": stable_traits,
            "current_state": dict(self.current_state or {}),
            "active_constraints": list(self.constraints or []),
            "active_bottlenecks": list(self.active_bottlenecks or []),
            "key_uncertainties": list(self.uncertainty_markers or []),
            "missing_information": list(self.missing_information or []),
            "confidence_map": dict(self.confidence_metadata or {}),
            "freshness_map": dict(self.freshness_metadata or {}),
            "contradiction_map": list(self.active_contradictions or []),
            "planning_readiness": dict(self.readiness or {}),
            "multi_span_analysis": dict(self.multi_span_analysis or {}),
            "prediction_summary": dict(self.prediction_summaries or {}),
            "calibration_summary": dict(self.calibration_summary or {}),
            "recommended_clarification": list(self.recommended_clarification or []),
            "version": self.version,
            "generated_at": self.generated_at,
        }
