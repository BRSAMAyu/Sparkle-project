from __future__ import annotations

import json

from app.services.profile_eval_runner import ProfileEvalRunner, main


def test_profile_eval_runner_executes_prediction_accuracy_fixture() -> None:
    payload = ProfileEvalRunner().run_fixture("prediction_accuracy_baseline.json")

    assert payload["write_scope"] == "evaluation_records_only"
    assert payload["llm_runtime"] == "optional_not_attached"
    assert payload["runner_mode"] == "rubric_fixture_eval"
    assert payload["scoring_mode"] == "rubric_only"
    assert payload["rubric_version"] == "stage9.ev2.rubric.v1"
    assert payload["evaluation_focus"] == "prediction_accuracy"
    assert payload["summary"]["status"] == "pass"
    metric_record = payload["evaluation_records"][0]["metric_records"][0]
    assert metric_record["metric_id"] == "overload_risk_precision"
    assert metric_record["diagnostic_summary"].startswith("matched:")
    assert metric_record["criterion_records"]
    assert metric_record["rubric_version"] == "stage9.ev2.rubric.v1"
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
    payload = ProfileEvalRunner(llm_judge=lambda _: {"score": 0.9, "rationale": "mock attached judge"}).run_fixture(
        "prediction_accuracy_baseline.json"
    )

    assert payload["llm_runtime"] == "attached"
    assert payload["runner_mode"] == "llm_attached_rubric_eval"
    assert payload["scoring_mode"] == "llm_attached"
    assert payload["evaluation_records"][0]["metric_records"][0]["llm_attachment"]["rationale"] == "mock attached judge"
