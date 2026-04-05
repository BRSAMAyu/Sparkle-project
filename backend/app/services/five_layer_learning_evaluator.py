from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from app.services.plan_outcome_evaluator import PlanOutcomeEvaluator
from app.services.soul_drift_evaluator import SoulDriftEvaluator


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
class FiveLayerLearningEvaluationResult:
    scenario_id: str
    continuity_fit: float
    personalization_fit: float
    contradiction_safety: float
    drift_safety: float
    plan_improvement_over_time: float
    trust_preservation: float
    overall_score: float
    recommendation: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "continuity_fit": self.continuity_fit,
            "personalization_fit": self.personalization_fit,
            "contradiction_safety": self.contradiction_safety,
            "drift_safety": self.drift_safety,
            "plan_improvement_over_time": self.plan_improvement_over_time,
            "trust_preservation": self.trust_preservation,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation,
            "notes": list(self.notes),
        }


class FiveLayerLearningEvaluator:
    """Deterministic Phase E regression harness for scenario comparison.

    This evaluator is meant to keep the canonical Phase E journeys stable over time and
    compare implementation revisions against the same fixture bundle. It is not final
    proof that five-layer learning improves live product outcomes in production.
    """

    def __init__(self) -> None:
        self.plan_outcome_evaluator = PlanOutcomeEvaluator()
        self.soul_drift_evaluator = SoulDriftEvaluator()

    @staticmethod
    def load_scenarios(path: str | Path) -> list[dict[str, Any]]:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [dict(item) for item in raw if isinstance(item, dict)]
        return []

    def evaluate_scenario(self, payload: dict[str, Any]) -> FiveLayerLearningEvaluationResult:
        plan_eval = self.plan_outcome_evaluator.evaluate_scenario(dict(payload))
        soul_eval = self.soul_drift_evaluator.evaluate(
            scenario_id=_strip(payload.get("scenario_id")),
            current_runtime=_as_dict(payload.get("current_runtime")),
            previous_runtime=_as_dict(payload.get("previous_runtime")),
            outcomes=_as_dict(payload.get("drift_outcomes") or payload.get("outcomes")),
            signals=_as_dict(payload.get("drift_signals") or payload.get("signals")),
        )

        continuity_fit = _bounded(
            _as_dict(payload.get("phase_e_scores")).get(
                "continuity_fit",
                mean(
                    [
                        soul_eval.companion_integrity["continuity"].score,
                        1.0 if _as_dict(payload.get("later_cycle")).get("session_to_session_memory_used") else 0.55,
                    ]
                ),
            ),
            fallback=0.55,
        )
        personalization_fit = _bounded(
            _as_dict(payload.get("phase_e_scores")).get(
                "personalization_fit",
                mean(
                    [
                        plan_eval.improvement_score,
                        plan_eval.stability_score,
                    ]
                ),
            ),
            fallback=0.55,
        )
        unresolved_conflicts = max(0, int(payload.get("unresolved_conflicts") or 0))
        contradiction_safety = _bounded(
            _as_dict(payload.get("phase_e_scores")).get(
                "contradiction_safety",
                max(0.0, 1.0 - (unresolved_conflicts * 0.25)),
            ),
            fallback=0.6,
        )
        drift_safety = _bounded(
            _as_dict(payload.get("phase_e_scores")).get(
                "drift_safety",
                max(0.0, 1.0 - float(soul_eval.drift_score)),
            ),
            fallback=0.5,
        )
        plan_improvement_over_time = _bounded(
            _as_dict(payload.get("phase_e_scores")).get(
                "plan_improvement_over_time",
                plan_eval.improvement_score,
            ),
            fallback=0.55,
        )
        trust_preservation = _bounded(
            _as_dict(payload.get("phase_e_scores")).get(
                "trust_preservation",
                plan_eval.trust_preservation_score,
            ),
            fallback=0.55,
        )

        overall = round(
            mean(
                [
                    continuity_fit,
                    personalization_fit,
                    contradiction_safety,
                    drift_safety,
                    plan_improvement_over_time,
                    trust_preservation,
                ]
            ),
            4,
        )
        recommendation = "pass"
        if min(
            continuity_fit,
            contradiction_safety,
            drift_safety,
            trust_preservation,
        ) < 0.6 or overall < 0.7:
            recommendation = "needs_iteration"

        notes = list(plan_eval.notes)
        if soul_eval.drift_indicators:
            notes.append(f"Drift indicators: {', '.join(soul_eval.drift_indicators[:3])}")
        if unresolved_conflicts:
            notes.append(f"Unresolved conflicts: {unresolved_conflicts}")

        return FiveLayerLearningEvaluationResult(
            scenario_id=_strip(payload.get("scenario_id")),
            continuity_fit=continuity_fit,
            personalization_fit=personalization_fit,
            contradiction_safety=contradiction_safety,
            drift_safety=drift_safety,
            plan_improvement_over_time=plan_improvement_over_time,
            trust_preservation=trust_preservation,
            overall_score=overall,
            recommendation=recommendation,
            notes=tuple(notes),
        )

    def evaluate_scenarios(self, scenarios: list[dict[str, Any]]) -> list[FiveLayerLearningEvaluationResult]:
        return [self.evaluate_scenario(dict(item)) for item in scenarios if isinstance(item, dict)]

    def summarize(self, scenarios: list[dict[str, Any]]) -> dict[str, Any]:
        results = self.evaluate_scenarios(scenarios)
        if not results:
            return {
                "scenario_count": 0,
                "overall_score": 0.0,
                "recommendation": "needs_iteration",
                "results": [],
            }
        overall = round(mean(item.overall_score for item in results), 4)
        recommendation = "pass" if all(item.recommendation == "pass" for item in results) else "needs_iteration"
        return {
            "scenario_count": len(results),
            "overall_score": overall,
            "recommendation": recommendation,
            "results": [item.to_dict() for item in results],
        }
