import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.plan import Plan  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.response_feedback import ResponseFeedback  # noqa: F401
from app.models.intervention import InterventionRequest  # noqa: F401
from app.models.nightly_review import NightlyReview  # noqa: F401
from app.models.memory import MemoryPreference, MemoryGoal, EpisodicMemory  # noqa: F401
from app.models.context_pack import ContextPackRun, ContextBudgetProfile, ContextPackFeedback  # noqa: F401
from app.models.memory_rank_policy import MemoryRankPolicy  # noqa: F401
from app.models.user_memory_settings import UserMemorySettings  # noqa: F401
from app.models.ltm_daily_snapshot import LtmDailySnapshot  # noqa: F401
from app.models.intervention_adaptive import (  # noqa: F401
    ScaffoldingState,
    PassiveSignal,
    BehavioralOutcome,
    InterventionTemplate,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(name="db_session")
async def db_session_fixture():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
