from uuid import uuid4

import pytest

from app.orchestration.chat_modes import CHAT_MODE_ERROR_DIAGNOSIS
from app.orchestration.executor import PlanExecutionResult
from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.services.plan_execution_validator import ExecutionValidationResult


class _Planner:
    async def plan(self, **kwargs):
        # Planner proposes record_error, adapter should gate it when no confirmation is present.
        return ExecutablePlan(tool_calls=[ToolCallSpec(id="s1", name="record_error", params={"question": "q"})])


class _Executor:
    async def execute_plan(self, plan, user_id, db_session):
        return PlanExecutionResult(plan_id=plan.plan_id, step_results=[], tool_results=[])


class _LLM:
    async def stream_chat(self, messages, model=None, temperature=0.6):
        yield "fallback"


@pytest.mark.asyncio
async def test_error_mode_requires_confirmation_before_recording(monkeypatch):
    orchestrator = type("O", (), {})()
    orchestrator.lang_graph_planner = _Planner()
    orchestrator.tool_executor = _Executor()
    orchestrator.db_session = None
    orchestrator.redis = None

    adapter = MultiAgentWorkflowAdapter(orchestrator)
    adapter.llm_service = _LLM()

    async def _validate(plan, execution_result, user_id):
        return ExecutionValidationResult(
            plan_id=plan.plan_id,
            validation_status="passed",
            quality_score=1.0,
            criteria_results={"all_passed": True, "checks": {}},
            tool_summary={"total": 0, "successful": 0, "failed": 0},
            issues=[],
            step_validations=[],
            aborted=False,
        )

    monkeypatch.setattr(adapter, "_validate_plan", _validate)

    responses = []
    async for resp in adapter.execute_mode_workflow(
        chat_mode=CHAT_MODE_ERROR_DIAGNOSIS,
        message="我这道题又错了",
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        context_data={"conversation_context": {"messages": []}},
        stream_callback=lambda x: None,
    ):
        responses.append(resp)

    # Because record_error is gated out, workflow falls back to LLM-only synthesis.
    assert any(r.delta == "fallback" for r in responses)
    assert responses[-1].finish_reason == 1  # STOP
