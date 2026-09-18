"""M-2 stream variance guards (round2/m2-stream-variance.md).

Red-green coverage for the three provider-side amplifiers:
1. OpenAI SDK implicit retries disabled (max_retries=0).
2. First-chunk stream deadline (45s / 90s reasoning) triggers the existing
   fallback path instead of hanging for the full 120s/300s stream budget,
   while the overall budget still applies after the first chunk arrives.
3. Provider-level TTFT histogram (sparkle_llm_provider_ttft_seconds) is
   registered and observed per provider/model.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from prometheus_client import REGISTRY

import app.services.llm_service as llm_service_module
from app.core.agent_profiles import AgentRole
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider
from app.services.llm.base import LLMProvider
from app.services.llm.fallback import FallbackReason, llm_fallback_manager
from app.services.llm.providers import OpenAICompatibleProvider
from app.services.llm_service import LLMService

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


def _make_selection(model_key: str = "m2-test-primary", model_name: str = "deepseek-chat") -> LLMSelection:
    return LLMSelection(
        model_key=model_key,
        config=ModelConfig(
            provider=ModelProvider.DEEPSEEK,
            model_name=model_name,
            base_url=DEEPSEEK_BASE_URL,
            api_key="sk-test",
        ),
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="m2 test selection",
    )


def _make_service(provider: LLMProvider, selection: LLMSelection) -> LLMService:
    service = LLMService(enable_dynamic_routing=False)
    service.demo_mode = False
    service._current_selection = selection
    service._provider = provider
    return service


class _ScriptedStreamProvider(LLMProvider):
    """Yields per-call scripted streams; each call pops the next behavior."""

    def __init__(self, behaviors: list[str]):
        self.behaviors = list(behaviors)
        self.calls = 0

    async def chat(self, messages, model, temperature: float = 0.7, **kwargs) -> str:
        return ""

    async def stream_chat(self, messages, model, temperature: float = 0.7, **kwargs):
        self.calls += 1
        behavior = self.behaviors.pop(0) if self.behaviors else "hang"
        if behavior == "hang":
            # Silent provider: no first chunk within any sane window.
            await asyncio.sleep(30)
            yield "never"
            return
        # behavior == "ok": healthy stream with a pause AFTER the first chunk.
        yield "ok-1"
        await asyncio.sleep(0.15)
        yield "ok-2"


class _RawClientProvider(LLMProvider):
    """Exposes .client.chat.completions.create like OpenAICompatibleProvider,
    serving scripted raw streams — the main chat generation path
    (chat_stream_with_tools -> _create_raw_stream)."""

    def __init__(self, behaviors: list[str]):
        self.behaviors = list(behaviors)
        self.calls = 0
        provider = self

        async def create(**params):
            provider.calls += 1
            behavior = provider.behaviors.pop(0) if provider.behaviors else "hang"
            if behavior == "hang":
                return _hanging_raw_stream()
            return _healthy_raw_stream()

        self.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    async def chat(self, messages, model, temperature: float = 0.7, **kwargs) -> str:
        return ""

    async def stream_chat(self, messages, model, temperature: float = 0.7, **kwargs):
        yield "unused"


async def _hanging_raw_stream():
    # Silent provider: no first chunk within any sane window.
    await asyncio.sleep(30)
    yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="never"))])


def _raw_chunk(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=None))])


async def _healthy_raw_stream():
    yield _raw_chunk("raw-1")
    await asyncio.sleep(0.15)
    yield _raw_chunk("raw-2")


class _StubFallbackManager:
    """Records the first stream attempt; on a fallback-eligible error it
    re-runs the stream once, mirroring execute_stream_with_fallback."""

    def __init__(self) -> None:
        self.first_error: Exception | None = None
        self.attempts = 0

    async def execute_stream_with_fallback(self, selection, stream_fn, operation_type="stream_chat"):
        self.attempts += 1
        try:
            async for chunk in stream_fn(selection):
                yield chunk
            return
        except Exception as exc:  # noqa: BLE001 - test stub mirrors real manager
            self.first_error = exc
            if "timeout" not in str(exc).lower():
                raise
        # Fallback switch (same stream_fn, second attempt succeeds).
        async for chunk in stream_fn(selection):
            yield chunk


# ---------------------------------------------------------------------------
# 1. SDK implicit retries
# ---------------------------------------------------------------------------


def test_openai_provider_disables_sdk_implicit_retries():
    provider = OpenAICompatibleProvider(api_key="sk-test", base_url=DEEPSEEK_BASE_URL)
    # openai DEFAULT_MAX_RETRIES=2 stacked invisible exponential backoff on
    # TTFT tails; the fallback manager owns retry policy now.
    assert provider.client.max_retries == 0


def test_openai_provider_name_resolution_unchanged():
    provider = OpenAICompatibleProvider(api_key="sk-test", base_url=DEEPSEEK_BASE_URL)
    assert provider._get_provider_name() == "deepseek"


# ---------------------------------------------------------------------------
# 2. First-chunk deadline -> fallback path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_chunk_timeout_triggers_fallback(monkeypatch):
    monkeypatch.setattr(llm_service_module, "LLM_STREAM_FIRST_CHUNK_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(llm_service_module, "LLM_STREAM_OVERALL_TIMEOUT_SECONDS", 1.0)

    selection = _make_selection()
    provider = _ScriptedStreamProvider(["hang", "ok"])
    service = _make_service(provider, selection)

    stub = _StubFallbackManager()
    monkeypatch.setattr(llm_service_module, "llm_fallback_manager", stub)

    chunks: list[str] = []
    async for chunk in service.stream_chat([{"role": "user", "content": "hi"}], user_context={"user_id": "u1"}):
        chunks.append(chunk)

    assert chunks == ["ok-1", "ok-2"]
    assert provider.calls == 2, "first attempt hangs, fallback re-runs the stream"
    assert stub.first_error is not None
    assert "timeout" in str(stub.first_error).lower()
    # The raised error must be classified as TIMEOUT by the real fallback
    # manager, otherwise no model switch would happen.
    assert llm_fallback_manager._detect_fallback_reason(stub.first_error) is FallbackReason.TIMEOUT


@pytest.mark.asyncio
async def test_first_chunk_arrival_relaxes_deadline_for_stream_body(monkeypatch):
    # A 0.15s gap between chunks exceeds the 0.05s first-chunk window but is
    # well within the overall budget: the deadline must be rescheduled after
    # the first chunk, not cut the healthy stream.
    monkeypatch.setattr(llm_service_module, "LLM_STREAM_FIRST_CHUNK_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(llm_service_module, "LLM_STREAM_OVERALL_TIMEOUT_SECONDS", 5.0)

    selection = _make_selection()
    provider = _ScriptedStreamProvider(["ok"])
    service = _make_service(provider, selection)

    stub = _StubFallbackManager()
    monkeypatch.setattr(llm_service_module, "llm_fallback_manager", stub)

    chunks: list[str] = []
    async for chunk in service.stream_chat([{"role": "user", "content": "hi"}], user_context={"user_id": "u1"}):
        chunks.append(chunk)

    assert chunks == ["ok-1", "ok-2"]
    assert stub.first_error is None, "healthy stream must not hit the first-chunk deadline"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_main_chain_raw_stream_first_chunk_timeout_triggers_fallback(monkeypatch):
    monkeypatch.setattr(llm_service_module, "LLM_STREAM_FIRST_CHUNK_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(llm_service_module, "LLM_STREAM_OVERALL_TIMEOUT_SECONDS", 1.0)

    selection = _make_selection()
    provider = _RawClientProvider(["hang", "ok"])
    service = _make_service(provider, selection)

    stub = _StubFallbackManager()
    monkeypatch.setattr(llm_service_module, "llm_fallback_manager", stub)

    chunks = [
        chunk
        async for chunk in service.chat_stream_with_tools(
            system_prompt="sys",
            user_message="hi",
            tools=[],
            user_context={"user_id": "u1"},
        )
        if chunk.type == "text"
    ]

    assert [chunk.content for chunk in chunks] == ["raw-1", "raw-2"]
    assert provider.calls == 2, "first attempt hangs, fallback re-runs the stream"
    assert stub.first_error is not None
    assert "timeout" in str(stub.first_error).lower()
    assert llm_fallback_manager._detect_fallback_reason(stub.first_error) is FallbackReason.TIMEOUT


@pytest.mark.asyncio
async def test_raw_stream_observes_provider_ttft_histogram():
    selection = _make_selection()
    provider = _RawClientProvider(["ok"])
    service = _make_service(provider, selection)

    before = _ttft_count("deepseek", "deepseek-chat") or 0.0

    _ = [
        chunk
        async for chunk in service.chat_stream_with_tools(
            system_prompt="sys",
            user_message="hi",
            tools=[],
            user_context={"user_id": "u1"},
        )
        if chunk.type == "text"
    ]

    after = _ttft_count("deepseek", "deepseek-chat")
    assert after == before + 1


# ---------------------------------------------------------------------------
# 3. Provider TTFT probe
# ---------------------------------------------------------------------------


def _ttft_count(provider_label: str, model: str) -> float | None:
    return REGISTRY.get_sample_value(
        "sparkle_llm_provider_ttft_seconds_count",
        {"provider": provider_label, "model": model},
    )


@pytest.mark.asyncio
async def test_provider_ttft_histogram_registered_and_observed():
    provider = OpenAICompatibleProvider(api_key="sk-test", base_url=DEEPSEEK_BASE_URL)

    class _Chunk:
        def __init__(self, content: str):
            self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]

    async def fake_stream():
        await asyncio.sleep(0.05)  # simulated provider TTFT
        yield _Chunk("hello")
        yield _Chunk(" world")

    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=fake_stream())))
    )

    model = "deepseek-chat"
    before = _ttft_count("deepseek", model) or 0.0

    chunks = [chunk async for chunk in provider.stream_chat([{"role": "user", "content": "hi"}], model=model)]

    assert chunks == ["hello", " world"]
    after = _ttft_count("deepseek", model)
    assert after is not None, "sparkle_llm_provider_ttft_seconds must be registered"
    assert after == before + 1
