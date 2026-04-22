from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.cache import cache_service
from app.models.base import Base
from app.models.aurora_stage20 import RoutingDecisionLog
from app.models.card_protocol import InterventionRecord
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.schemas.error_book import ErrorRecordCreate, SubjectEnum
from app.services.error_book_service import ErrorBookService
from app.services.error_replan_bridge import ErrorReplanBridge
from app.services.system_update_service import SystemUpdateService, build_system_update
from scripts.journey_smoke.runner import EventRecorder, RecordingRedis, assert_system_update, fail_for_hop

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _seed_error_bridge_fixture(db_session) -> tuple[User, Plan, KnowledgeNode]:
    user = User(
        username="error_stage35",
        email="error_stage35@example.com",
        hashed_password="hashed",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="Stage35 错题旅程计划",
        type=PlanType.SPRINT,
        description="error smoke",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date() + timedelta(days=7),
        daily_available_minutes=60,
        total_estimated_hours=6,
        subject="physics",
        mastery_level=0.2,
        progress=0.0,
        is_active=True,
        priority=PlanPriority.HIGH,
        is_primary=True,
    )
    db_session.add(plan)
    await db_session.flush()

    node = KnowledgeNode(name="Entropy", description="node")
    db_session.add(node)
    await db_session.flush()

    db_session.add(
        UserNodeStatus(
            user_id=user.id,
            node_id=node.id,
            mastery_score=35,
            bkt_mastery_prob=0.35,
            total_minutes=0,
            total_study_minutes=0,
            study_count=0,
            is_unlocked=True,
        )
    )
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title="Bridge task",
        type=TaskType.ERROR_FIX,
        tags=["physics"],
        estimated_minutes=20,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.PENDING,
        priority=3,
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
    await db_session.commit()
    return user, plan, node


async def _drain_single_update(redis_client: RecordingRedis, user_id: str, expected_type: str) -> dict:
    updates = await SystemUpdateService(redis_client).drain(user_id, limit=20)
    for item in updates:
        if item.get("type") == expected_type:
            return assert_system_update(item, expected_type=expected_type)
    raise AssertionError(f"Missing system update `{expected_type}`")


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_stage35_error_journey_smoke(db_session, monkeypatch) -> None:
    fake_redis = RecordingRedis()
    events = EventRecorder()
    hop_order: list[str] = []

    monkeypatch.setattr(cache_service, "redis", fake_redis)

    user, plan, node = await _seed_error_bridge_fixture(db_session)
    bridge = ErrorReplanBridge(db_session, redis=fake_redis)

    try:
        error = await ErrorBookService(db_session).create_error(
            user.id,
            ErrorRecordCreate(
                subject=SubjectEnum.PHYSICS,
                chapter="thermodynamics",
                question_text="Entropy question",
                user_answer="I confused state variables",
                correct_answer="Entropy increases in isolated systems",
                cognitive_tags=["analysis"],
                ai_analysis_summary="concept gap",
            ),
        )
        error.latest_analysis = {"error_type": "concept_confusion"}
        error.linked_knowledge_node_ids = [str(node.id)]
        await db_session.commit()
        await db_session.refresh(error)

        await events.publish(
            "error_created",
            {
                "event_type": "error_created",
                "user_id": str(user.id),
                "error_id": str(error.id),
                "linked_node_ids": [str(node.id)],
            },
        )
        error_event = events.pop("error_created")
        await SystemUpdateService(fake_redis).enqueue(
            str(user.id),
            build_system_update(
                update_type="journey_error_captured",
                category="journey",
                title="错题已记录",
                description="错题子旅程 smoke 已记录 error-created hop。",
                metadata={"error_id": str(error.id)},
            ),
        )
        error_update = await _drain_single_update(fake_redis, str(user.id), "journey_error_captured")
        stored_error = await db_session.get(ErrorRecord, error.id)
        assert error_event["error_id"] == str(error.id)
        assert stored_error is not None
        assert error_update["metadata"]["error_id"] == str(error.id)
        hop_order.append("error-created")
    except AssertionError as exc:
        raise fail_for_hop("error-created", str(exc))

    try:
        with patch(
            "app.services.error_replan_bridge.AuroraStage34KillSwitchService.get_feature_mode",
            new=AsyncMock(return_value="shadow"),
        ):
            shadow_result = await bridge.on_error_created(
                user_id=user.id,
                error_id=error.id,
                linked_node_ids=[UUID(str(node.id))],
            )
        await events.publish(
            "error.bridge_evaluated",
            {
                "event_type": "error.bridge_evaluated",
                "user_id": str(user.id),
                "error_id": str(error.id),
                "mode": "shadow",
                "triggered": shadow_result["triggered"],
            },
        )
        shadow_event = events.pop("error.bridge_evaluated")
        shadow_log = (
            await db_session.execute(
                select(RoutingDecisionLog).where(
                    RoutingDecisionLog.user_id == user.id,
                    RoutingDecisionLog.decision_type == "stage34_error_replan_bridge_shadow",
                )
            )
        ).scalar_one()
        await SystemUpdateService(fake_redis).enqueue(
            str(user.id),
            build_system_update(
                update_type="journey_error_replan_evaluated",
                category="journey",
                title="错题重规划已评估",
                description="错题子旅程 smoke 已记录 shadow 评估 hop。",
                metadata={"triggered": bool(shadow_result["triggered"])},
            ),
        )
        shadow_update = await _drain_single_update(fake_redis, str(user.id), "journey_error_replan_evaluated")
        assert shadow_event["triggered"] is False
        assert shadow_log is not None
        assert shadow_update["metadata"]["triggered"] is False
        hop_order.append("replan-evaluated")
    except AssertionError as exc:
        raise fail_for_hop("replan-evaluated", str(exc))

    try:
        with (
            patch(
                "app.services.error_replan_bridge.AuroraStage34KillSwitchService.get_feature_mode",
                new=AsyncMock(return_value="live"),
            ),
            patch(
                "app.services.error_replan_bridge.AdaptiveReplanner.evaluate_plan_health_now",
                new=AsyncMock(),
            ),
        ):
            live_result = await bridge.on_error_created(
                user_id=user.id,
                error_id=error.id,
                linked_node_ids=[UUID(str(node.id))],
            )
        await events.publish(
            "error.bridge_triggered",
            {
                "event_type": "error.bridge_triggered",
                "user_id": str(user.id),
                "plan_id": str(plan.id),
                "triggered": live_result["triggered"],
            },
        )
        live_event = events.pop("error.bridge_triggered")
        intervention = (
            await db_session.execute(
                select(InterventionRecord).where(InterventionRecord.user_id == user.id)
            )
        ).scalar_one()
        live_update = await _drain_single_update(fake_redis, str(user.id), "plan_adjusted_from_error")
        assert live_event["triggered"] is True
        assert intervention is not None
        assert live_update["metadata"]["trigger"] == "error_replan_bridge"
        hop_order.append("replan-triggered")
    except AssertionError as exc:
        raise fail_for_hop("replan-triggered", str(exc))

    assert hop_order == ["error-created", "replan-evaluated", "replan-triggered"]
