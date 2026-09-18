"""realtime-next-step 有界降级回归测试。

背景（round2 P2 复现）：POST /api/v1/predictive/realtime-next-step 500。
根因：实时预测模型链（free → free_fast → fast）逐档尝试时，
openai SDK 抛出的 ``BadRequestError``（"Unsupported model mimo-v2-flash"）
不属于 ``PREDICTION_MODEL_ERRORS``，逃逸出逐档捕获循环直达 API 层，
被 handler 兜底成 500，规则基线（rule-based base）再也无法兜底。

契约：LLM 单档失败（含 openai APIError 家族、熔断 HTTPException、
LLMServiceError）只允许跳过该档，最终必须返回规则基线或 None，
绝不向上抛异常。
"""

import httpx
import pytest
from openai import BadRequestError, RateLimitError
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.predictive_service as predictive_service_module
from app.core.agent_profiles import ModelTier
from app.services.predictive_service import PREDICTION_MODEL_ERRORS, PredictiveService


def _make_status_error(cls, message: str, status_code: int):
    request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
    response = httpx.Response(
        status_code,
        request=request,
        json={"error": {"code": str(status_code), "message": message}},
    )
    return cls(message, response=response, body=None)


def _minimal_base() -> dict:
    return {
        "title": "继续当前任务",
        "summary": "规则基线",
        "confidence": 0.4,
        "predicted_action_type": "continue_task",
        "predicted_window": "now",
        "reasons": ["rule"],
        "suggested_prompt": "继续",
        "signals": {"surface": "chat_input"},
    }


def _service() -> PredictiveService:
    return PredictiveService(db=MagicMock())


class TestPredictionModelErrorsCoverOpenAIFamily:
    def test_openai_api_status_error_is_in_prediction_model_errors(self):
        err = _make_status_error(
            BadRequestError, "Unsupported model mimo-v2-flash", 400
        )
        assert isinstance(err, PREDICTION_MODEL_ERRORS), (
            "openai 4xx/5xx APIError 必须被逐档降级捕获，否则 realtime-next-step 会 500"
        )

    def test_openai_rate_limit_error_is_in_prediction_model_errors(self):
        err = _make_status_error(RateLimitError, "rate limited", 429)
        assert isinstance(err, PREDICTION_MODEL_ERRORS)


@pytest.mark.asyncio
async def test_realtime_llm_bad_request_degrades_instead_of_raising():
    """单档模型抛 openai 4xx 时，整条链应降级返回 None（由规则基线兜底）。"""
    service = _service()
    boom = _make_status_error(
        BadRequestError, "Unsupported model mimo-v2-flash", 400
    )

    async def _raise_for_specific_model(model_key, agent_role=None):
        raise boom

    with (
        patch.object(
            predictive_service_module,
            "is_llm_within_budget",
            new=AsyncMock(return_value=True),
        ),
        patch.object(
            predictive_service_module,
            "get_llm_service_for_specific_model",
            new=_raise_for_specific_model,
        ),
        patch.object(
            PredictiveService,
            "_realtime_model_attempts",
            return_value=[("xiaomi_chat", ModelTier.FAST, 1.0)],
        ),
    ):
        result = await service._generate_realtime_llm_prediction(
            "00000000-0000-0000-0000-000000000001",
            partial_text="帮我复习密码学",
            base=_minimal_base(),
            surface="chat_input",
        )

    assert result is None


@pytest.mark.asyncio
async def test_realtime_forecast_returns_rule_base_when_all_tiers_fail():
    """端到端契约：所有 LLM 档失败后，realtime forecast 必须返回规则基线而非异常。"""
    service = _service()
    base = _minimal_base()
    boom = _make_status_error(
        BadRequestError, "Unsupported model mimo-v2-flash", 400
    )

    async def _raise_for_specific_model(model_key, agent_role=None):
        raise boom

    async def _rule_base(*args, **kwargs):
        return base

    with (
        patch.object(
            PredictiveService,
            "_build_rule_based_realtime_next_step",
            new=_rule_base,
        ),
        patch.object(
            predictive_service_module,
            "is_llm_within_budget",
            new=AsyncMock(return_value=True),
        ),
        patch.object(
            predictive_service_module,
            "get_llm_service_for_specific_model",
            new=_raise_for_specific_model,
        ),
        patch.object(
            PredictiveService,
            "_realtime_model_attempts",
            return_value=[
                ("siliconflow_free", ModelTier.FREE, 1.0),
                ("glm_4_5_air_free", ModelTier.FREE_FAST, 1.0),
                ("xiaomi_chat", ModelTier.FAST, 1.0),
            ],
        ),
    ):
        forecast = await service.get_realtime_next_step_forecast(
            "00000000-0000-0000-0000-000000000002",
            partial_text="帮我复习密码学",
            surface="chat_input",
        )

    assert forecast is base
