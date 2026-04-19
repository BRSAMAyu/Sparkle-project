from __future__ import annotations

import json

from app.services.profile_eval_runner import ProfileEvalRunner, main


def test_profile_eval_runner_executes_prediction_accuracy_fixture() -> None:
    payload = ProfileEvalRunner().run_fixture("prediction_accuracy_baseline.json")

    assert payload["write_scope"] == "evaluation_records_only"
    assert payload["llm_runtime"] == "not_attached"
    assert payload["runner_mode"] == "deterministic_fixture_eval"
    assert payload["evaluation_focus"] == "prediction_accuracy"
    assert payload["summary"]["status"] == "pass"
    assert payload["evaluation_records"][0]["metric_records"][0]["metric_id"] == "overload_risk_precision"


def test_profile_eval_runner_cli_emits_json(capsys) -> None:
    exit_code = main(["--fixture", "freshness_validation_baseline.json", "--pretty"])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["write_scope"] == "evaluation_records_only"
    assert payload["summary"]["fixture_count"] == 1
    assert payload["evaluations"][0]["fixture_name"] == "freshness_validation_baseline.json"
