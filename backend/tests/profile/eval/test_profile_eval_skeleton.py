from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("filename", "expected_focus", "required_metric_ids"),
    [
        (
            "prediction_accuracy_baseline.json",
            "prediction_accuracy",
            {"overload_risk_precision", "planning_readiness_alignment"},
        ),
        (
            "calibration_effectiveness_baseline.json",
            "calibration_effectiveness",
            {"signal_demotion_stickiness", "hypothesis_promotion_retention"},
        ),
        (
            "freshness_validation_baseline.json",
            "freshness_validation",
            {"freshness_label_alignment", "staleness_window_breach_rate"},
        ),
    ],
)
def test_profile_eval_fixture_shape(
    filename: str,
    expected_focus: str,
    required_metric_ids: set[str],
) -> None:
    payload = _load_fixture(filename)

    assert payload["schema_version"] == "stage6.eval.v1"
    assert payload["evaluation_focus"] == expected_focus
    assert isinstance(payload["metrics"], list) and payload["metrics"]
    assert isinstance(payload["fixture_cases"], list) and payload["fixture_cases"]
    assert isinstance(payload["acceptance_questions"], list) and payload["acceptance_questions"]

    metric_ids = {metric["metric_id"] for metric in payload["metrics"]}
    assert required_metric_ids.issubset(metric_ids)

    for metric in payload["metrics"]:
        assert metric["metric_id"]
        assert metric["description"]
        assert metric["expected_signal_family"]

    for case in payload["fixture_cases"]:
        assert case["case_id"]
        assert case["prompt_context"]
        assert case["expected_observation"]
        assert case["status"] in {"draft", "ready_for_runner"}


def test_profile_eval_skeleton_only_describes_read_only_evaluation_contract() -> None:
    fixture_names = [
        "prediction_accuracy_baseline.json",
        "calibration_effectiveness_baseline.json",
        "freshness_validation_baseline.json",
    ]

    for fixture_name in fixture_names:
        payload = _load_fixture(fixture_name)
        assert payload["runner_mode"] == "skeleton_only"
        assert payload["write_scope"] == "evaluation_records_only"
        assert payload["llm_runtime"] == "not_attached"
