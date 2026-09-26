"""V3-FIX-40 · 账本同事务缺口 —— notification/plan_state/persona 内部 commit 收编.

卡面缺陷（wt474 扫陈核实，位置双登记）：

- executor 账本开行（``AgentToolCall`` in_progress，flush 进**调用方事务**）与
  工具写入约定「同生共死」；
- 但 notification/plan_state/persona 服务路径存在**内部 ``db.commit()``**——
  工具执行中途把账本 in_progress 行与半截业务写**提前落库**：后续失败路径
  rollback 对已提交行无效 → 半状态可见 + 账本残留（X-09 两阶段只能把残留
  收敛为 interrupted / side_effect_state=unknown，同 key 重试须换新键）。

本文件锁定**同事务语义**：真实服务（非桩 commit）在 executor 工具路径里，
失败 ⇒ 业务写与账本行一起回滚——

- ``side_effect_state == "none"``（账本随事务回滚，无效果残留，可安全重试）；
- 业务表（plan_states / notifications / persona_snapshots）无半提交行；
- 账本无任何残留行。

另含独立调用路径的回归锁：无工具上下文时服务仍保持自带 commit（Celery/
路由等既有调用方零行为变化）。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.compliance import PersonaSnapshot
from app.models.notification import Notification
from app.models.plan_state import PlanState
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.executor import ToolExecutor
from app.schemas.notification import NotificationCreate
from app.services.notification_service import NotificationService
from app.services.persona_service import ProfileSnapshotService
from app.services.plan_state_service import PlanStateService
from app.tools.base import ToolCategory
from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel

# ---------------------------------------------------------------------------
# 桩：真实服务调用后引爆（模拟工具后半步失败）
# ---------------------------------------------------------------------------


class _Params(BaseModel):
    title: str = "t"


class _RealServiceExplodeTool:
    """side-effect 工具桩：先走**真实服务写路径**（内部 commit），再失败."""

    name = "stub_service_write"
    description = "real-service internal-commit tool"
    category = ToolCategory.TASK
    parameters_schema = _Params
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "write"
    risk = "medium"
    reversible = True
    required_permission = "task.write"
    cost_usd = 0.0

    def __init__(self, action):
        self.action = action
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        await self.action(db_session, user_id)
        raise RuntimeError("exploded after internal service commit")


_WRITE_METADATA = ToolMetadata(
    name="stub_service_write",
    effect=ToolEffect.WRITE,
    risk=ToolRiskLevel.MEDIUM,
    reversible=True,
    required_permission="task.write",
    cost_usd=0.0,
)


@pytest.fixture
async def ledger_db():
    """独立 sqlite 引擎（executor 账本 + run 权威/账本收敛会话工厂共用）."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield SimpleNamespace(session=session, factory=factory)
    finally:
        await session.close()
        await engine.dispose()


async def _make_user(session) -> User:
    user = User(id=uuid4(), username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@x.io", hashed_password="t")
    session.add(user)
    await session.commit()
    return user


def _install_registry(monkeypatch, *, tool):
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(
            get_tool=lambda name: tool if name == tool.name else None,
            get_tool_metadata=lambda name: _WRITE_METADATA if name == tool.name else None,
        ),
    )


async def _run_exploding_tool(monkeypatch, ledger_db, user: User, action, key: str):
    tool = _RealServiceExplodeTool(action)
    _install_registry(monkeypatch, tool=tool)
    monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
    monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)

    result = await ToolExecutor().execute_tool_call(
        tool.name,
        {"title": "a"},
        str(user.id),
        ledger_db.session,
        tool_call_id="c1",
        idempotency_key=key,
    )
    assert result.success is False
    assert result.error_type == "RuntimeError"
    return result


async def _fresh_counts(factory, model, **filters) -> int:
    async with factory() as fresh:
        stmt = select(model)
        for col, val in filters.items():
            stmt = stmt.where(getattr(model, col) == val)
        return len(list((await fresh.execute(stmt)).scalars().all()))


# ---------------------------------------------------------------------------
# 红测：业务写必须与账本行同生共死（真实服务内部 commit 收编）
# ---------------------------------------------------------------------------


class TestLedgerSameTransactionSemantics:
    async def test_plan_state_internal_commit_rolls_back_with_failure(self, monkeypatch, ledger_db):
        """plan_state：get_or_create 内部 commit 后工具失败 ⇒ 半状态不可见、
        账本无残留（side_effect_state=none，同 key 可安全重试）."""
        user = await _make_user(ledger_db.session)
        plan_id = uuid4()

        async def action(db, uid):
            await PlanStateService(db).get_or_create_plan_state(
                UUID(uid), plan_id, initial_facts={"difficulty_preference": 0.7}
            )

        result = await _run_exploding_tool(monkeypatch, ledger_db, user, action, "k-fix40-plan")

        assert result.side_effect_state == "none", "账本必须随事务回滚（而非中断残留）"
        assert await _fresh_counts(ledger_db.factory, PlanState, plan_id=plan_id) == 0, "半提交的业务写不可见"
        assert await _fresh_counts(ledger_db.factory, AgentToolCall) == 0, "账本不得残留 in_progress/interrupted 行"

    async def test_notification_internal_commit_rolls_back_with_failure(self, monkeypatch, ledger_db):
        """notification：create 内部 commit 后工具失败 ⇒ 通知行随事务回滚."""
        user = await _make_user(ledger_db.session)
        uid = user.id  # 先取值：executor 失败路径 rollback 会过期会话内 ORM 属性

        async def action(db, uid_):
            await NotificationService.create(
                db,
                UUID(uid_),
                NotificationCreate(title="t", content="c", type="reminder", data={}),
                push_via_websocket=False,
            )

        result = await _run_exploding_tool(monkeypatch, ledger_db, user, action, "k-fix40-notif")

        assert result.side_effect_state == "none"
        assert await _fresh_counts(ledger_db.factory, Notification, user_id=uid) == 0
        assert await _fresh_counts(ledger_db.factory, AgentToolCall) == 0

    async def test_persona_snapshot_internal_commit_rolls_back_with_failure(self, monkeypatch, ledger_db):
        """persona：_persist_snapshot 内部 commit 后工具失败 ⇒ 快照行随事务回滚."""
        user = await _make_user(ledger_db.session)
        uid = user.id  # 先取值：executor 失败路径 rollback 会过期会话内 ORM 属性

        async def action(db, uid_):
            await ProfileSnapshotService(db).build_profile_snapshot(UUID(uid_), "chat_style")

        result = await _run_exploding_tool(monkeypatch, ledger_db, user, action, "k-fix40-persona")

        assert result.side_effect_state == "none"
        assert await _fresh_counts(ledger_db.factory, PersonaSnapshot, user_id=uid) == 0
        assert await _fresh_counts(ledger_db.factory, AgentToolCall) == 0


# ---------------------------------------------------------------------------
# 回归锁：无工具上下文的独立调用保持自带 commit（既有调用方零行为变化）
# ---------------------------------------------------------------------------


class TestStandaloneCommitPreserved:
    async def test_plan_state_standalone_still_persists(self, ledger_db):
        """无 executor 上下文（Celery/路由形态）：服务自带 commit 照常落库."""
        user = await _make_user(ledger_db.session)
        plan_id = uuid4()
        async with ledger_db.factory() as standalone:
            await PlanStateService(standalone).get_or_create_plan_state(user.id, plan_id, initial_facts={"k": "v"})
        assert await _fresh_counts(ledger_db.factory, PlanState, plan_id=plan_id) == 1

    async def test_notification_standalone_still_persists(self, ledger_db):
        user = await _make_user(ledger_db.session)
        async with ledger_db.factory() as standalone:
            await NotificationService.create(
                standalone,
                user.id,
                NotificationCreate(title="t", content="c", type="reminder", data={}),
                push_via_websocket=False,
            )
        assert await _fresh_counts(ledger_db.factory, Notification, user_id=user.id) == 1

    async def test_persona_standalone_still_persists(self, ledger_db):
        user = await _make_user(ledger_db.session)
        async with ledger_db.factory() as standalone:
            await ProfileSnapshotService(standalone).build_profile_snapshot(user.id, "chat_style")
        assert await _fresh_counts(ledger_db.factory, PersonaSnapshot, user_id=user.id) == 1
