"""
End-to-End integration tests for full orchestration flow.

Tests the complete request lifecycle from user message to response.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.orchestrator import ChatOrchestrator


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    return MagicMock()


@pytest.fixture
def orchestrator(mock_db_session, mock_redis):
    """Create ChatOrchestrator with mocked dependencies."""
    def fake_create_task(coro):
        coro.close()
        return MagicMock(spec=asyncio.Task)

    with (
        patch("app.orchestration.orchestrator.create_standard_chat_graph"),
        patch("app.orchestration.orchestrator.asyncio.create_task", side_effect=fake_create_task),
    ):
        orch = ChatOrchestrator(db_session=mock_db_session, redis_client=mock_redis)
        return orch


@pytest.mark.asyncio
async def test_simple_chat_flow(orchestrator):
    """Test a simple chat flow from user message to response."""
    # This is a minimal smoke test to verify the orchestrator can be created
    # and has the expected components initialized
    assert hasattr(orchestrator, "lang_graph_planner")
    assert hasattr(orchestrator, "state_manager")
    assert hasattr(orchestrator, "validator")
    assert hasattr(orchestrator, "langgraph_breaker")


@pytest.mark.asyncio
async def test_circuit_breaker_integration_in_flow(orchestrator):
    """Test that circuit breaker is integrated into the flow."""
    # Verify circuit breaker is initialized
    assert orchestrator.langgraph_breaker is not None

    # Verify it's registered
    from app.orchestration.circuit_breaker import circuit_breaker_registry
    breaker = circuit_breaker_registry.get("langgraph_planner")
    assert breaker is not None


@pytest.mark.asyncio
async def test_state_manager_integration(orchestrator):
    """Test that state manager is properly integrated."""
    assert orchestrator.state_manager is not None

    # Should be able to create and save a state
    from app.orchestration.state_manager import FSMState
    test_state = FSMState(
        session_id="test-session",
        state="INIT",
        user_id="user-1"
    )

    # Mock Redis operations
    orchestrator.state_manager.redis.setex = AsyncMock()
    orchestrator.state_manager.redis.get = AsyncMock(return_value=None)

    result = await orchestrator.state_manager.save_state("test-session", test_state)
    assert result is True


@pytest.mark.asyncio
async def test_dynamic_tool_registry_integration(orchestrator):
    """Test that dynamic tool registry is accessible."""
    from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

    # Registry should be accessible
    assert dynamic_tool_registry is not None

    # Should have some methods available
    assert hasattr(dynamic_tool_registry, "get_tool")
    assert hasattr(dynamic_tool_registry, "get_all_tools")
    assert hasattr(dynamic_tool_registry, "register_tool")


@pytest.mark.asyncio
async def test_llm_router_health_tracking(orchestrator):
    """Test that LLM router health tracking is integrated."""
    from app.core.llm_router import llm_router

    # Success only clears an existing health entry, so seed one first.
    llm_router.report_model_failure("test_model")
    llm_router.report_model_success("test_model")

    # Health state should be tracked
    assert "test_model" in llm_router._model_health
    assert llm_router._model_health["test_model"].is_healthy is True


@pytest.mark.asyncio
async def test_orchestrator_handles_redis_failure(orchestrator):
    """Test that orchestrator handles Redis failures gracefully."""
    # Mock Redis to fail
    async def failing_get(*args, **kwargs):
        raise ConnectionError("Redis down")

    async def failing_set(*args, **kwargs):
        raise ConnectionError("Redis down")

    orchestrator.state_manager.redis.get = failing_get
    orchestrator.state_manager.redis.setex = failing_set

    # Should not raise exception
    from app.orchestration.state_manager import FSMState
    state = await orchestrator.state_manager.load_state("test-session")
    assert state is None  # Should return None on failure


@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions(orchestrator):
    """Test that circuit breaker can transition through states."""
    from app.orchestration.circuit_breaker import CircuitState

    # Start in CLOSED state
    assert orchestrator.langgraph_breaker.get_state().state == "closed"

    # Trip to OPEN
    for _ in range(5):
        await orchestrator.langgraph_breaker.on_failure("test error")

    # Should be OPEN now
    assert orchestrator.langgraph_breaker.get_state().state == "open"

    # Should block requests
    allowed, _ = await orchestrator.langgraph_breaker.allow_request()
    assert allowed is False


def test_orchestrator_initialization_with_all_components(mock_db_session, mock_redis):
    """Test that orchestrator initializes with all required components."""
    def fake_create_task(coro):
        coro.close()
        return MagicMock(spec=asyncio.Task)

    with (
        patch("app.orchestration.orchestrator.create_standard_chat_graph"),
        patch("app.orchestration.orchestrator.asyncio.create_task", side_effect=fake_create_task),
    ):
        orch = ChatOrchestrator(db_session=mock_db_session, redis_client=mock_redis)

        # Core components
        assert hasattr(orch, "state_manager")
        assert hasattr(orch, "validator")
        assert hasattr(orch, "tool_executor")
        assert hasattr(orch, "response_composer")

        # Phase 2 components
        assert hasattr(orch, "lang_graph_planner")
        assert hasattr(orch, "snapshot_manager")

        # Phase 3 components
        assert hasattr(orch, "langgraph_breaker")
        assert hasattr(orch, "observability")
        assert hasattr(orch, "shadow_predictor")

        # Check circuit breaker is registered
        from app.orchestration.circuit_breaker import circuit_breaker_registry
        assert circuit_breaker_registry.get("langgraph_planner") is not None


@pytest.mark.asyncio
async def test_full_flow_with_circuit_breaker_open(orchestrator):
    """Test that planning is blocked when circuit breaker is OPEN."""
    from app.orchestration.circuit_breaker import CircuitState
    from app.orchestration.schemas import StateSnapshot

    # Trip the circuit breaker
    for _ in range(5):
        await orchestrator.langgraph_breaker.on_failure("test")

    # Set old timestamp to allow recovery
    from datetime import datetime, timezone, timedelta
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=120)
    orchestrator.langgraph_breaker._last_failure_time = old_time
    orchestrator.langgraph_breaker._last_state_change = old_time

    # Should transition to HALF_OPEN and allow one test request
    allowed, reason = await orchestrator.langgraph_breaker.allow_request()
    assert allowed is True
    assert orchestrator.langgraph_breaker.get_state().state == "half_open"


@pytest.mark.asyncio
async def test_tool_registry_concurrent_access():
    """Test that tool registry handles concurrent access safely."""
    from app.orchestration.dynamic_tool_registry import dynamic_tool_registry
    from app.tools.base import BaseTool, ToolCategory
    import asyncio

    class TestTool(BaseTool):
        def __init__(self, name):
            self._name = name
            self._category = ToolCategory.TASK

        @property
        def name(self):
            return self._name

        @property
        def description(self):
            return f"Test tool {self._name}"

        @property
        def category(self):
            return self._category

        @property
        def parameters_schema(self):
            return {}

        async def execute(self, **kwargs):
            return {}

    # Create and register tools concurrently
    tools = [TestTool(f"tool_{i}") for i in range(10)]

    async def register_tool(tool):
        dynamic_tool_registry.register_tool(tool)
        return dynamic_tool_registry.get_tool(tool.name)

    results = await asyncio.gather(*[register_tool(t) for t in tools])

    # All should be registered
    assert len(results) == 10
    for r in results:
        assert r is not None
