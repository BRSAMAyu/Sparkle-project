from app.services.capability_selection_evaluator import CapabilitySelectionEvaluator


def test_capability_selection_evaluator_integration_regression_pack() -> None:
    result = CapabilitySelectionEvaluator().evaluate()

    assert result["scenario_count"] == 10
    assert "scenario_results" in result
    assert len(result["scenario_results"]) == 10
    assert result["user_facing_coherence"] >= 0.6


def test_capability_selection_evaluator_integration_strict_runtime_pack() -> None:
    result = CapabilitySelectionEvaluator().evaluate(mode="strict_runtime")

    assert result["scenario_count"] == 10
    assert result["mode"] == "strict_runtime"
    assert len(result["scenario_results"]) == 10
