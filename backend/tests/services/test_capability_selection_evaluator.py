from app.services.capability_selection_evaluator import CapabilitySelectionEvaluator


def test_capability_selection_evaluator_scores_phase_d_fixture() -> None:
    payload = CapabilitySelectionEvaluator().evaluate()

    assert payload["scenario_count"] == 10
    assert payload["mode"] == "regression_guided"
    assert payload["selection_correctness"] >= 0.75
    assert payload["grounding_win_rate"] > 0
    assert payload["cost_discipline"] > 0
    assert payload["status"] in {"pass", "needs_iteration"}


def test_capability_selection_evaluator_strict_runtime_uses_blocked_organ_simulations() -> None:
    payload = CapabilitySelectionEvaluator().evaluate(mode="strict_runtime")

    assert payload["scenario_count"] == 10
    assert payload["mode"] == "strict_runtime"
    assert any(result["blocked_capabilities"] for result in payload["scenario_results"])
    assert payload["status"] in {"pass", "needs_iteration"}
