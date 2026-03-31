from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.core.event_types import (
    TOOL_EXECUTION_COMPLETED,
    TOOL_EXECUTION_STARTED,
    TOOL_EXECUTION_TIMED_OUT,
)
from app.orchestration.executor import ToolExecutor
from app.tools.base import ToolResult


class _Args(BaseModel):
    query: str


class _SuccessfulTool:
    parameters_schema = _Args
    category = "knowledge"
    timeout_seconds = 1.0

    async def execute(self, params, user_id, db_session, tool_call_id=None):
        return ToolResult(
            success=True,
            tool_name="search_knowledge",
            data={"query": params.query, "user_id": user_id},
        )


class _SlowTool:
    parameters_schema = _Args
    category = "knowledge"

    async def execute(self, params, user_id, db_session, tool_call_id=None):
        await asyncio.sleep(1)
        return ToolResult(success=True, tool_name="search_knowledge", data={"query": params.query})


@pytest.mark.asyncio
async def test_execute_tool_call_publishes_started_and_completed(monkeypatch):
    executor = ToolExecutor()
    publish = AsyncMock()

    monkeypatch.setattr("app.orchestration.executor.tool_registry.get_tool", lambda _: _SuccessfulTool())
    monkeypatch.setattr("app.orchestration.executor.event_bus.publish", publish)
    monkeypatch.setattr(executor, "_record_tool_execution", AsyncMock())
    monkeypatch.setattr(executor, "_commit_if_owned", AsyncMock())

    result = await executor.execute_tool_call(
        tool_name="search_knowledge",
        arguments={"query": "sparkle"},
        user_id="user-1",
        db_session=SimpleNamespace(),
        tool_call_id="call-1",
    )

    assert result.success is True
    assert result.tool_call_id == "call-1"
    assert publish.await_args_list[0].args[0] == TOOL_EXECUTION_STARTED
    assert publish.await_args_list[1].args[0] == TOOL_EXECUTION_COMPLETED
    assert publish.await_args_list[1].args[1]["tool_call_id"] == "call-1"


@pytest.mark.asyncio
async def test_execute_tool_call_timeout_returns_failure_and_event(monkeypatch):
    executor = ToolExecutor()
    publish = AsyncMock()

    monkeypatch.setattr("app.orchestration.executor.tool_registry.get_tool", lambda _: _SlowTool())
    monkeypatch.setattr("app.orchestration.executor.event_bus.publish", publish)
    monkeypatch.setattr("app.orchestration.executor.settings", SimpleNamespace(TOOL_EXECUTION_TIMEOUT_SECONDS=0.01))
    monkeypatch.setattr(executor, "_record_tool_execution", AsyncMock())
    monkeypatch.setattr(executor, "_commit_if_owned", AsyncMock())
    monkeypatch.setattr(executor, "_safe_rollback", AsyncMock())
    monkeypatch.setattr(executor, "_maybe_execute_compensation", AsyncMock())

    result = await executor.execute_tool_call(
        tool_name="search_knowledge",
        arguments={"query": "slow"},
        user_id="user-1",
        db_session=SimpleNamespace(),
        tool_call_id="call-timeout",
    )

    assert result.success is False
    assert result.error_type == "TimeoutError"
    assert "超时" in (result.error_message or "")
    assert publish.await_args_list[0].args[0] == TOOL_EXECUTION_STARTED
    assert publish.await_args_list[1].args[0] == TOOL_EXECUTION_TIMED_OUT
    assert publish.await_args_list[1].args[1]["tool_call_id"] == "call-timeout"
