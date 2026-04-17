from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _bounded(value: Any, *, fallback: float = 0.0) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return fallback


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class PlanOutcomeEvaluationResult:
    scenario_id: str
    improvement_score: float
    stability_score: float
    trust_preservation_score: float
    drift_safety_score: float
    repeated_mistake_reduction: float
    overall_score: float
    recommendation: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "improvement_score": self.improvement_score,
            "stability_score": self.stability_score,
            "trust_preservation_score": self.trust_preservation_score,
            "drift_safety_score": self.drift_safety_score,
            "repeated_mistake_reduction": self.repeated_mistake_reduction,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation,
            "notes": list(self.notes),
        }


class PlanOutcomeEvaluator:
    """Deterministic regression harness for comparing scenario cycles.

    This evaluator is intentionally not product-truth. It scores fixture-backed
    scenario payloads so Phase C can detect drift in repeated comparisons, while
    real truth still comes from human-eval review and repeated live-cycle evidence.
    """

    @staticmethod
    def load_scenarios(path: str | Path) -> list[dict[str, Any]]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [dict(item) for item in raw if isinstance(item, dict)]
        return []

    def evaluate_scenario(self, payload: dict[str, Any]) -> PlanOutcomeEvaluationResult:
        first_cycle = _as_dict(payload.get("first_cycle"))
        later_cycle = _as_dict(payload.get("later_cycle"))
        learned = [str(item).strip() for item in (payload.get("validated_learning_applied") or []) if str(item).strip()]

        first_quality = _bounded(first_cycle.get("plan_quality"))
        later_quality = _bounded(later_cycle.get("plan_quality"))
        first_trust = _bounded(first_cycle.get("trust_score"), fallback=0.5)
        later_trust = _bounded(later_cycle.get("trust_score"), fallback=0.5)
        first_mistakes = max(0, int(first_cycle.get("repeated_mistakes") or 0))
        later_mistakes = max(0, int(later_cycle.get("repeated_mistakes") or 0))
        later_overfit = bool(later_cycle.get("overfit_risk"))

        if first_quality < 0.6:
            improvement_score = min(1.0, later_quality + 0.2)
        else:
            improvement_score = max(0.0, later_quality - max(first_quality - 0.05, 0.0))
        stability_score = later_quality if first_quality >= 0.75 else max(0.0, 1.0 - abs(later_quality - first_quality))
        trust_preservation_score = max(0.0, 1.0 - max(first_trust - later_trust, 0.0))
        repeated_mistake_reduction = 1.0 if first_mistakes == 0 else max(
            0.0,
            min(1.0, (first_mistakes - later_mistakes) / max(first_mistakes, 1)),
        )
        drift_safety_score = 0.2 if later_overfit else 0.95
        if later_trust < 0.45:
            drift_safety_score = min(drift_safety_score, 0.4)

        overall_score = round(
            (
                improvement_score * 0.3
                + stability_score * 0.2
                + trust_preservation_score * 0.2
                + repeated_mistake_reduction * 0.2
                + drift_safety_score * 0.1
            ),
            4,
        )

        notes: list[str] = []
        if learned:
            notes.append(f"Validated learning applied: {', '.join(learned[:3])}")
        if later_mistakes < first_mistakes:
            notes.append("Later cycle reduced repeated mistakes.")
        if later_overfit:
            notes.append("Later cycle shows potential overfit risk.")
        if later_trust < first_trust:
            notes.append("Trust dropped relative to the first cycle.")

        recommendation = "pass"
        if overall_score < 0.7 or drift_safety_score < 0.5 or trust_preservation_score < 0.6:
            recommendation = "needs_iteration"

        return PlanOutcomeEvaluationResult(
            scenario_id=_strip(payload.get("scenario_id")),
            improvement_score=round(improvement_score, 4),
            stability_score=round(stability_score, 4),
            trust_preservation_score=round(trust_preservation_score, 4),
            drift_safety_score=round(drift_safety_score, 4),
            repeated_mistake_reduction=round(repeated_mistake_reduction, 4),
            overall_score=overall_score,
            recommendation=recommendation,
            notes=tuple(notes),
        )

    def evaluate_scenarios(self, scenarios: list[dict[str, Any]]) -> list[PlanOutcomeEvaluationResult]:
        return [self.evaluate_scenario(dict(item)) for item in scenarios if isinstance(item, dict)]
