from __future__ import annotations

import pytest

from app.orchestration.executor import ToolExecutor
from app.orchestration.schemas import ExecutablePlan, StepCriteria, ToolCallSpec
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_execute_plan_emits_observer_events(monkeypatch):
    executor = ToolExecutor()
    emitted: list[dict] = []

    async def fake_execute_tool_call(**kwargs):
        return ToolResult(
            success=True,
            tool_name=kwargs["tool_name"],
            data={"ok": True},
        )

    async def observer(event: dict):
        emitted.append(event)

    monkeypatch.setattr(executor, "execute_tool_call", fake_execute_tool_call)

    t1 = ToolCallSpec(id="step-1", name="create_plan", params={})
    t2 = ToolCallSpec(id="step-2", name="create_task", params={}, depends_on=["step-1"])
    plan = ExecutablePlan(
        plan_id="plan-1",
        tool_calls=[t1, t2],
        execution_order=[["step-1"], ["step-2"]],
        total_steps=2,
    )

    result = await executor.execute_plan(
        plan=plan,
        user_id="u1",
        db_session=None,
        execution_observer=observer,
    )

    assert result.aborted is False
    assert [e["event"] for e in emitted][:2] == ["layer_start", "step_completed"]
    assert emitted[-1]["event"] == "execution_end"
    assert emitted[-1]["steps_total"] == 2


@pytest.mark.asyncio
async def test_execute_plan_emits_abort_events(monkeypatch):
    executor = ToolExecutor()
    emitted: list[dict] = []

    async def fake_execute_tool_call(**kwargs):
        if kwargs["tool_name"] == "create_plan":
            return ToolResult(
                success=False,
                tool_name="create_plan",
                error_message="boom",
            )
        return ToolResult(success=True, tool_name=kwargs["tool_name"], data={"ok": True})

    monkeypatch.setattr(executor, "execute_tool_call", fake_execute_tool_call)

    plan = ExecutablePlan(
        plan_id="plan-2",
        tool_calls=[
            ToolCallSpec(
                id="step-1",
                name="create_plan",
                params={},
                success_criteria=StepCriteria(required=True),
            ),
            ToolCallSpec(
                id="step-2",
                name="create_task",
                params={},
                depends_on=["step-1"],
            ),
        ],
        execution_order=[["step-1"], ["step-2"]],
        total_steps=2,
    )

    await executor.execute_plan(
        plan=plan,
        user_id="u1",
        db_session=None,
        execution_observer=lambda event: emitted.append(event),
    )

    event_types = [e["event"] for e in emitted]
    assert "execution_aborted" in event_types
    assert emitted[-1]["event"] == "execution_end"
    assert emitted[-1]["aborted"] is True
