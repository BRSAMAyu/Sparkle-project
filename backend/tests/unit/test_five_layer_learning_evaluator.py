from pathlib import Path

from app.services.five_layer_learning_evaluator import FiveLayerLearningEvaluator


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "phase_e_five_layer_learning_scenarios.json"


def test_five_layer_learning_evaluator_scores_fixture_bundle() -> None:
    evaluator = FiveLayerLearningEvaluator()
    scenarios = evaluator.load_scenarios(_fixture_path())

    summary = evaluator.summarize(scenarios)

    assert summary["scenario_count"] == 10
    assert summary["overall_score"] >= 0.7
    assert summary["results"]


def test_five_layer_learning_evaluator_flags_constitution_adjacent_drift_but_keeps_bundle_passing() -> None:
    evaluator = FiveLayerLearningEvaluator()
    scenarios = evaluator.load_scenarios(_fixture_path())

    result = next(
        item for item in evaluator.evaluate_scenarios(scenarios)
        if item.scenario_id == "constitution_adjacent_drift_proposal"
    )

    assert result.drift_safety < 0.8
    assert result.trust_preservation >= 0.75
