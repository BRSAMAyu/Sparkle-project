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
from app.models.event import TrackingEvent  # noqa: F401
from app.models.plan_execution_record import PlanExecutionRecord  # noqa: F401
from app.models.user_preferences import UserPreferencesCenter  # noqa: F401
from app.models.intervention_adaptive import (  # noqa: F401
    ScaffoldingState,
    PassiveSignal,
    BehavioralOutcome,
    InterventionTemplate,
)
from app.models.task_feedback import TaskFeedback  # noqa: F401
from app.models.community import (  # noqa: F401
    Group, GroupMember, GroupMessage, PrivateMessage,
    Friendship, GroupType, GroupRole
)
from app.models.shop import (  # noqa: F401
    ShopItem, ShopPurchase, UserConsumable,
    PhotonTransactionType, ShopItemType, ItemRarity, ConsumableEffectType
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


@pytest_asyncio.fixture(name="test_user")
async def test_user_fixture(db_session: AsyncSession) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        photon_balance=0
    )
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
            item_type=ShopItemType.SKIN,
            category="galaxy_skin",
            price_photons=100,
            rarity=ItemRarity.COMMON,
            is_available=True,
            is_limited=False,
            sort_order=10,
        ),
        ShopItem(
            id="skin_rare_001",
            name="Rare Skin",
            description="A rare skin",
            item_type=ShopItemType.SKIN,
            category="galaxy_skin",
            price_photons=250,
            rarity=ItemRarity.RARE,
            is_available=True,
            is_limited=False,
            sort_order=5,
        ),
        ShopItem(
            id="consumable_boost_001",
            name="EXP Boost",
            description="Double experience for 1 hour",
            item_type=ShopItemType.CONSUMABLE,
            category="exp_boost",
            price_photons=150,
            rarity=ItemRarity.RARE,
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
            item_type=ShopItemType.TITLE,
            category="achievement_title",
            price_photons=500,
            rarity=ItemRarity.LEGENDARY,
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
