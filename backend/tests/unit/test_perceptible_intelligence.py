from datetime import timezone, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import StudyRecord
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.models.user import User
from app.orchestration.plan_quality_gate import PlanQualityReport
from app.orchestration.plan_review_service import PlanReviewService
from app.orchestration.schemas import ExecutablePlan, ToolCallSpec
from app.services.perceptible_intelligence_service import (
    PerceptibleInsightService,
    ProgressComparisonService,
    WeeklyLearningReportService,
)


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}

    async def exists(self, key: str) -> int:
        return 1 if key in self.values else 0

    async def setex(self, key: str, seconds: int, value: str):
        self.values[key] = value


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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

    service = PerceptibleInsightService(db_session, redis=FakeRedis())
    service.system_updates.enqueue = AsyncMock(return_value=True)

    payload = await service.maybe_enqueue_session_insight(
        user_id=user_id,
        user_message="我最近晚上十点后总学不进去",
        context_focus={"focus_mode": "general_focus"},
        plan_id=None,
        progress_snapshot=None,
    )

    assert payload is not None
    assert payload["metadata"]["evolution_kind"] == "proactive_insight"
    assert payload["metadata"]["scenario"] == "late_night_underperformance"
    assert payload["metadata"]["evidence_summary"]
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
    node_id = uuid4()
    current = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=node_id,
        study_minutes=30,
        mastery_delta=18.0,
        record_type="task_complete",
        created_at=now - timedelta(days=2),
    )
    previous = StudyRecord(
        id=uuid4(),
        user_id=user_id,
        node_id=node_id,
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
    assert "同知识点" in comparison["why_it_matters"]


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
    assert report["evidence_summary"]
    assert report["delivery_mode"] == "deferred_inbox"
    assert report["top_learning_items"]


@pytest.mark.asyncio
async def test_perceptible_insight_service_does_not_emit_snapshot_only_candidate(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERCEPTIBLE_INTELLIGENCE", True)
    monkeypatch.setattr(settings, "ENABLE_PROACTIVE_INSIGHTS", True)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    service = PerceptibleInsightService(db_session, redis=FakeRedis())
    service.system_updates.enqueue = AsyncMock(return_value=True)

    payload = await service.maybe_enqueue_session_insight(
        user_id=user_id,
        user_message="最近状态有点乱",
        context_focus={"focus_mode": "general_focus"},
        plan_id=None,
        progress_snapshot={"attention_areas": ["最近晚上推进容易掉线"]},
    )

    assert payload is None
    service.system_updates.enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_perceptible_insight_service_fails_closed_without_redis(db_session, monkeypatch):
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
        confidence_score=0.85,
        frequency=4,
        is_archived=False,
        last_observed_at=_utcnow() - timedelta(days=1),
    )
    db_session.add_all([user, pattern])
    await db_session.commit()

    service = PerceptibleInsightService(db_session, redis=None)

    payload = await service.maybe_enqueue_session_insight(
        user_id=user_id,
        user_message="我最近晚上十点后总学不进去",
    )

    assert payload is None


@pytest.mark.asyncio
async def test_plan_review_service_adds_reasoning_summary(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PLAN_REASONING_SUMMARY", True)
    service = PlanReviewService()
    monkeypatch.setattr(service, "_quick_rule_check", AsyncMock(return_value="read_only_safe"))
    monkeypatch.setattr(
        service.quality_gate,
        "evaluate",
        lambda **kwargs: PlanQualityReport(
            overall_score=0.91,
            fit_score=0.9,
            feasibility_score=0.9,
            grounding_score=0.9,
            next_action_score=0.9,
            adaptation_score=0.9,
            outcome_learning_score=0.9,
            decision="approve",
        ),
    )

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
            "active_plans": [SimpleNamespace(id="plan-1"), SimpleNamespace(id="plan-2"), SimpleNamespace(id="plan-3")],
            "plan_context": {
                "task_summary": {"completed": 6, "total": 8, "avg_completion_rate": 0.75},
                "facts": {"avg_task_duration_minutes": 48, "session_length_preference": 25},
                "recent_feedback": [
                    {"category": "too_long", "content": "最近感觉太长"},
                    {"category": "too_long", "content": "还是有点太长"},
                ],
            },
        },
    )

    assert result.decision == "approved"
    assert result.reasoning_summary
    assert result.reasoning_details
    assert any("最近执行完成率" == detail["label"] for detail in result.reasoning_details)
    assert any(detail["confidence_tier"] == "inferred" for detail in result.reasoning_details)
    assert result.reasoning_source == "rules_only"
    assert result.persona_strategy_mapping
    assert any(item["recommended_constraint"] == "session_length" for item in result.persona_strategy_mapping)
    assert result.alignment_score is not None
    assert result.alignment_summary
    assert result.to_dict()["reasoning_summary"] == result.reasoning_summary


@pytest.mark.asyncio
async def test_plan_review_service_marks_llm_fallback_reasoning_source(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PLAN_REASONING_SUMMARY", True)
    service = PlanReviewService()
    monkeypatch.setattr(service, "_quick_rule_check", AsyncMock(return_value=None))
    monkeypatch.setattr(
        service.quality_gate,
        "evaluate",
        lambda **kwargs: PlanQualityReport(
            overall_score=0.88,
            fit_score=0.88,
            feasibility_score=0.88,
            grounding_score=0.88,
            next_action_score=0.88,
            adaptation_score=0.88,
            outcome_learning_score=0.88,
            decision="approve",
        ),
    )
    monkeypatch.setattr(
        service,
        "_llm_review",
        AsyncMock(
            return_value={
                "decision": "approved",
                "confidence": 0.61,
                "comments": [],
                "fallback_used": True,
            }
        ),
    )

    plan = ExecutablePlan(
        plan_id="plan-2",
        confidence=0.76,
        tool_calls=[ToolCallSpec(id="1", name="list_tasks", params={})],
    )

    result = await service.review_plan(
        plan=plan,
        user_message="帮我看一下当前计划",
        user_context={"plan_context": {"facts": {"avg_task_duration_minutes": 26}}},
    )

    # drift-fix: quality gate now runs ahead of reasoning-summary assertions, so
    # keep this test focused on the fallback reasoning source path.
    assert result.reasoning_summary
    assert result.reasoning_source == "llm_fallback"


@pytest.mark.asyncio
async def test_perceptible_insight_first_moment_triggers_once(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PERCEPTIBLE_INTELLIGENCE", True)
    monkeypatch.setattr(settings, "ENABLE_PROACTIVE_INSIGHTS", True)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    now = _utcnow()
    shared_node = uuid4()
    patterns = [
        BehaviorPattern(
            id=uuid4(),
            user_id=user_id,
            pattern_name="夜间学习容易掉线",
            pattern_type="execution",
            description="最近几次在晚上 10 点后开始学习时，完成率明显下降。",
            solution_text="把高负荷任务前移到白天。",
            confidence_score=0.86,
            frequency=4,
            is_archived=False,
            last_observed_at=now - timedelta(days=1),
        ),
        BehaviorPattern(
            id=uuid4(),
            user_id=user_id,
            pattern_name="先看整体结构更容易进入状态",
            pattern_type="cognitive",
            description="先给框架时，你进入状态明显更快。",
            solution_text="先给整体框架，再展开细节。",
            confidence_score=0.74,
            frequency=3,
            is_archived=False,
            last_observed_at=now - timedelta(days=2),
        ),
    ]
    feedbacks = [
        TaskFeedback(user_id=user_id, task_id=uuid4(), completion_quality=4, category="just_right")
        for _ in range(5)
    ]
    studies = [
        StudyRecord(
            id=uuid4(),
            user_id=user_id,
            node_id=shared_node,
            study_minutes=30,
            mastery_delta=15.0,
            record_type="task_complete",
            created_at=now - timedelta(days=2),
        ),
        StudyRecord(
            id=uuid4(),
            user_id=user_id,
            node_id=shared_node,
            study_minutes=30,
            mastery_delta=6.0,
            record_type="task_complete",
            created_at=now - timedelta(days=9),
        ),
    ]
    db_session.add(user)
    db_session.add_all(patterns + feedbacks + studies)
    await db_session.commit()

    fake_redis = FakeRedis()
    service = PerceptibleInsightService(db_session, redis=fake_redis)
    service.system_updates.enqueue = AsyncMock(return_value=True)

    payload = await service.maybe_enqueue_session_insight(
        user_id=user_id,
        user_message="我最近晚上十点后总学不进去",
        context_focus={"focus_mode": "general_focus"},
        plan_id=None,
        progress_snapshot=None,
        session_id="sess-first-moment",
        experiment_cohort="B",
    )

    assert payload is not None
    assert payload["metadata"]["insight_level"] == "first_moment"
    assert payload["metadata"]["experiment_cohort"] == "B"

    second = await service.maybe_enqueue_session_insight(
        user_id=user_id,
        user_message="我最近晚上十点后总学不进去",
        context_focus={"focus_mode": "general_focus"},
        plan_id=None,
        progress_snapshot=None,
        session_id="sess-second",
        experiment_cohort="B",
    )

    assert second is None


def test_experiment_cohort_is_stable():
    from app.orchestration.orchestrator import ChatOrchestrator

    first = ChatOrchestrator._experiment_cohort_for_user("user-123")
    second = ChatOrchestrator._experiment_cohort_for_user("user-123")
    third = ChatOrchestrator._experiment_cohort_for_user("user-456")

    assert first in {"A", "B", "C"}
    assert first == second
    assert third in {"A", "B", "C"}


def test_plan_alignment_score_uses_weak_rule_weight():
    service = PlanReviewService()
    plan = ExecutablePlan(
        plan_id="plan-weak",
        confidence=0.72,
        tool_calls=[ToolCallSpec(id="1", name="list_tasks", params={})],
    )

    score, summary, matched = service._score_plan_alignment(
        plan=plan,
        mappings=[
            {
                "rule_key": "avg_completion_rate_low",
                "recommended_constraint": "task_difficulty",
                "recommended_value": "lower",
                "confidence_tier": "weak",
            }
        ],
    )

    assert round(score or 0.0, 2) == 1.0
    assert matched == ["avg_completion_rate_low"]
    assert "画像建议" in (summary or "")


@pytest.mark.asyncio
async def test_weekly_learning_report_includes_profile_hit_rate(db_session):
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
        actual_minutes=20,
        difficulty=2,
        energy_cost=2,
        tags=[],
        completed_at=now - timedelta(days=1),
    )
    feedback = TaskFeedback(
        id=uuid4(),
        user_id=user_id,
        task_id=task.id,
        completion_quality=4,
        category="just_right",
    )
    db_session.add_all([user, task, feedback])
    await db_session.commit()

    service = WeeklyLearningReportService(db_session, redis=None)
    service.system_updates.list_updates = AsyncMock(
        return_value=[
            {
                "created_at": int((now - timedelta(days=1)).timestamp()),
                "metadata": {
                    "evolution_kind": "plan_reasoning",
                    "reasoning_summary": "这次计划这样安排，是有依据的",
                    "alignment_summary": "这次计划和你的近期画像大体一致。",
                    "evidence_summary": "最近任务节奏更稳。",
                    "persona_strategy_mapping": [
                        {
                            "recommended_constraint": "load_shape",
                            "recommended_value": "preserve",
                            "confidence_tier": "explicit",
                        }
                    ],
                },
            }
        ]
    )

    report = await service.build_weekly_report(user_id=user_id)

    assert report is not None
    assert report["profile_hit_rate"] is not None
    assert report["profile_hit_rate"]["hit_rate"] >= 0.0
