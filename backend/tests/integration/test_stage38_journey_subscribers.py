from __future__ import annotations

from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.consumers.achievement_plan_consumer import AchievementPlanConsumer
from app.consumers.plan_task_generation_consumer import PlanTaskGenerationConsumer
from app.consumers.user_memory_seed_consumer import UserMemorySeedConsumer
from app.consumers.user_profile_bootstrap_consumer import UserProfileBootstrapConsumer
from app.consumers.welcome_onboarding_consumer import WelcomeOnboardingConsumer
from app.models.base import Base
from app.models.memory import EpisodicMemory
from app.models.plan import Plan, PlanType
from app.models.user import User
from app.services.system_update_service import SystemUpdateService


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class RecordingRedis:
    def __init__(self) -> None:
        self.store: dict[str, list[str]] = {}

    def pipeline(self):
        return _RecordingPipeline(self)

    async def lpush(self, key: str, value: str) -> int:
        bucket = self.store.setdefault(key, [])
        bucket.insert(0, value)
        return len(bucket)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        bucket = self.store.setdefault(key, [])
        if end == -1:
            self.store[key] = bucket[start:]
        else:
            self.store[key] = bucket[start : end + 1]

    async def expire(self, key: str, seconds: int) -> None:
        return None

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        bucket = self.store.get(key, [])
        if end == -1:
            return bucket[start:]
        return bucket[start : end + 1]


class _RecordingPipeline:
    def __init__(self, redis_client: RecordingRedis) -> None:
        self.redis = redis_client
        self.ops: list[tuple[str, tuple]] = []

    def lpush(self, key: str, value: str):
        self.ops.append(("lpush", (key, value)))
        return self

    def ltrim(self, key: str, start: int, end: int):
        self.ops.append(("ltrim", (key, start, end)))
        return self

    def expire(self, key: str, seconds: int):
        self.ops.append(("expire", (key, seconds)))
        return self

    def lrange(self, key: str, start: int, end: int):
        self.ops.append(("lrange", (key, start, end)))
        return self

    async def execute(self):
        results = []
        for op, args in self.ops:
            results.append(await getattr(self.redis, op)(*args))
        self.ops.clear()
        return results


class _SessionFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
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


def _bind_consumer_session(monkeypatch: pytest.MonkeyPatch, session: AsyncSession) -> None:
    monkeypatch.setattr(
        "app.consumers.welcome_onboarding_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.user_profile_bootstrap_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.user_memory_seed_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.achievement_plan_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.plan_task_generation_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )
    monkeypatch.setattr(
        "app.consumers.galaxy_plan_consumer.AsyncSessionLocal",
        lambda: _SessionFactory(session),
    )


@pytest.mark.asyncio
async def test_journey_user_registered_subscribers_cover_profile_welcome_and_memory(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_consumer_session(monkeypatch, db_session)
    fake_redis = RecordingRedis()

    pref_bootstrap = AsyncMock()
    profile_bootstrap = AsyncMock()
    monkeypatch.setattr(
        "app.consumers.user_profile_bootstrap_consumer.PreferenceService.get_preferences",
        pref_bootstrap,
    )
    monkeypatch.setattr(
        "app.consumers.user_profile_bootstrap_consumer.ProfileContextService.get_profile_context",
        profile_bootstrap,
    )

    user = User(
        id=uuid4(),
        username="journey_stage38",
        email="journey_stage38@example.com",
        hashed_password="hashed",
        nickname="Journey",
    )
    db_session.add(user)
    await db_session.commit()

    event = {
        "event_type": "user.registered",
        "user_id": str(user.id),
        "username": user.username,
        "metadata": {"nickname": user.nickname},
    }

    await WelcomeOnboardingConsumer(event_bus=object(), redis_client=fake_redis).handle_event(event)
    await UserProfileBootstrapConsumer(event_bus=object(), redis_client=fake_redis).handle_event(event)
    await UserMemorySeedConsumer(event_bus=object(), redis_client=fake_redis).handle_event(event)

    pref_bootstrap.assert_awaited_once()
    profile_bootstrap.assert_awaited_once()

    updates = await SystemUpdateService(fake_redis).drain(str(user.id), limit=20)
    assert any(item.get("type") == "welcome_onboarding" for item in updates)

    memories = (
        (await db_session.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == user.id))).scalars().all()
    )
    assert len(memories) == 1
    assert "完成注册" in memories[0].summary


@pytest.mark.asyncio
async def test_journey_plan_created_subscribers_cover_generation_and_achievement(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_consumer_session(monkeypatch, db_session)

    async def capture_spawn(coro, *args, **kwargs):
        coro.close()
        return None

    spawn = AsyncMock(side_effect=capture_spawn)
    achievement = AsyncMock()
    galaxy_seed = AsyncMock()
    monkeypatch.setattr("app.consumers.plan_task_generation_consumer.task_manager.spawn", spawn)
    monkeypatch.setattr("app.consumers.achievement_plan_consumer.AchievementEngine.process_event", achievement)
    monkeypatch.setattr("app.consumers.galaxy_plan_consumer.GalaxyBootstrapService.seed_from_goal", galaxy_seed)

    user = User(
        id=uuid4(),
        username="plan_stage38",
        email="plan_stage38@example.com",
        hashed_password="hashed",
    )
    plan = Plan(
        id=uuid4(),
        user_id=user.id,
        name="Stage38 Plan",
        type=PlanType.GROWTH,
        description="journey",
        daily_available_minutes=45,
        is_active=True,
    )
    db_session.add(user)
    db_session.add(plan)
    await db_session.commit()

    event = {
        "event_type": "plan.created",
        "user_id": str(user.id),
        "plan_id": str(plan.id),
    }

    from app.consumers.galaxy_plan_consumer import GalaxyPlanConsumer

    await AchievementPlanConsumer(event_bus=object(), redis_client=None).handle_event(event)
    await PlanTaskGenerationConsumer(event_bus=object(), redis_client=None).handle_event(event)
    await GalaxyPlanConsumer(event_bus=object(), redis_client=None).handle_event(event)

    achievement.assert_awaited_once()
    spawn.assert_awaited_once()
    galaxy_seed.assert_awaited_once()
