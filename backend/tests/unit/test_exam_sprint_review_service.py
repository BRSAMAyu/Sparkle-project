from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.achievement import Achievement, AchievementRarity, AchievementType, UserAchievement
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.notification import Notification
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import HelpfulFeature, PostExamReviewRequest, ReviewPlanSelection, ReviewTopicSelection
from app.services.exam_sprint_review_service import ExamSprintReviewService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_submit_post_exam_review_archives_plan_and_writes_growth_profile(db_session, test_user, monkeypatch):
    ws_manager = AsyncMock()
    monkeypatch.setattr("app.core.websocket.get_ws_manager", lambda: ws_manager)
    user_id = test_user.id

    exam_date = date.today() - timedelta(days=1)
    started_at = datetime.combine(exam_date - timedelta(days=6), time(hour=9))

    node_a = KnowledgeNode(
        id=uuid4(),
        name="TCP 拥塞控制",
        description="TCP 拥塞控制",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    node_b = KnowledgeNode(
        id=uuid4(),
        name="IP / 子网划分",
        description="IP / 子网划分",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    achievement = Achievement(
        id="sprint_first",
        name="初出茅庐",
        description="完成第一个冲刺计划",
        type=AchievementType.SPRINT,
        rarity=AchievementRarity.COMMON,
        trigger_code="SPRINTS_TOTAL",
        trigger_config={"count": 1},
        reward_config=[],
        category="sprint",
    )
    plan = Plan(
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="计算机网络",
        target_date=exam_date,
        progress=0.85,
        is_active=True,
        source_metadata={"post_exam_review": {}},
        created_at=started_at,
        updated_at=started_at,
    )
    tasks = [
        Task(
            user_id=user_id,
            plan=plan,
            title="Day 1 · 高频保底",
            type=TaskType.LEARNING,
            tags=[],
            estimated_minutes=45,
            actual_minutes=50,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.COMPLETED,
            completed_at=started_at + timedelta(days=1),
        ),
        Task(
            user_id=user_id,
            plan=plan,
            title="Day 2 · TCP 补强",
            type=TaskType.LEARNING,
            tags=[],
            estimated_minutes=40,
            actual_minutes=42,
            difficulty=3,
            energy_cost=3,
            status=TaskStatus.COMPLETED,
            completed_at=started_at + timedelta(days=3),
        ),
        Task(
            user_id=user_id,
            plan=plan,
            title="Day 3 · 路由回顾",
            type=TaskType.LEARNING,
            tags=[],
            estimated_minutes=35,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
        ),
    ]
    prefs = UserPreferencesCenter(
        user_id=user_id,
        explicit={
            "cold_start_context": {
                "estimated_score_now": 38,
                "diagnostic_estimated_score": 38.0,
                "diagnostic_node_mastery_snapshot": [
                    {
                        "node_id": str(node_a.id),
                        "node_name": node_a.name,
                        "mastery": 38.0,
                    },
                    {
                        "node_id": str(node_b.id),
                        "node_name": node_b.name,
                        "mastery": 42.0,
                    },
                ],
            }
        },
    )
    status_rows = [
        UserNodeStatus(user_id=user_id, node_id=node_a.id, mastery_score=72.0),
        UserNodeStatus(user_id=user_id, node_id=node_b.id, mastery_score=58.0),
    ]
    study_records = [
        StudyRecord(
            user_id=user_id,
            node_id=node_a.id,
            task_id=tasks[0].id,
            study_minutes=50,
            mastery_delta=8.0,
            initial_mastery=38.0,
            created_at=started_at + timedelta(days=1),
        ),
        StudyRecord(
            user_id=user_id,
            node_id=node_a.id,
            task_id=tasks[1].id,
            study_minutes=42,
            mastery_delta=6.0,
            initial_mastery=46.0,
            created_at=started_at + timedelta(days=3),
        ),
    ]
    errors = [
        ErrorRecord(
            user_id=user_id,
            subject_code="计算机网络",
            chapter="TCP",
            question_text="q1",
            mastery_level=0.9,
            review_count=2,
            created_at=started_at + timedelta(days=2),
        ),
        ErrorRecord(
            user_id=user_id,
            subject_code="计算机网络",
            chapter="IP",
            question_text="q2",
            mastery_level=0.4,
            review_count=1,
            created_at=started_at + timedelta(days=4),
        ),
    ]

    db_session.add_all([node_a, node_b, achievement, plan, prefs, *tasks, *status_rows, *study_records, *errors])
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.submit_post_exam_review(
        user_id=user_id,
        request=PostExamReviewRequest(
            self_rating=7,
            underprepared_topics=[ReviewTopicSelection(node_id=node_a.id, node_name=node_a.name)],
            prepared_but_not_tested_topics=[ReviewPlanSelection(task_id=tasks[2].id, label=tasks[2].title)],
            sparkle_helped=True,
            helpful_features=[HelpfulFeature.ERROR_REVIEW, HelpfulFeature.STRATEGY_ADJUSTMENT],
        ),
    )

    await db_session.refresh(plan)
    stored_prefs = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
    ).scalar_one()
    unlocked = (
        await db_session.execute(select(UserAchievement).where(UserAchievement.user_id == user_id))
    ).scalars().all()

    assert plan.is_active is False
    assert response.summary.task_stats.completed == 2
    assert response.summary.task_stats.total == 3
    assert response.summary.top_improvement is not None
    assert response.summary.top_improvement.node_name == "TCP 拥塞控制"
    assert response.summary.top_improvement.before_mastery == 38.0
    assert response.summary.top_improvement.after_mastery == 72.0
    assert response.summary.high_frequency_coverage.current_rate == 0.5
    assert response.summary.error_recovery.repair_rate == 0.5
    assert response.summary.invitation_status.completed_at is not None
    assert stored_prefs.explicit["exam_sprint_last_review"]["headline"] == response.summary.headline
    assert stored_prefs.explicit["exam_sprint_growth_archive"]["entries"][-1]["review_id"] == response.review_id
    assert len(unlocked) == 1
    assert unlocked[0].achievement_id == "sprint_first"


@pytest.mark.asyncio
async def test_scan_due_review_invitations_creates_notification_and_marks_plan(db_session, test_user):
    user_id = test_user.id
    exam_date = date.today() - timedelta(days=1)
    plan = Plan(
        user_id=user_id,
        name="期末冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="计算机网络",
        target_date=exam_date,
        is_active=True,
        source_metadata={"post_exam_review": {}},
    )
    db_session.add(plan)
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    result = await service.scan_due_review_invitations(limit=10)

    await db_session.refresh(plan)
    notifications = (
        await db_session.execute(select(Notification).where(Notification.user_id == user_id))
    ).scalars().all()

    assert result["invited"] == 1
    assert len(notifications) == 1
    assert notifications[0].type == "exam_sprint_review"
    assert plan.source_metadata["post_exam_review"]["invited_at"] is not None
