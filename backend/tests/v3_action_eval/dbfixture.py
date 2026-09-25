"""X-10 · 逐场景真实 DB fixture（独立于 pytest conftest 的自足引擎工厂）.

纪律（卡面红线「禁止 mock 冒充」）：
- 真实服务层（TaskService / ActionCommandService / AgentRunService / outcome
  capture+ledger）直接构造，**不 mock、不 stub**；
- DB = sqlite+aiosqlite 内存引擎 + ``Base.metadata.create_all`` 真实 schema
  （pytest conftest ``db_session`` 同款形态），另补 ``event_outbox`` /
  ``event_sequence_counters`` 两张 outbox 表（与既有 run/proposal 测试同法——
  这两张表在 ORM metadata 之外，生产由迁移建立）；
- 零 LLM：不配置任何 LLM 依赖；allocation 语义层默认关闭
  （``SPARKLE_ALLOCATION_SEMANTIC_ENABLED=False``，settings 默认值，不 override）；
- worktree 无 .env：密钥等仅经 ``SECRET_KEY`` 环境变量注入（settings test 约定）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "x10-eval-test-key")
# 事件总线是无 Redis 环境下的 best-effort 广播（账本读模型才是真相面）；
# 零重试只去掉退避 sleep，失败语义不变（log + 返回 None），评测不被拖慢。
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base

# 模型注册面（与 tests/conftest.py 同款：import 才进 Base.metadata，否则 FK 解析缺表）
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
from app.models.task import Task, TaskStatus, TaskType  # noqa: F401
from app.models.task_feedback import TaskFeedback  # noqa: F401
from app.models.task_resources import TaskResourceLink  # noqa: F401
from app.models.theater_candidate_bundle import TheaterCandidateBundle  # noqa: F401
from app.models.theater_prediction import TheaterPrediction  # noqa: F401
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings  # noqa: F401
from app.models.user_preferences import UserPreferencesCenter  # noqa: F401
from app.models.user_push_opt_in import UserPushOptIn  # noqa: F401
from app.models.user_settings import UserSettings

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

#: outbox 两表（与 test_x04/test_hybrid_run_steps 同款最小 DDL；sqlite 方言）。
_OUTBOX_DDL = (
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id VARCHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        payload JSON NOT NULL,
        metadata JSON,
        sequence_number INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        published_at DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mastery_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id VARCHAR(36),
        user_id VARCHAR(36),
        old_mastery FLOAT,
        new_mastery FLOAT,
        reason VARCHAR(255),
        request_id VARCHAR(64),
        revision INTEGER,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class ScenarioContext:
    """一个场景的执行上下文（独立 DB + 主用户 + cost 记录器）。"""

    session: AsyncSession
    user: User
    session_factory: Any = None  # async_sessionmaker（冷启动读面用：新 session 模拟新进程）
    service_ops: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def record_op(self, name: str) -> None:
        self.service_ops += 1
        self.extras.setdefault("ops", []).append(name)

    def fresh_session(self) -> AsyncSession:
        """新 session（同引擎）：模拟冷启动/新进程的持久化推导读面。"""
        if self.session_factory is None:
            return self.session
        return self.session_factory()


class ScenarioDB:
    """per-scenario 引擎生命周期（create_all → session → drop_all）。"""

    def __init__(self) -> None:
        self._engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    async def __aenter__(self) -> "ScenarioDB":
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            for ddl in _OUTBOX_DDL:
                await conn.execute(text(ddl))
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self._engine.dispose()

    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)

    async def new_context(self, *, auto_grant: bool = False) -> ScenarioContext:
        """建主用户（可选授予低风险自动权限）→ 返回场景上下文。

        P-04 起完整预授权 = 总开关（UserSettings.low_risk_auto_execute）∧ 类别级
        allowlist（UserPreferencesCenter.explicit 的 grant/revoke 面）。auto_grant
        语义随授权模型升级：同时授予全部 auto-eligible 类别，保持场景
        auth_z01「用户已授予自动权限 → 低风险可逆操作 inline 执行」的判题口径
        不变（auth_z02 无授权/auth_z03 不可逆目标仍照原样走 confirmation）。
        """
        factory = self.session_factory()
        session = factory()
        user_id = uuid4()
        user = User(
            id=user_id,
            username=f"x10_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@x10.eval",
            hashed_password="x10",
        )
        session.add(user)
        if auto_grant:
            session.add(UserSettings(user_id=user_id, low_risk_auto_execute=True))
        await session.commit()
        if auto_grant:
            from app.services.action_permission_service import ActionPermissionService

            permissions = ActionPermissionService(session)
            for category in ("task.update_status", "task.update_fields"):
                await permissions.grant_category(user_id, category)
        await session.refresh(user)
        return ScenarioContext(session=session, user=user, session_factory=factory)


async def seed_task(
    ctx: ScenarioContext,
    spec: dict[str, Any] | None,
) -> Task | None:
    """按场景 seed 规格建任务（真实 ORM 行；时间偏移换算真实时间戳）。"""
    if spec is None:
        return None
    now = _utcnow()
    started_at = None
    offset = spec.get("started_at_offset_min")
    if offset is not None:
        started_at = now + timedelta(minutes=float(offset))
    knowledge_node_id = ctx.extras.pop("_knowledge_node_id", None)
    task = Task(
        user_id=ctx.user.id,
        title=str(spec.get("title") or "X-10 task"),
        type=TaskType(spec.get("type") or "PLANNING"),
        tags=["x10"],
        estimated_minutes=int(spec.get("estimated_minutes") or 30),
        difficulty=2,
        energy_cost=1,
        status=TaskStatus(spec.get("status") or "PENDING"),
        started_at=started_at,
        completion_evidence=spec.get("completion_evidence"),
        knowledge_node_id=spec.get("with_knowledge_node") and knowledge_node_id or None,
    )
    ctx.session.add(task)
    await ctx.session.commit()
    await ctx.session.refresh(task)
    return task


async def backdate_proposal_expiry(ctx: ScenarioContext, proposal_id: Any, seconds: int) -> None:
    """时钟注入：把 proposal.expires_at 回拨（过期语义的时间模拟，真实 sweep 同一谓词）。"""
    past = _utcnow() - timedelta(seconds=seconds)
    from sqlalchemy import update

    from app.models.action_proposal import ActionProposal

    await ctx.session.execute(
        update(ActionProposal).where(ActionProposal.id == proposal_id).values(expires_at=past)
    )
    await ctx.session.commit()
