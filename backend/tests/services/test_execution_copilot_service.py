from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.task import TaskStatus
from app.services.execution_copilot_service import ExecutionCopilotService
from app.services.learning_event_service import _MEM_EVENTS, LearningEventService


@pytest.mark.asyncio
async def test_execution_copilot_build_contains_summary_and_risk(monkeypatch):
    monkeypatch.setattr("app.services.learning_event_service.settings.ENABLE_LEARNING_CONTROL_PLANE", True)
    _MEM_EVENTS.clear()

    service = ExecutionCopilotService(db=MagicMock(), redis=None)
    user_id = uuid4()
    plan_id = uuid4()

    service._get_plan = AsyncMock(return_value=SimpleNamespace(name="期中冲刺计划"))

    today = date.today()
    service._get_plan_tasks = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=uuid4(),
                title="整理错题",
                estimated_minutes=25,
                priority=5,
                status=TaskStatus.IN_PROGRESS,
                due_date=today - timedelta(days=1),
                guide_content="",
                created_at=None,
            ),
            SimpleNamespace(
                id=uuid4(),
                title="重做高频题",
                estimated_minutes=30,
                priority=4,
                status=TaskStatus.PENDING,
                due_date=today,
                guide_content="补齐验收标准",
                created_at=None,
            ),
        ]
    )

    event_service = LearningEventService(redis_client=None)
    await event_service.emit(
        event_type="checkpoint_done",
        user_id=str(user_id),
        workflow_id=str(plan_id),
        task_type="execution_copilot",
        data={"status": "done"},
    )
    await event_service.emit(
        event_type="checkpoint_skipped",
        user_id=str(user_id),
        workflow_id=str(plan_id),
        task_type="execution_copilot",
        data={"status": "skipped"},
    )

    result = await service.build_copilot(user_id=user_id, plan_id=plan_id, limit=3)

    assert result["plan_name"] == "期中冲刺计划"
    assert "checkpoint_summary" in result
    assert result["checkpoint_summary"]["done"] >= 1
    assert result["checkpoint_summary"]["skipped"] >= 1
    assert result["risk_level"] in {"low", "medium", "high"}
    assert isinstance(result["adoptable_actions"], list)


@pytest.mark.asyncio
async def test_execution_copilot_timeline_returns_window_and_blockers(monkeypatch):
    monkeypatch.setattr("app.services.learning_event_service.settings.ENABLE_LEARNING_CONTROL_PLANE", True)
    _MEM_EVENTS.clear()

    service = ExecutionCopilotService(db=MagicMock(), redis=None)
    user_id = uuid4()
    plan_id = uuid4()
    service._get_plan = AsyncMock(return_value=SimpleNamespace(name="英语提分计划"))

    event_service = LearningEventService(redis_client=None)
    await event_service.emit(
        event_type="checkpoint_due",
        user_id=str(user_id),
        workflow_id=str(plan_id),
        task_type="execution_copilot",
        data={"blockers": ["overdue_tasks_present", "missing_task_guidance"]},
    )
    await event_service.emit(
        event_type="checkpoint_done",
        user_id=str(user_id),
        workflow_id=str(plan_id),
        task_type="execution_copilot",
        data={"status": "done"},
    )

    timeline = await service.build_timeline(user_id=user_id, plan_id=plan_id, days=7)

    assert timeline["plan_name"] == "英语提分计划"
    assert timeline["timeline_days"] == 7
    assert len(timeline["timeline"]) == 7
    assert "checkpoint_summary" in timeline
    assert isinstance(timeline["top_blockers"], list)
