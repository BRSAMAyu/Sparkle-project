from __future__ import annotations

from typing import Any, Literal

from app.orchestration.schemas import CompiledInsightState


class PlanningReadinessGate:
    """
    Planning Readiness Gate - Phase A3
    Decides if Sparkle is ready to plan or needs to ask questions.
    """

    LEVEL_LOW = "low"
    LEVEL_MEDIUM = "medium"
    LEVEL_HIGH = "high"

    def evaluate(
        self,
        *,
        insight_state: CompiledInsightState,
        gaps: list[str]
    ) -> dict[str, Any]:
        """Compute readiness and recommend action."""

        # Scoring logic
        score = 1.0
        # Deduct per gap
        # If no gaps, score is 1.0 (High Readiness)
        gap_weights = {
            "baseline_mastery": 0.4,
            "deadline": 0.2,
            "capacity_hours": 0.2,
            "goal_specificity": 0.3,
            "material_source": 0.1
        }
        for gap in gaps:
            score -= gap_weights.get(gap, 0.1)

        contradiction_penalty = 0.0
        blocking_contradictions: list[str] = []
        for contradiction in insight_state.contradiction_map:
            severity = str(contradiction.get("severity") or "").strip().lower()
            description = str(contradiction.get("description") or "").strip()
            penalty = {
                "high": 0.25,
                "medium": 0.15,
                "low": 0.08,
            }.get(severity, 0.1)
            contradiction_penalty += penalty
            if severity in {"high", "medium"} and description:
                blocking_contradictions.append(description)

        score -= contradiction_penalty

        score = max(0.0, score)

        # Determination
        level = self.LEVEL_HIGH
        action: Literal["ask", "provisional", "proceed"] = "proceed"

        if score <= 0.4:
            level = self.LEVEL_LOW
            action = "ask"
        elif score < 0.8:
            level = self.LEVEL_MEDIUM
            action = "provisional"
        else:
            level = self.LEVEL_HIGH
            action = "proceed"

        return {
            "readiness_score": round(score, 2),
            "readiness_level": level,
            "recommended_action": action,
            "blocking_unknowns": gaps,
            "blocking_contradictions": blocking_contradictions[:2],
            "ask_before_plan": action == "ask",
        }
