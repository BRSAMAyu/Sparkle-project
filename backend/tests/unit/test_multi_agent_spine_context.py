from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter


class _FakeLLM:
    default_model = "fake-model"

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def stream_chat(self, *, messages, model=None, temperature=0.5):
        self.messages = messages
        yield "ok"


def _adapter(fake_llm: _FakeLLM) -> MultiAgentWorkflowAdapter:
    adapter = MultiAgentWorkflowAdapter.__new__(MultiAgentWorkflowAdapter)
    adapter.llm_service = fake_llm
    return adapter


def _spine_context() -> dict[str, Any]:
    return {
        "user_context": {"language": "en"},
        "conversation_context": {"messages": []},
        "spine_response_directive": {
            "tone": "calm_urgent",
            "length": "short",
            "must_acknowledge": ["the user is tired"],
        },
        "spine_chronicle_summary": "The user recovered from a hard week.",
        "spine_fatigue_context": {"fatigue_level": "high"},
    }


@pytest.mark.asyncio
async def test_multi_agent_synthesis_forwards_spine_context(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_build_system_prompt(**kwargs):
        captured.update(kwargs)
        return "BASE"

    monkeypatch.setattr("app.orchestration.multi_agent_adapter.build_system_prompt", fake_build_system_prompt)
    fake_llm = _FakeLLM()
    adapter = _adapter(fake_llm)

    chunks = [
        chunk async for chunk in adapter._stream_synthesis_response(
            chat_mode="deep_analysis",
            user_message="analyze this",
            execution_result=SimpleNamespace(),
            validation_result=SimpleNamespace(validation_status="passed", quality_score=0.9, aborted=False, issues=[]),
            execution_summary="done",
            synthesis_template="summarize",
            context_data=_spine_context(),
            locale="en",
        )
    ]

    assert chunks[-1].delta == "ok"
    assert captured["spine_response_directive"]["tone"] == "calm_urgent"
    assert captured["spine_chronicle_summary"] == "The user recovered from a hard week."
    assert captured["spine_fatigue_context"]["fatigue_level"] == "high"


@pytest.mark.asyncio
async def test_multi_agent_fallback_forwards_spine_context(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_build_system_prompt(**kwargs):
        captured.update(kwargs)
        return "BASE"

    monkeypatch.setattr("app.orchestration.multi_agent_adapter.build_system_prompt", fake_build_system_prompt)
    fake_llm = _FakeLLM()
    adapter = _adapter(fake_llm)

    chunks = [
        chunk async for chunk in adapter._fallback_simple_stream(
            message="help",
            chat_mode="study_plan",
            context_data=_spine_context(),
            locale="en",
        )
    ]

    assert chunks[-1].delta == "ok"
    assert captured["spine_response_directive"]["length"] == "short"
    assert captured["spine_chronicle_summary"] == "The user recovered from a hard week."
    assert captured["spine_fatigue_context"]["fatigue_level"] == "high"
