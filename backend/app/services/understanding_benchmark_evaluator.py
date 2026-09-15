from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prometheus_client import Counter

from app.core.business_metrics import get_or_create_metric
from app.services.human_eval_review_service import HumanEvalReviewService
from app.services.understanding_benchmark_service import UnderstandingBenchmarkRun, UnderstandingBenchmarkScenario

UNDERSTANDING_BENCHMARK_RUNS_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_understanding_benchmark_runs_total",
    "Understanding benchmark runs by family and verdict",
    ["benchmark_family", "verdict"],
)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _bounded(value: float) -> float:
    return round(max(0.0, min(value, 1.0)), 4)


@dataclass(frozen=True)
class UnderstandingBenchmarkScore:
    overall_score: float
    dimensions: dict[str, dict[str, Any]]
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "dimensions": dict(self.dimensions),
            "verdict": self.verdict,
        }


class UnderstandingBenchmarkEvaluator:
    """Deterministically score understanding quality for Stage 2 proof runs."""

    def evaluate_run(
        self,
        *,
        scenario: UnderstandingBenchmarkScenario,
        run: UnderstandingBenchmarkRun,
    ) -> UnderstandingBenchmarkScore:
        artifact = _as_dict(run.artifact)
        decision_context = _as_dict(artifact.get("decision_context"))
        insight_state = _as_dict(artifact.get("insight_state"))
        transparency = _as_dict(artifact.get("user_insight_transparency") or artifact.get("transparency"))

        claim_ids = {
            _strip(item.get("id"))
            for item in _as_list(transparency.get("claims"))
            if isinstance(item, dict) and _strip(item.get("id"))
        }
        if not claim_ids:
            claim_ids = {
                _strip(item.get("signal_id"))
                for item in _as_list(_as_dict(insight_state.get("current_state")).get("signal_evidence"))
                if isinstance(item, dict) and _strip(item.get("signal_id"))
            }
        prediction_ids = {
            _strip(item.get("id"))
            for item in _as_list(transparency.get("predictions"))
            if isinstance(item, dict) and _strip(item.get("id"))
        } or set(_as_dict(insight_state.get("prediction_summary")).keys())
        unknown_ids = {
            _strip(item.get("id"))
            for item in _as_list(transparency.get("unknowns"))
            if isinstance(item, dict) and _strip(item.get("id"))
        }
        if not unknown_ids:
            unknown_ids = {
                _strip(item)
                for item in _as_list(insight_state.get("missing_information"))
                if _strip(item)
            }

        signal_score = self._coverage_score(scenario.expected_signal_ids, claim_ids)
        prediction_score = self._coverage_score(scenario.expected_prediction_ids, prediction_ids)
        unknown_score = self._coverage_score(scenario.expected_unknown_ids, unknown_ids)
        clarification_score = self._clarification_score(
            scenario.expected_clarification_hint,
            decision_context=decision_context,
            insight_state=insight_state,
        )
        calibration_score = self._calibration_score(
            transparency=transparency,
            insight_state=insight_state,
        )

        dimensions = {
            "signal_coverage": {"score": signal_score, "notes": "Expected insight claims are surfaced."},
            "prediction_usefulness": {"score": prediction_score, "notes": "Expected prediction surfaces are available."},
            "unknown_honesty": {"score": unknown_score, "notes": "Expected unknowns remain visible instead of being hallucinated away."},
            "clarification_quality": {"score": clarification_score, "notes": "Sparkle asks or surfaces the expected clarification when needed."},
            "calibration_visibility": {"score": calibration_score, "notes": "Calibration and anti-drift posture are visible to product surfaces."},
        }
        overall = _bounded(
            (signal_score * 0.28)
            + (prediction_score * 0.2)
            + (unknown_score * 0.22)
            + (clarification_score * 0.15)
            + (calibration_score * 0.15)
        )
        verdict = "pass" if overall >= 0.72 else ("needs_iteration" if overall >= 0.55 else "fail")
        UNDERSTANDING_BENCHMARK_RUNS_TOTAL.labels(
            benchmark_family=scenario.benchmark_family or "unknown",
            verdict=verdict,
        ).inc()
        return UnderstandingBenchmarkScore(
            overall_score=overall,
            dimensions=dimensions,
            verdict=verdict,
        )

    @staticmethod
    def _coverage_score(expected: tuple[str, ...], actual: set[str]) -> float:
        if not expected:
            return 1.0
        matched = sum(1 for item in expected if item in actual)
        return _bounded(matched / max(len(expected), 1))

    @staticmethod
    def _clarification_score(
        expected_hint: str,
        *,
        decision_context: dict[str, Any],
        insight_state: dict[str, Any],
    ) -> float:
        if not expected_hint:
            return 1.0
        questions = [
            _strip(item)
            for item in _as_list(decision_context.get("strategic_clarification_questions") or insight_state.get("recommended_clarification"))
            if _strip(item)
        ]
        lowered = expected_hint.lower()
        if any(lowered in item.lower() for item in questions):
            return 1.0
        if _strip(decision_context.get("planning_readiness_action")) == "ask":
            return 0.7
        return 0.0

    @staticmethod
    def _calibration_score(*, transparency: dict[str, Any], insight_state: dict[str, Any]) -> float:
        calibration = _as_dict(transparency.get("calibration") or insight_state.get("calibration_summary"))
        if not calibration:
            return 0.0
        posture = _strip(calibration.get("calibration_posture"))
        recent_corrections = int(calibration.get("recent_correction_count") or 0)
        score = 0.55
        if posture in {"supported", "mixed", "uncalibrated", "correction_heavy"}:
            score += 0.2
        if "prediction_adjustments" in calibration:
            score += 0.15
        if recent_corrections >= 0:
            score += 0.1
        return _bounded(score)

    def build_product_proof_report(
        self,
        *,
        scenario: UnderstandingBenchmarkScenario,
        score: UnderstandingBenchmarkScore,
        human_review_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        human_ops_report = None
        if human_review_payload:
            human_ops_report = HumanEvalReviewService().build_operations_report(human_review_payload)
        return {
            "proof_level": "understanding_benchmark_v1",
            "scenario_id": scenario.scenario_id,
            "benchmark_family": scenario.benchmark_family,
            "overall_score": score.overall_score,
            "verdict": score.verdict,
            "dimensions": dict(score.dimensions),
            "comparison_focus": scenario.comparison_focus,
            "human_eval_required": True,
            "human_eval_ops_report": human_ops_report,
        }
