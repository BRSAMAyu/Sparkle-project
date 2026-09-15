from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.profile_eval_llm_judge import (
    JUDGE_CONTRACT_VERSION,
    ProfileEvalJudgeConfig,
    ProfileEvalLLMJudge,
)


def test_profile_eval_llm_judge_returns_real_payload_when_llm_json_is_valid() -> None:
    fake_llm = AsyncMock()
    fake_llm.reason_json = AsyncMock(
        return_value={
            "score": 0.91,
            "rationale": "attached judge accepted the evidence alignment",
            "decision_trace": "rubric_plus_judge",
            "judge_version": JUDGE_CONTRACT_VERSION,
        }
    )

    with patch(
        "app.services.profile_eval_llm_judge.get_configured_llm_service_for_tier",
        AsyncMock(return_value=fake_llm),
    ):
        payload = ProfileEvalLLMJudge(config=ProfileEvalJudgeConfig(judge_weight=0.4, timeout_ms=6000, budget_tokens=900))(  # sync wrapper
            {
                "evaluation_focus": "prediction_accuracy",
                "metric_id": "overload_risk_precision",
                "prompt_context": {"prediction_key": "overload_risk"},
                "expected_observation": {"verification_window": "next_compile"},
                "rubric_score": 0.8,
            }
        )

    assert payload["score"] == 0.91
    assert payload["judge_version"] == JUDGE_CONTRACT_VERSION
    assert payload["fallback_used"] is False
    assert payload["judge_weight"] == 0.4
    assert payload["timeout_ms"] == 6000
    assert payload["budget_tokens"] == 900
    fake_llm.reason_json.assert_awaited_once()
    assert fake_llm.reason_json.await_args.kwargs["max_tokens"] == 900


def test_profile_eval_llm_judge_falls_back_to_rubric_only_when_llm_unavailable() -> None:
    with patch(
        "app.services.profile_eval_llm_judge.get_configured_llm_service_for_tier",
        AsyncMock(side_effect=RuntimeError("provider unavailable")),
    ):
        payload = ProfileEvalLLMJudge(config=ProfileEvalJudgeConfig())(
            {
                "evaluation_focus": "prediction_accuracy",
                "metric_id": "overload_risk_precision",
                "prompt_context": {},
                "expected_observation": {},
                "rubric_score": 0.74,
            }
        )

    assert payload["score"] == 0.74
    assert payload["fallback_used"] is True
    assert payload["fallback_reason"] == "RuntimeError"


def test_profile_eval_judge_config_rejects_out_of_range_weight() -> None:
    with pytest.raises(ValueError):
        ProfileEvalJudgeConfig(judge_weight=1.0)
