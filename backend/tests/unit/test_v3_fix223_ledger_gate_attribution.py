"""V3-FIX-223 · executor 账本闸门失效归因分流——错误类型不再说谎.

危害定性（wt509 V3-FIX-217 探针钉住，本卡闭账）：
``_authorize_and_begin_call`` 账本开行 catch-all（executor.py 原 :595-601）把
一切开行失败统一伪装成 ``IdempotencyConflict``"Concurrent duplicate call"：
身份串非法（``uuid.UUID`` ValueError）与 DB 基建故障都被归因为"并发重复调用"，
排障方向被带偏；``_find_ledger_row`` 读失败 re-raise 把裸异常顶到直调面
（无 ToolResult 包裹）。

修法（fail-closed 不变，只换诚实归因）：
- 身份串非法 → ``InvalidUserIdentity``（参数错误类；
  FailureKind.VALIDATION_ERROR，不可重试）；
- 真并发同 (user, tool, key) 撞 ``uq_agent_tool_calls_idem`` 唯一索引 →
  ``IdempotencyConflict``（语义原样保留）；
- 其余开行/读故障（连接断、约束外的完整性错误等）→ ``LedgerUnavailable``
  （基建不可用类；FailureKind.TOOL_EXCEPTION，暂态可重试）；
- ``_find_ledger_row`` 读失败不再裸抛——闸门统一包装为 fail-closed ToolResult。

三类故障各自红→绿实录；真并发归因保留为绿回归（防分流误伤诚实路径）。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.failure_semantics import FailureKind
from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.executor import ToolExecutor, failure_kind_for_error_type
from app.tools.base import ToolCategory, ToolResult
from app.tools.metadata import canonical_args_hash


class _Params(BaseModel):
    title: str = "t"


class _StubReadTool:
    name = "stub_get_task"
    description = "stub read tool"
    category = ToolCategory.TASK
    parameters_schema = _Params
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "read"
    risk = "low"
    reversible = True
    required_permission = "task.read"
    cost_usd = 0.0

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


class _StubWriteTool:
    name = "stub_create_task"
    description = "stub write tool"
    category = ToolCategory.TASK
    parameters_schema = _Params
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "write"
    risk = "medium"
    reversible = True
    required_permission = "task.write"
    cost_usd = 0.0

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


@pytest.fixture
async def guard_db():
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


def _install_registry(monkeypatch, *, read: _StubReadTool | None = None, write: _StubWriteTool | None = None):
    tools = {}
    metadata = {}
    for tool in (read, write):
        if tool is not None:
            tools[tool.name] = tool
            metadata[tool.name] = SimpleNamespace(
                name=tool.name,
                effect=tool.effect,
                risk=tool.risk,
                reversible=tool.reversible,
                required_permission=tool.required_permission,
                cost_usd=0.0,
                is_side_effect=tool.effect == "write",
            )
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(
            get_tool=lambda name: tools.get(name),
            get_tool_metadata=lambda name: metadata.get(name),
        ),
    )


async def _ledger_rows(session) -> list[AgentToolCall]:
    return list((await session.execute(select(AgentToolCall))).scalars().all())


# ---------------------------------------------------------------------------
# 1. 身份串非法 → InvalidUserIdentity（参数错误类；不再伪装成并发冲突）
# ---------------------------------------------------------------------------


class TestIllegalIdentityAttribution:
    async def test_illegal_uid_read_tool_rejected_as_parameter_error(self, monkeypatch, guard_db):
        """红→绿：user_id 非法 + read 工具（无幂等键）→ InvalidUserIdentity。

        红（wt509 探针同型实录）：开行 catch-all 把 uuid 解析失败伪装成
        IdempotencyConflict"Concurrent duplicate call"——归因说谎。
        """
        tool = _StubReadTool()
        _install_registry(monkeypatch, read=tool)
        executor = ToolExecutor()
        result = await executor.execute_tool_call(tool.name, {"title": "x"}, "not-a-uuid", guard_db.session)
        assert result.success is False
        assert result.error_type == "InvalidUserIdentity"  # 参数错误类诚实归因
        assert result.error_type != "IdempotencyConflict"
        assert "Concurrent duplicate call" not in (result.error_message or "")
        assert tool.execute_count == 0  # fail-closed 不变
        assert await _ledger_rows(guard_db.session) == []  # 账本零开行

    async def test_illegal_uid_with_key_no_bare_raise(self, monkeypatch, guard_db):
        """红→绿：user_id 非法 + tool_call_id（幂等键）→ 不再裸抛 ValueError。

        红（wt509 探针②同型实录）：``_find_ledger_row`` uuid 解析失败裸抛到
        直调面（无 ToolResult 包裹）。
        """
        tool = _StubReadTool()
        _install_registry(monkeypatch, read=tool)
        executor = ToolExecutor()
        result = await executor.execute_tool_call(
            tool.name, {"title": "x"}, "not-a-uuid", guard_db.session, tool_call_id="c9"
        )
        assert isinstance(result, ToolResult)  # 直调面得到 ToolResult，非裸异常
        assert result.success is False
        assert result.error_type == "InvalidUserIdentity"
        assert tool.execute_count == 0
        assert await _ledger_rows(guard_db.session) == []

    async def test_illegal_uid_write_tool_with_explicit_key(self, monkeypatch, guard_db):
        """红→绿：非法身份 + write 工具显式幂等键 → 同型 InvalidUserIdentity（读账本先行路径）。"""
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        executor = ToolExecutor()
        result = await executor.execute_tool_call(
            tool.name, {"title": "x"}, "12345678-aaaa-bbbb-cccc-not-a-uuid", guard_db.session, idempotency_key="op-x"
        )
        assert result.success is False
        assert result.error_type == "InvalidUserIdentity"
        assert tool.execute_count == 0

    async def test_kind_map_identity_is_validation_error(self):
        """封闭映射：InvalidUserIdentity → VALIDATION_ERROR（确定性、不可重试）。"""
        assert failure_kind_for_error_type("InvalidUserIdentity") is FailureKind.VALIDATION_ERROR


# ---------------------------------------------------------------------------
# 2. DB/基建故障 → LedgerUnavailable（基建不可用类；不再伪装成并发冲突）
# ---------------------------------------------------------------------------


class TestInfraFailureAttribution:
    async def test_begin_flush_infra_failure_is_ledger_unavailable(self, monkeypatch, guard_db):
        """红→绿：开行 flush 连接故障 → LedgerUnavailable（原伪装 IdempotencyConflict）。"""
        tool = _StubReadTool()
        _install_registry(monkeypatch, read=tool)
        user = await _make_user(guard_db.session)

        async def _boom():
            raise OperationalError("INSERT", {}, Exception("server closed the connection unexpectedly"))

        guard_db.session.flush = _boom  # type: ignore[method-assign]
        executor = ToolExecutor()
        result = await executor.execute_tool_call(tool.name, {"title": "x"}, str(user.id), guard_db.session)
        assert result.success is False
        assert result.error_type == "LedgerUnavailable"
        assert result.error_type != "IdempotencyConflict"
        assert "Concurrent duplicate call" not in (result.error_message or "")
        assert tool.execute_count == 0
        assert await _ledger_rows(guard_db.session) == []

    async def test_ledger_read_failure_wrapped_fail_closed(self, monkeypatch, guard_db):
        """红→绿：账本读故障（execute 抛连接错）→ fail-closed ToolResult 不裸抛。"""
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        user = await _make_user(guard_db.session)

        async def _boom(*a, **kw):
            raise OperationalError("SELECT", {}, Exception("connection reset by peer"))

        original_execute = guard_db.session.execute
        guard_db.session.execute = _boom  # type: ignore[method-assign]
        executor = ToolExecutor()
        result = await executor.execute_tool_call(
            tool.name, {"title": "x"}, str(user.id), guard_db.session, tool_call_id="c1", idempotency_key="op-r"
        )
        guard_db.session.execute = original_execute  # type: ignore[method-assign]  # 还原后核对账本
        assert isinstance(result, ToolResult)  # 不再裸抛到直调面
        assert result.success is False
        assert result.error_type == "LedgerUnavailable"
        assert tool.execute_count == 0
        assert await _ledger_rows(guard_db.session) == []

    async def test_non_idem_integrity_error_is_infra_not_conflict(self, monkeypatch, guard_db):
        """红→绿：非幂等索引的完整性错误（如 FK）→ LedgerUnavailable，不冒充并发冲突。"""
        tool = _StubReadTool()
        _install_registry(monkeypatch, read=tool)
        user = await _make_user(guard_db.session)

        async def _boom():
            raise IntegrityError("INSERT", {}, Exception('violates foreign key constraint "other_fk"'))

        guard_db.session.flush = _boom  # type: ignore[method-assign]
        executor = ToolExecutor()
        result = await executor.execute_tool_call(tool.name, {"title": "x"}, str(user.id), guard_db.session)
        assert result.success is False
        assert result.error_type == "LedgerUnavailable"
        assert tool.execute_count == 0

    async def test_kind_map_ledger_unavailable_is_tool_exception(self):
        """封闭映射：LedgerUnavailable → TOOL_EXCEPTION（暂态族；side effect 未发生可重试）。"""
        assert failure_kind_for_error_type("LedgerUnavailable") is FailureKind.TOOL_EXCEPTION


# ---------------------------------------------------------------------------
# 3. 真并发冲突 → IdempotencyConflict 语义原样保留（防分流误伤诚实路径）
# ---------------------------------------------------------------------------


class TestTrueConcurrentConflictPreserved:
    async def test_unique_index_hit_keeps_idempotency_conflict(self, monkeypatch, guard_db):
        """绿回归：SELECT 与 flush 之间窗口内并发同 key 插入 → 保留 IdempotencyConflict。

        模拟竞态：同 key 行已在表里，但 ``_find_ledger_row`` 返回 None（另一
        事务尚未提交时读不到）→ 开行 flush 撞 ``uq_agent_tool_calls_idem``。
        """
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        user = await _make_user(guard_db.session)
        # 并发方已插入（模拟另一会话已开行；本会话 SELECT 因隔离看不到）
        guard_db.session.add(
            AgentToolCall(
                user_id=user.id,
                tool_name=tool.name,
                idempotency_key="op-race",
                args_hash="x" * 64,
                status="in_progress",
            )
        )
        await guard_db.session.commit()

        async def _miss(*a, **kw):
            return None  # 竞态窗口：账本查询未命中

        monkeypatch.setattr(ToolExecutor, "_find_ledger_row", staticmethod(_miss))
        executor = ToolExecutor()
        result = await executor.execute_tool_call(
            tool.name, {"title": "x"}, str(user.id), guard_db.session, tool_call_id="c1", idempotency_key="op-race"
        )
        assert result.success is False
        assert result.error_type == "IdempotencyConflict"  # 真并发冲突：归因语义不变
        assert "Concurrent duplicate call" in (result.error_message or "")
        assert tool.execute_count == 0

    async def test_read_path_in_progress_conflict_unchanged(self, monkeypatch, guard_db):
        """绿回归：读账本命中 in_progress 同 key → 原有 IdempotencyConflict 路径不变。"""
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        user = await _make_user(guard_db.session)
        guard_db.session.add(
            AgentToolCall(
                user_id=user.id,
                tool_name=tool.name,
                idempotency_key="op-live",
                args_hash=canonical_args_hash({"title": "x"}),
                status="in_progress",
            )
        )
        await guard_db.session.commit()
        executor = ToolExecutor()
        result = await executor.execute_tool_call(
            tool.name, {"title": "x"}, str(user.id), guard_db.session, tool_call_id="c2", idempotency_key="op-live"
        )
        assert result.success is False
        assert result.error_type == "IdempotencyConflict"
        assert tool.execute_count == 0
