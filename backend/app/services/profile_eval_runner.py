from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections.abc import Callable

from app.services.profile_eval_llm_judge import (
    JUDGE_CONTRACT_VERSION,
    ProfileEvalJudgeConfig,
    build_profile_eval_judge_config,
    build_profile_eval_llm_judge,
)

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


@dataclass(frozen=True)
class RubricCriterion:
    criterion_id: str
    label: str
    weight: float
    matched: bool
    evidence: str


LLMJudge = Callable[[dict[str, Any]], dict[str, Any]]


class ProfileEvalRunner:
    """Read-only rubric runner for Stage 9 profile-eval fixtures."""

    runner_version = "stage11.ev4.runner.v1"
    write_scope = "evaluation_records_only"
    rubric_version = "stage11.ev4.rubric.v1"

    def __init__(self, llm_judge: LLMJudge | None = None, judge_config: ProfileEvalJudgeConfig | None = None):
        self.llm_judge = llm_judge
        self.judge_config = judge_config or build_profile_eval_judge_config(enabled=llm_judge is not None)

    @property
    def llm_runtime(self) -> str:
        return "attached" if self.llm_judge is not None else "optional_not_attached"

    @property
    def runner_mode(self) -> str:
        return "llm_attached_rubric_eval" if self.llm_judge is not None else "rubric_fixture_eval"

    @property
    def scoring_mode(self) -> str:
        return "llm_attached" if self.llm_judge is not None else "rubric_only"

    @property
    def judge_contract_version(self) -> str | None:
        return JUDGE_CONTRACT_VERSION if self.llm_judge is not None else None

    @property
    def prompt_version(self) -> str | None:
        return self.judge_config.prompt_version if self.llm_judge is not None else None

    @classmethod
    def from_runtime(
        cls,
        *,
        enable_llm_judge: bool = False,
        judge_weight: float | None = None,
        timeout_ms: int | None = None,
        budget_tokens: int | None = None,
        prompt_version: str | None = None,
    ) -> ProfileEvalRunner:
        config = build_profile_eval_judge_config(
            enabled=enable_llm_judge,
            judge_weight=judge_weight,
            timeout_ms=timeout_ms,
            budget_tokens=budget_tokens,
            prompt_version=prompt_version,
        )
        return cls(llm_judge=build_profile_eval_llm_judge(enabled=enable_llm_judge, config=config), judge_config=config)

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
            "scoring_mode": self.scoring_mode,
            "rubric_version": self.rubric_version,
            "judge_contract_version": self.judge_contract_version,
            "judge_config": self.judge_config.as_payload() if self.llm_judge is not None else None,
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
            "scoring_mode": self.scoring_mode,
            "rubric_version": self.rubric_version,
            "judge_contract_version": self.judge_contract_version,
            "prompt_version": self.prompt_version,
            "judge_config": self.judge_config.as_payload() if self.llm_judge is not None else None,
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
            "scoring_mode": self.scoring_mode,
            "rubric_version": self.rubric_version,
            "judge_contract_version": self.judge_contract_version,
            "prompt_version": self.prompt_version,
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
        criteria = self._build_rubric(
            evaluation_focus=evaluation_focus,
            metric_id=metric_id,
            prompt_context=prompt_context,
            expected_observation=expected_observation,
        )
        total_weight = sum(max(item.weight, 0.0) for item in criteria) or 1.0
        rubric_score = round(sum(item.weight for item in criteria if item.matched) / total_weight, 3)

        llm_attachment: dict[str, Any] | None = None
        final_score = rubric_score
        if self.llm_judge is not None:
            llm_attachment = dict(
                self.llm_judge(
                    {
                        "evaluation_focus": evaluation_focus,
                        "metric_id": metric_id,
                        "prompt_context": prompt_context,
                        "expected_observation": expected_observation,
                        "rubric_score": rubric_score,
                    }
                )
                or {}
            )
            try:
                llm_score = float(llm_attachment.get("score"))
            except (TypeError, ValueError):
                llm_score = rubric_score
            final_score = round(
                (rubric_score * self.judge_config.rubric_weight)
                + (llm_score * self.judge_config.judge_weight),
                3,
            )

        observed = (
            "; ".join(item.evidence for item in criteria if item.evidence) or "rubric produced no diagnostic evidence"
        )

        return {
            "metric_id": metric_id,
            "expected_signal_family": metric.get("expected_signal_family"),
            "score": round(final_score, 3),
            "status": _score_label(final_score),
            "observed_summary": observed,
            "diagnostic_summary": self._build_diagnostic_summary(criteria),
            "criterion_records": [
                {
                    "criterion_id": item.criterion_id,
                    "label": item.label,
                    "weight": item.weight,
                    "matched": item.matched,
                    "evidence": item.evidence,
                }
                for item in criteria
            ],
            "rubric_version": self.rubric_version,
            "scoring_mode": self.scoring_mode,
            "llm_runtime": self.llm_runtime,
            "llm_attachment": llm_attachment,
            "judge_contract_version": self.judge_contract_version,
            "prompt_version": self.prompt_version,
            "judge_weight": self.judge_config.judge_weight if self.llm_judge is not None else None,
            "rubric_weight": self.judge_config.rubric_weight if self.llm_judge is not None else None,
            "evidence_excerpt": {
                "prompt_context_keys": sorted(prompt_context.keys()),
                "verification_window": expected_observation.get("verification_window"),
            },
            "verification_window": expected_observation.get("verification_window"),
        }

    def _build_rubric(
        self,
        *,
        evaluation_focus: str,
        metric_id: str,
        prompt_context: dict[str, Any],
        expected_observation: dict[str, Any],
    ) -> list[RubricCriterion]:
        if evaluation_focus == "prediction_accuracy":
            predicted_level = str(prompt_context.get("predicted_level") or "").strip().lower()
            prediction_key = str(prompt_context.get("prediction_key") or "").strip().lower()
            supporting_signals = {str(item).strip() for item in list(prompt_context.get("supporting_signals") or [])}
            verification_window = str(expected_observation.get("verification_window") or "").strip()
            success_if = str(expected_observation.get("success_if") or "").strip()
            if metric_id == "overload_risk_precision":
                return [
                    RubricCriterion(
                        "prediction_key_present",
                        "prediction key explicitly targets overload risk",
                        0.2,
                        prediction_key == "overload_risk",
                        f"prediction_key={prediction_key or 'missing'}",
                    ),
                    RubricCriterion(
                        "high_risk_level_explicit",
                        "predicted level is explicitly high",
                        0.4,
                        predicted_level == "high",
                        f"predicted_level={predicted_level or 'missing'}",
                    ),
                    RubricCriterion(
                        "supporting_overload_signal_present",
                        "fixture includes overload-supporting evidence",
                        0.4,
                        "error_summary" in supporting_signals,
                        f"supporting_signals={sorted(supporting_signals)}",
                    ),
                ]
            return [
                RubricCriterion(
                    "supporting_planning_signal_present",
                    "planning readiness can be checked against named supporting signals",
                    0.4,
                    bool(supporting_signals.intersection({"recent_mastery_changes", "error_summary"})),
                    f"supporting_signals={sorted(supporting_signals)}",
                ),
                RubricCriterion(
                    "verification_window_present",
                    "fixture preserves a verification window",
                    0.2,
                    bool(verification_window),
                    f"verification_window={verification_window or 'missing'}",
                ),
                RubricCriterion(
                    "success_clause_present",
                    "fixture describes the expected planning outcome",
                    0.4,
                    bool(success_if),
                    f"success_if={'present' if success_if else 'missing'}",
                ),
            ]

        if evaluation_focus == "calibration_effectiveness":
            correction_type = str(prompt_context.get("correction_type") or "").strip().lower()
            target_signal_id = str(prompt_context.get("target_signal_id") or "").strip()
            pre_confidence = float(prompt_context.get("pre_calibration_confidence") or 0.0)
            verification_window = str(expected_observation.get("verification_window") or "").strip()
            success_if = str(expected_observation.get("success_if") or "").strip().lower()
            if metric_id == "signal_demotion_stickiness":
                return [
                    RubricCriterion(
                        "wrong_correction_present",
                        "fixture contains a direct user correction",
                        0.45,
                        correction_type == "wrong",
                        f"correction_type={correction_type or 'missing'}",
                    ),
                    RubricCriterion(
                        "high_confidence_prior",
                        "pre-calibration confidence is strong enough to test demotion",
                        0.35,
                        pre_confidence >= 0.75,
                        f"pre_calibration_confidence={pre_confidence:.2f}",
                    ),
                    RubricCriterion(
                        "next_compile_window_defined",
                        "verification window checks the next compilation cycle",
                        0.2,
                        verification_window == "next_compile",
                        f"verification_window={verification_window or 'missing'}",
                    ),
                ]
            return [
                RubricCriterion(
                    "target_signal_named",
                    "fixture names the target signal whose state must persist",
                    0.3,
                    bool(target_signal_id),
                    f"target_signal_id={target_signal_id or 'missing'}",
                ),
                RubricCriterion(
                    "promotion_or_retention_clause_present",
                    "success clause is rich enough to score retention behavior",
                    0.4,
                    "confidence" in success_if or "retain" in success_if or "remain" in success_if,
                    f"success_if={success_if or 'missing'}",
                ),
                RubricCriterion(
                    "calibration_window_present",
                    "fixture keeps an explicit verification window",
                    0.3,
                    bool(verification_window),
                    f"verification_window={verification_window or 'missing'}",
                ),
            ]

        if evaluation_focus == "freshness_validation":
            signal_id = str(prompt_context.get("signal_id") or "").strip()
            label = str(prompt_context.get("freshness_label") or "").strip().lower()
            evidence_age_days = int(prompt_context.get("evidence_age_days") or 0)
            verification_window = str(expected_observation.get("verification_window") or "").strip()
            mismatch_detected = label == "high" and evidence_age_days >= 30
            if metric_id == "freshness_label_alignment":
                return [
                    RubricCriterion(
                        "signal_named",
                        "fixture names the signal under freshness review",
                        0.1,
                        bool(signal_id),
                        f"signal_id={signal_id or 'missing'}",
                    ),
                    RubricCriterion(
                        "freshness_label_present",
                        "fixture preserves the emitted freshness label",
                        0.2,
                        bool(label),
                        f"freshness_label={label or 'missing'}",
                    ),
                    RubricCriterion(
                        "mismatch_detected",
                        "runner can detect stale evidence behind a high freshness label",
                        0.7,
                        mismatch_detected,
                        f"evidence_age_days={evidence_age_days}",
                    ),
                ]
            return [
                RubricCriterion(
                    "stale_window_crossed",
                    "fixture crosses the stale-evidence window",
                    0.6,
                    evidence_age_days >= 30,
                    f"evidence_age_days={evidence_age_days}",
                ),
                RubricCriterion(
                    "runner_window_explicit",
                    "fixture scopes freshness checking to an evaluation-only window",
                    0.4,
                    verification_window == "eval_runner_only",
                    f"verification_window={verification_window or 'missing'}",
                ),
            ]

        return [
            RubricCriterion(
                "unsupported_focus",
                "evaluation focus is unsupported",
                1.0,
                False,
                f"unsupported evaluation_focus={evaluation_focus}",
            )
        ]

    @staticmethod
    def _build_diagnostic_summary(criteria: list[RubricCriterion]) -> str:
        matched = [item.label for item in criteria if item.matched]
        missing = [item.label for item in criteria if not item.matched]
        parts: list[str] = []
        if matched:
            parts.append(f"matched: {', '.join(matched)}")
        if missing:
            parts.append(f"missing: {', '.join(missing)}")
        return "; ".join(parts) if parts else "no rubric criteria were evaluated"

    @staticmethod
    def _load_fixture(fixture_name: str) -> dict[str, Any]:
        return json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Stage 11 read-only profile evaluation runner.")
    parser.add_argument(
        "--fixture",
        dest="fixtures",
        action="append",
        help="Fixture filename under tests/profile/eval/fixtures/. Can be passed multiple times.",
    )
    parser.add_argument(
        "--llm-judge",
        choices=("disabled", "real"),
        default="disabled",
        help="Attach the real Stage 11 LLM judge or keep rubric_only mode.",
    )
    parser.add_argument("--judge-weight", type=float, help="Judge score weight in [0.1, 0.9]")
    parser.add_argument("--judge-timeout-ms", type=int, help="Judge timeout in milliseconds")
    parser.add_argument("--judge-budget-tokens", type=int, help="Judge max token budget")
    parser.add_argument("--judge-prompt-version", type=str, help="Committed judge prompt version label")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    payload = ProfileEvalRunner.from_runtime(
        enable_llm_judge=args.llm_judge == "real",
        judge_weight=args.judge_weight,
        timeout_ms=args.judge_timeout_ms,
        budget_tokens=args.judge_budget_tokens,
        prompt_version=args.judge_prompt_version,
    ).run_fixture_names(args.fixtures)
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
