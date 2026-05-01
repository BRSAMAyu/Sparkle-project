from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.chat_modes import CHAT_MODE_DEEP_ANALYSIS
from app.orchestration.executor import PlanExecutionResult, StepResult
from app.orchestration.mode_workflow_config import get_workflow_config
from app.orchestration.multi_agent_adapter import MultiAgentWorkflowAdapter
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.services.plan_execution_validator import ExecutionValidationResult
from app.tools.base import ToolResult


class _Planner:
    async def plan(self, **kwargs):
        cfg = get_workflow_config(CHAT_MODE_DEEP_ANALYSIS)
        return ExecutablePlan(
            tool_calls=[ToolCallSpec(id="s1", name="query_knowledge", params={"query": "x"})],
            collaboration_mode=cfg.collaboration_mode,
            collaboration_order=cfg.collaboration_order,
            agents_involved=cfg.collaboration_agents,
        )


class _Executor:
    async def execute_plan(self, plan, user_id, db_session):
        tr = ToolResult(success=True, tool_name="query_knowledge", data={"results": []})
        sr = StepResult(step_id="s1", tool_name="query_knowledge", tool_result=tr, output_data={"results": []})
        return PlanExecutionResult(plan_id=plan.plan_id, step_results=[sr], tool_results=[tr], total_layers=1, execution_layers_completed=1)


class _LLM:
    async def stream_chat(self, messages, model=None, temperature=0.5):
        yield "ok"


class _EmptyLLM:
    async def stream_chat(self, messages, model=None, temperature=0.5):
        if False:
            yield ""


class _CapturingLLM:
    def __init__(self):
        self.messages = None

    def get_current_selection(self):
        return SimpleNamespace(config=SimpleNamespace(model_name="deep-analyst-synth"))

    async def stream_chat(self, messages, model=None, temperature=0.5):
        self.messages = messages
        yield "综合结论"


@pytest.mark.asyncio
async def test_execute_mode_workflow_runs_plan_and_returns_stop(monkeypatch):
    orchestrator = type("O", (), {})()
    orchestrator.lang_graph_planner = _Planner()
    orchestrator.tool_executor = _Executor()
    orchestrator.db_session = None
    orchestrator.redis = None

    adapter = MultiAgentWorkflowAdapter(orchestrator)
    adapter.llm_service = _LLM()

    async def _validate(plan, execution_result, user_id, db_session=None):
        return ExecutionValidationResult(
            plan_id=plan.plan_id,
            validation_status="passed",
            quality_score=1.0,
            criteria_results={"all_passed": True, "checks": {}},
            tool_summary={"total": 1, "successful": 1, "failed": 0},
            issues=[],
            step_validations=[],
            aborted=False,
        )

    monkeypatch.setattr(adapter, "_validate_plan", _validate)

    responses = []
    async for resp in adapter.execute_mode_workflow(
        chat_mode=CHAT_MODE_DEEP_ANALYSIS,
        message="分析这个问题",
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        context_data={"conversation_context": {"messages": []}},
        stream_callback=lambda x: None,
    ):
        responses.append(resp)

    assert any(r.WhichOneof("content") == "status_update" for r in responses)
    assert any(r.delta == "ok" for r in responses)
    assert responses[-1].finish_reason == 1  # STOP


@pytest.mark.asyncio
async def test_execute_mode_workflow_falls_back_when_stream_empty(monkeypatch):
    orchestrator = type("O", (), {})()
    orchestrator.lang_graph_planner = _Planner()
    orchestrator.tool_executor = _Executor()
    orchestrator.db_session = None
    orchestrator.redis = None

    adapter = MultiAgentWorkflowAdapter(orchestrator)
    adapter.llm_service = _EmptyLLM()

    async def _validate(plan, execution_result, user_id, db_session=None):
        return ExecutionValidationResult(
            plan_id=plan.plan_id,
            validation_status="passed",
            quality_score=1.0,
            criteria_results={"all_passed": True, "checks": {}},
            tool_summary={"total": 1, "successful": 1, "failed": 0},
            issues=[],
            step_validations=[],
            aborted=False,
        )

    monkeypatch.setattr(adapter, "_validate_plan", _validate)

    responses = []
    async for resp in adapter.execute_mode_workflow(
        chat_mode=CHAT_MODE_DEEP_ANALYSIS,
        message="分析这个问题",
        user_id=str(uuid4()),
        session_id=str(uuid4()),
        context_data={"conversation_context": {"messages": []}},
        stream_callback=lambda x: None,
    ):
        responses.append(resp)

    deltas = [r.delta for r in responses if r.delta]
    assert any("structured summary" in d for d in deltas)
    assert responses[-1].finish_reason == 1


@pytest.mark.asyncio
async def test_stream_synthesis_response_uses_role_scoped_llm_and_context(monkeypatch):
    orchestrator = type("O", (), {})()
    adapter = MultiAgentWorkflowAdapter(orchestrator)
    capturing_llm = _CapturingLLM()
    captured_prompt_kwargs = {}

    monkeypatch.setattr(
        "app.orchestration.multi_agent_adapter.get_configured_llm_service",
        AsyncMock(return_value=capturing_llm),
    )
    monkeypatch.setattr(
        "app.orchestration.multi_agent_adapter.build_system_prompt",
        lambda **kwargs: captured_prompt_kwargs.update(kwargs) or "BASE_SYSTEM_PROMPT",
    )

    validation_result = ExecutionValidationResult(
        plan_id="plan-1",
        validation_status="passed",
        quality_score=0.92,
        criteria_results={"all_passed": True, "checks": {}},
        tool_summary={"total": 1, "successful": 1, "failed": 0},
        issues=["minor drift"],
        step_validations=[],
        aborted=False,
    )

    responses = []
    async for resp in adapter._stream_synthesis_response(
        chat_mode=CHAT_MODE_DEEP_ANALYSIS,
        user_message="帮我深度分析",
        execution_result=None,
        validation_result=validation_result,
        execution_summary="- [成功] query_knowledge: {...}",
        synthesis_template="SYNTH_TEMPLATE",
        context_data={
            "prompt_version": "v2",
            "user_context": {"preferences": {"tone": "precise"}},
            "plan_context": {"goal": "analyze"},
            "conversation_context": {
                "messages": [
                    {"role": "user", "content": "前一个问题"},
                    {"role": "assistant", "content": "前一个回答"},
                ],
                "summary": "历史摘要",
                "summary_used": True,
            },
            "dual_core_prompt_instruction": "先共情，再给步骤。",
        },
    ):
        responses.append(resp)

    assert responses[-1].delta == "综合结论"
    assert capturing_llm.messages is not None
    assert capturing_llm.messages[0]["role"] == "system"
    assert "BASE_SYSTEM_PROMPT" in capturing_llm.messages[0]["content"]
    assert "Summarized Verified Execution Results" in capturing_llm.messages[0]["content"]
    assert captured_prompt_kwargs["dual_core_instruction"] == "先共情，再给步骤。"
    assert capturing_llm.messages[1]["content"] == "前一个问题"
    assert capturing_llm.messages[2]["content"] == "前一个回答"
    assert capturing_llm.messages[-1]["content"] == "帮我深度分析"
