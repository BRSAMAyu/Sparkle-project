from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents import standard_workflow
from app.orchestration.executor import PlanExecutionResult, StepResult
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.orchestration.statechart_engine import WorkflowState
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_tool_execution_node_executes_non_langgraph_source_plan(monkeypatch):
    executed: dict[str, str] = {}

    async def fake_execute_plan(self, plan, user_id, db_session, progress_callback=None, execution_observer=None):
        executed["source"] = plan.source
        return PlanExecutionResult(
            plan_id=plan.plan_id,
            step_results=[
                StepResult(
                    step_id="create-plan-step",
                    tool_name="create_plan",
                    tool_result=ToolResult(
                        success=True,
                        tool_name="create_plan",
                        data={"plan_id": "real-plan-id"},
                        widget_type="plan_card",
                    ),
                )
            ],
            tool_results=[
                ToolResult(
                    success=True,
                    tool_name="create_plan",
                    data={"plan_id": "real-plan-id"},
                    widget_type="plan_card",
                )
            ],
            execution_layers_completed=1,
            total_layers=1,
        )

    async def fake_write_feedback(**kwargs):
        return None

    monkeypatch.setattr(standard_workflow.ToolExecutor, "execute_plan", fake_execute_plan)
    monkeypatch.setattr(standard_workflow, "_write_feedback", fake_write_feedback)

    state = WorkflowState(
        context_data={
            "user_id": "user-1",
            "session_id": "session-1",
            "db_session": None,
            "redis_client": None,
            "executable_plan": ExecutablePlan(
                plan_id="fallback-plan-id",
                source="fast_path",
                tool_calls=[ToolCallSpec(id="create-plan-step", name="create_plan", params={})],
                execution_order=[["create-plan-step"]],
                total_steps=1,
            ),
            "snapshot": SimpleNamespace(snapshot_id="snapshot-1"),
        }
    )

    new_state = await standard_workflow.tool_execution_node(state)

    assert executed["source"] == "fast_path"
    assert new_state.context_data["plan_execution_result"].plan_id == "fallback-plan-id"
    assert new_state.context_data["executable_plan"] is None
    assert new_state.next_step == "generation"
    assert any(msg.get("role") == "tool" and msg.get("name") == "create_plan" for msg in new_state.messages)


@pytest.mark.asyncio
async def test_generation_node_short_circuits_to_tool_execution_when_plan_exists():
    state = WorkflowState(
        messages=[{"role": "user", "content": "帮我生成学习计划"}],
        context_data={
            "session_id": "session-2",
            "executable_plan": ExecutablePlan(
                plan_id="ready-plan-id",
                source="langgraph",
                tool_calls=[ToolCallSpec(id="step-1", name="create_plan", params={})],
                execution_order=[["step-1"]],
                total_steps=1,
            ),
        },
    )

    new_state = await standard_workflow.generation_node(state)

    assert new_state.next_step == "tool_execution"
    assert not any(msg.get("role") == "assistant" for msg in new_state.messages)
