from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.gen.sparkle.inference.v1 import inference_pb2
from app.services.llm_dispatcher import LLMDispatcher


class _FakeLimiter:
    def __init__(self) -> None:
        self.reserved: list[tuple[str, int]] = []
        self.refunded: list[tuple[str, int]] = []

    async def check_and_decr(self, user_id: str, amount: int):
        self.reserved.append((user_id, amount))
        return type("Quota", (), {"allowed": True, "current": amount})()

    async def refund(self, user_id: str, amount: int) -> int:
        self.refunded.append((user_id, amount))
        return 0


def _request(message: str, *, max_output_tokens: int = 20) -> inference_pb2.InferenceRequest:
    return inference_pb2.InferenceRequest(
        request_id="req-1",
        trace_id="trace-1",
        user_id="user-1",
        task_type=inference_pb2.SHORT_INFERENCE,
        schema_version="v1",
        prompt_version="p1",
        budgets=inference_pb2.Budgets(max_output_tokens=max_output_tokens),
        messages=[inference_pb2.Message(role="user", content=message)],
        response_format=inference_pb2.TEXT,
    )


@pytest.mark.asyncio
async def test_dispatcher_refunds_reserved_quota_on_provider_failure(monkeypatch):
    dispatcher = LLMDispatcher()
    limiter = _FakeLimiter()

    async def _fail_chat(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(dispatcher, "_cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(dispatcher, "_cache_set", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.llm_dispatcher.get_rate_limiter", AsyncMock(return_value=limiter))
    monkeypatch.setattr("app.services.llm_dispatcher.circuit_breaker_service.check", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.llm_dispatcher.circuit_breaker_service.record_failure", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.llm_dispatcher.llm_service.chat", _fail_chat)

    response = await dispatcher.run(_request("你好，帮我整理今天的计划"))

    assert response.ok is False
    assert response.error_reason == inference_pb2.PROVIDER_UNAVAILABLE
    assert limiter.refunded == limiter.reserved


@pytest.mark.asyncio
async def test_dispatcher_refunds_unused_success_reservation(monkeypatch):
    dispatcher = LLMDispatcher()
    limiter = _FakeLimiter()

    async def _chat(*args, **kwargs):
        return "ok"

    monkeypatch.setattr(dispatcher, "_cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(dispatcher, "_cache_set", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.llm_dispatcher.get_rate_limiter", AsyncMock(return_value=limiter))
    monkeypatch.setattr("app.services.llm_dispatcher.circuit_breaker_service.check", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.llm_dispatcher.circuit_breaker_service.record_success", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.llm_dispatcher.llm_service.chat", _chat)

    response = await dispatcher.run(_request("你好", max_output_tokens=20))

    assert response.ok is True
    assert limiter.reserved == [("user-1", 22)]
    assert limiter.refunded == [("user-1", 19)]


def test_dispatcher_estimates_cjk_without_four_char_discount():
    dispatcher = LLMDispatcher()

    cjk = dispatcher._estimate_tokens(_request("你好世界", max_output_tokens=0))
    english = dispatcher._estimate_tokens(_request("abcd", max_output_tokens=0))

    assert cjk == 4
    assert english == 1
