"""RB-01 regression tests: `_build_final_response` must not crash when
`focused_memory` is absent from `final_state.context_data`.

The bug: `semantic_meta` was only assigned inside the
`isinstance(focused_memory, dict)` branch but read unconditionally afterwards,
raising `UnboundLocalError` and turning an already-generated successful answer
into an ERROR frame that is never persisted.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration import response_builder as response_builder_module
from app.orchestration.response_builder import ResponseBuilderMixin
from app.orchestration.schemas import RouteDecision
from app.orchestration.statechart_engine import WorkflowState


class _StubEnvelopeBuilder:
    async def build(self, **kwargs: Any) -> dict[str, Any]:
        return {}

    def to_metadata_map(self, envelope: dict[str, Any]) -> dict[str, str]:
        return {}


class _StubbedResponseBuilder(ResponseBuilderMixin):
    """Host object with heavy cross-mixin dependencies stubbed out."""

    def __init__(self) -> None:
        self.redis = None
        self.token_tracker = None

    @staticmethod
    def _extract_llm_profile_meta(user_context_payload: dict[str, Any] | None) -> dict[str, Any]:
        return {}

    async def _validate_plan_execution(self, **kwargs: Any) -> None:
        return None

    def _derive_task_context_for_execution(
        self,
        *,
        task_context: Any,
        plan_context: Any,
        user_context_payload: Any,
    ) -> None:
        return None

    async def _detect_execution_suggestion(self, **kwargs: Any) -> None:
        return None

    async def _hydrate_evolution_context(self, **kwargs: Any) -> None:
        return None

    async def _persist_assistant_message(self, **kwargs: Any) -> None:
        self.persisted = kwargs

    async def _record_decision(self, **kwargs: Any) -> None:
        return None


def _make_final_state(*, with_focused_memory: bool) -> WorkflowState:
    state = WorkflowState()
    state.messages.append({"role": "user", "content": "帮我梳理今天的重点"})
    state.messages.append({"role": "assistant", "content": "好的，先从三门课的复习顺序说起。"})
    if with_focused_memory:
        state.context_data["focused_memory"] = {
            "preferences": {},
            "active_goals": [],
            "episodic_memories": [],
            "context_pack": {"metadata": {"semantic_gating": {"mode": "anchored"}}},
        }
    return state


async def _build(builder: _StubbedResponseBuilder, final_state: WorkflowState):
    return await builder._build_final_response(
        final_state=final_state,
        executable_plan=None,
        active_db=None,
        user_id=str(uuid.uuid4()),
        session_id="session-rb01",
        response_id="resp-rb01",
        request_id="req-rb01",
        trace_id="trace-rb01",
        workflow_id="wf-rb01",
        prompt_version="v1",
        route_decision=RouteDecision(execution_mode="direct", reason="unit", risk_level="low"),
        plan_switched=False,
        plan_id=None,
        plan_context=None,
        user_context_payload=None,
        total_prompt_tokens=0,
        total_completion_tokens=0,
    )


@pytest.fixture
def builder(monkeypatch: pytest.MonkeyPatch) -> _StubbedResponseBuilder:
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_FOCUS_METADATA", True)
    monkeypatch.setattr(response_builder_module, "ux_envelope_builder", _StubEnvelopeBuilder())
    return _StubbedResponseBuilder()


@pytest.mark.asyncio
async def test_build_final_response_survives_missing_focused_memory(builder: _StubbedResponseBuilder) -> None:
    final_state = _make_final_state(with_focused_memory=False)

    response, data = await _build(builder, final_state)

    assert response.finish_reason == agent_service_pb2.STOP
    assert response.full_text == "好的，先从三门课的复习顺序说起。"
    assert data["message"] == "好的，先从三门课的复习顺序说起。"
    assert getattr(builder, "persisted", None) is not None, "assistant message should be persisted"


@pytest.mark.asyncio
async def test_build_final_response_still_emits_semantic_gating_when_present(
    builder: _StubbedResponseBuilder,
) -> None:
    final_state = _make_final_state(with_focused_memory=True)

    response, _ = await _build(builder, final_state)

    assert response.finish_reason == agent_service_pb2.STOP
    assert "focused_memory_summary" in response.metadata
    assert "context_semantic_gating" in response.metadata
