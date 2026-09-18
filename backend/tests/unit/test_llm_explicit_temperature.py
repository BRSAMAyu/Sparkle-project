"""Regression tests for explicit temperature passthrough (E2)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider, llm_router
from app.services.llm_service import LLMService


class FakeProvider:
    calls: list[dict] = []

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 60.0):
        self.base_url = base_url

    async def chat(self, messages, model, temperature=0.7, **kwargs):
        FakeProvider.calls.append({"base_url": self.base_url, "kwargs": {"model": model, "temperature": temperature, **kwargs}})
        return "ok"

    async def stream_chat(self, messages, model, temperature=0.7, **kwargs):
        FakeProvider.calls.append({"base_url": self.base_url, "kwargs": {"model": model, "temperature": temperature, **kwargs}})
        yield "ok"


def _build_selection(model_key: str, config: ModelConfig, task_type=None) -> LLMSelection:
    return LLMSelection(
        model_key=model_key,
        config=config,
        agent_role=AgentRole.GENERATION,
        task_type=task_type,
        reason="test",
    )


@pytest.fixture
def routed_service(monkeypatch):
    primary = ModelConfig(
        provider=ModelProvider.ZHIPU,
        model_name="glm-primary",
        base_url="https://primary.test",
        api_key="primary-key",
        temperature=0.3,
        tier=ModelTier.STANDARD,
    )
    secondary = ModelConfig(
        provider=ModelProvider.DASHSCOPE,
        model_name="qwen-secondary",
        base_url="https://secondary.test",
        api_key="secondary-key",
        temperature=0.2,
        tier=ModelTier.STANDARD,
    )
    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {"primary_standard": primary, "secondary_standard": secondary, "default": secondary},
    )
    monkeypatch.setattr(
        llm_router,
        "_tier_mapping",
        {
            ModelTier.STANDARD: ["primary_standard", "secondary_standard"],
            ModelTier.REASONING: [],
            ModelTier.FAST: [],
            ModelTier.FREE_REASONING: [],
            ModelTier.FREE_FAST: [],
            ModelTier.SPECIALIST: [],
        },
    )
    monkeypatch.setattr(
        llm_router,
        "select_model",
        lambda agent_role, task_type=None, force_tier=None: _build_selection("primary_standard", primary, task_type),
    )
    monkeypatch.setattr("app.services.llm_service.OpenAICompatibleProvider", FakeProvider)

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.check", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_success", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_failure", _noop)

    FakeProvider.calls = []
    return SimpleNamespace(primary=primary, secondary=secondary)


@pytest.mark.asyncio
async def test_chat_honors_explicit_temperature(routed_service):
    """E2: caller 显式传入的 temperature 不得被动态路由 selection 静默覆盖。"""
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    await service.chat([{"role": "user", "content": "hello"}], temperature=0.0)

    assert FakeProvider.calls, "provider should have been called"
    assert FakeProvider.calls[0]["kwargs"]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_chat_without_explicit_temperature_uses_selection_config(routed_service):
    """E2 对照：未显式传 temperature 时仍用路由 selection 的配置值。"""
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    await service.chat([{"role": "user", "content": "hello"}])

    assert FakeProvider.calls[0]["kwargs"]["temperature"] == 0.3


@pytest.mark.asyncio
async def test_reason_honors_explicit_temperature(routed_service):
    """E2: reason 路径同样必须尊重 caller 显式 temperature。"""
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    await service.reason([{"role": "user", "content": "think"}], temperature=0.0)

    assert FakeProvider.calls, "provider should have been called"
    assert FakeProvider.calls[0]["kwargs"]["temperature"] == 0.0
