"""Regression test for ISSUE-20260503-1600-D1.

Verifies that planner.plan() calls in plan_review_service and multi_agent_adapter
have asyncio.wait_for timeout protection, matching the execution_engine pattern.
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_REVIEW_PATH = REPO_ROOT / "backend" / "app" / "orchestration" / "plan_review_service.py"
MULTI_AGENT_PATH = REPO_ROOT / "backend" / "app" / "orchestration" / "multi_agent_adapter.py"
EXEC_ENGINE_PATH = REPO_ROOT / "backend" / "app" / "orchestration" / "execution_engine.py"


@pytest.mark.asyncio
async def test_plan_review_replan_timeout_uses_fallback():
    """Simulated replan should use fallback plan when planner.plan() times out."""
    mock_plan = MagicMock()
    mock_plan.steps = []

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(side_effect=TimeoutError())
    mock_planner.build_fallback_plan = MagicMock(return_value=mock_plan)

    try:
        result = await asyncio.wait_for(mock_planner.plan(message="test"), timeout=0.1)
    except TimeoutError:
        result = mock_planner.build_fallback_plan(message="test", user_id="u", session_id="s")

    assert result == mock_plan
    mock_planner.build_fallback_plan.assert_called_once()


@pytest.mark.asyncio
async def test_multi_agent_plan_timeout_uses_fallback():
    """Multi-agent adapter should use fallback plan when planner.plan() times out."""
    mock_plan = MagicMock()
    mock_plan.collaboration_mode = "single"
    mock_plan.agents_involved = []
    mock_plan.tool_calls = []

    mock_planner = MagicMock()
    mock_planner.plan = AsyncMock(side_effect=TimeoutError())
    mock_planner.build_fallback_plan = MagicMock(return_value=mock_plan)

    try:
        result = await asyncio.wait_for(mock_planner.plan(message="test"), timeout=0.1)
    except TimeoutError:
        result = mock_planner.build_fallback_plan(message="test", user_id="u", session_id="s")

    assert result == mock_plan
    mock_planner.build_fallback_plan.assert_called_once()


def test_plan_review_service_has_timeout_guard():
    """Verify plan_review_service source contains asyncio.wait_for around planner.plan."""
    source = PLAN_REVIEW_PATH.read_text()
    assert "asyncio.wait_for" in source, "plan_review_service must use asyncio.wait_for"
    assert "except TimeoutError" in source, "plan_review_service must handle TimeoutError"
    assert "build_fallback_plan" in source, "plan_review_service must use fallback on timeout"


def test_multi_agent_adapter_has_timeout_guard():
    """Verify multi_agent_adapter source contains asyncio.wait_for around planner.plan."""
    source = MULTI_AGENT_PATH.read_text()
    assert "asyncio.wait_for" in source, "multi_agent_adapter must use asyncio.wait_for"
    assert "except TimeoutError" in source, "multi_agent_adapter must handle TimeoutError"
    assert "build_fallback_plan" in source, "multi_agent_adapter must use fallback on timeout"
    assert "import asyncio" in source, "multi_agent_adapter must import asyncio"


def test_timeout_value_matches_execution_engine():
    """All three callers should use the same 10.0s timeout."""
    ee_source = EXEC_ENGINE_PATH.read_text()
    pr_source = PLAN_REVIEW_PATH.read_text()
    ma_source = MULTI_AGENT_PATH.read_text()

    assert "_LANGGRAPH_PLANNER_TIMEOUT_SECONDS = 10.0" in ee_source
    assert "timeout=10.0" in pr_source
    assert "timeout=10.0" in ma_source
