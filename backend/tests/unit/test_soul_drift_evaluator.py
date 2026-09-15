from __future__ import annotations

from pathlib import Path

from app.services.soul_drift_evaluator import SoulDriftEvaluator


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "soul_drift_scenarios.json"


def test_soul_drift_evaluator_distinguishes_growth_from_stylized_drift() -> None:
    evaluator = SoulDriftEvaluator()
    scenarios = evaluator.load_scenarios(_fixture_path())
    reports = {report.scenario_id: report for report in evaluator.evaluate_scenarios(scenarios)}

    healthy = reports["healthy_governed_growth"]
    stylized = reports["stylized_vividness_drift"]

    assert healthy.drift_score < 0.4
    assert healthy.recommendation == "continue"
    assert stylized.drift_score >= 0.4
    assert "stylized_self_authored_notes" in stylized.drift_indicators
    assert "vividness_without_outcome" in stylized.drift_indicators


def test_soul_drift_evaluator_flags_constitution_adjacent_drift() -> None:
    evaluator = SoulDriftEvaluator()
    scenarios = evaluator.load_scenarios(_fixture_path())
    reports = {report.scenario_id: report for report in evaluator.evaluate_scenarios(scenarios)}

    report = reports["constitution_adjacent_silent_drift"]

    assert "constitution_adjacent_proposals" in report.drift_indicators
    assert report.companion_integrity["independence"].score < 0.8
    assert report.companion_integrity["governability"].score < 0.8


def test_soul_drift_evaluator_returns_scorecards_and_alarm_payloads() -> None:
    evaluator = SoulDriftEvaluator()
    scenario = evaluator.load_scenarios(_fixture_path())[0]

    report = evaluator.evaluate(
        scenario_id=scenario["scenario_id"],
        current_runtime=scenario["current_runtime"],
        previous_runtime=scenario["previous_runtime"],
        outcomes=scenario["outcomes"],
        signals=scenario["signals"],
    )

    payload = report.to_dict()

    assert set(payload["companion_integrity"].keys()) == {
        "consistency",
        "independence",
        "vividness",
        "continuity",
        "growth",
        "governability",
    }
    assert set(payload["product_value"].keys()) == {
        "residual_resolution",
        "leap_support",
        "freedom_preservation",
        "felt_understanding",
    }
    assert isinstance(payload["drift_alarms"], list)
    assert "outcome_average" in payload["supporting_metrics"]
