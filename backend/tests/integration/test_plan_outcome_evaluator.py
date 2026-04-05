from pathlib import Path

from app.services.plan_outcome_evaluator import PlanOutcomeEvaluator


def test_plan_outcome_evaluator_scores_improvement_and_overfit() -> None:
    evaluator = PlanOutcomeEvaluator()
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "phase_c_outcome_evaluator_scenarios.json"

    reports = evaluator.evaluate_scenarios(evaluator.load_scenarios(fixture))

    assert len(reports) == 2
    first = next(item for item in reports if item.scenario_id == "phase_c_failure_then_improves")
    second = next(item for item in reports if item.scenario_id == "phase_c_overfits_after_success")

    assert first.recommendation == "pass"
    assert first.repeated_mistake_reduction > 0.5
    assert second.recommendation == "needs_iteration"
    assert second.drift_safety_score < 0.5


def test_plan_outcome_evaluator_is_explicitly_a_regression_harness() -> None:
    doc = (PlanOutcomeEvaluator.__doc__ or "").lower()
    assert "regression harness" in doc
    assert "not product-truth" in doc
