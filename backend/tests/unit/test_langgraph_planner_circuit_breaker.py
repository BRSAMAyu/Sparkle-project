"""
Circuit Breaker Integration Tests for LangGraphPlanner

Tests that LangGraphPlanner properly checks circuit breaker state
before invoking the planning graph.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.graph.state import SparkleState
from app.orchestration.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from app.orchestration.lang_graph_planner import LangGraphPlanner
from app.orchestration.schemas import StateSnapshot


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return MagicMock()


@pytest.fixture
def langgraph_planner_with_breaker(mock_redis):
    """Create LangGraphPlanner with circuit breaker."""
    planner = LangGraphPlanner(redis_client=mock_redis)
    # Inject circuit breaker
    planner.circuit_breaker = CircuitBreaker(
        name="langgraph_planner",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_ms=1000,
        ),
        redis_client=mock_redis,
    )
    return planner


@pytest.mark.asyncio
async def test_plan_returns_fallback_when_circuit_breaker_open(
    langgraph_planner_with_breaker, mock_redis
):
    """Test that plan() returns fallback plan when circuit breaker is OPEN."""
    planner = langgraph_planner_with_breaker
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})

    # Force circuit breaker to OPEN state
    planner.circuit_breaker._state = CircuitState.OPEN
    planner.circuit_breaker._last_failure_time = datetime.now(timezone.utc).replace(
        tzinfo=None
    )
    planner.circuit_breaker._last_state_change = datetime.now(timezone.utc).replace(
        tzinfo=None
    )

    with patch.object(planner.graph, "ainvoke", AsyncMock()) as mock_ainvoke:
        plan = await planner.plan(
            message="test message",
            snapshot=snapshot,
            user_id="user-1",
            session_id="session-1",
        )

    # Verify fallback plan is returned
    mock_ainvoke.assert_not_called()
    assert plan is not None
    assert "circuit" in plan.rationale.lower() or "breaker" in plan.rationale.lower()
    assert "fallback" in plan.rationale.lower()


@pytest.mark.asyncio
async def test_plan_succeeds_when_circuit_breaker_closed(
    langgraph_planner_with_breaker, mock_redis
):
    """Test that plan() proceeds normally when circuit breaker is CLOSED."""
    planner = langgraph_planner_with_breaker
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})

    # Ensure circuit breaker is CLOSED
    planner.circuit_breaker._state = CircuitState.CLOSED

    # Mock the graph to return a valid state
    mock_state: SparkleState = {
        "messages": [],
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

    with patch.object(
        planner.graph, "ainvoke", AsyncMock(return_value=mock_state)
    ):
        plan = await planner.plan(
            message="test message",
            snapshot=snapshot,
            user_id="user-1",
            session_id="session-1",
        )

    # Should succeed with a plan (possibly synthesized)
    assert plan is not None
    assert plan.plan_id is not None


@pytest.mark.asyncio
async def test_plan_transitions_to_half_open_after_timeout(
    langgraph_planner_with_breaker, mock_redis
):
    """Test that circuit breaker transitions to HALF_OPEN after timeout."""
    planner = langgraph_planner_with_breaker
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})

    # Set circuit breaker to OPEN with old timestamp
    planner.circuit_breaker._state = CircuitState.OPEN
    planner.circuit_breaker._last_failure_time = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(seconds=2)
    planner.circuit_breaker._last_state_change = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(seconds=2)

    # Mock the graph to return a valid state
    mock_state: SparkleState = {
        "messages": [],
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

    with patch.object(
        planner.graph, "ainvoke", AsyncMock(return_value=mock_state)
    ):
        plan = await planner.plan(
            message="test message",
            snapshot=snapshot,
            user_id="user-1",
            session_id="session-1",
        )

    # Should succeed and transition to HALF_OPEN
    assert planner.circuit_breaker.get_state().state == "half_open"
    assert plan is not None


@pytest.mark.asyncio
async def test_plan_records_success_on_successful_planning(
    langgraph_planner_with_breaker, mock_redis
):
    """Test that successful planning is recorded in circuit breaker."""
    planner = langgraph_planner_with_breaker
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})

    # Set to HALF_OPEN state
    planner.circuit_breaker._state = CircuitState.HALF_OPEN
    planner.circuit_breaker._success_count = 1

    # Mock the graph to return a valid state
    mock_state: SparkleState = {
        "messages": [],
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

    with patch.object(
        planner.graph, "ainvoke", AsyncMock(return_value=mock_state)
    ):
        plan = await planner.plan(
            message="test message",
            snapshot=snapshot,
            user_id="user-1",
            session_id="session-1",
        )

    # After 2 successes in HALF_OPEN, should recover to CLOSED
    assert planner.circuit_breaker.get_state().state == "closed"
    assert plan is not None


@pytest.mark.asyncio
async def test_plan_records_failure_on_planning_error(
    langgraph_planner_with_breaker, mock_redis
):
    """Test that planning failures are recorded in circuit breaker."""
    planner = langgraph_planner_with_breaker
    snapshot = StateSnapshot(snapshot_id="snap-1", context_versions={"tasks": "v1"})

    # Start with CLOSED state
    planner.circuit_breaker._state = CircuitState.CLOSED
    planner.circuit_breaker._failure_count = 2

    # Mock the graph to raise an error
    with patch.object(
        planner.graph, "ainvoke", AsyncMock(side_effect=RuntimeError("LLM error"))
    ):
        plan = await planner.plan(
            message="test message",
            snapshot=snapshot,
            user_id="user-1",
            session_id="session-1",
        )

    # Should trip to OPEN after 3 failures
    # Note: The planner catches exceptions and returns fallback plan,
    # so we need to verify the failure was recorded
    assert planner.circuit_breaker._failure_count >= 3
    # The fallback plan should still be returned
    assert plan is not None
    assert "fallback" in plan.rationale.lower()
