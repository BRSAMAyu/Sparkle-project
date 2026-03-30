from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import (
    ChatOrchestrator,
    STATE_DONE,
    STATE_GENERATING,
    STATE_INIT,
    STATE_THINKING,
    STATE_TOOL_CALLING,
)
from app.orchestration.schemas import RouteDecision
from app.orchestration.statechart_engine import WorkflowState


class _RunLedgerStub:
    def __init__(self, *args, **kwargs):
        pass

    async def record_event(self, *args, **kwargs) -> None:
        return None


class _ChatSignalCollectorStub:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    async def collect_signals(self, *args, **kwargs) -> None:
        return None


async def _passthrough_route(route_decision: RouteDecision, **kwargs) -> RouteDecision:
    return route_decision


async def _emit_noop(*args, **kwargs) -> None:
    return None


def _make_request(*, message: str = "帮我整理今天的学习重点") -> agent_service_pb2.ChatRequest:
    return agent_service_pb2.ChatRequest(
        request_id=f"req-{uuid.uuid4()}",
        session_id=f"session-{uuid.uuid4()}",
        user_id=str(uuid.uuid4()),
        message=message,
    )


async def _collect(
    orchestrator: ChatOrchestrator,
    request: agent_service_pb2.ChatRequest,
) -> list[agent_service_pb2.ChatResponse]:
    return [response async for response in orchestrator.process_stream(request)]


async def _drain_queue(
    queue,
) -> AsyncGenerator[agent_service_pb2.ChatResponse, None]:
    while not queue.empty():
        item = await queue.get()
        yield item
        queue.task_done()


@pytest.fixture
def orchestrator_factory(monkeypatch):
    monkeypatch.setattr("app.orchestration.orchestrator.create_standard_chat_graph", lambda: MagicMock())
    monkeypatch.setattr("app.orchestration.orchestrator.RunLedgerRecorder", _RunLedgerStub)
    monkeypatch.setattr("app.orchestration.orchestrator.ChatSignalCollector", _ChatSignalCollectorStub)

    async def _breaker_initialize(self) -> None:
        return None

    monkeypatch.setattr("app.orchestration.circuit_breaker.CircuitBreaker.initialize", _breaker_initialize)

    def _factory() -> tuple[ChatOrchestrator, AsyncMock, list[tuple[str, str]]]:
        redis_client = AsyncMock()
        redis_client.get.return_value = None
        redis_client.set.return_value = True
        redis_client.setex.return_value = True
        redis_client.eval.return_value = 1
        redis_client.keys.return_value = []
        redis_client.ttl.return_value = 60
        redis_client.delete.return_value = 1
        redis_client.expire.return_value = True
        redis_client.ping.return_value = True

        orchestrator = ChatOrchestrator(db_session=None, redis_client=redis_client)
        state_updates: list[tuple[str, str]] = []
        real_update_state = orchestrator._update_state

        async def tracked_update_state(session_id: str, state: str, details: str = "", **kwargs):
            state_updates.append((state, details))
            return await real_update_state(session_id, state, details, **kwargs)

        orchestrator._update_state = tracked_update_state
        orchestrator._validate_request = AsyncMock(return_value=None)
        orchestrator._check_idempotency_response = AsyncMock(return_value=None)
        orchestrator._acquire_session_lock = AsyncMock(return_value=True)
        orchestrator.state_manager.start_lock_renewal = AsyncMock(return_value=(None, None))
        orchestrator._resolve_active_tools = MagicMock(return_value=[])
        orchestrator._maybe_short_circuit_bridge_tool = AsyncMock(return_value=None)
        orchestrator._build_full_context = AsyncMock(return_value=({}, None, False, {}, {"messages": []}, None))
        orchestrator._detect_session_feedback = AsyncMock(return_value=(None, None, None))
        orchestrator._apply_cohort_to_session_feedback_signal = MagicMock(side_effect=lambda signal, cohort: signal)
        orchestrator._maybe_enqueue_perceptible_insight = AsyncMock(return_value=None)
        orchestrator._maybe_enqueue_understanding_depth = AsyncMock(return_value=None)
        orchestrator._drain_system_updates = AsyncMock(return_value=([], [], [], [], None, None))
        orchestrator._check_sufficiency = AsyncMock(return_value=(False, "chat"))
        orchestrator._check_goal_quality = AsyncMock(return_value=False)
        orchestrator._prepare_runtime_context = AsyncMock(return_value=(None, _emit_noop))
        orchestrator._notify_pending_milestone_proposals = AsyncMock(return_value=None)
        orchestrator._apply_context_focus_overlay = AsyncMock(side_effect=lambda **kwargs: kwargs["user_context_payload"])
        orchestrator._apply_dual_core_routing = AsyncMock(side_effect=_passthrough_route)
        orchestrator._emit_orchestration_trace = AsyncMock(return_value=None)
        orchestrator._cache_response = AsyncMock(return_value=True)
        orchestrator._cleanup = AsyncMock(return_value=None)
        orchestrator._track_task = MagicMock()
        orchestrator._persist_assistant_message = AsyncMock(return_value=None)
        orchestrator._record_decision = AsyncMock(return_value=None)
        orchestrator.observability.log_route_decision = AsyncMock(return_value=None)
        orchestrator.observability.log_circuit_state_change = AsyncMock(return_value=None)
        orchestrator.observability.log_collaboration_start = AsyncMock(return_value=None)
        orchestrator.observability.log_collaboration_end = AsyncMock(return_value=None)
        orchestrator.observability.log_langgraph_plan = AsyncMock(return_value=None)
        orchestrator.observability.log_validation_failed = AsyncMock(return_value=None)
        orchestrator.shadow_predictor.predict_and_record = AsyncMock(return_value=None)

        return orchestrator, redis_client, state_updates

    return _factory


@pytest.mark.asyncio
async def test_process_stream_direct_flow_reaches_done(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request()
    captured_modes: list[str] = []

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._plan_and_validate = AsyncMock(side_effect=lambda **kwargs: (
        kwargs["route_decision"],
        None,
        None,
        False,
    ))

    async def execute_graph(*, queue, result_holder, **kwargs):
        async for item in _drain_queue(queue):
            yield item
        await orchestrator._update_state(request.session_id, STATE_THINKING, "Understanding request")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.THINKING,
                details="理解问题中",
            )
        )
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Drafting final answer")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details="组织回答中",
            )
        )
        yield agent_service_pb2.ChatResponse(delta="先帮你梳理重点。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, route_decision, session_id, **kwargs):
        captured_modes.append(route_decision.execution_mode)
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="先帮你梳理重点。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "先帮你梳理重点。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert captured_modes == ["direct"]
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_DONE]
    assert any(
        response.HasField("status_update")
        and response.status_update.state == agent_service_pb2.AgentStatus.THINKING
        for response in responses
    )
    assert any(
        response.HasField("status_update")
        and response.status_update.state == agent_service_pb2.AgentStatus.GENERATING
        for response in responses
    )
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "先帮你梳理重点。"
    assert final_state is not None
    assert final_state.state == STATE_DONE


@pytest.mark.asyncio
async def test_process_stream_tool_result_continuation_marks_done(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="")
    request.tool_result.tool_call_id = "tool-1"
    request.tool_result.tool_name = "search_knowledge"
    request.tool_result.result_json = '{"summary":"找到 3 条相关知识"}'

    async def continue_after_tool_result(**kwargs):
        await orchestrator._update_state(request.session_id, STATE_TOOL_CALLING, "Tool result received")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
                details="处理工具结果",
            )
        )
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Synthesizing tool result")
        yield agent_service_pb2.ChatResponse(
            status_update=agent_service_pb2.AgentStatus(
                state=agent_service_pb2.AgentStatus.GENERATING,
                details="整合工具输出",
            )
        )
        yield agent_service_pb2.ChatResponse(
            full_text="根据工具结果，我已经帮你整理出关键结论。",
            finish_reason=agent_service_pb2.STOP,
        )

    orchestrator._continue_after_tool_result = continue_after_tool_result

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_TOOL_CALLING, STATE_GENERATING, STATE_DONE]
    assert any(
        response.HasField("status_update")
        and response.status_update.state == agent_service_pb2.AgentStatus.EXECUTING_TOOL
        for response in responses
    )
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "根据工具结果，我已经帮你整理出关键结论。"
    assert final_state is not None
    assert final_state.state == STATE_DONE


@pytest.mark.asyncio
async def test_process_stream_planner_failure_falls_back_to_direct_mode(orchestrator_factory):
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request(message="帮我设计一个跨学科长期学习方案")
    captured_modes: list[str] = []

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="langgraph", reason="complex_plan", risk_level="medium"), None)
    )
    orchestrator.snapshot_manager.create_snapshot = AsyncMock(return_value=MagicMock(snapshot_id="snap-1"))
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator.lang_graph_planner.plan = AsyncMock(side_effect=RuntimeError("llm timeout"))

    async def execute_graph(*, queue, result_holder, **kwargs):
        async for item in _drain_queue(queue):
            yield item
        await orchestrator._update_state(request.session_id, STATE_GENERATING, "Fallback direct response")
        yield agent_service_pb2.ChatResponse(delta="我先用直接模式给你一个稳定版本。")
        result_holder["final_state"] = WorkflowState()

    async def build_final_response(*, route_decision, session_id, **kwargs):
        captured_modes.append(route_decision.execution_mode)
        return (
            agent_service_pb2.ChatResponse(
                session_id=session_id,
                full_text="我先用直接模式给你一个稳定版本。",
                finish_reason=agent_service_pb2.STOP,
            ),
            {"message": "我先用直接模式给你一个稳定版本。"},
        )

    orchestrator._execute_graph = execute_graph
    orchestrator._build_final_response = AsyncMock(side_effect=build_final_response)

    responses = await _collect(orchestrator, request)
    final_state = await orchestrator.state_manager.load_state(request.session_id)

    assert captured_modes == ["direct"]
    assert any("规划失败，使用直接模式" in response.delta for response in responses if response.HasField("delta"))
    orchestrator.langgraph_breaker.on_failure.assert_awaited_once()
    assert [state for state, _ in state_updates] == [STATE_INIT, STATE_GENERATING, STATE_DONE]
    assert responses[-1].finish_reason == agent_service_pb2.STOP
    assert responses[-1].full_text == "我先用直接模式给你一个稳定版本。"
    assert final_state is not None
    assert final_state.state == STATE_DONE
