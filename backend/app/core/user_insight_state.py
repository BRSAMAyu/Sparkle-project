from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

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

    # ------------------------------------------------------------------
    # Inline snapshot — bounded compact render material for prompt path
    # ------------------------------------------------------------------

    INLINE_SNAPSHOT_BUDGET_CHARS: ClassVar[int] = 1200  # ~200 CJK tokens at ~6 chars/token

    def to_inline_snapshot(self) -> dict[str, Any]:
        """Produce a compact, budget-bounded snapshot for inline prompt injection.

        Returns a dict (not a raw string) so the caller can selectively render
        sections.  All lists are capped and the total character budget is
        enforced by the ``_truncate_to_budget`` helper.
        """
        items: list[str] = []

        # Goals (up to 2)
        for goal in (self.goals or [])[:2]:
            label = str(goal.get("label") or goal.get("type") or "").strip()
            if label:
                items.append(f"- 目标: {label}")

        # Top constraints (up to 2)
        for constraint in (self.constraints or [])[:2]:
            label = str(constraint.get("label") or "").strip()
            if label:
                ctype = str(constraint.get("type") or "").strip()
                items.append(f"- 约束: {label}" + (f" ({ctype})" if ctype else ""))

        # Pain points (up to 2)
        for pain in (self.recent_pain_points or [])[:2]:
            label = str(pain.get("label") or "").strip()
            if label:
                items.append(f"- 痛点: {label}")

        # Wins (up to 2)
        for win in (self.recent_wins or [])[:2]:
            label = str(win.get("label") or "").strip()
            if label:
                items.append(f"- 进展: {label}")

        # Readiness
        readiness_level = ""
        if isinstance(self.readiness, dict):
            readiness_level = str(self.readiness.get("predicted_level") or self.readiness.get("recommended_action") or "").strip()
        if readiness_level:
            items.append(f"- 规划就绪度: {readiness_level}")

        # Overload risk
        overload = ""
        current_state = self.current_state or {}
        if current_state.get("predicted_overload_risk"):
            overload = str(current_state["predicted_overload_risk"])
        elif isinstance(self.prediction_summaries, dict) and isinstance(self.prediction_summaries.get("overload_risk"), dict):
            overload = str(self.prediction_summaries["overload_risk"].get("level") or "")
        if overload:
            items.append(f"- 过载风险: {overload}")

        # Top bottleneck
        for bottleneck in (self.active_bottlenecks or [])[:1]:
            label = str(bottleneck.get("label") or "").strip()
            if label:
                items.append(f"- 主要瓶颈: {label}")

        # Work style highlights (up to 2)
        ws = self.inferred_work_style or {}
        if ws.get("peak_focus_hours"):
            hours = ws["peak_focus_hours"]
            if isinstance(hours, list):
                items.append(f"- 高效时段: {', '.join(str(h) + ':00' for h in hours[:3])}")
        if ws.get("accountability_support"):
            items.append(f"- 伙伴支持: {ws['accountability_support']}")

        body = "\n".join(items)
        body = self._truncate_to_budget(body)

        return {
            "available": bool(items),
            "body": body,
            "item_count": len(items),
            "budget_chars": self.INLINE_SNAPSHOT_BUDGET_CHARS,
            "truncated": len("\n".join(items)) > self.INLINE_SNAPSHOT_BUDGET_CHARS,
        }

    @classmethod
    def _truncate_to_budget(cls, text: str) -> str:
        """Hard-truncate to character budget, breaking at last newline."""
        if len(text) <= cls.INLINE_SNAPSHOT_BUDGET_CHARS:
            return text
        truncated = text[: cls.INLINE_SNAPSHOT_BUDGET_CHARS]
        last_nl = truncated.rfind("\n")
        if last_nl > cls.INLINE_SNAPSHOT_BUDGET_CHARS // 2:
            return truncated[:last_nl]
        return truncated
