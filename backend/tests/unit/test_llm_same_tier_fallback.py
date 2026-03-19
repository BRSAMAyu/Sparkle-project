from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.agent_profiles import AgentRole, ModelTier
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider, llm_router
from app.services.llm_service import LLMService


class _FakeRawStream:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def __aiter__(self):
        self._iter = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeCompletions:
    def __init__(self, base_url: str, calls: list[dict]):
        self.base_url = base_url
        self.calls = calls

    async def create(self, **kwargs):
        self.calls.append({"base_url": self.base_url, "kwargs": kwargs})
        if self.base_url == "https://primary.test":
            raise Exception("429 Too Many Requests")

        if kwargs.get("stream"):
            chunks = [
                SimpleNamespace(usage=None, choices=[SimpleNamespace(delta=SimpleNamespace(content="ok", tool_calls=None))]),
                SimpleNamespace(usage=None, choices=[]),
            ]
            return _FakeRawStream(chunks)

        message = SimpleNamespace(content=f"reply from {self.base_url}", tool_calls=None)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)


class _FakeChatNamespace:
    def __init__(self, base_url: str, calls: list[dict]):
        self.completions = _FakeCompletions(base_url, calls)


class FakeProvider:
    calls: list[dict] = []

    def __init__(self, api_key: str, base_url: str, timeout_seconds: float = 60.0):
        self.api_key = api_key
        self.base_url = base_url
        self.client = SimpleNamespace(chat=_FakeChatNamespace(base_url, self.calls))

    async def chat(self, messages, model, temperature=0.7, **kwargs):
        self.calls.append(
            {
                "base_url": self.base_url,
                "kwargs": {
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                    **kwargs,
                },
            }
        )
        if self.base_url == "https://primary.test":
            raise Exception("429 Too Many Requests")
        return f"reply from {self.base_url}"

    async def stream_chat(self, messages, model, temperature=0.7, **kwargs):
        self.calls.append(
            {
                "base_url": self.base_url,
                "kwargs": {
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                    **kwargs,
                },
            }
        )
        if self.base_url == "https://primary.test":
            raise Exception("429 Too Many Requests")
        yield "reply "
        yield "from stream"


def _build_selection(model_key: str, config: ModelConfig, task_type=None) -> LLMSelection:
    return LLMSelection(
        model_key=model_key,
        config=config,
        agent_role=AgentRole.GENERATION,
        task_type=task_type,
        reason="test",
    )


@pytest.fixture
def fallback_router(monkeypatch):
    primary = ModelConfig(
        provider=ModelProvider.ZHIPU,
        model_name="glm-primary",
        base_url="https://primary.test",
        api_key="primary-key",
        temperature=0.3,
        clear_thinking=True,
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

    original_models = llm_router._available_models.copy()
    original_tiers = llm_router._tier_mapping.copy()

    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {
            "primary_standard": primary,
            "secondary_standard": secondary,
            "default": secondary,
        },
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
    monkeypatch.setattr(
        "app.services.llm_service.OpenAICompatibleProvider",
        FakeProvider,
    )

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.check", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_success", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_failure", _noop)

    FakeProvider.calls = []

    yield SimpleNamespace(primary=primary, secondary=secondary)

    llm_router._available_models = original_models
    llm_router._tier_mapping = original_tiers


@pytest.mark.asyncio
async def test_chat_same_tier_fallback_on_429(fallback_router):
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    response = await service.chat([{"role": "user", "content": "hello"}])

    assert response == "reply from https://secondary.test"
    assert [call["base_url"] for call in FakeProvider.calls[:2]] == [
        "https://primary.test",
        "https://secondary.test",
    ]
    assert FakeProvider.calls[0]["kwargs"]["extra_body"] == {"clear_thinking": True}


@pytest.mark.asyncio
async def test_chat_with_tools_same_tier_fallback_on_429(fallback_router):
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    response = await service.chat_with_tools(
        system_prompt="You are helpful.",
        user_message="hello",
        tools=[],
        conversation_history=None,
    )

    assert response.content == "reply from https://secondary.test"
    assert [call["base_url"] for call in FakeProvider.calls[:2]] == [
        "https://primary.test",
        "https://secondary.test",
    ]
    assert FakeProvider.calls[0]["kwargs"]["extra_body"] == {"clear_thinking": True}


@pytest.mark.asyncio
async def test_reason_same_tier_fallback_on_429(fallback_router):
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    response = await service.reason([{"role": "user", "content": "think deeply"}])

    assert response == "reply from https://secondary.test"
    assert [call["base_url"] for call in FakeProvider.calls[:2]] == [
        "https://primary.test",
        "https://secondary.test",
    ]
    assert FakeProvider.calls[0]["kwargs"]["extra_body"] == {"clear_thinking": True}


@pytest.mark.asyncio
async def test_reason_honors_explicit_glm_batch_override(monkeypatch):
    explicit_primary = ModelConfig(
        provider=ModelProvider.ZHIPU,
        model_name="glm-4.7",
        base_url="https://primary.test",
        api_key="primary-key",
        temperature=0.2,
        clear_thinking=False,
        tier=ModelTier.GLM_BATCH,
    )
    explicit_secondary = ModelConfig(
        provider=ModelProvider.ZHIPU,
        model_name="glm-4.7-flash",
        base_url="https://secondary.test",
        api_key="secondary-key",
        temperature=0.2,
        clear_thinking=False,
        tier=ModelTier.GLM_BATCH,
    )
    unrelated_reasoning = ModelConfig(
        provider=ModelProvider.XIAOMI,
        model_name="mimo-v2-pro",
        base_url="https://reasoning.test",
        api_key="reasoning-key",
        temperature=0.2,
        tier=ModelTier.REASONING,
    )

    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {
            "glm_4_7_thinking": explicit_primary,
            "glm_4_7_flash_thinking": explicit_secondary,
            "mimo_pro": unrelated_reasoning,
            "default": unrelated_reasoning,
        },
    )
    monkeypatch.setattr(
        llm_router,
        "_tier_mapping",
        {
            ModelTier.GLM_BATCH: ["glm_4_7_thinking", "glm_4_7_flash_thinking"],
            ModelTier.REASONING: ["mimo_pro"],
            ModelTier.STANDARD: [],
            ModelTier.FAST: [],
            ModelTier.FREE_REASONING: [],
            ModelTier.FREE_FAST: [],
            ModelTier.SPECIALIST: [],
        },
    )
    monkeypatch.setattr(
        llm_router,
        "select_model",
        lambda agent_role, task_type=None, force_tier=None: _build_selection("mimo_pro", unrelated_reasoning, task_type),
    )
    monkeypatch.setattr(
        llm_router,
        "select_specific_model",
        lambda model_key, agent_role=None: _build_selection(model_key, llm_router._available_models[model_key]),
    )
    monkeypatch.setattr(
        "app.services.llm_service.OpenAICompatibleProvider",
        FakeProvider,
    )

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.check", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_success", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_failure", _noop)

    FakeProvider.calls = []

    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)
    await service.switch_to_specific_model("glm_4_7_thinking")

    response = await service.reason([{"role": "user", "content": "think deeply"}])

    assert response == "reply from https://secondary.test"
    assert [call["base_url"] for call in FakeProvider.calls[:2]] == [
        "https://primary.test",
        "https://secondary.test",
    ]
    assert all(call["base_url"] != "https://reasoning.test" for call in FakeProvider.calls[:2])


@pytest.mark.asyncio
async def test_chat_stream_with_tools_skips_original_model_after_429(fallback_router):
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    chunks = []
    async for chunk in service.chat_stream_with_tools(
        system_prompt="You are helpful.",
        user_message="hello",
        tools=[],
        user_context=None,
    ):
        if chunk.type == "text":
            chunks.append(chunk.content)

    assert "".join(chunks) == "ok"
    assert [call["base_url"] for call in FakeProvider.calls[:2]] == [
        "https://primary.test",
        "https://secondary.test",
    ]


@pytest.mark.asyncio
async def test_thinking_mode_is_sent_via_extra_body_not_top_level(monkeypatch):
    xiaomi_cfg = ModelConfig(
        provider=ModelProvider.XIAOMI,
        model_name="mimo-v2-pro",
        base_url="https://mimo.test",
        api_key="mimo-key",
        temperature=0.2,
        thinking_mode="enabled",
        tier=ModelTier.STANDARD,
    )

    monkeypatch.setattr(
        llm_router,
        "_available_models",
        {
            "mimo_pro": xiaomi_cfg,
            "default": xiaomi_cfg,
        },
    )
    monkeypatch.setattr(
        llm_router,
        "_tier_mapping",
        {
            ModelTier.STANDARD: ["mimo_pro"],
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
        lambda agent_role, task_type=None, force_tier=None: _build_selection("mimo_pro", xiaomi_cfg, task_type),
    )
    monkeypatch.setattr("app.services.llm_service.OpenAICompatibleProvider", FakeProvider)

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.check", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_success", _noop)
    monkeypatch.setattr("app.services.llm_service.circuit_breaker_service.record_failure", _noop)

    FakeProvider.calls = []
    service = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

    await service.chat_with_tools(
        system_prompt="You are helpful.",
        user_message="hello",
        tools=[],
        conversation_history=None,
    )

    kwargs = FakeProvider.calls[0]["kwargs"]
    assert "thinking" not in kwargs
    assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}
