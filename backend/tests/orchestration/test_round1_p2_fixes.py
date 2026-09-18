"""Round-1 review wave P2/P3 regression tests (RB-03..RB-16).

Each test targets one finding from
docs/competition/2026-tmall-hackathon/系统审查/round1/01-engine-orchestration.md.
"""

from __future__ import annotations

import asyncio
import importlib
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.schemas import RouteDecision
from app.orchestration.state_manager import FSMState, SessionStateManager
from app.orchestration.statechart_engine import WorkflowState, _merge_context_data
from app.orchestration.token_tracker import TokenTracker
from tests.orchestration.test_orchestrator_process_stream_integration import (
    _install_import_stubs,
    _make_request,
    _MemoryRedis,
    orchestrator_factory,  # noqa: F401 — pytest fixture re-export
)

# ---------------------------------------------------------------------------
# RB-03: usage events must accumulate across multiple generation calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rb03_execute_graph_accumulates_usage_events(orchestrator_factory, monkeypatch):  # noqa: F811
    _install_import_stubs()
    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")

    class _DirectSpawn:
        @staticmethod
        async def spawn(coro, **kwargs):
            return asyncio.create_task(coro)

    monkeypatch.setattr(execution_engine_module, "task_manager", _DirectSpawn)

    class _InstantGraph:
        async def invoke(self, state, **kwargs):
            return state

    orchestrator, _, _ = orchestrator_factory()
    orchestrator.graph = _InstantGraph()

    queue: asyncio.Queue = asyncio.Queue()
    await queue.put(
        agent_service_pb2.ChatResponse(
            usage=agent_service_pb2.Usage(prompt_tokens=100, completion_tokens=20, total_tokens=120)
        )
    )
    await queue.put(
        agent_service_pb2.ChatResponse(
            usage=agent_service_pb2.Usage(prompt_tokens=50, completion_tokens=10, total_tokens=60)
        )
    )

    result_holder: dict[str, Any] = {}
    async for _ in orchestrator._execute_graph(
        state=WorkflowState(), user_id="user-rb03", queue=queue, result_holder=result_holder
    ):
        pass

    assert result_holder["total_prompt_tokens"] == 150, "usage events must accumulate, not overwrite"
    assert result_holder["total_completion_tokens"] == 30


# ---------------------------------------------------------------------------
# RB-04: failure-rate breaker needs a minimum sample size
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rb04_single_failure_does_not_trip_rate_breaker():
    breaker = CircuitBreaker(
        "rb04-single",
        CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            timeout_ms=1000,
            failure_rate_threshold=0.5,
            window_size=10,
        ),
    )

    await breaker.on_failure("transient")

    assert breaker._state == CircuitState.CLOSED, "first failure in an empty window must not trip the breaker"


@pytest.mark.asyncio
async def test_rb04_rate_breaker_trips_after_min_samples():
    breaker = CircuitBreaker(
        "rb04-rate",
        CircuitBreakerConfig(
            failure_threshold=50,  # consecutive-failure path must stay out of the way
            success_threshold=2,
            timeout_ms=1000,
            failure_rate_threshold=0.5,
            window_size=4,  # min_samples = max(3, 4 // 2) = 3
        ),
    )

    for i in range(2):
        await breaker.on_failure(f"boom-{i}")
    assert breaker._state == CircuitState.CLOSED, "2 samples (100% rate) are below min_samples=3"

    await breaker.on_failure("boom-2")
    assert breaker._state == CircuitState.OPEN, "3 samples with 100% failure rate must trip via failure rate"


@pytest.mark.asyncio
async def test_rb04_rate_breaker_healthy_window_stays_closed():
    breaker = CircuitBreaker(
        "rb04-healthy",
        CircuitBreakerConfig(
            failure_threshold=50,
            success_threshold=2,
            timeout_ms=1000,
            failure_rate_threshold=0.5,
            window_size=10,
        ),
    )

    for _ in range(8):
        await breaker.on_success()
    await breaker.on_failure("boom")
    # 8/9 success = 11% failure rate with min_samples satisfied

    assert breaker._state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# RB-05: get_top_users must tolerate str keys from decode_responses clients
# ---------------------------------------------------------------------------


class _StrKeyRedis:
    """Redis stub mimicking decode_responses=True: scan_iter yields str keys."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {
            "user:daily_tokens:user-a:2026-09-17": "120",
            "user:daily_tokens:user-b:2026-09-17": "30",
        }

    async def scan_iter(self, match: str | None = None):
        for key in list(self.values):
            yield key

    async def get(self, key: str):
        return self.values.get(key)


@pytest.mark.asyncio
async def test_rb05_get_top_users_handles_str_keys():
    tracker = TokenTracker(_StrKeyRedis())

    top_users = await tracker.get_top_users(days=7, limit=10)

    assert top_users == [
        {"user_id": "user-a", "total_tokens": 120},
        {"user_id": "user-b", "total_tokens": 30},
    ]


# ---------------------------------------------------------------------------
# RB-06: _persist_context_plan must flush, not commit the shared session
# ---------------------------------------------------------------------------


class _SessionStateHost:
    """Minimal host exposing the mixin method under test without a full orchestrator."""

    def __init__(self) -> None:
        from app.orchestration.session_state_mixin import SessionStateMixin

        self.persist = SessionStateMixin._persist_context_plan.__get__(self, _SessionStateHost)


@pytest.mark.asyncio
async def test_rb06_persist_context_plan_uses_flush_not_commit():
    host = _SessionStateHost()
    state = WorkflowState()
    state.context_data["context_plan"] = {"mode": "focused"}

    active_db = MagicMock()
    active_db.flush = AsyncMock()
    active_db.commit = AsyncMock()

    await host.persist(user_id=str(uuid.uuid4()), state=state, active_db=active_db)

    active_db.add.assert_called_once()
    active_db.flush.assert_awaited_once()
    active_db.commit.assert_not_awaited(), "RB-06: shared session must not be committed mid-turn"


# ---------------------------------------------------------------------------
# RB-07: empty sync summary falls back to importance compression
# ---------------------------------------------------------------------------


class _PrunerRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value
        return True

    def _decode(self, value):
        return value


@pytest.mark.asyncio
async def test_rb07_empty_summary_falls_back_to_compression(monkeypatch):
    pruner = ContextPruner(
        redis_client=_PrunerRedis(),
        max_history_messages=5,
        summary_threshold=10,
        summary_cache_ttl=3600,
    )

    async def _empty_summary(messages):
        return ""

    monkeypatch.setattr(pruner, "_summarize_sync", _empty_summary)

    history = [{"role": "user", "content": f"历史消息 {i}，包含需要保留的上下文信息"} for i in range(12)]

    result = await pruner._get_summarized_history(
        session_id="sess-rb07",
        history=history,
        user_id="user-rb07",
    )

    assert result["summary"] is None
    total_kept = len(result["messages"])
    assert total_kept >= len(history) * 0.5, (
        "empty summary must not silently drop all middle history; " f"kept {total_kept} of {len(history)}"
    )


@pytest.mark.asyncio
async def test_rb07_no_earlier_messages_keeps_full_history(monkeypatch):
    pruner = ContextPruner(
        redis_client=_PrunerRedis(),
        max_history_messages=50,
        summary_threshold=100,
        summary_cache_ttl=3600,
    )
    history = [{"role": "user", "content": f"消息 {i}"} for i in range(4)]

    result = await pruner._get_summarized_history(
        session_id="sess-rb07b",
        history=history,
        user_id="user-rb07b",
    )

    assert len(result["messages"]) == 4


# ---------------------------------------------------------------------------
# RB-08 / RB-13: planning error sanitization + shadow predictor task tracking
# ---------------------------------------------------------------------------


def _plan_and_validate_kwargs(stream_callback, state):
    return {
        "user_message": "帮我做复习计划",
        "user_id": str(uuid.uuid4()),
        "session_id": "sess-rb08",
        "active_db": None,
        "plan_id": None,
        "conversation_context": None,
        "plan_context": None,
        "stream_callback": stream_callback,
        "state": state,
        "user_context_payload": {},  # production always passes a dict here by this stage
        "orchestration_trace": None,
    }


@pytest.mark.asyncio
async def test_rb08_planning_failure_streams_sanitized_message(orchestrator_factory, monkeypatch):  # noqa: F811
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_failure = AsyncMock(return_value=None)
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator.lang_graph_planner.plan = AsyncMock(
        side_effect=RuntimeError("LEAK internal sql://postgres:secret@db:5432 failed")
    )

    deltas: list[str] = []

    async def stream_callback(response) -> None:
        if response.HasField("delta"):
            deltas.append(response.delta)

    route_decision = RouteDecision(execution_mode="langgraph", reason="complex", risk_level="low")
    state = WorkflowState()

    (
        returned_decision,
        executable_plan,
        snapshot,
        should_return,
    ) = await orchestrator._plan_and_validate(
        route_decision=route_decision, **_plan_and_validate_kwargs(stream_callback, state)
    )

    assert returned_decision.execution_mode == "direct", "planning failure must degrade to direct mode"
    assert should_return is False
    joined = "".join(deltas)
    assert "LEAK internal sql" not in joined, "raw exception text must not reach the client"
    assert "规划失败" in joined
    orchestrator.langgraph_breaker.on_failure.assert_awaited_once()


@pytest.mark.asyncio
async def test_rb13_shadow_predictor_task_is_tracked(orchestrator_factory, monkeypatch):  # noqa: F811
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()
    orchestrator.langgraph_breaker.allow_request = AsyncMock(return_value=(True, "closed"))
    orchestrator.langgraph_breaker.on_success = AsyncMock(return_value=None)
    orchestrator._load_recent_execution_feedback = AsyncMock(return_value=None)
    orchestrator._load_context_versions = AsyncMock(return_value={})
    orchestrator._emit_roundtable_preview = AsyncMock(return_value=None)
    orchestrator._track_task = MagicMock()
    orchestrator.shadow_predictor.predict_and_record = AsyncMock(return_value=None)
    plan_stub = SimpleNamespace(
        plan_id="plan-rb13",
        tool_calls=[],
        confidence=0.9,
        rationale="stub",
        collaboration_mode="single",
        agents_involved=[],
    )
    orchestrator.lang_graph_planner.plan = AsyncMock(return_value=plan_stub)
    orchestrator.lang_graph_planner.pop_rendered_plan_artifact = MagicMock(return_value=None)
    execution_engine_module = importlib.import_module("app.orchestration.execution_engine")
    monkeypatch.setattr(
        execution_engine_module,
        "plan_review_service",
        SimpleNamespace(
            review_plan=AsyncMock(
                return_value=SimpleNamespace(
                    decision="approved",
                    confidence=0.9,
                    alignment_score=0.9,
                    alignment_summary="stub review",
                    reasoning_summary="",
                    reasoning_details=[],
                    reasoning_source="stub",
                    user_facing_reason="",
                    review_id="review-1",
                    plan_id="plan-1",
                    quality_report={},
                    to_dict=lambda: {"decision": "approved", "confidence": 0.9},
                )
            ),
            store_review_result=AsyncMock(return_value="review-action-1"),
        ),
    )

    async def stream_callback(response) -> None:
        return None

    state = WorkflowState()
    (
        _,
        executable_plan,
        _,
        should_return,
    ) = await orchestrator._plan_and_validate(
        route_decision=RouteDecision(execution_mode="langgraph", reason="complex", risk_level="low"),
        **_plan_and_validate_kwargs(stream_callback, state),
    )

    assert should_return is False
    assert executable_plan is not None
    assert orchestrator._track_task.called, "shadow predictor task must be tracked via _track_task"


# ---------------------------------------------------------------------------
# RB-09: router must route on the last human message after tool loops
# ---------------------------------------------------------------------------


def test_rb09_router_resolves_last_human_message():
    from app.agents.graph.nodes.router import _resolve_router_user_query

    human = SimpleNamespace(type="human", content="我该先复习哪门课？")
    tool_msg = SimpleNamespace(type="tool", content='{"result": "课程列表"}')
    ai = SimpleNamespace(type="ai", content="让我查一下")

    assert _resolve_router_user_query([human]) == "我该先复习哪门课？"
    assert _resolve_router_user_query([human, ai, tool_msg]) == "我该先复习哪门课？"
    assert _resolve_router_user_query([]) == ""


# ---------------------------------------------------------------------------
# RB-10: precedence gate must use the threshold key, not the weight key
# ---------------------------------------------------------------------------


def test_rb10_high_cognitive_load_precedence_uses_threshold_key():
    from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput

    class _WeightSnapshot:
        """Simulates RoutingParameterSnapshot where "high_cognitive_load" stores the weight 5.0."""

        version = "test-snapshot"
        source = "test"

        def get(self, key, default):
            if key == "high_cognitive_load":
                return 5.0
            return default

    router = DualCoreRouter(parameter_snapshot=_WeightSnapshot())
    routing_input = DualCoreRoutingInput(
        intent="chat",
        intent_confidence=0.8,
        information_sufficient=True,
        primary_challenge_area=None,
        recent_sentiment_distribution={},
        has_active_plan=False,
        plan_health_status=None,
        recent_task_feedback_distribution={},
        cognitive_load=0.9,
    )

    decision = router.route(routing_input)

    scores = decision.routing_debug.get("precedence_scores") or {}
    assert scores.get("high_cognitive_load") == 5.0, (
        "load 0.9 >= threshold 0.55 must grant precedence even when the "
        "'high_cognitive_load' param key carries the weight value 5.0"
    )


# ---------------------------------------------------------------------------
# RB-11: capacity eviction must protect identity/runtime keys
# ---------------------------------------------------------------------------


def test_rb11_eviction_protects_session_and_runtime_keys(monkeypatch):
    monkeypatch.setattr(settings, "MAX_CONTEXT_DATA_KEYS", 10)

    target: dict[str, Any] = {
        "session_id": "sess-1",
        "user_id": "user-1",
        "request_id": "req-1",
        "db_session": object(),
        "stream_callback": object(),
    }
    filler = {f"filler_{i}": i for i in range(20)}
    _merge_context_data(target, filler)

    assert target["session_id"] == "sess-1"
    assert target["user_id"] == "user-1"
    assert target["request_id"] == "req-1"
    assert "db_session" in target
    assert "stream_callback" in target
    assert len(target) <= 10 + 5, "cap enforced for evictable keys; protected keys may exceed the cap"


def test_rb11_eviction_still_drops_unprotected_old_keys(monkeypatch):
    monkeypatch.setattr(settings, "MAX_CONTEXT_DATA_KEYS", 5)

    target: dict[str, Any] = {"session_id": "sess-1"}
    filler = {f"filler_{i}": i for i in range(12)}
    _merge_context_data(target, filler)

    assert target["session_id"] == "sess-1"
    assert "filler_0" not in target, "oldest unprotected keys must be evicted first"
    assert len(target) <= 6


# ---------------------------------------------------------------------------
# RB-12: update_state with unknown kwargs must not TypeError on fresh sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rb12_update_state_filters_unknown_kwargs():
    manager = SessionStateManager(_MemoryRedis(), db_session=None)

    ok = await manager.update_state("sess-rb12", "INIT", "创建会话", unknown_field="surprise")

    assert ok is True, "unknown kwargs must be filtered, not raise TypeError"
    restored = await manager.load_state("sess-rb12")
    assert isinstance(restored, FSMState)
    assert restored.state == "INIT"

    ok_existing = await manager.update_state("sess-rb12", "THINKING", "推进", another_unknown=1)
    assert ok_existing is True
    restored = await manager.load_state("sess-rb12")
    assert restored.state == "THINKING"


# ---------------------------------------------------------------------------
# RB-14: empty aurora plan STOP handling — proposal NOT adopted, documented here
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rb14_empty_aurora_plan_stop_is_cached_as_wait_turn(orchestrator_factory, monkeypatch):  # noqa: F811
    """The report proposed skipping `_cache_response` for empty aurora plans (RB-14).

    Not adopted: `test_process_stream_aurora_wait_turn_emits_terminal_frame_and_caches_response`
    codifies empty-response caching as intended wait-turn semantics — the idempotency
    slot must replay the "say nothing" decision on client retries. This test pins
    that contract so the trade-off stays visible.
    """
    _install_import_stubs()
    orchestrator, _, _ = orchestrator_factory()
    monkeypatch.setattr(settings, "ENABLE_AURORA_RUNTIME_V1", True)

    plan_stub = SimpleNamespace(
        surface="daily_checkin",
        surface_complete=True,
        modeling_complete=False,
        messages=[],
        wake_policy="normal",
        action="emit_message",
    )
    orchestrator.aurora_runtime_v1.plan_turn = AsyncMock(return_value=plan_stub)
    orchestrator._cache_response = AsyncMock(return_value=True)
    orchestrator._maybe_upsert_session_mood = AsyncMock(return_value=None)

    request = _make_request()
    responses = [
        response
        async for response in orchestrator._stream_aurora_runtime_v1(
            request=request,
            active_db=None,
            user_id=str(uuid.uuid4()),
            session_id="sess-rb14",
            response_id="resp-rb14",
            request_id="req-rb14",
            trace_id="trace-rb14",
            workflow_id="wf-rb14",
            prompt_version="v1",
            request_extra_context={"aurora_surface": "daily_checkin"},
            conversation_context={},
            user_context_payload={},
        )
    ]

    assert len(responses) == 1
    assert responses[0].finish_reason == agent_service_pb2.STOP
    assert responses[0].full_text == ""
    orchestrator._cache_response.assert_awaited_once(), "wait turns replay from the idempotency cache"


# ---------------------------------------------------------------------------
# RB-16: sufficiency / goal-quality short-circuits must advance the FSM to DONE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rb16_sufficiency_short_circuit_sets_done(orchestrator_factory):  # noqa: F811
    _install_import_stubs()
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request()

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._check_sufficiency = AsyncMock(return_value=(True, "sufficiency_fast_track"))
    orchestrator._check_goal_quality = AsyncMock(return_value=False)

    responses = [response async for response in orchestrator.process_stream(request)]
    assert responses, "sufficiency short-circuit should still produce stream output"

    assert any(
        next_state == "DONE" for next_state, _ in state_updates
    ), f"sufficiency short-circuit must reach DONE; got {state_updates}"


@pytest.mark.asyncio
async def test_rb16_goal_quality_short_circuit_sets_done(orchestrator_factory):  # noqa: F811
    _install_import_stubs()
    orchestrator, _, state_updates = orchestrator_factory()
    request = _make_request()

    orchestrator._route_and_classify = AsyncMock(
        return_value=(RouteDecision(execution_mode="direct", reason="simple_chat", risk_level="low"), None)
    )
    orchestrator._check_sufficiency = AsyncMock(return_value=(False, "chat"))
    orchestrator._check_goal_quality = AsyncMock(return_value=True)

    [response async for response in orchestrator.process_stream(request)]

    assert any(
        next_state == "DONE" for next_state, _ in state_updates
    ), f"goal quality short-circuit must reach DONE; got {state_updates}"
