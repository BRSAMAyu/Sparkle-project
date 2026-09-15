from __future__ import annotations

from app.core.agent_profiles import ModelTier
from app.services.llm_dispatcher import LLMDispatcher


class _FailingPredictionService:
    async def chat_json(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


class _SuccessfulPredictionService:
    def __init__(self, payload):
        self.payload = payload

    async def chat_json(self, *args, **kwargs):
        return self.payload


async def _fake_service_for_tier(tier: ModelTier, attempts: list[ModelTier]):
    attempts.append(tier)
    if tier == ModelTier.FREE:
        return _FailingPredictionService()
    return _SuccessfulPredictionService(
        {
            "summary": "建议先拆小任务再开始。",
            "candidates": [
                {
                    "action_type": "plan_split",
                    "title": "拆小任务",
                    "reason": "当前上下文显示你容易中断，先把任务拆小更稳。",
                    "confidence": 0.78,
                    "timing_hint": "now",
                    "payload_seed": "breakdown_current_task",
                    "metadata": {"source": "llm"},
                }
            ],
        }
    )


async def _fake_get_service(agent_role, force_tier, task_type=None, reasoning_mode=None):
    raise NotImplementedError


import pytest


@pytest.mark.asyncio
async def test_prediction_llm_falls_back_from_free_to_free_fast(monkeypatch):
    dispatcher = LLMDispatcher()
    attempts: list[ModelTier] = []

    async def fake_get_service(agent_role, force_tier, task_type=None, reasoning_mode=None):
        return await _fake_service_for_tier(force_tier, attempts)

    monkeypatch.setattr(
        "app.services.llm_dispatcher.get_configured_llm_service_for_tier",
        fake_get_service,
    )

    result = await dispatcher._try_llm_predict_next_actions(
        user_id="user-1",
        envelope={"window": "focus"},
        features={"energy": {"late_night_fatigue": False}},
        signals={"signals": []},
        rule_candidates=[],
    )

    assert attempts == [ModelTier.FREE, ModelTier.FREE_FAST]
    assert result is not None
    assert result["prediction_tier"] == ModelTier.FREE_FAST.value
    assert result["prediction_source"] == "free_fast_llm"
    assert result["candidates"][0]["action_type"] == "plan_split"


def test_prediction_payload_normalization_rejects_invalid_candidates():
    dispatcher = LLMDispatcher()

    invalid = dispatcher._normalize_prediction_payload(
        {
            "summary": "bad",
            "candidates": [
                {"title": "missing action_type"},
            ],
        }
    )
    valid = dispatcher._normalize_prediction_payload(
        {
            "summary": "ok",
            "candidates": [
                {
                    "action_type": "review",
                    "title": "复习巩固",
                    "reason": "刚好处于适合复盘的窗口。",
                    "confidence": 0.66,
                }
            ],
        }
    )

    assert invalid is None
    assert valid is not None
    assert valid["candidates"][0]["timing_hint"] == "now"
