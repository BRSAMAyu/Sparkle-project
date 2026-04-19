from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.services.profile_eval_llm_judge import JUDGE_CONTRACT_VERSION, ProfileEvalLLMJudge


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
        payload = ProfileEvalLLMJudge()(  # sync wrapper
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


def test_profile_eval_llm_judge_falls_back_to_rubric_only_when_llm_unavailable() -> None:
    with patch(
        "app.services.profile_eval_llm_judge.get_configured_llm_service_for_tier",
        AsyncMock(side_effect=RuntimeError("provider unavailable")),
    ):
        payload = ProfileEvalLLMJudge()(
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
