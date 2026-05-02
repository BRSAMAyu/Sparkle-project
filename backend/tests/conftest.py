import os
from urllib.parse import urlparse, urlunparse
import pytest
import pytest_asyncio
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.config import settings
from app.core.redis_utils import resolve_redis_password

from app.models.base import Base
from app.models.plan import Plan  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.response_feedback import ResponseFeedback  # noqa: F401
from app.models.report_snapshot import ReportSnapshot  # noqa: F401
from app.models.intervention import InterventionRequest  # noqa: F401
from app.models.nightly_review import NightlyReview  # noqa: F401
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference, Scene  # noqa: F401
from app.models.context_pack import ContextPackRun, ContextBudgetProfile, ContextPackFeedback  # noqa: F401
from app.models.memory_rank_policy import MemoryRankPolicy  # noqa: F401
from app.models.user_memory_settings import UserMemorySettings  # noqa: F401
from app.models.ltm_daily_snapshot import LtmDailySnapshot  # noqa: F401
from app.models.event import TrackingEvent  # noqa: F401
from app.models.plan_execution_record import PlanExecutionRecord  # noqa: F401
from app.models.execution_audit_log import ExecutionAuditLog  # noqa: F401
from app.models.execution_schedule import ExecutionSchedule  # noqa: F401
from app.models.card_protocol import Card, CardEdge, TaskOccurrence, PlanningArtifact, InterventionRecord  # noqa: F401
from app.models.user_preferences import UserPreferencesCenter  # noqa: F401
from app.models.recommendation import RecommendationCache, UserItemInteraction  # noqa: F401
from app.models.intervention_adaptive import (  # noqa: F401
    ScaffoldingState,
    PassiveSignal,
    BehavioralOutcome,
    InterventionTemplate,
)
from app.models.intervention_strategy_outcome import InterventionStrategyOutcome  # noqa: F401
from app.models.distilled_strategy_cache import DistilledStrategyCacheEntry  # noqa: F401
from app.models.document_chunks import DocumentChunk  # noqa: F401
from app.models.document_feedback import DocumentRetrievalFeedback  # noqa: F401
from app.models.file_storage import StoredFile  # noqa: F401
from app.models.task_feedback import TaskFeedback  # noqa: F401
from app.models.session_completion import SessionCompletion  # noqa: F401
from app.models.srl_phase_state import SRLPhaseStateRecord  # noqa: F401
from app.models.north_star_metrics import NorthStarMetricEvent  # noqa: F401
from app.models.notification import Notification, PushHistory  # noqa: F401
from app.models.push_delivery_record import PushDeliveryRecord  # noqa: F401
from app.models.aurora_stage20 import (  # noqa: F401
    AuroraJudgmentRecord,
    ConflictResolutionRecord,
    RoutingDecisionLog,
    UnresolvedConflict,
)
from app.models.aurora_stage21 import SharedSkill, SkillShareModerationQueue, UserSkill  # noqa: F401
from app.models.aurora_stage27 import PersDynAttractor  # noqa: F401
from app.models.aurora_stage31 import (  # noqa: F401
    DailyBehaviorVector,
    IdiographicAssociation,
    IdiographicChangepoint,
)
from app.models.user_push_opt_in import UserPushOptIn  # noqa: F401
from app.models.galaxy import KnowledgeNode, UserNodeStatus, StudyRecord  # noqa: F401
from app.models.community import (  # noqa: F401
    Group,
    GroupMember,
    GroupMessage,
    PrivateMessage,
    Friendship,
    GroupType,
    GroupRole,
    UserBlock,
)
from app.models.accountability import AccountabilityPartnership, AccountabilityCheckin  # noqa: F401
from app.models.achievement import Achievement, UserAchievement  # noqa: F401
from app.models.cognitive import BehaviorPattern, CognitiveFragment  # noqa: F401
from app.models.shop import (  # noqa: F401
    ShopItem,
    ShopPurchase,
    UserConsumable,
    PhotonTransactionType,
    ShopItemType,
    ItemRarity,
    ConsumableEffectType,
)
from app.models.simulation_run import SimulationRun  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Centralized mock credentials for tests — never use real keys in test code.
TEST_INTERNAL_API_KEY = "test-internal-api-key"
TEST_ZHIPU_API_KEY = "test-zhipu-api-key"
TEST_SF_API_KEY = "test-sf-api-key"
TEST_XUNFEI_API_KEY = "test-xunfei-api-key"
TEST_XUNFEI_API_SECRET = "test-xunfei-api-secret"
TEST_HASHED_PASSWORD = "hashed"


def _normalize_test_redis_url(raw_url: str) -> str:
    """Normalize docker-internal redis host to localhost for host-side test runs."""
    parsed = urlparse(raw_url)
    hostname = parsed.hostname
    if hostname != "sparkle_redis":
        return raw_url

    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth = f"{auth}:{parsed.password}"
        auth = f"{auth}@"
    elif parsed.password:
        auth = f":{parsed.password}@"

    port = f":{parsed.port}" if parsed.port else ""
    return urlunparse(parsed._replace(netloc=f"{auth}127.0.0.1{port}"))


_runtime_redis_url = os.getenv("REDIS_URL", settings.REDIS_URL or "redis://localhost:6379/0")
_runtime_redis_url = _normalize_test_redis_url(_runtime_redis_url)
os.environ["REDIS_URL"] = _runtime_redis_url
settings.REDIS_URL = _runtime_redis_url


@pytest_asyncio.fixture(name="db_session")
async def db_session_fixture():
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


@pytest_asyncio.fixture(name="db")
async def db_fixture(db_session: AsyncSession) -> AsyncSession:
    return db_session


@pytest_asyncio.fixture(name="test_user")
async def test_user_fixture(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(username="testuser", email="test@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(name="test_shop_items")
async def test_shop_items_fixture(db_session: AsyncSession) -> list[ShopItem]:
    """Create test shop items"""
    items = [
        ShopItem(
            id="skin_common_001",
            name="Common Skin",
            description="A common skin",
            item_type="skin",
            category="galaxy_skin",
            price_photons=100,
            rarity="common",
            is_available=True,
            is_limited=False,
            sort_order=10,
        ),
        ShopItem(
            id="skin_rare_001",
            name="Rare Skin",
            description="A rare skin",
            item_type="skin",
            category="galaxy_skin",
            price_photons=250,
            rarity="rare",
            is_available=True,
            is_limited=False,
            sort_order=5,
        ),
        ShopItem(
            id="consumable_boost_001",
            name="EXP Boost",
            description="Double experience for 1 hour",
            item_type="consumable",
            category="exp_boost",
            price_photons=150,
            rarity="rare",
            is_available=True,
            is_limited=True,
            stock_quantity=10,
            sort_order=3,
            item_config={"effect_type": "exp_boost", "duration_hours": 1, "multiplier": 2},
        ),
        ShopItem(
            id="title_legendary_001",
            name="Legendary Title",
            description="A legendary title",
            item_type="title",
            category="achievement_title",
            price_photons=500,
            rarity="legendary",
            is_available=True,
            is_limited=False,
            sort_order=1,
            item_config={"text": "Legendary Learner", "color": "#FFD700"},
        ),
    ]
    for item in items:
        db_session.add(item)
    await db_session.commit()
    return items


@pytest_asyncio.fixture(name="redis_client")
async def redis_client_fixture():
    """Create Redis client for integration tests."""
    redis_url = _normalize_test_redis_url(os.getenv("REDIS_URL", settings.REDIS_URL or "redis://localhost:6379/0"))
    password, _ = resolve_redis_password(redis_url, os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD))
    client = redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        password=password,
    )
    try:
        await client.ping()
    except Exception as exc:
        if hasattr(client, "aclose"):
            await client.aclose()
        else:
            await client.close()
        pytest.skip(f"Redis unavailable for integration fixture: {exc}")
    yield client

    try:
        await client.flushdb()
    except Exception:
        pass
    if hasattr(client, "aclose"):
        await client.aclose()
    else:
        await client.close()


def pytest_collection_modifyitems(config, items):
    perf_enabled = os.getenv("PERF_TESTS") == "1"
    for item in items:
        nodeid = item.nodeid
        if "tests/benchmark/" in nodeid and not perf_enabled:
            item.add_marker(pytest.mark.skip(reason="PERF_TESTS=1 required"))
