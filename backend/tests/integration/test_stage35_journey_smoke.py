from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.consumers.galaxy_plan_consumer import GalaxyPlanConsumer
from app.consumers.user_profile_bootstrap_consumer import UserProfileBootstrapConsumer
from app.consumers.welcome_onboarding_consumer import WelcomeOnboardingConsumer
from app.core.cache import cache_service
from app.core.pending_actions import pending_actions_store
from app.models.base import Base
from app.models.galaxy import UserNodeStatus
from app.models.memory import MemoryGoal
from app.models.task import Task
from app.models.task_feedback import TaskFeedback
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter
from app.orchestration.plan_review_service import PlanReviewService
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.memory_service import MemoryService
from app.services.plan_service import PlanService
from app.services.profile_write_service import ProfileWriteService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.services.task_feedback_service import TaskFeedbackService
from app.services.task_service import TaskService
from scripts.journey_smoke.runner import (
    EventRecorder,
    RecordingRedis,
    assert_pubsub_message,
    assert_system_update,
    fail_for_hop,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class _SessionFactory:
    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

def _bind_consumer_session(monkeypatch, session) -> None:
    monkeypatch.setattr(
        "app.consumers.welcome_onboarding_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.user_profile_bootstrap_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.galaxy_plan_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )


async def _swallow_spawn(coro, **_kwargs) -> None:
    coro.close()


def _close_background_task(coro):
    coro.close()
    return SimpleNamespace(cancel=lambda: None)


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
async def test_stage35_journey_smoke_main_path(db_session, monkeypatch) -> None:
    fake_redis = RecordingRedis()
    events = EventRecorder()
    hop_order: list[str] = []

    monkeypatch.setattr(cache_service, "redis", fake_redis)
    monkeypatch.setattr("app.core.celery_app.celery_app.send_task", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.profile_write_service.MemoryService.upsert_preference", AsyncMock(return_value=None))
    pending_actions_store.set_redis(fake_redis)
    _bind_consumer_session(monkeypatch, db_session)

    monkeypatch.setattr("app.services.profile_write_service.event_bus.publish", events.publish)
    monkeypatch.setattr("app.services.task_service.event_bus.publish", events.publish)
    monkeypatch.setattr("app.services.task_feedback_service.event_bus.publish", events.publish)
    monkeypatch.setattr("app.orchestration.plan_review_service.event_bus.publish", events.publish)

    try:
        user = User(
            username="journey_stage35",
            email="journey_stage35@example.com",
            hashed_password="hashed",
            nickname="Journey",
            registration_source="email",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        user_pk = user.id
        user_id = str(user_pk)
        await events.publish(
            "user.registered",
            {
                "event_type": "user.registered",
                "user_id": user_id,
                "username": user.username,
                "registration_source": "email",
                "metadata": {
                    "nickname": user.nickname or user.username,
                    "default_community_permissions": {
                        "discoverable": True,
                        "allow_friend_requests": True,
                        "allow_group_invites": True,
                    },
                },
            },
        )
        user_event = events.pop("user.registered")
        assert user_event["user_id"] == user_id

        await WelcomeOnboardingConsumer(event_bus=object(), redis_client=fake_redis).handle_event(user_event)
        await UserProfileBootstrapConsumer(event_bus=object(), redis_client=fake_redis).handle_event(user_event)

        user_row = await db_session.get(User, user_pk)
        prefs = (
            await db_session.execute(
                select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_pk)
            )
        ).scalar_one()
        signup_update = await _drain_single_update(fake_redis, user_id, "welcome_onboarding")
        assert user_row is not None
        assert prefs.user_id == user_pk
        assert signup_update["category"] == "system"
        hop_order.append("signup")
    except AssertionError as exc:
        raise fail_for_hop("signup", str(exc))

    try:
        await ProfileWriteService(db_session, redis=None).set_explicit_preference(
            user_id=user_pk,
            pref_key="learning_goal_type",
            pref_value="exam",
            evidence_refs=[{"source": "journey_smoke"}],
            source_type="journey_smoke",
            source="journey_smoke",
        )
        goal_event = events.pop("profile.preference.updated")
        assert "learning_goal_type" in goal_event["pref_keys"]

        goal = await MemoryService(db_session).create_goal(
            user_id=user_pk,
            title="热力学第二章期中冲刺",
            target_date=(datetime.utcnow() + timedelta(days=14)).date(),
            source_type="journey_smoke",
        )
        goal_row = (
            await db_session.execute(select(MemoryGoal).where(MemoryGoal.user_id == user_pk))
        ).scalar_one()
        goal_update = await _drain_single_update(fake_redis, user_id, "memory_goal_created")
        assert goal is not None
        assert goal_row.title == "热力学第二章期中冲刺"
        assert goal_update["metadata"]["goal_id"] == str(goal.id)
        hop_order.append("goal")
    except AssertionError as exc:
        raise fail_for_hop("goal", str(exc))

    try:
        with (
            patch("app.services.plan_service._sync_plan_card_projection", AsyncMock()),
            patch("app.services.plan_quota_service.PlanQuotaService") as quota_service_cls,
        ):
            quota_service_cls.return_value.get_quota_status = AsyncMock(return_value=SimpleNamespace(used=0))
            plan = await PlanService.create(
                db=db_session,
                obj_in=PlanCreate(
                    name="Stage35 主旅程计划",
                    type="growth",
                    description="journey smoke",
                    daily_available_minutes=45,
                ),
                user_id=user_pk,
                skip_quota_check=True,
            )
        plan_event = events.pop("plan.created")
        assert plan_event["plan_id"] == str(plan.id)

        monkeypatch.setattr("app.core.task_manager.task_manager.spawn", _swallow_spawn)
        await GalaxyPlanConsumer(event_bus=object(), redis_client=None).handle_event(plan_event)
        node_rows = (
            await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == user_pk))
        ).scalars().all()
        await SystemUpdateService(fake_redis).enqueue(
            user_id,
            build_system_update(
                update_type="journey_plan_created",
                category="journey",
                title="学习计划已创建",
                description="主旅程 smoke 已记录计划创建 hop。",
                metadata={"plan_id": str(plan.id)},
            ),
        )
        plan_update = await _drain_single_update(fake_redis, user_id, "journey_plan_created")
        assert node_rows
        assert plan_update["metadata"]["plan_id"] == str(plan.id)
        hop_order.append("plan")
    except AssertionError as exc:
        raise fail_for_hop("plan", str(exc))

    try:
        with patch("app.services.task_service._sync_task_card_projection", AsyncMock()):
            task = await TaskService.create(
                db_session,
                TaskCreate(
                    title="完成第一道热力学错题",
                    type="error_fix",
                    plan_id=plan.id,
                    tags=["physics"],
                    estimated_minutes=25,
                    difficulty=2,
                    energy_cost=2,
                ),
                user_pk,
            )
            started_task = await TaskService.start_task(db_session, task.id, user_pk)
        started_event = events.pop("task.started")
        assert started_event["task_id"] == str(task.id)
        assert started_task.started_at is not None
        await SystemUpdateService(fake_redis).enqueue(
            user_id,
            build_system_update(
                update_type="journey_first_task_started",
                category="journey",
                title="第一步已经启动",
                description="主旅程 smoke 已记录 first-task hop。",
                metadata={"task_id": str(task.id)},
            ),
        )
        task_update = await _drain_single_update(fake_redis, user_id, "journey_first_task_started")
        assert task_update["metadata"]["task_id"] == str(task.id)
        hop_order.append("first-task")
    except AssertionError as exc:
        raise fail_for_hop("first-task", str(exc))

    try:
        with (
            patch("app.services.task_service._sync_task_card_projection", AsyncMock()),
            patch("app.services.plan_service.PlanService.update_progress", AsyncMock()),
        ):
            completed_task = await TaskService.complete_task(
                db_session,
                task.id,
                user_pk,
                actual_minutes=28,
                note="第一步已经打通了",
            )
        completed_event = events.pop("task.completed")
        assert completed_event["task_id"] == str(task.id)
        assert completed_task.completed_at is not None
        await SystemUpdateService(fake_redis).enqueue(
            user_id,
            build_system_update(
                update_type="journey_task_completed",
                category="journey",
                title="第一项任务已完成",
                description="主旅程 smoke 已记录 complete hop。",
                metadata={"task_id": str(task.id)},
            ),
        )
        complete_update = await _drain_single_update(fake_redis, user_id, "journey_task_completed")
        assert complete_update["metadata"]["task_id"] == str(task.id)
        hop_order.append("complete")
    except AssertionError as exc:
        raise fail_for_hop("complete", str(exc))

    try:
        with (
            patch("app.services.task_feedback_service.AdaptiveReplanner.on_task_feedback", AsyncMock()),
            patch(
                "app.services.task_feedback_service.TaskReflectionService.maybe_enqueue_reflection_prompt",
                AsyncMock(return_value=None),
            ),
        ):
            feedback, _ = await TaskFeedbackService(db_session, redis=None).submit_feedback(
                user_id=user_pk,
                task_id=task.id,
                completion_quality=4,
                feedback_text="我需要更轻一点的第一步",
                category="too_difficult",
            )
        feedback_event = events.pop("task.feedback_submitted")
        feedback_row = (
            await db_session.execute(select(TaskFeedback).where(TaskFeedback.id == feedback.id))
        ).scalar_one()
        await SystemUpdateService(fake_redis).enqueue(
            user_id,
            build_system_update(
                update_type="journey_feedback_recorded",
                category="journey",
                title="任务反馈已记录",
                description="主旅程 smoke 已记录 feedback hop。",
                metadata={"feedback_id": str(feedback.id)},
            ),
        )
        feedback_update = await _drain_single_update(fake_redis, user_id, "journey_feedback_recorded")
        assert feedback_event["feedback_id"] == str(feedback.id)
        assert feedback_row.feedback_text == "我需要更轻一点的第一步"
        assert feedback_update["metadata"]["feedback_id"] == str(feedback.id)
        hop_order.append("feedback")
    except AssertionError as exc:
        raise fail_for_hop("feedback", str(exc))

    try:
        with patch("app.orchestration.plan_review_service.asyncio.create_task", _close_background_task):
            service = PlanReviewService(redis_client=fake_redis)
            service.set_redis(fake_redis)
            replan_result = await service.trigger_replanning(
                str(plan.id),
                user_id,
                "把错题链路提前，并把第一步再降一点难度",
            )
        replan_event = events.pop("plan.replanned")
        pending_action = await pending_actions_store.get(replan_result["action_id"], user_id)
        replan_ws = assert_pubsub_message(
            fake_redis,
            channel=f"user:{user_id}:replan",
            expected_type="replan_requested",
        )
        assert replan_event["original_plan_id"] == str(plan.id)
        assert pending_action is not None
        assert replan_ws["original_plan_id"] == str(plan.id)
        hop_order.append("replan")
    except AssertionError as exc:
        raise fail_for_hop("replan", str(exc))

    assert hop_order == ["signup", "goal", "plan", "first-task", "complete", "feedback", "replan"]
