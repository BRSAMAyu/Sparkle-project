from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.consumers.achievement_plan_consumer import AchievementPlanConsumer
from app.consumers.galaxy_plan_consumer import GalaxyPlanConsumer
from app.consumers.user_profile_bootstrap_consumer import UserProfileBootstrapConsumer
from app.consumers.welcome_onboarding_consumer import WelcomeOnboardingConsumer
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.user import User


class _SessionFactory:
    def __init__(self, session: Any) -> None:
        self._session = session

    async def __aenter__(self) -> Any:
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
    monkeypatch.setattr(
        "app.consumers.achievement_plan_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )


async def _swallow_spawn(coro, **_kwargs) -> None:
    coro.close()


@pytest.mark.asyncio
async def test_welcome_onboarding_consumer_happy_path(db_session, monkeypatch) -> None:
    user = User(username="journey_user", email="journey@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.commit()
    _bind_consumer_session(monkeypatch, db_session)

    enqueue = AsyncMock(return_value=True)
    monkeypatch.setattr("app.consumers.welcome_onboarding_consumer.SystemUpdateService.enqueue", enqueue)

    consumer = WelcomeOnboardingConsumer(event_bus=object(), redis_client=object())
    await consumer.handle_event(
        {
            "event_type": "user.registered",
            "user_id": str(user.id),
            "username": user.username,
            "metadata": {"nickname": "小火花"},
        }
    )

    payload = enqueue.await_args.args[-1]
    assert payload["type"] == "welcome_onboarding"
    assert "小火花" in payload["description"]


@pytest.mark.asyncio
async def test_welcome_onboarding_consumer_error_path_emits_system_update(monkeypatch) -> None:
    enqueue = AsyncMock(return_value=True)
    consumer = WelcomeOnboardingConsumer(event_bus=object(), redis_client=object())
    monkeypatch.setattr(consumer, "_process_event", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr("app.consumers.journey_consumer_base.SystemUpdateService.enqueue", enqueue)

    await consumer.handle_event(
        {
            "event_type": "user.registered",
            "user_id": "00000000-0000-0000-0000-000000000123",
        }
    )

    payload = enqueue.await_args.args[-1]
    assert payload["type"] == "journey_consumer_error"
    assert payload["metadata"]["consumer"] == "WelcomeOnboardingConsumer"


@pytest.mark.asyncio
async def test_user_profile_bootstrap_consumer_happy_path(db_session, monkeypatch) -> None:
    user = User(username="bootstrap_user", email="bootstrap@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.commit()
    _bind_consumer_session(monkeypatch, db_session)

    consumer = UserProfileBootstrapConsumer(event_bus=object(), redis_client=None)
    await consumer.handle_event(
        {
            "event_type": "user.registered",
            "user_id": str(user.id),
        }
    )

    from app.models.user_preferences import UserPreferencesCenter
    from sqlalchemy import select

    prefs = (await db_session.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user.id))).scalar_one()
    assert prefs.user_id == user.id


@pytest.mark.asyncio
async def test_user_profile_bootstrap_consumer_error_path_emits_system_update(monkeypatch) -> None:
    enqueue = AsyncMock(return_value=True)
    consumer = UserProfileBootstrapConsumer(event_bus=object(), redis_client=object())
    monkeypatch.setattr(consumer, "_process_event", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr("app.consumers.journey_consumer_base.SystemUpdateService.enqueue", enqueue)

    await consumer.handle_event(
        {
            "event_type": "user.registered",
            "user_id": "00000000-0000-0000-0000-000000000124",
        }
    )

    assert enqueue.await_args.args[-1]["metadata"]["consumer"] == "UserProfileBootstrapConsumer"


@pytest.mark.asyncio
async def test_galaxy_plan_consumer_happy_path_bootstraps_when_user_has_no_nodes(db_session, test_user, monkeypatch) -> None:
    _bind_consumer_session(monkeypatch, db_session)
    monkeypatch.setattr("app.core.task_manager.task_manager.spawn", _swallow_spawn)
    plan = Plan(
        user_id=test_user.id,
        name="热力学起步",
        type=PlanType.SPRINT,
        description="first",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date(),
        daily_available_minutes=60,
        total_estimated_hours=4,
        subject="physics",
        mastery_level=0.1,
        progress=0.0,
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.commit()

    consumer = GalaxyPlanConsumer(event_bus=object(), redis_client=None)
    await consumer.handle_event(
        {
            "event_type": "plan.created",
            "user_id": str(test_user.id),
            "plan_id": str(plan.id),
        }
    )

    from app.models.galaxy import UserNodeStatus
    from sqlalchemy import select

    rows = (await db_session.execute(select(UserNodeStatus).where(UserNodeStatus.user_id == test_user.id))).scalars().all()
    assert rows


@pytest.mark.asyncio
async def test_galaxy_plan_consumer_error_path_emits_system_update(monkeypatch) -> None:
    enqueue = AsyncMock(return_value=True)
    consumer = GalaxyPlanConsumer(event_bus=object(), redis_client=object())
    monkeypatch.setattr(consumer, "_process_event", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr("app.consumers.journey_consumer_base.SystemUpdateService.enqueue", enqueue)

    await consumer.handle_event(
        {
            "event_type": "plan.created",
            "user_id": "00000000-0000-0000-0000-000000000125",
            "plan_id": "00000000-0000-0000-0000-000000000225",
        }
    )

    assert enqueue.await_args.args[-1]["metadata"]["consumer"] == "GalaxyPlanConsumer"


@pytest.mark.asyncio
async def test_achievement_plan_consumer_happy_path_updates_progress(db_session, test_user, monkeypatch) -> None:
    from app.data.achievement_seeds import INITIAL_ACHIEVEMENTS
    from app.models.achievement import Achievement, UserAchievement
    from sqlalchemy import select

    _bind_consumer_session(monkeypatch, db_session)
    for payload in INITIAL_ACHIEVEMENTS:
        if payload["id"] == "plan_first":
            db_session.add(
                Achievement(
                    id=payload["id"],
                    name=payload["name"],
                    description=payload["description"],
                    icon_url=payload["icon_url"],
                    type=payload["type"],
                    rarity=payload["rarity"],
                    trigger_code=payload["trigger_code"],
                    trigger_config=payload["trigger_config"],
                    category=payload["category"],
                    sort_order=payload["sort_order"],
                    reward_config=payload["reward_config"],
                )
            )
    plan = Plan(
        user_id=test_user.id,
        name="第一份计划",
        type=PlanType.GROWTH,
        description="first",
        plan_stage=PlanStage.DAILY,
        target_date=datetime.utcnow().date(),
        daily_available_minutes=60,
        total_estimated_hours=6,
        subject="math",
        mastery_level=0.1,
        progress=0.0,
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.commit()

    consumer = AchievementPlanConsumer(event_bus=object(), redis_client=None)
    await consumer.handle_event(
        {
            "event_type": "plan.created",
            "user_id": str(test_user.id),
            "plan_id": str(plan.id),
        }
    )

    progress = (
        await db_session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == test_user.id,
                UserAchievement.achievement_id == "plan_first",
            )
        )
    ).scalar_one()
    assert progress.progress >= 1.0


@pytest.mark.asyncio
async def test_achievement_plan_consumer_error_path_emits_system_update(monkeypatch) -> None:
    enqueue = AsyncMock(return_value=True)
    consumer = AchievementPlanConsumer(event_bus=object(), redis_client=object())
    monkeypatch.setattr(consumer, "_process_event", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr("app.consumers.journey_consumer_base.SystemUpdateService.enqueue", enqueue)

    await consumer.handle_event(
        {
            "event_type": "plan.created",
            "user_id": "00000000-0000-0000-0000-000000000126",
            "plan_id": "00000000-0000-0000-0000-000000000226",
        }
    )

    assert enqueue.await_args.args[-1]["metadata"]["consumer"] == "AchievementPlanConsumer"
