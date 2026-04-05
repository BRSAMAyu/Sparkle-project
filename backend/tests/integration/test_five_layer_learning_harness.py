from pathlib import Path

from app.services.five_layer_learning_evaluator import FiveLayerLearningEvaluator


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "phase_e_five_layer_learning_scenarios.json"


def test_five_layer_learning_harness_runs_all_phase_e_scenarios() -> None:
    evaluator = FiveLayerLearningEvaluator()
    scenarios = evaluator.load_scenarios(_fixture_path())

    results = evaluator.evaluate_scenarios(scenarios)

    assert len(results) == 10
    assert min(item.continuity_fit for item in results) >= 0.6
    assert min(item.trust_preservation for item in results) >= 0.75
