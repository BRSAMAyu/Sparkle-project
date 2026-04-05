from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.orchestration.statechart_engine import WorkflowState
from app.tools.base import ToolResult


def _build_orchestrator_stub() -> ChatOrchestrator:
    orchestrator = object.__new__(ChatOrchestrator)
    orchestrator.redis = object()
    return orchestrator


def test_extract_execution_feedback_from_feedback_entry() -> None:
    entry = {
        "type": "plan_execution_feedback",
        "slow_tools": ["query_knowledge"],
        "failed_tools": ["create_task"],
        "unreliable_dependencies": ["step-1"],
        "quality_score": 0.42,
    }
    feedback = ChatOrchestrator._extract_execution_feedback_from_log_entry(entry)
    assert feedback == {
        "slow_tools": ["query_knowledge"],
        "failed_tools": ["create_task"],
        "unreliable_dependencies": ["step-1"],
        "quality_score": 0.42,
    }


def test_extract_execution_feedback_from_plan_execution_entry() -> None:
    entry = {
        "type": "plan_execution",
        "applied_adjustment": {
            "slow_tools": ["query_knowledge"],
            "failed_tools": [],
            "unreliable_dependencies": ["step-1"],
            "quality_score": 0.65,
        },
    }
    feedback = ChatOrchestrator._extract_execution_feedback_from_log_entry(entry)
    assert feedback == {
        "slow_tools": ["query_knowledge"],
        "failed_tools": [],
        "unreliable_dependencies": ["step-1"],
        "quality_score": 0.65,
    }


@pytest.mark.asyncio
async def test_load_recent_execution_feedback(monkeypatch) -> None:
    orchestrator = _build_orchestrator_stub()
    user_id = str(uuid4())
    plan_id = str(uuid4())

    class MockPlanStateService:
        def __init__(self, db, redis):
            self.db = db
            self.redis = redis

        async def get_plan_state(self, *_args, **_kwargs):
            return SimpleNamespace(
                feedback_log=[
                    {"type": "other", "content": "ignore"},
                    {
                        "type": "plan_execution",
                        "applied_adjustment": {
                            "slow_tools": ["tool_a"],
                            "failed_tools": ["tool_b"],
                            "unreliable_dependencies": [],
                            "quality_score": 0.73,
                        },
                    },
                ]
            )

    monkeypatch.setattr("app.services.plan_state_service.PlanStateService", MockPlanStateService)

    feedback = await orchestrator._load_recent_execution_feedback(
        active_db=object(),
        user_id=user_id,
        plan_id=plan_id,
    )
    assert feedback == {
        "slow_tools": ["tool_a"],
        "failed_tools": ["tool_b"],
        "unreliable_dependencies": [],
        "quality_score": 0.73,
    }


@pytest.mark.asyncio
async def test_validate_plan_execution_uses_dag_path(monkeypatch) -> None:
    orchestrator = _build_orchestrator_stub()
    orchestrator._publish_execution_feedback = AsyncMock()

    validation_result = SimpleNamespace(
        plan_id=str(uuid4()),
        validation_status="partial",
        quality_score=0.66,
        tool_summary={"total": 2, "successful": 1},
        step_validations=[
            SimpleNamespace(passed=True),
            SimpleNamespace(passed=False),
        ],
        aborted=False,
    )

    class MockValidator:
        def __init__(self, record_service=None):
            self.record_service = record_service

        async def validate_plan_execution(self, **_kwargs):
            return validation_result

        async def validate_and_record(self, **_kwargs):
            raise AssertionError("legacy validate_and_record path should not be called")

    monkeypatch.setattr("app.orchestration.validation_engine.PlanExecutionValidator", MockValidator)
    monkeypatch.setattr("app.orchestration.validation_engine.PlanExecutionRecordService", lambda _db: object())

    plan_id = str(uuid4())
    executable_plan = ExecutablePlan(
        plan_id=plan_id,
        tool_calls=[ToolCallSpec(id="step-1", name="create_task", params={})],
    )
    plan_result = SimpleNamespace(
        step_results=[
            SimpleNamespace(
                step_id="step-1",
                tool_name="create_task",
                tool_result=ToolResult(success=True, tool_name="create_task", data={"task_id": "t1"}),
                duration_ms=123,
                output_data={"task_id": "t1"},
            )
        ],
        tool_results=[ToolResult(success=True, tool_name="create_task", data={"task_id": "t1"})],
        aborted=False,
    )
    final_state = WorkflowState(context_data={"plan_execution_result": plan_result})

    result = await orchestrator._validate_plan_execution(
        executable_plan=executable_plan,
        active_db=object(),
        final_state=final_state,
        user_id=str(uuid4()),
        session_id=str(uuid4()),
    )

    assert result is not None
    assert result["validation_status"] == "partial"
    assert result["steps_total"] == 2
    assert result["steps_passed"] == 1
    orchestrator._publish_execution_feedback.assert_awaited_once()
