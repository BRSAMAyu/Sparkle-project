import os
import sys
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.cache import cache_service
from app.core.redis_utils import resolve_redis_password

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
APP_GEN_DIR = os.path.join(APP_DIR, "gen")
if APP_GEN_DIR not in sys.path:
    sys.path.insert(0, APP_GEN_DIR)

from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership  # noqa: F401
from app.models.achievement import Achievement, UserAchievement  # noqa: F401
from app.models.agent_run import AgentRun, AgentRunTransition  # noqa: F401 — X-05 run 脊柱
from app.models.action_proposal import ActionProposal, ActionProposalTransition  # noqa: F401 — X-03 command path
from app.models.agent_tool_call import AgentToolCall  # noqa: F401 — X-06 工具调用账本
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
from app.models.base import Base
from app.models.card_protocol import Card, CardEdge, InterventionRecord, PlanningArtifact, TaskOccurrence  # noqa: F401
from app.models.cognitive import BehaviorPattern, CognitiveFragment  # noqa: F401
from app.models.community import (  # noqa: F401
    Friendship,
    Group,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupType,
    PrivateMessage,
    UserBlock,
)
from app.models.context_pack import ContextBudgetProfile, ContextPackFeedback, ContextPackRun  # noqa: F401
from app.models.distilled_strategy_cache import DistilledStrategyCacheEntry  # noqa: F401
from app.models.document_chunks import DocumentChunk  # noqa: F401
from app.models.document_feedback import DocumentRetrievalFeedback  # noqa: F401
from app.models.event import TrackingEvent  # noqa: F401
from app.models.execution_audit_log import ExecutionAuditLog  # noqa: F401
from app.models.execution_schedule import ExecutionSchedule  # noqa: F401
from app.models.file_storage import StoredFile  # noqa: F401
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus  # noqa: F401
from app.models.intervention import InterventionRequest  # noqa: F401
from app.models.intervention_adaptive import (  # noqa: F401
    BehavioralOutcome,
    InterventionTemplate,
    PassiveSignal,
    ScaffoldingState,
)
from app.models.intervention_strategy_outcome import InterventionStrategyOutcome  # noqa: F401
from app.models.ltm_daily_snapshot import LtmDailySnapshot  # noqa: F401
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference, Scene  # noqa: F401
from app.models.memory_rank_policy import MemoryRankPolicy  # noqa: F401
from app.models.nightly_review import NightlyReview  # noqa: F401
from app.models.north_star_metrics import NorthStarMetricEvent  # noqa: F401
from app.models.notification import Notification, PushHistory  # noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.plan_execution_record import PlanExecutionRecord  # noqa: F401
from app.models.push_delivery_record import PushDeliveryRecord  # noqa: F401
from app.models.recommendation import RecommendationCache, UserItemInteraction  # noqa: F401
from app.models.report_snapshot import ReportSnapshot  # noqa: F401
from app.models.research_consent import ResearchConsentRecord  # noqa: F401
from app.models.response_feedback import ResponseFeedback  # noqa: F401
from app.models.session_completion import SessionCompletion  # noqa: F401
from app.models.shop import (  # noqa: F401
    ConsumableEffectType,
    ItemRarity,
    PhotonTransactionType,
    ShopItem,
    ShopItemType,
    ShopPurchase,
    UserConsumable,
)
from app.models.simulation_run import SimulationRun  # noqa: F401
from app.models.srl_phase_state import SRLPhaseStateRecord  # noqa: F401
from app.models.strategy_belief import StrategyBeliefSnapshot  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.task_feedback import TaskFeedback  # noqa: F401
from app.models.task_resources import TaskResourceLink  # noqa: F401
from app.models.theater_candidate_bundle import TheaterCandidateBundle  # noqa: F401
from app.models.theater_prediction import TheaterPrediction  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_memory_settings import UserMemorySettings  # noqa: F401
from app.models.user_preferences import UserPreferencesCenter  # noqa: F401
from app.models.user_push_opt_in import UserPushOptIn  # noqa: F401
from tests import _dbguard
from tests._credentials import (  # noqa: F401 — re-exported for legacy imports
    TEST_HASHED_PASSWORD,
    TEST_HY_API_KEY,
    TEST_INTERNAL_API_KEY,
    TEST_SF_API_KEY,
    TEST_XUNFEI_API_KEY,
    TEST_XUNFEI_API_SECRET,
    TEST_ZHIPU_API_KEY,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
# AUTH-FOLLOWUP：单测进程环境判据。cache_service 对三个安全前缀
# （token_blacklist:/session_revoked:/user_revoked_before:）在 Redis 缺席时禁用
# 本地兜底（AUTH-DEEP A-2 P1），豁免判据读 settings.ENVIRONMENT（见 cache.py
# _TESTING_ENVIRONMENTS）；测试进程在此显式置为 "test" 以保持既有单测行为。
settings.ENVIRONMENT = "test"

# V3-FIX-120（测试顺序/共享态隔离审计）：settings 是进程级单例，kill_switch 在
# Redis 缺席时 read_mode 回落 settings.AURORA_SRL_*——任何用例裸赋值这些属性都
# 会跨文件污染整个 SRL 族（CI 全量序实证：一处 mode=off 残留 → 24 例
# UNKNOWN/DID NOT RAISE）。此 autouse fixture 在每个用例后复位该族属性 +
# 清 cache_service 进程内本地缓存，作为单例治理兜底（对齐 fakeredis 注入+
# 哨兵恢复先例）；泄漏源本身已在对应用例内改为 monkeypatch 注入。
_SRL_KILL_SWITCH_SETTINGS_ATTRS = (
    "AURORA_SRL_MODE",
    "AURORA_SRL_TRACKER_MODE",
    "AURORA_SRL_BRIDGE_MODE",
    "AURORA_SRL_SCAFFOLDING_CONSUME_MODE",
    "AURORA_SRL_EVENT_LAG_P95_THRESHOLD_SECONDS",
    "AURORA_SRL_MISJUDGMENT_THRESHOLD",
    "AURORA_SRL_TRACKER_P95_MS_BUDGET",
    "AURORA_SRL_AGGREGATOR_TTL_SECONDS",
)
_ABSENT = object()


@pytest.fixture(autouse=True)
def _reset_srl_kill_switch_singleton_state():
    snapshot = {name: getattr(settings, name, _ABSENT) for name in _SRL_KILL_SWITCH_SETTINGS_ATTRS}
    cache_service._local_cache.clear()
    yield
    for name, value in snapshot.items():
        if value is _ABSENT:
            try:
                delattr(settings, name)
            except AttributeError:
                pass
        else:
            setattr(settings, name, value)
    cache_service._local_cache.clear()


# V3-FIX-120（同卡第二单例）：DynamicToolRegistry 是进程级单例（__new__ 恒返
# _instance），而 phase2_core/x06 等用例对它 clear_all + monkeypatch 假注册——
# CI 全量序实证：tests/test_phase2_core.py 的 registers_package_only_once 用假
# register_from_package 把 "app.tools" 记入 _registered_packages 但零真工具入册，
# 此后全进程 get_tool 恒 None（wt392_r2v3 5 例 "未知工具: retrieve_user_material"
# 即此）。此 autouse fixture 每用例前后对四份注册态做快照/原位恢复，治愈一切
# 注册表污染（工具实例是模块级对象，浅拷贝足够）。
@pytest.fixture(autouse=True)
def _restore_dynamic_tool_registry_singleton():
    from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

    registry = dynamic_tool_registry
    snapshot = (
        dict(registry._tools),
        dict(registry._tool_info),
        dict(registry._tool_metadata),
        set(registry._registered_packages),
    )
    yield
    tools, tool_info, tool_metadata, registered_packages = snapshot
    registry._tools.clear()
    registry._tools.update(tools)
    registry._tool_info.clear()
    registry._tool_info.update(tool_info)
    registry._tool_metadata.clear()
    registry._tool_metadata.update(tool_metadata)
    registry._registered_packages.clear()
    registry._registered_packages.update(registered_packages)
    # 关键配套：ToolRegistry 包装层的 _dynamic_registry 是**实例属性**（首次
    # _get_dynamic_registry 时 self.xxx= 落在单例上），一旦置位就不再 ensure——
    # 若快照是"首次注册前"的空态（首注册发生在某用例体内），只还原数据会把
    # 后续用例留在空注册表 + 记忆位已置的死局（probe 实证：f1_swept 过后
    # f1_active 恒 未知工具）。复位单例记忆位，下次访问按需重注册。
    from app.tools.registry import tool_registry as _tool_registry_wrapper

    _tool_registry_wrapper._dynamic_registry = None


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


TEST_REDIS_DB = int(os.getenv("TEST_REDIS_DB", "15"))


def _isolate_test_redis_db(raw_url: str) -> str:
    """HYGIENE-2：把测试用 redis URL 指到隔离 DB index（默认 db15）。

    旧实现直连 REDIS_URL（通常 db0）且 teardown ``flushdb()``——在主仓跑测试
    会清空 dev redis 的真实缓存/队列数据。现统一改写到专用测试 DB（可用
    ``TEST_REDIS_DB`` 覆盖），teardown 的 flushdb 只影响该隔离 DB。
    """
    parsed = urlparse(raw_url)
    return urlunparse(parsed._replace(path=f"/{TEST_REDIS_DB}"))


@pytest_asyncio.fixture(name="redis_client")
async def redis_client_fixture():
    """Create Redis client for integration tests (isolated DB index)."""
    redis_url = _normalize_test_redis_url(os.getenv("REDIS_URL", settings.REDIS_URL or "redis://localhost:6379/0"))
    redis_url = _isolate_test_redis_db(redis_url)
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
        await client.flushdb()  # 只 flush 隔离测试 DB（见 _isolate_test_redis_db）
    except Exception:
        pass
    if hasattr(client, "aclose"):
        await client.aclose()
    else:
        await client.close()


def pytest_configure(config):
    """TEST-DBGUARD 会话门：测试进程永不连接演示库（详见 tests/_dbguard.py）。

    - 显式配置（env / .env）的 DATABASE_URL 指向演示库（库名 == sparkle）→
      整个进程拒跑（UsageError，退出码 4），这是 2026-09 泔染事故的根因路径；
    - 裸 worktree（无 .env）由 POSTGRES_* 默认值构造出的同形 URL：密码为空必然
      认证失败，保持历史行为（仅打印提示），不拒跑、不改任何测试结果。
    """
    db_url = settings.DATABASE_URL or ""
    if not _dbguard.is_demo_db_url(db_url):
        return
    if _dbguard.explicit_db_config() and not _dbguard.allow_named_sparkle():
        raise pytest.UsageError(_dbguard.demo_guard_message(db_url, "backend/tests 会话门 (pytest_configure)"))
    note = "（CI 临时栈白名单开启，降级为告警）" if _dbguard.allow_named_sparkle() else "（无显式 DB 配置，默认构造串）"
    print("\n" + "!" * 78)
    print(f"TEST-DBGUARD 警告: 测试进程的 DATABASE_URL 指向演示库形状的串 {note}")
    print(_dbguard.demo_guard_message(db_url, "backend/tests 会话门 (pytest_configure)"))
    print("!" * 78)


def pytest_collection_modifyitems(config, items):
    perf_enabled = os.getenv("PERF_TESTS") == "1"
    for item in items:
        nodeid = item.nodeid
        if "tests/benchmark/" in nodeid and not perf_enabled:
            item.add_marker(pytest.mark.skip(reason="PERF_TESTS=1 required"))


def pytest_collection_finish(session):
    """TEST-HYGIENE：0-collected 防护（zsh 通配族「no tests ran」警示）。

    合并会话多次踩坑：zsh 通配不匹配/猜错测试文件名后，pytest 静默收集到
    0 个用例，退出码 5（no tests ran）容易被误读为「无事发生」。此处仅在
    收集结果为 0 时打印醒目定位提示；刻意空跑（如 -k 过滤全剔除）看到提示
    也无害——不改变任何退出码语义，CI 判定不受影响。
    """
    # pytest 9.x 里 session.testscollected 在本 hook 之后才赋值，取 session.items。
    if getattr(session, "items", None):
        return
    invocation_args = list(session.config.invocation_params.args or [])
    print("\n" + "=" * 78)
    print("WARNING: pytest collected 0 tests —— 本次运行没有收集到任何用例！")
    print(f"  invocation args: {invocation_args!r}")
    print("  提示：zsh 通配不匹配会静默失败；请先用 `rg --files -g 'test_*.py'`")
    print("  在 backend/tests/ 下确认真实文件名，再把确切路径传给 pytest。")
    print("  （本警示不改变退出码：no-tests 仍为退出码 5。）")
    print("=" * 78)
