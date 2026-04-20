from __future__ import annotations

import json
from unittest.mock import patch

from app.services.profile_eval_runner import ProfileEvalRunner, main


def test_profile_eval_runner_executes_prediction_accuracy_fixture() -> None:
    payload = ProfileEvalRunner().run_fixture("prediction_accuracy_baseline.json")

    assert payload["write_scope"] == "evaluation_records_only"
    assert payload["llm_runtime"] == "optional_not_attached"
    assert payload["runner_mode"] == "rubric_fixture_eval"
    assert payload["scoring_mode"] == "rubric_only"
    assert payload["rubric_version"] == "stage11.ev4.rubric.v1"
    assert payload["judge_contract_version"] is None
    assert payload["evaluation_focus"] == "prediction_accuracy"
    assert payload["summary"]["status"] == "pass"
    metric_record = payload["evaluation_records"][0]["metric_records"][0]
    assert metric_record["metric_id"] == "overload_risk_precision"
    assert metric_record["diagnostic_summary"].startswith("matched:")
    assert metric_record["criterion_records"]
    assert metric_record["rubric_version"] == "stage11.ev4.rubric.v1"
    assert metric_record["llm_attachment"] is None


def test_profile_eval_runner_cli_emits_json(capsys) -> None:
    exit_code = main(["--fixture", "freshness_validation_baseline.json", "--pretty"])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["write_scope"] == "evaluation_records_only"
    assert payload["summary"]["fixture_count"] == 1
    assert payload["runner_mode"] == "rubric_fixture_eval"
    assert payload["evaluations"][0]["fixture_name"] == "freshness_validation_baseline.json"


def test_profile_eval_runner_supports_optional_llm_attachment() -> None:
    payload = ProfileEvalRunner(
        llm_judge=lambda _: {"score": 0.9, "rationale": "mock attached judge"},
        judge_config=ProfileEvalRunner.from_runtime(
            enable_llm_judge=False,
            judge_weight=0.4,
            timeout_ms=6000,
            budget_tokens=900,
            prompt_version="stage11.ev4.judge.v1",
        ).judge_config,
    ).run_fixture("prediction_accuracy_baseline.json")

    assert payload["llm_runtime"] == "attached"
    assert payload["runner_mode"] == "llm_attached_rubric_eval"
    assert payload["scoring_mode"] == "llm_attached"
    assert payload["evaluation_records"][0]["metric_records"][0]["llm_attachment"]["rationale"] == "mock attached judge"
    assert payload["judge_contract_version"] == "stage11.ev4.judge.v1"
    assert payload["evaluation_records"][0]["metric_records"][0]["judge_weight"] == 0.4


def test_profile_eval_runner_runtime_factory_can_attach_real_judge() -> None:
    with patch("app.services.profile_eval_runner.build_profile_eval_llm_judge", return_value=lambda _: {"score": 0.82}):
        payload = ProfileEvalRunner.from_runtime(
            enable_llm_judge=True,
            judge_weight=0.25,
            timeout_ms=5000,
            budget_tokens=700,
            prompt_version="stage11.ev4.judge.v2",
        ).run_fixture(
            "prediction_accuracy_baseline.json"
        )

    assert payload["llm_runtime"] == "attached"
    assert payload["scoring_mode"] == "llm_attached"
    assert payload["judge_config"]["judge_weight"] == 0.25
    assert payload["judge_config"]["prompt_version"] == "stage11.ev4.judge.v2"
