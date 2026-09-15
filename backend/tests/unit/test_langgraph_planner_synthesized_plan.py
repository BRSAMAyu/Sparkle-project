from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from langchain_core.messages import HumanMessage

from app.agents.graph.state import SparkleState
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
from app.orchestration.lang_graph_planner import LangGraphPlanner
from app.orchestration.schemas import StateSnapshot


def test_circuit_breaker_open_state_can_recover_from_persisted_timestamp():
    breaker = CircuitBreaker(
        name="langgraph_planner",
        config=CircuitBreakerConfig(timeout_ms=1000),
    )
    breaker._state = CircuitState.OPEN
    breaker._last_failure_time = None
    breaker._last_state_change = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)

    allow, reason = __import__("asyncio").run(breaker.allow_request())

    assert allow is True
    assert reason == "circuit_half_open_attempting"
    assert breaker.get_state().state == "half_open"


def test_convert_to_plan_synthesizes_minimal_tool_chain_when_langgraph_has_no_tool_calls():
    planner = LangGraphPlanner()
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})
    state: SparkleState = {
        "messages": [HumanMessage(content="我想在4周内掌握 Python 数据分析基础，并完成一个可视化项目")],
        "user_id": "user-1",
        "session_id": "session-1",
        "user_profile": None,
        "current_plan": None,
        "planning_status": None,
        "next_step": None,
        "intent_data": None,
        "active_agent": "study_planner",
        "collaboration_mode": "single",
        "collaboration_agents": ["study_planner"],
        "collaboration_order": [],
        "collaboration_index": 0,
        "mode_name": None,
        "mode_constraints": None,
        "synthesis_policy": None,
        "review_feedback": None,
        "require_approval": False,
        "approval_context": None,
        "approval_result": None,
    }

    plan = planner._convert_to_plan(state, snapshot, "user-1", "session-1")

    assert len(plan.tool_calls) == 2
    assert plan.tool_calls[0].name == "create_plan"
    assert plan.tool_calls[1].name == "generate_tasks_for_plan"
    assert plan.tool_calls[1].params["plan_id"] == "__pending__"
    assert plan.tool_calls[1].depends_on == [plan.tool_calls[0].id]


def test_planner_exception_returns_synthesized_fallback_plan():
    planner = LangGraphPlanner()
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})

    with patch.object(planner.graph, "ainvoke", AsyncMock(side_effect=RuntimeError("rate limited"))):
        plan = __import__("asyncio").run(
            planner.plan(
                message="我想学习 Python 数据分析，并生成任务",
                snapshot=snapshot,
                user_id="user-1",
                session_id="session-1",
            )
        )

    assert len(plan.tool_calls) == 2
    assert plan.tool_calls[0].name == "create_plan"
    assert plan.tool_calls[1].name == "generate_tasks_for_plan"
    assert "synthesized fallback" in plan.rationale
