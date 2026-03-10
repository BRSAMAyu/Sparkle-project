from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import StudyRecord
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.orchestration.plan_review_service import PlanReviewService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.services.perceptible_intelligence_service import (
    PerceptibleInsightService,
    ProgressComparisonService,
    WeeklyLearningReportService,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_perceptible_insight_service_enqueues_proactive_insight(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERCEPTIBLE_INTELLIGENCE", True)
    monkeypatch.setattr(settings, "ENABLE_PROACTIVE_INSIGHTS", True)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    pattern = BehaviorPattern(
        id=uuid4(),
        user_id=user_id,
        pattern_name="夜间学习容易掉线",
        pattern_type="execution",
        description="最近几次在晚上 10 点后开始学习时，完成率明显下降。",
        solution_text="把高负荷任务前移到白天。",
        confidence_score=0.85,
        frequency=4,
        is_archived=False,
        last_observed_at=_utcnow() - timedelta(days=1),
    )
    db_session.add_all([user, pattern])
    await db_session.commit()

    service = PerceptibleInsightService(db_session, redis=None)
    service.system_updates.enqueue = AsyncMock()

    payload = await service.maybe_enqueue_session_insight(
        user_id=user_id,
        user_message="我最近晚上十点后总学不进去",
        context_focus={"focus_mode": "general_focus"},
        plan_id=None,
        progress_snapshot=None,
    )

    assert payload is not None
    assert payload["metadata"]["evolution_kind"] == "proactive_insight"
    assert "完成率明显下降" in payload["metadata"]["evidence_summary"] or payload["metadata"]["confidence"] == 0.85
    service.system_updates.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_progress_comparison_service_prefers_mastery_delta(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    now = _utcnow()
    current = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=uuid4(),
        study_minutes=30,
        mastery_delta=18.0,
        record_type="task_complete",
        created_at=now - timedelta(days=2),
    )
    previous = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=uuid4(),
        study_minutes=30,
        mastery_delta=6.0,
        record_type="task_complete",
        created_at=now - timedelta(days=9),
    )
    db_session.add_all([user, current, previous])
    await db_session.commit()

    comparison = await ProgressComparisonService(db_session).build_best_comparison(
        user_id=user_id,
    )

    assert comparison is not None
    assert comparison["source"] == "mastery"
    assert "掌握度提升" in comparison["before_label"]


@pytest.mark.asyncio
async def test_weekly_learning_report_service_builds_structured_report(db_session):
    user_id = uuid4()
    now = _utcnow()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=uuid4(),
        user_id=user_id,
        title="复习线代",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=30,
        actual_minutes=25,
        difficulty=3,
        energy_cost=2,
        tags=[],
        completed_at=now - timedelta(days=1),
    )
    study = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=uuid4(),
        task_id=task.id,
        study_minutes=25,
        mastery_delta=12.0,
        record_type="task_complete",
        created_at=now - timedelta(days=1),
    )
    pattern = BehaviorPattern(
        id=uuid4(),
        user_id=user_id,
        pattern_name="先看结构再进入细节",
        pattern_type="cognitive",
        description="当先给整体框架时，你的进入状态明显更快。",
        solution_text="后续先给框架，再展开细节。",
        confidence_score=0.82,
        frequency=3,
        is_archived=False,
        last_observed_at=now - timedelta(days=2),
    )
    db_session.add_all([user, task, study, pattern])
    await db_session.commit()

    report = await WeeklyLearningReportService(db_session, redis=None).build_weekly_report(
        user_id=user_id,
    )

    assert report is not None
    assert report["headline"] == "这周我更了解你了一点"
    assert report["top_learnings"]
    assert len(report["top_learnings"]) <= 3
    assert report["one_key_adjustment"]


@pytest.mark.asyncio
async def test_plan_review_service_adds_reasoning_summary(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PLAN_REASONING_SUMMARY", True)
    service = PlanReviewService()
    monkeypatch.setattr(service, "_quick_rule_check", AsyncMock(return_value="read_only_safe"))

    plan = ExecutablePlan(
        plan_id="plan-1",
        confidence=0.91,
        tool_calls=[
            ToolCallSpec(id="1", name="list_tasks", params={}),
            ToolCallSpec(id="2", name="get_plan", params={}),
        ],
    )

    result = await service.review_plan(
        plan=plan,
        user_message="帮我看一下当前计划",
        user_context={
            "llm_profile": {"verbosity_target": "balanced", "tone": "structured"},
            "active_plans": [SimpleNamespace(id="plan-1")],
        },
    )

    assert result.decision == "approved"
    assert result.reasoning_summary
    assert result.reasoning_details
    assert result.to_dict()["reasoning_summary"] == result.reasoning_summary
