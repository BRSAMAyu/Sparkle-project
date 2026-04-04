from __future__ import annotations

from pathlib import Path

from app.services.experience_phase_evaluator import ExperiencePhaseEvaluator


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "experience_phase_thermodynamics_journey.json"


def test_experience_phase_evaluator_scores_thermodynamics_journey() -> None:
    evaluator = ExperiencePhaseEvaluator()
    scenarios = evaluator.load_scenarios(_fixture_path())

    reports = {report.scenario_id: report for report in evaluator.evaluate_scenarios(scenarios)}
    report = reports["thermodynamics_exam_14_day_journey"]

    assert set(report.outcome_scorecard.keys()) == {
        "misconception_reduction",
        "task_execution",
        "consistency",
        "real_world_performance",
    }
    assert set(report.experience_scorecard.keys()) == {
        "felt_understood",
        "timely_guidance",
        "real_change",
        "continuity_and_trust",
    }
    assert set(report.intelligence_scorecard.keys()) == {
        "correct_residual_diagnosis",
        "correct_loop_selection",
        "grounded_evidence_use",
        "good_reversibility",
        "freedom_preservation",
        "low_drift",
    }
    assert report.overall_scores["outcome_average"] >= 0.7
    assert report.overall_scores["experience_average"] >= 0.8
    assert report.overall_scores["intelligence_average"] >= 0.8
    assert report.recommendation == "accept"
    assert report.supporting_metrics["residual_accuracy_rate"] == 1.0


def test_experience_phase_evaluator_blocks_when_judgment_and_grounding_fail() -> None:
    evaluator = ExperiencePhaseEvaluator()

    report = evaluator.evaluate(
        scenario_id="bad_journey",
        turns=[
            {
                "expected_residual": "R_n",
                "expected_loop_type": "normative",
                "expected_mode": "decide",
                "expected_grounding": "user_values_and_constraints",
                "decision_context": {
                    "primary_residual": "R_e",
                    "loop_type": "truth_seeking",
                    "experience_mode": "explain",
                    "grounding_priority": ["general_knowledge"],
                },
                "auto_strategy_adjustments": [
                    {"field": "session_mode", "layer": "episode"}
                ],
                "user_signal": "still_stuck",
                "freedom_preservation": 0.3,
            }
        ],
        outcomes={
            "misconception_reduction": 0.32,
            "task_execution": 0.28,
            "consistency": 0.25,
            "real_world_performance": 0.2,
        },
        current_runtime={
            "effective_companion_state": {
                "warmth_calibration": 0.88,
                "candor_calibration": 0.21,
                "relationship_stage": "deepening",
                "stylized_support_notes": ["You were born for this."],
            }
        },
        previous_runtime={
            "effective_companion_state": {
                "warmth_calibration": 0.55,
                "candor_calibration": 0.52,
                "relationship_stage": "building",
            }
        },
        drift_outcomes={
            "residual_resolution": 0.22,
            "leap_support": 0.25,
            "freedom_preservation": 0.28,
            "felt_understanding": 0.31,
        },
        drift_signals={
            "outcome_delta": -0.15,
            "vividness_signal": 0.92,
            "stylized_note_signal": 0.84,
            "constitution_adjacent_proposal_count": 2,
            "self_authored_note_ratio": 0.78,
        },
    )

    assert report.intelligence_scorecard["correct_residual_diagnosis"].score == 0.0
    assert report.intelligence_scorecard["correct_loop_selection"].score == 0.0
    assert report.intelligence_scorecard["grounded_evidence_use"].score == 0.0
    assert report.intelligence_scorecard["good_reversibility"].score == 0.0
    assert report.recommendation == "block"
    assert report.soul_drift is not None


def test_experience_phase_evaluator_does_not_credit_missing_user_material_hits() -> None:
    evaluator = ExperiencePhaseEvaluator()

    report = evaluator.evaluate(
        scenario_id="grounding_miss",
        turns=[
            {
                "expected_residual": "R_e",
                "expected_loop_type": "truth_seeking",
                "expected_grounding": "user_materials",
                "decision_context": {
                    "primary_residual": "R_e",
                    "loop_type": "truth_seeking",
                    "grounding_priority": ["user_materials"],
                },
                "user_material_grounding": {
                    "status": "no_hits",
                    "results": [],
                },
            }
        ],
        outcomes={
            "misconception_reduction": 0.4,
            "task_execution": 0.4,
            "consistency": 0.4,
            "real_world_performance": 0.4,
        },
    )

    assert report.intelligence_scorecard["grounded_evidence_use"].score == 0.0
