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
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.schemas.exam_sprint import HelpfulFeature, PostExamReviewRequest, ReviewPlanSelection, ReviewTopicSelection
from app.services.exam_sprint_review_service import ExamSprintReviewService
from app.services.galaxy_service import GalaxyService
from app.services.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_submit_post_exam_review_archives_plan_and_writes_growth_profile(db_session, test_user, monkeypatch):
    ws_manager = AsyncMock()
    monkeypatch.setattr("app.core.websocket.get_ws_manager", lambda: ws_manager)
    user_id = test_user.id

    exam_date = date.today() - timedelta(days=2)
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
            },
            "exam_sprint_growth_archive": {
                "entries": [{"review_id": f"old-review-{index}", "plan_id": str(uuid4())} for index in range(10)]
            },
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
        (await db_session.execute(select(UserAchievement).where(UserAchievement.user_id == user_id))).scalars().all()
    )

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
    assert len(stored_prefs.explicit["exam_sprint_growth_archive"]["entries"]) == 11
    assert stored_prefs.explicit["exam_sprint_growth_archive"]["entries"][0]["review_id"] == "old-review-0"
    assert stored_prefs.explicit["exam_sprint_growth_archive"]["entries"][-1]["review_id"] == response.review_id
    assert len(unlocked) == 1
    assert unlocked[0].achievement_id == "sprint_first"


@pytest.mark.asyncio
async def test_get_portfolio_merges_archived_active_and_planned_sprints(db_session, test_user):
    user_id = test_user.id
    archived_plan_id = uuid4()
    now = _utcnow()

    prefs = UserPreferencesCenter(
        user_id=user_id,
        explicit={
            "exam_sprint_growth_archive": {
                "entries": [
                    {
                        "review_id": "review-1",
                        "plan_id": str(archived_plan_id),
                        "plan_name": "7天计网冲刺",
                        "subject": "计算机网络",
                        "exam_date": "2026-04-10",
                        "reviewed_at": "2026-04-10T20:00:00",
                        "self_rating": 8,
                        "result_rating": 4,
                        "result_description": "估计 82 分",
                        "underprepared_topics": [{"node_name": "子网划分"}],
                        "persistent_weak_nodes": [{"node_name": "子网划分"}],
                        "summary": {
                            "plan_id": str(archived_plan_id),
                            "plan_name": "7天计网冲刺",
                            "subject": "计算机网络",
                            "started_at": "2026-04-04T09:00:00",
                            "headline": "7 天内补齐了高频保底点。",
                            "score_stats": {"current_score": 82.0},
                            "top_improvement": {"node_name": "TCP 拥塞控制"},
                            "mastery_changes": [{"node_name": "TCP 拥塞控制"}],
                            "high_frequency_coverage": {
                                "current_rate": 0.8,
                                "total_topics": 40,
                                "covered_topics_after": 32,
                            },
                            "task_stats": {"completion_rate": 1.0},
                        },
                    }
                ]
            }
        },
    )
    active_plan = Plan(
        user_id=user_id,
        name="14天操作系统冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="操作系统",
        target_date=date(2026, 4, 30),
        progress=0.3,
        mastery_level=0.18,
        is_active=True,
        source_metadata={
            "exam_sprint_intake": {
                "sprint_mode": "fourteen_day_build_and_retrieve",
                "weak_chapters": ["死锁"],
            }
        },
        created_at=datetime(2026, 4, 17, 9, 0, 0),
        updated_at=now,
    )
    planned_plan = Plan(
        user_id=user_id,
        name="高等数学冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="高等数学",
        target_date=date(2026, 5, 14),
        progress=0.0,
        mastery_level=0.0,
        is_active=False,
        source_metadata={
            "exam_sprint_intake": {
                "sprint_mode": "standard_exam_sprint",
                "weak_chapters": ["积分中值定理"],
            }
        },
        created_at=datetime(2026, 5, 1, 9, 0, 0),
        updated_at=now,
    )

    db_session.add_all([prefs, active_plan, planned_plan])
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.get_portfolio(user_id=user_id)

    assert response.total_mastered_nodes == 80
    assert response.active_count == 1
    assert response.completed_count == 1
    assert response.planned_count == 1

    entries_by_subject = {entry.subject: entry for entry in response.entries}

    completed = entries_by_subject["计算机网络"]
    assert completed.status == "completed"
    assert completed.mastered_nodes_count == 80
    assert completed.proud_nodes == ["TCP 拥塞控制"]
    assert completed.weakest_points == ["子网划分"]
    assert completed.current_score == 82.0

    active = entries_by_subject["操作系统"]
    assert active.status == "active"
    assert active.sprint_mode == "fourteen_day_build_and_retrieve"
    assert active.mastered_nodes_count == 0
    assert active.weakest_points == ["死锁"]

    planned = entries_by_subject["高等数学"]
    assert planned.status == "planned"
    assert planned.sprint_mode == "standard_exam_sprint"
    assert planned.mastered_nodes_count == 0
    assert planned.weakest_points == ["积分中值定理"]


@pytest.mark.asyncio
async def test_completed_sprint_auto_archives_without_post_exam_review(db_session, test_user):
    user_id = test_user.id
    started_at = datetime.combine(date.today() - timedelta(days=2), time(hour=9))
    target_date = started_at.date() + timedelta(days=2)
    plan = Plan(
        user_id=user_id,
        name="3天计网冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="计算机网络",
        target_date=target_date,
        progress=0.5,
        mastery_level=0.42,
        is_active=True,
        is_primary=True,
        source_metadata={
            "exam_sprint_intake": {
                "sprint_mode": "seven_day_survival",
                "weak_chapters": ["TCP 拥塞控制"],
            }
        },
        created_at=started_at,
        updated_at=started_at,
    )
    completed_task = Task(
        user_id=user_id,
        plan=plan,
        title="Day 1 · 高频保底",
        type=TaskType.LEARNING,
        tags=["day:1"],
        estimated_minutes=30,
        actual_minutes=28,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.COMPLETED,
        completed_at=started_at + timedelta(days=1),
    )
    final_task = Task(
        user_id=user_id,
        plan=plan,
        title="Day 2 · 闭卷输出",
        type=TaskType.TRAINING,
        tags=["day:2"],
        estimated_minutes=35,
        difficulty=3,
        energy_cost=3,
        # R1A4-P2-2 FSM：PENDING -> COMPLETED 非法，完成前置为 IN_PROGRESS
        status=TaskStatus.IN_PROGRESS,
    )
    db_session.add_all([plan, completed_task, final_task])
    await db_session.commit()

    await TaskService.complete(db=db_session, db_obj=final_task, actual_minutes=36)

    await db_session.refresh(plan)
    state = (
        await db_session.execute(select(PlanState).where(PlanState.user_id == user_id, PlanState.plan_id == plan.id))
    ).scalar_one()
    portfolio = await ExamSprintReviewService(db_session).get_portfolio(user_id=user_id)
    entry = next(item for item in portfolio.entries if item.plan_id == plan.id)

    assert plan.is_active is False
    assert plan.is_primary is False
    assert plan.progress == 1.0
    assert plan.source_metadata["exam_sprint_completion"]["trigger"] == "all_tasks_completed"
    assert plan.source_metadata["exam_sprint_completion"]["completed_at"] is not None
    assert state.status == PlanStateStatus.ARCHIVED.value
    assert state.archived_at is not None
    assert portfolio.active_count == 0
    assert portfolio.completed_count == 1
    assert entry.status == "completed"
    assert entry.completed_at == plan.source_metadata["exam_sprint_completion"]["completed_at"]
    assert entry.self_rating is None


@pytest.mark.asyncio
async def test_submit_post_exam_review_penalizes_tcp_state_and_archives_weak_nodes(db_session, test_user, monkeypatch):
    user_id = test_user.id
    exam_date = date.today() - timedelta(days=2)
    started_at = datetime.combine(exam_date - timedelta(days=6), time(hour=9))

    tcp_state = KnowledgeNode(
        id=uuid4(),
        name="cn.tcp_state",
        description="TCP 状态机",
        keywords=["TCP 状态机"],
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    tcp_state_id = tcp_state.id
    plan = Plan(
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="计算机网络",
        target_date=exam_date,
        progress=0.8,
        is_active=True,
        source_metadata={"post_exam_review": {}},
        created_at=started_at,
        updated_at=started_at,
    )
    prefs = UserPreferencesCenter(user_id=user_id, explicit={"cold_start_context": {}})
    status = UserNodeStatus(user_id=user_id, node_id=tcp_state_id, mastery_score=0.8, is_unlocked=True)
    db_session.add_all([tcp_state, plan, prefs, status])
    await db_session.commit()

    update_calls = []

    async def fake_update_node_mastery(self, *, user_id, node_id, new_mastery, reason, **_kwargs):
        update_calls.append(
            {
                "user_id": user_id,
                "node_id": node_id,
                "new_mastery": new_mastery,
                "reason": reason,
            }
        )
        row = (
            await self.db.execute(
                select(UserNodeStatus).where(UserNodeStatus.user_id == user_id, UserNodeStatus.node_id == node_id)
            )
        ).scalar_one()
        row.mastery_score = new_mastery
        await self.db.flush()
        return {"success": True, "new_mastery": new_mastery}

    monkeypatch.setattr(
        "app.services.galaxy_service.GalaxyService.update_node_mastery",
        fake_update_node_mastery,
    )

    service = ExamSprintReviewService(db_session)
    response = await service.submit_post_exam_review(
        user_id=user_id,
        request=PostExamReviewRequest(
            result_rating=2,
            biggest_challenge="TCP状态机全错了",
            sparkle_helped=False,
        ),
    )

    refreshed_status = (
        await db_session.execute(
            select(UserNodeStatus).where(UserNodeStatus.user_id == user_id, UserNodeStatus.node_id == tcp_state_id)
        )
    ).scalar_one()
    stored_prefs = (
        await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
    ).scalar_one()
    archive_entry = stored_prefs.explicit["exam_sprint_growth_archive"]["entries"][-1]
    weak_node_ids = {item["node_id"] for item in archive_entry["persistent_weak_nodes"]}

    assert update_calls[0]["node_id"] == tcp_state_id
    assert update_calls[0]["new_mastery"] == pytest.approx(0.6)
    assert update_calls[0]["reason"] == "post_exam_review_weak_node"
    assert refreshed_status.mastery_score == pytest.approx(0.6)
    assert archive_entry["review_id"] == response.review_id
    assert "cn.tcp_state" in weak_node_ids
    assert "cn.tcp_three_way" in weak_node_ids


@pytest.mark.asyncio
async def test_check_sprint_completion_returns_summary_when_all_seven_days_done(db_session, test_user):
    user_id = test_user.id
    started_at = datetime.combine(date.today() - timedelta(days=6), time(hour=9))
    target_date = started_at.date() + timedelta(days=6)

    node_a = KnowledgeNode(
        id=uuid4(),
        name="TCP/IP 协议栈",
        description="TCP/IP 协议栈",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    node_b = KnowledgeNode(
        id=uuid4(),
        name="子网划分",
        description="子网划分",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    plan = Plan(
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="计算机网络",
        target_date=target_date,
        progress=1.0,
        is_active=True,
        created_at=started_at,
        updated_at=started_at,
    )
    tasks = [
        Task(
            user_id=user_id,
            plan=plan,
            title=f"Day {day} · 冲刺任务",
            type=TaskType.LEARNING,
            tags=[f"day:{day}"],
            estimated_minutes=30,
            actual_minutes=32,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.COMPLETED,
            completed_at=started_at + timedelta(days=day - 1),
            order_index=day * 1000,
        )
        for day in range(1, 8)
    ]
    prefs = UserPreferencesCenter(
        user_id=user_id,
        explicit={
            "cold_start_context": {
                "diagnostic_node_mastery_snapshot": [
                    {
                        "node_id": str(node_a.id),
                        "node_name": node_a.name,
                        "mastery": 40.0,
                    },
                    {
                        "node_id": str(node_b.id),
                        "node_name": node_b.name,
                        "mastery": 35.0,
                    },
                ],
            }
        },
    )
    db_session.add_all(
        [
            node_a,
            node_b,
            plan,
            *tasks,
            prefs,
            UserNodeStatus(user_id=user_id, node_id=node_a.id, mastery_score=82.0),
            UserNodeStatus(user_id=user_id, node_id=node_b.id, mastery_score=48.0),
            ErrorRecord(
                user_id=user_id,
                subject_code="计算机网络",
                chapter="TCP",
                question_text="q1",
                mastery_level=0.9,
                review_count=2,
                created_at=started_at + timedelta(days=3),
            ),
            ErrorRecord(
                user_id=user_id,
                subject_code="计算机网络",
                chapter="IP",
                question_text="q2",
                mastery_level=0.3,
                review_count=1,
                created_at=started_at + timedelta(days=4),
            ),
        ]
    )
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.check_sprint_completion(user_id=user_id, plan_id=plan.id)

    assert response.completed is True
    assert response.summary is not None
    assert response.summary.mastered_nodes_count == 1
    assert response.summary.repaired_errors_count == 1
    assert response.summary.completed_tasks_count == 7
    assert response.summary.strongest_area == "TCP/IP 协议栈"
    assert response.summary.growth_area == "子网划分"


@pytest.mark.asyncio
async def test_check_sprint_completion_stays_false_until_all_day_tasks_done(db_session, test_user):
    user_id = test_user.id
    plan = Plan(
        user_id=user_id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        subject="计算机网络",
        target_date=date.today(),
        progress=0.85,
        is_active=True,
    )
    tasks = [
        Task(
            user_id=user_id,
            plan=plan,
            title=f"Day {day} · 冲刺任务",
            type=TaskType.LEARNING,
            tags=[f"day:{day}"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.COMPLETED if day < 7 else TaskStatus.PENDING,
            order_index=day * 1000,
        )
        for day in range(1, 8)
    ]
    db_session.add_all([plan, *tasks])
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.check_sprint_completion(user_id=user_id, plan_id=plan.id)

    assert response.completed is False
    assert response.summary is None


@pytest.mark.asyncio
async def test_scan_due_review_invitations_creates_notification_and_marks_plan(db_session, test_user):
    user_id = test_user.id
    exam_date = date.today() - timedelta(days=2)
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
        (await db_session.execute(select(Notification).where(Notification.user_id == user_id))).scalars().all()
    )

    assert result["invited"] == 1
    assert len(notifications) == 1
    assert notifications[0].type == "exam_sprint_review"
    assert plan.source_metadata["post_exam_review"]["invited_at"] is not None


@pytest.mark.asyncio
async def test_analyze_pack_node_effectiveness_flags_underestimated_node_difficulty(db_session) -> None:
    sprint_node_id = GalaxyService.sprint_node_uuid("cn.subnetting")
    db_session.add(
        KnowledgeNode(
            id=sprint_node_id,
            name="子网划分与 CIDR",
            description="Sprint Pack 节点",
            source_type="sprint_pack",
            dominant_sector_code="VOID",
            sector_classification_status="pending",
        )
    )

    statuses: list[UserNodeStatus] = []
    for index in range(60):
        user = User(
            username=f"pack_quality_{index}",
            email=f"pack_quality_{index}@example.com",
            hashed_password="hashed",
        )
        db_session.add(user)
        await db_session.flush()
        statuses.append(
            UserNodeStatus(
                user_id=user.id,
                node_id=sprint_node_id,
                mastery_score=0.35,
                is_unlocked=True,
            )
        )

    db_session.add_all(statuses)
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    pack_payload = {
        "id": "computer_networks@v1",
        "name": "Computer Networks Sprint Pack",
        "knowledge_nodes": [
            {
                "node_id": "cn.subnetting",
                "label": "子网划分与 CIDR",
                "difficulty": 2,
            }
        ],
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("app.services.exam_sprint_review_service.load_pack", lambda *_args, **_kwargs: pack_payload)
        alerts = await service.analyze_pack_node_effectiveness("computer_networks@v1")
    subnetting_alert = next((alert for alert in alerts if alert.node_id == "cn.subnetting"), None)

    assert subnetting_alert is not None
    assert subnetting_alert.current_difficulty == 2
    assert subnetting_alert.suggested_difficulty == 3
    assert subnetting_alert.average_post_sprint_mastery == pytest.approx(0.35)
    assert subnetting_alert.expected_mastery == pytest.approx(0.65)
    assert subnetting_alert.evidence_count == 60


@pytest.mark.asyncio
async def test_analyze_pack_node_effectiveness_skips_insufficient_evidence(db_session) -> None:
    sprint_node_id = GalaxyService.sprint_node_uuid("cn.subnetting")
    db_session.add(
        KnowledgeNode(
            id=sprint_node_id,
            name="子网划分与 CIDR",
            description="Sprint Pack 节点",
            source_type="sprint_pack",
            dominant_sector_code="VOID",
            sector_classification_status="pending",
        )
    )

    statuses: list[UserNodeStatus] = []
    for index in range(49):
        user = User(
            username=f"pack_quality_small_{index}",
            email=f"pack_quality_small_{index}@example.com",
            hashed_password="hashed",
        )
        db_session.add(user)
        await db_session.flush()
        statuses.append(
            UserNodeStatus(
                user_id=user.id,
                node_id=sprint_node_id,
                mastery_score=0.35,
                is_unlocked=True,
            )
        )

    db_session.add_all(statuses)
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    pack_payload = {
        "id": "computer_networks@v1",
        "name": "Computer Networks Sprint Pack",
        "knowledge_nodes": [
            {
                "node_id": "cn.subnetting",
                "label": "子网划分与 CIDR",
                "difficulty": 2,
            }
        ],
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("app.services.exam_sprint_review_service.load_pack", lambda *_args, **_kwargs: pack_payload)
        alerts = await service.analyze_pack_node_effectiveness("computer_networks@v1")

    assert all(alert.node_id != "cn.subnetting" for alert in alerts)


def test_days_used_counts_elapsed_days_not_plan_length(db_session):
    """P2-Q1: a plan created today with the exam in 14 days must report
    days_used=1 on day one (previously 15 = full plan length)."""
    start = datetime.combine(date.today(), time(hour=8))
    plan = Plan(
        user_id=uuid4(),
        name="15天计算机网络冲刺",
        target_date=date.today() + timedelta(days=14),
        created_at=start,
    )
    service = ExamSprintReviewService(db_session)

    assert service._compute_days_used(plan=plan, today=date.today()) == 1
    assert service._compute_days_used(plan=plan, today=date.today() + timedelta(days=4)) == 5
    # never exceeds the plan length even after the exam date
    assert service._compute_days_used(plan=plan, today=date.today() + timedelta(days=40)) == 15


def test_days_used_without_target_date_counts_elapsed_days(db_session):
    start = datetime.combine(date.today() - timedelta(days=3), time(hour=8))
    plan = Plan(user_id=uuid4(), name="无截止计划", target_date=None, created_at=start)
    service = ExamSprintReviewService(db_session)

    assert service._compute_days_used(plan=plan, today=date.today()) == 4


# ---------------------------------------------------------------------------
# BP-4 · P1-4：sprint 仪表盘与任务账本对账（NORTHSTAR-LOOP1 NS-001 形态）
# 现象：账本 completed=2 vs sprint-summary completed=0、total=4（实际更多）、
# current_score=0.0/delta=-42.0（无测量数据时以 0 充当真实分数）。
# ---------------------------------------------------------------------------


async def _seed_ns001_shape(db_session, *, user_id):
    """复刻 NS-001 账本形态：goal plan 里程碑卡（最新 plan）+ intake plan day 卡
    （完成在此）+ 手动无 plan 任务（完成在此）。"""
    now = _utcnow()
    goal_plan = Plan(
        user_id=user_id,
        name="离散数学期末 7 天冲刺：及格冲 70+",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=7),
        is_active=True,
        created_at=now - timedelta(minutes=1),
        updated_at=now - timedelta(minutes=1),
    )
    intake_plan = Plan(
        user_id=user_id,
        name="7天离散数学冲刺",
        type=PlanType.SPRINT,
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=7),
        is_active=True,
        created_at=now - timedelta(minutes=5),
        updated_at=now - timedelta(minutes=5),
    )
    db_session.add_all([goal_plan, intake_plan])
    await db_session.flush()

    milestones = [
        Task(
            user_id=user_id,
            plan=goal_plan,
            title=name,
            type=TaskType.LEARNING,
            tags=["goal_milestone"],
            estimated_minutes=25,
            difficulty=3,
            energy_cost=2,
            status=TaskStatus.PENDING,
        )
        for name in ("Map the baseline", "Repair the core gaps", "Timed practice loop", "Readiness check")
    ]
    intake_day_card = Task(
        user_id=user_id,
        plan=intake_plan,
        title="Day 1 · 诊断分诊 - 诊断分诊",
        type=TaskType.LEARNING,
        tags=["规划生成", "离散数学", "phase:1", "day:1"],
        estimated_minutes=55,
        difficulty=3,
        energy_cost=3,
        status=TaskStatus.COMPLETED,
        completed_at=now - timedelta(minutes=2),
    )
    manual_day_task = Task(
        user_id=user_id,
        plan_id=None,
        title="Day1 数理逻辑 I：命题逻辑复习 + 图论弱点预习",
        type=TaskType.TRAINING,
        tags=["NS-001", "day1", "discrete-math"],
        estimated_minutes=45,
        difficulty=3,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
        completed_at=now - timedelta(minutes=3),
    )
    db_session.add_all([*milestones, intake_day_card, manual_day_task])
    return goal_plan, intake_plan


@pytest.mark.asyncio
async def test_sprint_summary_task_stats_reconcile_with_task_ledger(db_session, test_user):
    """账本口径对账：total/completed 必须等于用户任务账本全集统计，
    跨 plan（intake day 卡）与无 plan（手动任务）的完成事件不得不可见。"""
    user_id = test_user.id
    goal_plan, _intake_plan = await _seed_ns001_shape(db_session, user_id=user_id)
    db_session.add(UserPreferencesCenter(user_id=user_id, explicit={"cold_start_context": {}}))
    await db_session.commit()

    # 账本权威口径（与 GET /api/v1/tasks 同域：该用户全部未删除任务）
    ledger = (
        (await db_session.execute(select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))))
        .scalars()
        .all()
    )
    ledger_total = len(ledger)
    ledger_completed = sum(1 for task in ledger if task.status == TaskStatus.COMPLETED)
    assert (ledger_total, ledger_completed) == (6, 2), "前置：账本形态应为 6 任务 2 完成"

    service = ExamSprintReviewService(db_session)
    response = await service.get_sprint_summary(user_id=user_id, plan_id=goal_plan.id)

    assert response.task_stats.total == ledger_total
    assert response.task_stats.completed == ledger_completed
    assert response.task_stats.completion_rate == round(ledger_completed / ledger_total, 4)
    # AI 叙事必须与账本地基一致（旧实现：「完成了 0 / 4 项任务」）
    assert f"完成了 {ledger_completed} / {ledger_total} 项任务" in response.narrative_highlights[0]
    assert f"完成了 {ledger_completed} 项任务" in response.headline


@pytest.mark.asyncio
async def test_sprint_summary_current_score_without_measurements_is_no_data_not_zero(db_session, test_user):
    """无任何 >0 掌握度测量时，current_score 必须是「暂无数据」（None）而非 0，
    也不得与基线做差产出虚假退步叙事（旧实现：0 - 42 = -42）。"""
    user_id = test_user.id
    goal_plan, _intake_plan = await _seed_ns001_shape(db_session, user_id=user_id)
    node = KnowledgeNode(
        id=uuid4(),
        name="命题逻辑",
        description="命题逻辑",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    # 仅「解锁未学习」形态：掌握度全 0（列非空默认），无任何测量信号
    db_session.add_all(
        [
            node,
            UserPreferencesCenter(
                user_id=user_id,
                explicit={"cold_start_context": {"estimated_score_now": 42}},
            ),
            UserNodeStatus(user_id=user_id, node_id=node.id, mastery_score=0.0),
        ]
    )
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.get_sprint_summary(user_id=user_id, plan_id=goal_plan.id)

    assert response.score_stats.baseline_score == 42.0
    assert response.score_stats.current_score is None
    assert response.score_stats.delta is None


@pytest.mark.asyncio
async def test_sprint_summary_current_score_uses_measurements_when_present(db_session, test_user):
    """对照：存在真实测量（>0 掌握度）时，current_score 正常计算差值。"""
    user_id = test_user.id
    goal_plan, _intake_plan = await _seed_ns001_shape(db_session, user_id=user_id)
    node = KnowledgeNode(
        id=uuid4(),
        name="图论基础",
        description="图论基础",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    node_zero = KnowledgeNode(
        id=uuid4(),
        name="数理逻辑",
        description="数理逻辑",
        importance_level=3,
        source_type="seed",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    db_session.add_all(
        [
            node,
            node_zero,
            UserPreferencesCenter(
                user_id=user_id,
                explicit={"cold_start_context": {"estimated_score_now": 42}},
            ),
            UserNodeStatus(user_id=user_id, node_id=node.id, mastery_score=65.0),
            UserNodeStatus(user_id=user_id, node_id=node_zero.id, mastery_score=0.0),
        ]
    )
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.get_sprint_summary(user_id=user_id, plan_id=goal_plan.id)

    assert response.score_stats.current_score == 65.0
    assert response.score_stats.delta == 23.0


@pytest.mark.asyncio
async def test_sprint_summary_daily_trend_sees_ledger_completions_in_window(db_session, test_user):
    """同族修：每日学习趋势回退统计不得按 plan 域收窄漏掉账本完成事件。"""
    user_id = test_user.id
    goal_plan, _intake_plan = await _seed_ns001_shape(db_session, user_id=user_id)
    db_session.add(UserPreferencesCenter(user_id=user_id, explicit={"cold_start_context": {}}))
    await db_session.commit()

    service = ExamSprintReviewService(db_session)
    response = await service.get_sprint_summary(user_id=user_id, plan_id=goal_plan.id)

    completed_day_minutes = sum(point.minutes for point in response.daily_study_trend)
    assert completed_day_minutes >= 45 + 55, "完成事件的预估时长应计入趋势（手动 45 + intake 卡 55）"
