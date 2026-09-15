from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_execution_engine_passes_spine_state_to_multi_agent_context(monkeypatch) -> None:
    from app.orchestration.execution_engine import ExecutionEngineMixin

    captured: dict = {}

    class _Adapter:
        async def execute_mode_workflow(self, **kwargs):
            captured.update(kwargs["context_data"])
            if False:
                yield None

    engine = ExecutionEngineMixin()
    engine.multi_agent_adapter = _Adapter()
    engine._update_state = AsyncMock()
    monkeypatch.setattr("app.orchestration.execution_engine.settings.ENABLE_MODE_WORKFLOW_V2", True)

    state = SimpleNamespace(
        context_data={
            "spine_response_directive": {"tone": "calm_direct"},
            "spine_chronicle_summary": "steady recovery",
            "spine_fatigue_context": {"fatigue_level": "high"},
            "dual_core_prompt_instruction": "adjust explanation depth",
        }
    )

    results = [
        item async for item in engine._handle_multi_agent_mode(
            state=state,
            chat_mode="__test_unknown_mode__",
            user_message="help",
            user_id="u1",
            session_id="s1",
            response_id="r1",
            request_id="req1",
            trace_id="trace1",
            start_time=0.0,
            user_context_payload={},
            conversation_context={"messages": []},
            plan_context=None,
            active_db=None,
            workflow_id="wf1",
            prompt_version="v1",
            stream_callback=None,
        )
    ]

    assert results == []
    assert captured["spine_response_directive"] == {"tone": "calm_direct"}
    assert captured["spine_chronicle_summary"] == "steady recovery"
    assert captured["spine_fatigue_context"] == {"fatigue_level": "high"}
    assert captured["dual_core_prompt_instruction"] == "adjust explanation depth"


@pytest.mark.asyncio
async def test_spine_context_reaches_build_system_prompt():
    """Verify spine fields flow through _fallback_simple_stream to build_system_prompt."""
    from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter

    mock_orchestrator = MagicMock()
    adapter = MultiAgentWorkflowAdapter(mock_orchestrator)

    spine_directive = {"tone": "calm_direct", "length": "medium", "avoid": [], "must_acknowledge": []}
    context_data = {
        "user_context": {"language": "en"},
        "conversation_context": {"messages": []},
        "plan_context": None,
        "prompt_version": "v1",
        "spine_response_directive": spine_directive,
        "spine_chronicle_summary": "User showed improvement",
        "spine_fatigue_context": {"fatigue_level": "low"},
        "dual_core_prompt_instruction": "Adjust depth",
    }

    with patch("app.orchestration.multi_agent_adapter.build_system_prompt", return_value="prompt") as mock_build:
        # Mock the LLM service to return an async generator of strings
        async def fake_stream(*args, **kwargs):
            yield "test response"

        with patch("app.orchestration.multi_agent_adapter.get_configured_llm_service") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm.stream_chat = fake_stream
            mock_llm_factory.return_value = mock_llm

            gen = adapter._fallback_simple_stream(
                message="test",
                chat_mode="standard",
                context_data=context_data,
                locale="en",
            )
            results = []
            async for chunk in gen:
                results.append(chunk)
                if len(results) >= 1:
                    break

        mock_build.assert_called()
        kwargs = mock_build.call_args[1]
        assert kwargs["spine_response_directive"] == spine_directive
        assert kwargs["spine_chronicle_summary"] == "User showed improvement"
        assert kwargs["spine_fatigue_context"] == {"fatigue_level": "low"}
