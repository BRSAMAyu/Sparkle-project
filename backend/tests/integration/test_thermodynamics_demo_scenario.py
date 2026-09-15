from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.card_protocol import Card, CardCreatedBy, CardLifecycleStatus, CardSourceType, CardType
from app.models.error_book import ErrorRecord
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.orchestration.prompts import build_system_prompt
from app.services.error_replan_bridge import ErrorReplanBridge
from app.services.growth_dashboard_service import GrowthDashboardService
from app.services.weekly_digest_service import WeeklyDigestService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_thermodynamics_demo_story_flows_from_error_pressure_to_growth_digest(db_session):
    user = User(
        username="thermo_demo_user",
        email="thermo_demo_user@example.com",
        hashed_password="hashed",
        nickname="Ava",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="热力学两周冲刺",
        type=PlanType.SPRINT,
        description="考试前查漏补缺",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=14),
        daily_available_minutes=100,
        total_estimated_hours=24,
        subject="热力学",
        mastery_level=0.38,
        progress=0.35,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    plan_card = Card(
        card_type=CardType.PLAN,
        owner_id=user.id,
        holder_id=user.id,
        lifecycle_status=CardLifecycleStatus.ACTIVE,
        source_type=CardSourceType.ORIGINAL,
        created_by=CardCreatedBy.AI,
        updated_by=CardCreatedBy.AI,
        metadata_={"legacy_plan_id": str(plan.id), "name": plan.name},
    )
    db_session.add(plan_card)
    await db_session.flush()

    node = KnowledgeNode(
        name="可逆过程 vs 不可逆过程",
        description="热力学第二章核心混淆点",
    )
    db_session.add(node)
    await db_session.flush()

    status = UserNodeStatus(
        user_id=user.id,
        node_id=node.id,
        mastery_score=38,
        bkt_mastery_prob=0.38,
        total_minutes=0,
        total_study_minutes=0,
        study_count=0,
        is_unlocked=True,
    )
    db_session.add(status)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="区分可逆与不可逆过程",
        type=TaskType.LEARNING,
        tags=["thermodynamics"],
        estimated_minutes=35,
        difficulty=4,
        energy_cost=3,
        status=TaskStatus.PENDING,
        priority=5,
        due_date=datetime.utcnow().date() + timedelta(days=1),
        knowledge_node_id=node.id,
    )
    db_session.add(task)
    await db_session.flush()

    db_session.add(
        TaskKnowledgeLink(
            task_id=task.id,
            knowledge_node_id=node.id,
            relation_type="prerequisite",
            is_primary=True,
        )
    )

    errors = [
        ErrorRecord(
            user_id=user.id,
            subject_code="physics",
            chapter="thermodynamics",
            question_text=f"thermo-error-{idx}",
            mastery_level=0.2,
            latest_analysis={"error_type": "concept_confusion"},
            linked_knowledge_node_ids=[str(node.id)],
            created_at=datetime.utcnow() - timedelta(days=idx),
        )
        for idx in range(3)
    ]
    db_session.add_all(errors)
    await db_session.commit()

    bridge = ErrorReplanBridge(db_session)
    with patch(
        "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
        new=AsyncMock(),
    ) as mock_eval:
        bridge_result = await bridge.on_error_created(
            user_id=user.id,
            error_id=errors[-1].id,
            linked_node_ids=[node.id],
        )

    assert bridge_result["triggered"] is True
    mock_eval.assert_awaited_once()

    status.mastery_score = 61
    status.bkt_mastery_prob = 0.61
    db_session.add(
        StudyRecord(
            user_id=user.id,
            node_id=node.id,
            record_type="error_review",
            study_minutes=25,
            mastery_delta=23,
            created_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow() - timedelta(hours=3)
    task.actual_minutes = 30
    db_session.add(
        FocusSession(
            user_id=user.id,
            task_id=task.id,
            start_time=datetime.utcnow() - timedelta(hours=4),
            end_time=datetime.utcnow() - timedelta(hours=3, minutes=25),
            duration_minutes=35,
            focus_type=FocusType.POMODORO,
            status=FocusStatus.COMPLETED,
        )
    )
    next_task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="整理可逆过程错题",
        type=TaskType.ERROR_FIX,
        tags=["thermodynamics"],
        estimated_minutes=20,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=4,
        due_date=datetime.utcnow().date() + timedelta(days=2),
        knowledge_node_id=node.id,
    )
    db_session.add(next_task)
    await db_session.commit()

    snapshot = await GrowthDashboardService(db_session).build_snapshot(user.id, user=user)
    assert snapshot["growth_signal"]["topic"] == "可逆过程 vs 不可逆过程"
    assert "0.38" in snapshot["growth_signal"]["headline"]
    assert "0.61" in snapshot["growth_signal"]["headline"]
    assert snapshot["most_important_task"]["title"] == "整理可逆过程错题"

    digest_service = WeeklyDigestService(db_session, redis=None)
    digest_service.weekly_report_service.build_weekly_report = AsyncMock(
        return_value={
            "weekly_summary": "你在热力学第二章上的卡点明显松动了。",
            "one_key_adjustment": "我会继续把高难任务前移到上午。",
            "top_learning_items": [{"text": "可逆过程概念更稳了"}],
        }
    )
    digest_service.stats_service.get_weekly_summary = AsyncMock(
        return_value={
            "tasks_completed": 1,
            "focus_duration_minutes": 35,
            "active_days": 1,
            "mastery_gain": 23.0,
            "nodes_learned": 1,
        }
    )
    digest = await digest_service.generate_for_user(user_id=user.id, deliver=False)

    assert digest is not None
    assert digest["headline"].startswith("Ava")
    assert "热力学第二章上的卡点明显松动了" in digest["summary"]
    assert digest["whats_coming"][0] == "整理可逆过程错题"

    prompt = build_system_prompt(
        user_context={
            "user_context": {"nickname": "Ava"},
            "active_goals": [{"title": "两周内稳住热力学第二章"}],
            "learning_gaps_summary": "热力学第二定律相关概念仍然容易混淆。今天先补这块。",
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.7},
            "cognitive_insights": {
                "top_patterns": [{"pattern_name": "概念回避"}],
            },
        },
        conversation_history={"messages": []},
        plan_context={
            "plan_title": plan.name,
            "plan_stage": "冲刺阶段",
            "goal": "掌握热力学第二章",
        },
    )
    assert "你是 Sparkle，Ava 的学习成长伙伴。" in prompt
    assert "两周内稳住热力学第二章" in prompt
    assert "热力学第二定律相关概念仍然容易混淆" in prompt
