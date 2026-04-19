from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "profile" / "eval" / "fixtures"
DEFAULT_FIXTURE_NAMES = (
    "prediction_accuracy_baseline.json",
    "calibration_effectiveness_baseline.json",
    "freshness_validation_baseline.json",
)


def _score_label(score: float) -> str:
    if score >= 0.95:
        return "pass"
    if score >= 0.5:
        return "review"
    return "fail"


class ProfileEvalRunner:
    """Read-only deterministic runner for Stage 7 profile-eval fixtures."""

    runner_version = "stage7.e2.runner.v1"
    write_scope = "evaluation_records_only"
    llm_runtime = "not_attached"
    runner_mode = "deterministic_fixture_eval"

    def run_fixture_names(self, fixture_names: list[str] | None = None) -> dict[str, Any]:
        names = fixture_names or list(DEFAULT_FIXTURE_NAMES)
        evaluations = [self.run_fixture(name) for name in names]
        passed = sum(1 for item in evaluations if item["summary"]["status"] == "pass")
        review = sum(1 for item in evaluations if item["summary"]["status"] == "review")

        return {
            "runner_version": self.runner_version,
            "write_scope": self.write_scope,
            "llm_runtime": self.llm_runtime,
            "runner_mode": self.runner_mode,
            "evaluations": evaluations,
            "summary": {
                "fixture_count": len(evaluations),
                "pass_count": passed,
                "review_count": review,
                "fail_count": len(evaluations) - passed - review,
            },
        }

    def run_fixture(self, fixture_name: str) -> dict[str, Any]:
        payload = self._load_fixture(fixture_name)
        cases = [
            self._evaluate_case(
                evaluation_focus=str(payload["evaluation_focus"]),
                case=case,
                metrics=list(payload.get("metrics") or []),
            )
            for case in list(payload.get("fixture_cases") or [])
        ]
        scores = [float(case["score"]) for case in cases]
        average_score = round(sum(scores) / max(len(scores), 1), 3)

        return {
            "fixture_name": fixture_name,
            "evaluation_focus": payload["evaluation_focus"],
            "write_scope": self.write_scope,
            "llm_runtime": self.llm_runtime,
            "runner_mode": self.runner_mode,
            "evaluation_records": cases,
            "summary": {
                "status": _score_label(average_score),
                "average_score": average_score,
                "case_count": len(cases),
            },
        }

    def _evaluate_case(
        self,
        *,
        evaluation_focus: str,
        case: dict[str, Any],
        metrics: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt_context = dict(case.get("prompt_context") or {})
        expected_observation = dict(case.get("expected_observation") or {})
        metric_records = [
            self._evaluate_metric(
                evaluation_focus=evaluation_focus,
                metric=metric,
                prompt_context=prompt_context,
                expected_observation=expected_observation,
            )
            for metric in metrics
        ]
        average_score = round(
            sum(float(item["score"]) for item in metric_records) / max(len(metric_records), 1),
            3,
        )

        return {
            "case_id": case["case_id"],
            "status": _score_label(average_score),
            "score": average_score,
            "write_scope": self.write_scope,
            "metric_records": metric_records,
            "expected_observation": expected_observation,
        }

    def _evaluate_metric(
        self,
        *,
        evaluation_focus: str,
        metric: dict[str, Any],
        prompt_context: dict[str, Any],
        expected_observation: dict[str, Any],
    ) -> dict[str, Any]:
        metric_id = str(metric["metric_id"])
        if evaluation_focus == "prediction_accuracy":
            predicted_level = str(prompt_context.get("predicted_level") or "").strip().lower()
            supporting_signals = {str(item).strip() for item in list(prompt_context.get("supporting_signals") or [])}
            if metric_id == "overload_risk_precision":
                score = 1.0 if predicted_level == "high" and "error_summary" in supporting_signals else 0.4
                observed = "supporting overload evidence is available in fixture context"
            else:
                score = 1.0 if supporting_signals.intersection({"recent_mastery_changes", "error_summary"}) else 0.5
                observed = "planning readiness can be checked against named supporting signals"
        elif evaluation_focus == "calibration_effectiveness":
            correction_type = str(prompt_context.get("correction_type") or "").strip().lower()
            pre_confidence = float(prompt_context.get("pre_calibration_confidence") or 0.0)
            score = 1.0 if correction_type == "wrong" and pre_confidence >= 0.75 else 0.45
            observed = "fixture contains enough calibration posture to score demotion/promotion behavior"
        elif evaluation_focus == "freshness_validation":
            label = str(prompt_context.get("freshness_label") or "").strip().lower()
            evidence_age_days = int(prompt_context.get("evidence_age_days") or 0)
            is_mismatch = label == "high" and evidence_age_days >= 30
            score = 1.0 if is_mismatch else 0.5
            observed = "runner detects freshness mismatch from label vs evidence age"
        else:
            score = 0.0
            observed = "unsupported evaluation focus"

        return {
            "metric_id": metric_id,
            "expected_signal_family": metric.get("expected_signal_family"),
            "score": round(score, 3),
            "status": _score_label(score),
            "observed_summary": observed,
            "verification_window": expected_observation.get("verification_window"),
        }

    @staticmethod
    def _load_fixture(fixture_name: str) -> dict[str, Any]:
        return json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Stage 7 read-only profile evaluation runner.")
    parser.add_argument(
        "--fixture",
        dest="fixtures",
        action="append",
        help="Fixture filename under tests/profile/eval/fixtures/. Can be passed multiple times.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    payload = ProfileEvalRunner().run_fixture_names(args.fixtures)
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
