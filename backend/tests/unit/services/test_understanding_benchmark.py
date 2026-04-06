from pathlib import Path

from app.core.business_metrics import snapshot_metric
from app.services.understanding_benchmark_evaluator import (
    UNDERSTANDING_BENCHMARK_RUNS_TOTAL,
    UnderstandingBenchmarkEvaluator,
)
from app.services.understanding_benchmark_service import UnderstandingBenchmarkHarness, UnderstandingBenchmarkRun


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "understanding_benchmark_scenarios.json"


def test_understanding_benchmark_harness_loads_stage2_scenarios() -> None:
    harness = UnderstandingBenchmarkHarness()
    scenarios = harness.load_scenarios(_fixture_path())

    assert len(scenarios) == 4
    assert {item.benchmark_family for item in scenarios} == {
        "cold_start_understanding",
        "exam_planning",
        "continuity_understanding",
        "trust_and_recognition",
    }


def test_understanding_benchmark_harness_builds_raw_model_comparison_prompt_and_human_review_packet() -> None:
    harness = UnderstandingBenchmarkHarness()
    scenario = harness.load_scenarios(_fixture_path())[0]

    prompt = harness.build_raw_model_comparison_prompt(scenario)
    human_review = harness.build_human_review_payload(scenario)

    assert "generic frontier model" in prompt
    assert scenario.comparison_focus in prompt
    assert human_review["scenario_id"] == scenario.scenario_id
    assert human_review["segments"][0]["evidence_used"] == list(scenario.expected_signal_ids)


def test_understanding_benchmark_evaluator_scores_transparent_insight_artifact_and_builds_proof_report() -> None:
    harness = UnderstandingBenchmarkHarness()
    scenario = [item for item in harness.load_scenarios(_fixture_path()) if item.scenario_id == "trust_and_recognition"][0]
    run = UnderstandingBenchmarkRun(
        scenario_id=scenario.scenario_id,
        variant="sparkle_stage2",
        artifact={
            "decision_context": {
                "planning_readiness_action": "proceed",
                "strategic_clarification_questions": [],
            },
            "insight_state": {
                "prediction_summary": {
                    "planning_readiness": {"level": "medium"},
                    "overload_risk": {"level": "low"},
                },
                "calibration_summary": {
                    "calibration_posture": "supported",
                    "prediction_adjustments": [{"prediction": "planning_readiness"}],
                    "recent_correction_count": 0,
                },
            },
            "user_insight_transparency": {
                "claims": [
                    {"id": "achievement_motivation_response"},
                    {"id": "achievement_reward_sensitivity"},
                ],
                "predictions": [
                    {"id": "planning_readiness"},
                    {"id": "overload_risk"},
                ],
                "unknowns": [{"id": "uncertainty:capacity_hours"}],
                "calibration": {
                    "calibration_posture": "supported",
                    "prediction_adjustments": [{"prediction": "planning_readiness"}],
                    "recent_correction_count": 0,
                },
            },
        },
    )

    before = snapshot_metric(UNDERSTANDING_BENCHMARK_RUNS_TOTAL)
    evaluator = UnderstandingBenchmarkEvaluator()
    score = evaluator.evaluate_run(scenario=scenario, run=run)
    report = evaluator.build_product_proof_report(
        scenario=scenario,
        score=score,
        human_review_payload=harness.build_human_review_payload(scenario),
    )
    after = snapshot_metric(UNDERSTANDING_BENCHMARK_RUNS_TOTAL)

    assert score.overall_score >= 0.8
    assert score.verdict == "pass"
    assert report["proof_level"] == "understanding_benchmark_v1"
    assert report["human_eval_required"] is True
    delta = sum(after.values()) - sum(before.values())
    assert delta == 1.0
