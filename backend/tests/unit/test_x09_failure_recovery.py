"""X-09 · 失败/取消/未知结局/恢复 —— 执行链 chaos 契约测试.

覆盖卡面验收（20+ chaos cases；变异必红锚点）：

- **FIX-40 P2-3（内部 commit 工具收编）**：工具中途 commit（模拟 persona/
  plan_state/theater 服务的内部 db.commit()）后超时/异常 → 账本两阶段收敛为
  interrupted + side_effect_state=unknown；同 key 重放恒拒（IdempotencyInterrupted，
  duplicate side effect=0）；干净回滚路径（无内部 commit）side_effect_state=none；
- **FIX-40 P3-6（budget 切断循环）**：批量循环/DAG 循环在 BUDGET_EXCEEDED 后
  不再发起后续工具调用；
- **重试策略**：暂态 read 失败按退避重试至成功（派生键开新账本行）；PERMANENT
  /UNKNOWN 不重试；耗尽 → 死信；
- **部分完成语义**：terminalize_execution_failure 物化 result_ref（succeeded/
  compensation hints；写进度 → PARTIAL；CANCELLED 保留用户归因）；
- **主动恢复**：recover_inflight_runs 的证据驱动裁决（interrupted 账本 →
  UNKNOWN_OUTCOME；intent 终态 → 漂移修复；无证据 → reattach 建议）+ 幂等；
- **API 可见性**：GET /runs/{id}/tool-calls 暴露账本明细与部分完成证据。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.failure_semantics import (
    DEFAULT_MAX_RETRY_ATTEMPTS,
    classify_execution_failure,
)
from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.executor import ToolExecutor
from app.tools.base import ToolCategory, ToolResult
from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel

# ---------------------------------------------------------------------------
# 测试桩（全五元数据显式；registry 注入走 monkeypatch SimpleNamespace）
# ---------------------------------------------------------------------------


class _Params(BaseModel):
    title: str = "t"


class _StubWriteTool:
    """side-effect 工具桩：可选「中途 commit 账本」模拟内部 commit 服务."""

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

    def __init__(self, *, commit_midway: bool = False, hang: bool = False, raise_after_commit: bool = False):
        self.execute_count = 0
        self.commit_midway = commit_midway
        self.hang = hang
        self.raise_after_commit = raise_after_commit

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        if self.commit_midway and db_session is not None:
            # 模拟 persona/plan_state/theater 服务的内部 db.commit()：
            # 把 executor 已 flush 的账本 in_progress 行提前落库。
            await db_session.commit()
        if self.hang:
            await asyncio.sleep(30)  # 触发 executor asyncio.wait_for 超时
        if self.raise_after_commit:
            raise RuntimeError("exploded after internal commit")
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"title": params.title})


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

    def __init__(self, fail_times: int = 0):
        self.execute_count = 0
        self.fail_times = fail_times

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        if self.execute_count <= self.fail_times:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_type="ConnectionResetError",
                error_message="network partition blip",
            )
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


_WRITE_METADATA = ToolMetadata(
    name="stub_create_task",
    effect=ToolEffect.WRITE,
    risk=ToolRiskLevel.MEDIUM,
    reversible=True,
    required_permission="task.write",
    cost_usd=0.0,
)
_READ_METADATA = ToolMetadata(
    name="stub_get_task",
    effect=ToolEffect.READ,
    risk=ToolRiskLevel.LOW,
    reversible=True,
    required_permission="task.read",
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


def _install_registry(monkeypatch, *, write=None, read=None):
    tools, metadata = {}, {}
    if write is not None:
        tools[write.name] = write
        metadata[write.name] = _WRITE_METADATA
    if read is not None:
        tools[read.name] = read
        metadata[read.name] = _READ_METADATA
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(get_tool=lambda name: tools.get(name), get_tool_metadata=lambda name: metadata.get(name)),
    )


async def _ledger_rows(session, *, user_id=None, factory=None) -> list[AgentToolCall]:
    """读账本真值：优先新会话裸读（绕过调用方会话的 identity map 陈旧残影
    ——两阶段收敛由独立会话提交，同会话对象不自动失效）."""
    if factory is not None:
        async with factory() as fresh:
            stmt = select(AgentToolCall).order_by(AgentToolCall.created_at.asc())
            if user_id is not None:
                stmt = stmt.where(AgentToolCall.user_id == user_id)
            return list((await fresh.execute(stmt)).scalars().all())
    stmt = select(AgentToolCall).order_by(AgentToolCall.created_at.asc())
    if user_id is not None:
        stmt = stmt.where(AgentToolCall.user_id == user_id)
    return list((await session.execute(stmt)).scalars().all())


async def _make_run(session, user: User, *, status=RunStatus.RUNNING, budget=None, intent=None, **extra) -> AgentRun:
    run = AgentRun(
        user_id=user.id,
        objective="chaos run",
        status=status,
        budget=budget,
        intent_id=intent.id if intent is not None else None,
        heartbeat_at=datetime.now(UTC).replace(tzinfo=None),
        **extra,
    )
    session.add(run)
    await session.commit()
    return run


async def _make_ledger_row(
    session, user: User, run: AgentRun | None, *, status="in_progress", started_at=None, tool="stub_create_task"
) -> AgentToolCall:
    row = AgentToolCall(
        user_id=user.id,
        run_id=run.id if run is not None else None,
        tool_name=tool,
        idempotency_key=f"key-{uuid4().hex[:8]}",
        args_hash="x" * 64,
        status=status,
        started_at=started_at or datetime.now(UTC).replace(tzinfo=None),
    )
    session.add(row)
    await session.commit()
    return row


def _stub_registry_with(monkeypatch, *tool_names: str):
    """给 ledger 证据物化喂确定性的 registry 元数据（write/reversible=True）.

    全局 tool_registry 单例可能被并发套件 clear——部分完成证据测试不依赖
    全局注册表状态（生产注册表启动即装满，这里钉死测试所需元数据）。
    """
    from app.tools import registry as registry_module
    from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel

    metadata = {
        name: ToolMetadata(
            name=name,
            effect=ToolEffect.WRITE,
            risk=ToolRiskLevel.MEDIUM,
            reversible=True,
            required_permission="plan.write",
            cost_usd=0.0,
        )
        for name in tool_names
    }
    monkeypatch.setattr(
        registry_module,
        "tool_registry",
        SimpleNamespace(get_tool=lambda n: None, get_tool_metadata=lambda n: metadata.get(n)),
    )


# ---------------------------------------------------------------------------
# A. FIX-40 P2-3 · 内部 commit 工具的账本两阶段收敛
# ---------------------------------------------------------------------------


class TestLedgerTwoPhaseResolution:
    async def test_timeout_with_internal_commit_resolves_interrupted(self, monkeypatch, ledger_db):
        """[chaos] 工具中途 commit 后超时（kill 语义）：账本 in_progress →
        interrupted；结果携带 side_effect_state=unknown（不假装知道效果）."""
        user = await _make_user(ledger_db.session)
        tool = _StubWriteTool(commit_midway=True, hang=True)
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "settings", SimpleNamespace(TOOL_EXECUTION_TIMEOUT_SECONDS=0.2))

        result = await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c1",
            idempotency_key="k1",
        )
        assert result.success is False
        assert result.error_type == "TimeoutError"
        assert result.side_effect_state == "unknown"

        rows = await _ledger_rows(ledger_db.session, user_id=user.id, factory=ledger_db.factory)
        assert len(rows) == 1
        assert rows[0].status == "interrupted"
        assert rows[0].finished_at is not None
        assert rows[0].error_type == "TimeoutError"

    async def test_exception_after_internal_commit_resolves_interrupted(self, monkeypatch, ledger_db):
        """[chaos] 工具 commit 后抛异常：同一两阶段收敛（key 不再永久中毒）."""
        user = await _make_user(ledger_db.session)
        tool = _StubWriteTool(commit_midway=True, raise_after_commit=True)
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)

        result = await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c1",
            idempotency_key="k2",
        )
        assert result.success is False
        assert result.error_type == "RuntimeError"
        assert result.side_effect_state == "unknown"
        rows = await _ledger_rows(ledger_db.session, user_id=user.id, factory=ledger_db.factory)
        assert rows[0].status == "interrupted"

    async def test_clean_rollback_reports_none(self, monkeypatch, ledger_db):
        """[chaos] 无内部 commit 的超时：账本随事务回滚 → side_effect_state=none
        （可安全自动重试——账本无行，无效果残留）."""
        user = await _make_user(ledger_db.session)
        uid = str(user.id)
        tool = _StubWriteTool(hang=True)  # 不中途 commit
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "settings", SimpleNamespace(TOOL_EXECUTION_TIMEOUT_SECONDS=0.2))

        result = await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c1",
            idempotency_key="k3",
        )
        assert result.side_effect_state == "none"
        rows = await _ledger_rows(ledger_db.session, user_id=uid, factory=ledger_db.factory)
        assert rows == []  # 行随事务回滚

    async def test_interrupted_key_replay_refused_forever(self, monkeypatch, ledger_db):
        """[chaos] interrupted 账本行的同 key 重放恒拒（duplicate side effect=0）；
        错误显式声明「换新键」而非含糊冲突."""
        user = await _make_user(ledger_db.session)
        tool = _StubWriteTool(commit_midway=True, raise_after_commit=True)
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)

        first = await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c1",
            idempotency_key="k4",
        )
        assert first.side_effect_state == "unknown"
        replay = await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c2",
            idempotency_key="k4",
        )
        assert replay.success is False
        assert replay.error_type == "IdempotencyInterrupted"
        assert "NEW idempotency key" in replay.error_message
        assert tool.execute_count == 1  # 效果不可核实 → 绝不重执行

    async def test_new_key_after_interruption_executes_fresh_attempt(self, monkeypatch, ledger_db):
        """[chaos] 换新键 = 显式重试决策：执行新账本行（attempt 历史，非去重）."""
        user = await _make_user(ledger_db.session)
        tool = _StubWriteTool()  # 第二次正常成功
        tool.commit_midway = True
        tool.raise_after_commit = True
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)

        await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c1",
            idempotency_key="k5",
        )
        # 修复"故障"后用新键重试
        tool.raise_after_commit = False
        tool.commit_midway = False
        second = await ToolExecutor().execute_tool_call(
            tool.name,
            {"title": "a"},
            str(user.id),
            ledger_db.session,
            tool_call_id="c2",
            idempotency_key="k5-retry-1",
        )
        assert second.success is True
        assert tool.execute_count == 2
        # owns_session=False：executor 不代提交（生产由调用方事务提交）——此处
        # 模拟调用方 commit 后再验账本终值。
        await ledger_db.session.commit()
        rows = await _ledger_rows(ledger_db.session, user_id=user.id, factory=ledger_db.factory)
        assert [r.status for r in rows] == ["interrupted", "succeeded"]


# ---------------------------------------------------------------------------
# B. FIX-40 P3-6 · budget 终态切断循环
# ---------------------------------------------------------------------------


class TestBudgetLoopCut:
    async def test_batch_loop_cuts_after_budget_exceeded(self, monkeypatch, ledger_db):
        """[chaos] 3 连发工具调用、max_tool_calls=1：第 2 个被拒后第 3 个不再发起
        （此前会继续尝试直到 20 次硬顶）."""
        user = await _make_user(ledger_db.session)
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        run = await _make_run(ledger_db.session, user, budget={"limits": {"max_tool_calls": 1}})

        calls = [{"id": f"c{i}", "function": {"name": tool.name, "arguments": '{"title": "a"}'}} for i in range(3)]
        results = await ToolExecutor().execute_tool_calls(
            calls, str(user.id), ledger_db.session, runtime_context={"run_id": str(run.id)}
        )
        assert len(results) == 2  # 第 3 个被切断（不再发起）
        assert results[0].success is True
        assert results[1].success is False and results[1].error_type == "BudgetExceeded"
        assert tool.execute_count == 1  # 只有第一次真正执行
        await ledger_db.session.refresh(run)
        assert run.status == RunStatus.BUDGET_EXCEEDED  # 明确终态（X-06 语义保持）

    async def test_dag_plan_cuts_remaining_layers(self, monkeypatch, ledger_db):
        """[chaos] 两层 DAG、预算只够一层：第二层不启动（budget_exceeded 置位）."""
        from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

        user = await _make_user(ledger_db.session)
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        run = await _make_run(ledger_db.session, user, budget={"limits": {"max_tool_calls": 1}})

        plan = ExecutablePlan(
            plan_id="p1",
            context_version="v0",
            source="test",
            rationale="",
            execution_order=[["s1"], ["s2"]],
            tool_calls=[
                ToolCallSpec(id="s1", name=tool.name, params={"title": "a"}),
                ToolCallSpec(id="s2", name=tool.name, params={"title": "b"}, depends_on=["s1"]),
            ],
        )
        result = await ToolExecutor().execute_plan(
            plan,
            str(user.id),
            ledger_db.session,
            runtime_context={"run_id": str(run.id)},
        )
        assert result.budget_exceeded is True
        assert result.aborted is True
        assert "budget" in (result.abort_reason or "")
        assert tool.execute_count == 1  # 第二层未执行

    async def test_workflow_node_cuts_phase1_loop(self, monkeypatch, ledger_db):
        """[chaos] standard_workflow Phase-1 循环：BudgetExceeded 后不执行剩余
        工具、不回 generation 规划下一轮（FIX-40 P3-6 的 agent 循环切断）."""
        from app.agents import standard_workflow as sw
        from app.orchestration.statechart_engine import WorkflowState

        user = await _make_user(ledger_db.session)

        class _BudgetStubExecutor:
            def __init__(self):
                self.executed: list[str] = []

            async def execute_tool_call(self, *, tool_name, arguments, user_id, db_session, **kwargs):
                self.executed.append(tool_name)
                if len(self.executed) >= 2:
                    return ToolResult(
                        success=False,
                        tool_name=tool_name,
                        error_type="BudgetExceeded",
                        error_message="run budget exceeded: tool_calls",
                    )
                return ToolResult(success=True, tool_name=tool_name, data={"ok": True})

        stub_executor = _BudgetStubExecutor()
        monkeypatch.setattr(sw, "ToolExecutor", lambda: stub_executor)

        async def _no_fallback(**kwargs):
            return None

        monkeypatch.setattr(sw, "_write_feedback", _no_fallback)

        state = WorkflowState(
            messages=[{"role": "user", "content": "go"}],
            context_data={
                "tool_calls": [
                    SimpleNamespace(tool_name="t1", full_arguments={"a": 1}, tool_call_id="id1"),
                    SimpleNamespace(tool_name="t2", full_arguments={"a": 2}, tool_call_id="id2"),
                    SimpleNamespace(tool_name="t3", full_arguments={"a": 3}, tool_call_id="id3"),
                ],
                "db_session": ledger_db.session,
                "user_id": str(user.id),
            },
        )
        result_state = await sw.tool_execution_node(state)
        assert stub_executor.executed == ["t1", "t2"]  # t3 被切断
        assert result_state.context_data["budget_exceeded"] is True
        assert result_state.next_step == "__end__"  # 不回 generation
        assert result_state.context_data["tool_calls"] == []


# ---------------------------------------------------------------------------
# C. 重试策略（指数退避 + 上限 + 死信）执行链行为
# ---------------------------------------------------------------------------


class TestDeterministicRetry:
    async def test_transient_read_retries_to_success(self, monkeypatch, ledger_db):
        """[chaos] 网络分区抖动（read，2 次失败后成功）：退避重试后成功，账本
        按派生键开行（原 key 历史不改写）."""
        from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

        user = await _make_user(ledger_db.session)
        uid = str(user.id)
        tool = _StubReadTool(fail_times=2)
        _install_registry(monkeypatch, read=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "DEFAULT_RETRY_BASE_DELAY_SECONDS", 0.01)

        plan = ExecutablePlan(
            plan_id="p2",
            context_version="v0",
            source="test",
            rationale="",
            tool_calls=[ToolCallSpec(id="s1", name=tool.name, params={"title": "a"})],
        )
        result = await ToolExecutor().execute_plan(plan, str(user.id), ledger_db.session)
        assert result.tool_results[0].success is True
        assert tool.execute_count == 3  # 1 + 2 retries
        await ledger_db.session.commit()  # 调用方事务提交（owns_session=False）
        rows = await _ledger_rows(ledger_db.session, user_id=uid, factory=ledger_db.factory)
        assert len(rows) == 3  # 每次尝试一行（attempt 历史）

    async def test_retry_budget_exhausted_dead_letters(self, monkeypatch, ledger_db):
        """[chaos] 持续网络故障：重试耗尽 → 死信（保留最后失败，非无限执行）."""
        from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

        user = await _make_user(ledger_db.session)
        tool = _StubReadTool(fail_times=99)
        _install_registry(monkeypatch, read=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "DEFAULT_RETRY_BASE_DELAY_SECONDS", 0.01)

        plan = ExecutablePlan(
            plan_id="p3",
            context_version="v0",
            source="test",
            rationale="",
            tool_calls=[ToolCallSpec(id="s1", name=tool.name, params={"title": "a"})],
        )
        result = await ToolExecutor().execute_plan(plan, str(user.id), ledger_db.session)
        assert result.tool_results[0].success is False
        assert result.tool_results[0].error_type == "ConnectionResetError"
        assert tool.execute_count == 1 + DEFAULT_MAX_RETRY_ATTEMPTS

    async def test_permanent_failure_never_retries(self, monkeypatch, ledger_db):
        """[chaos] 权限拒绝（PERMANENT）：一次即死信，无重试轮."""
        from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

        user = await _make_user(ledger_db.session)
        run = await _make_run(
            ledger_db.session,
            user,
            allowed_tools=["stub_get_task"],  # 白名单不含写工具 → not_in_allowed_tools
        )
        tool = _StubWriteTool()
        _install_registry(monkeypatch, write=tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)

        plan = ExecutablePlan(
            plan_id="p4",
            context_version="v0",
            source="test",
            rationale="",
            tool_calls=[ToolCallSpec(id="s1", name=tool.name, params={"title": "a"})],
        )
        result = await ToolExecutor().execute_plan(
            plan, str(user.id), ledger_db.session, runtime_context={"run_id": str(run.id)}
        )
        assert result.tool_results[0].success is False
        assert result.tool_results[0].error_type == "PermissionDenied"
        assert tool.execute_count == 0

    def test_error_type_mapping_is_structural(self):
        """error_type → FailureKind 只按错误码，不按文案（确定性锚点）."""
        from app.orchestration.executor import failure_kind_for_error_type

        assert failure_kind_for_error_type("TimeoutError").value == "tool_timeout"
        assert failure_kind_for_error_type("BudgetExceeded").value == "budget_exceeded"
        assert failure_kind_for_error_type("PermissionDenied").value == "permission_denied"
        assert failure_kind_for_error_type("IdempotencyInterrupted").value == "idempotency_interrupted"
        assert failure_kind_for_error_type("ConnectionResetError").value == "network_unreachable"
        assert failure_kind_for_error_type("ClientConnectorError").value == "network_unreachable"
        assert failure_kind_for_error_type("WhateverElse").value == "tool_reported_failure"
        assert failure_kind_for_error_type(None).value == "tool_reported_failure"


# ---------------------------------------------------------------------------
# D. 部分完成语义（不静默丢弃 + 补偿提示 + API 可见）
# ---------------------------------------------------------------------------


class TestPartialCompletionSemantics:
    async def test_failure_with_durable_progress_terminalizes_partial(self, monkeypatch, ledger_db):
        """[chaos] 多步执行第 3 步失败：前两步写效果保留 → PARTIAL +
        result_ref 携带 succeeded/补偿提示（API 可见，不静默丢弃）."""
        _stub_registry_with(monkeypatch, "generate_tasks_for_plan")
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        # 两个成功写步（真实注册表工具名：effect=write, reversible=True）
        for _ in range(2):
            await _make_ledger_row(ledger_db.session, user, run, status="succeeded", tool="generate_tasks_for_plan")
        classification = classify_execution_failure(
            failure_kind="tool_reported_failure", tool_effect="write", side_effect_state="none"
        )
        result = await AgentRunService(ledger_db.session).terminalize_execution_failure(
            run.id, classification=classification, error_message="step 3 exploded", retries_exhausted=True
        )
        assert result.applied is True
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.PARTIAL
        assert run.terminal_reason == "completed_partial"
        assert run.error_category == "retryable_failure"
        assert run.result_ref["scheme"] == "partial_completion"
        assert run.result_ref["succeeded_steps"] == 2
        assert len(run.result_ref["compensation_hints"]) == 2
        assert run.result_ref["compensation_hints"][0]["reversible"] is True

    async def test_failure_without_progress_stays_failed(self, ledger_db):
        """[chaos] 零进度失败（无写效果成功步）：FAILED（不虚报 PARTIAL）."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        await _make_ledger_row(ledger_db.session, user, run, status="failed", tool="generate_tasks_for_plan")
        classification = classify_execution_failure(failure_kind="permission_denied", tool_effect="write")
        result = await AgentRunService(ledger_db.session).terminalize_execution_failure(
            run.id, classification=classification
        )
        assert result.applied is True
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.FAILED
        assert run.terminal_reason == "rejected"
        assert run.result_ref["succeeded_steps"] == 0

    async def test_cancel_keeps_user_attribution_with_evidence(self, monkeypatch, ledger_db):
        """[chaos] 有已完成步的取消：CANCELLED(user_cancelled) 不被系统归因覆盖，
        已完成部分仍随 result_ref 可见（AGENT_RUNTIME §6）."""
        _stub_registry_with(monkeypatch, "generate_tasks_for_plan")
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        await _make_ledger_row(ledger_db.session, user, run, status="succeeded", tool="generate_tasks_for_plan")
        classification = classify_execution_failure(failure_kind="user_cancelled")
        await AgentRunService(ledger_db.session).terminalize_execution_failure(run.id, classification=classification)
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.CANCELLED
        assert run.terminal_reason == "user_cancelled"
        assert run.result_ref["succeeded_steps"] == 1  # 完成部分不静默

    async def test_unknown_outcome_records_interruption_evidence(self, monkeypatch, ledger_db):
        """[chaos] 未知结局：interrupted 步在 result_ref.interrupted 里显式列出
        （outcome=unknown，不假装成功/失败）."""
        _stub_registry_with(monkeypatch, "generate_tasks_for_plan")
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        await _make_ledger_row(ledger_db.session, user, run, status="interrupted", tool="generate_tasks_for_plan")
        classification = classify_execution_failure(
            failure_kind="worker_crash_orphan", tool_effect="write", side_effect_state="unknown"
        )
        await AgentRunService(ledger_db.session).terminalize_execution_failure(run.id, classification=classification)
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.UNKNOWN_OUTCOME
        assert run.error_category == "unknown_outcome"
        assert run.result_ref["interrupted_steps"] == 1
        assert run.result_ref["interrupted"][0]["outcome"] == "unknown"

    async def test_terminalize_is_idempotent_on_terminal_run(self, ledger_db):
        """[chaos] 终态封闭：已终态 run 的失败终态化 → no-op 不双终态."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user, status=RunStatus.SUCCEEDED)
        classification = classify_execution_failure(failure_kind="tool_exception", tool_effect="read")
        result = await AgentRunService(ledger_db.session).terminalize_execution_failure(
            run.id, classification=classification
        )
        assert result.applied is False
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.SUCCEEDED  # 不被覆盖

    async def test_tool_calls_api_endpoint_exposes_ledger(self, ledger_db):
        """GET /runs/{id}/tool-calls：账本明细 + 部分完成证据（owner-only）."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.deps import get_current_user, get_db
        from app.api.v1.runs import router as runs_router

        user = await _make_user(ledger_db.session)
        other = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        await _make_ledger_row(ledger_db.session, user, run, status="succeeded", tool="generate_tasks_for_plan")
        await _make_ledger_row(ledger_db.session, user, run, status="interrupted", tool="generate_tasks_for_plan")

        app = FastAPI()
        app.include_router(runs_router)
        app.dependency_overrides[get_db] = lambda: ledger_db.session

        async def _user_override():
            return user

        async def _other_override():
            return other

        app.dependency_overrides[get_current_user] = _user_override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            resp = await client.get(f"/runs/{run.id}/tool-calls")
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["total"] == 2
            assert {i["status"] for i in payload["items"]} == {"succeeded", "interrupted"}
            assert payload["partial_completion"]["scheme"] == "partial_completion"
            assert payload["partial_completion"]["succeeded_steps"] == 1
            assert payload["partial_completion"]["interrupted_steps"] == 1

            # 跨用户读取 → 404（存在性不泄露）
            app.dependency_overrides[get_current_user] = _other_override
            resp_other = await client.get(f"/runs/{run.id}/tool-calls")
            assert resp_other.status_code == 404


# ---------------------------------------------------------------------------
# E. 主动崩溃恢复（recover_inflight_runs：证据驱动裁决）
# ---------------------------------------------------------------------------


class TestProactiveCrashRecovery:
    async def test_inflight_ledger_runs_to_unknown_outcome(self, ledger_db):
        """[chaos] 杀进程遗留（in_progress 陈旧账本 + RUNNING run）：重启恢复 →
        账本 interrupted + run UNKNOWN_OUTCOME（绝不自动重驱动）."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
        row = await _make_ledger_row(ledger_db.session, user, run, started_at=stale)

        payload = await AgentRunService(ledger_db.session).recover_inflight_runs(stale_after_seconds=600)
        await ledger_db.session.refresh(run)
        await ledger_db.session.refresh(row)
        assert row.status == "interrupted"
        assert run.status is RunStatus.UNKNOWN_OUTCOME
        assert run.error_category == "unknown_outcome"
        decided = [d for d in payload["decisions"] if d["run_id"] == str(run.id)]
        assert decided and decided[0]["decision"] == "unknown_outcome"

    async def test_active_run_without_evidence_is_reattach_candidate_only(self, ledger_db):
        """[chaos] 无中断证据的活跃 run：只输出 reattach 建议（不迁终态、不猜）."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        payload = await AgentRunService(ledger_db.session).recover_inflight_runs()
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.RUNNING  # 未被误判
        decisions = {d["run_id"]: d["decision"] for d in payload["decisions"]}
        assert decisions[str(run.id)] == "reattach_candidate"

    async def test_intent_terminal_beats_orphan_speculation(self, ledger_db):
        """[chaos] intent 已成功 + run 悬空（中断证据俱在）：漂移修复落真值
        SUCCEEDED——推测（UNKNOWN）不得覆盖 intent 真源."""
        from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus, ExecutorType, TrustLevel
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        from app.models.task import Task, TaskStatus, TaskType

        task = Task(user_id=user.id, title="t", type=TaskType.LEARNING, estimated_minutes=30, status=TaskStatus.PENDING)
        ledger_db.session.add(task)
        await ledger_db.session.commit()
        intent = ExecutionIntent(
            plan_id=None,
            task_id=task.id,
            user_id=user.id,
            execution_mode="agent",
            executor=ExecutorType.OPENCLAW,
            goal="g",
            instructions=[],
            target_env=None,
            policy={},
            success_criteria={},
            result_contract={},
            timeout_seconds=300,
            status=ExecutionIntentStatus.SUCCEEDED,
            trust_level=TrustLevel.RAW,
            idempotency_key=f"i-{uuid4().hex[:8]}",
        )
        ledger_db.session.add(intent)
        await ledger_db.session.commit()
        run = await _make_run(ledger_db.session, user, intent=intent)
        stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
        await _make_ledger_row(ledger_db.session, user, run, started_at=stale)

        payload = await AgentRunService(ledger_db.session).recover_inflight_runs(stale_after_seconds=600)
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.SUCCEEDED  # 真值优先
        decisions = {d["run_id"]: d["decision"] for d in payload["decisions"]}
        assert decisions[str(run.id)] == "drift_repaired"

    async def test_recovery_is_idempotent(self, ledger_db):
        """[chaos] 恢复 pass 重放：interrupted 行不再改写、终态 run 不再迁移."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
        row = await _make_ledger_row(ledger_db.session, user, run, started_at=stale)

        await AgentRunService(ledger_db.session).recover_inflight_runs(stale_after_seconds=600)
        finished_at = row.finished_at
        second = await AgentRunService(ledger_db.session).recover_inflight_runs(stale_after_seconds=600)
        await ledger_db.session.refresh(row)
        assert second["ledger_reconciled"] == 0
        assert second["ledger_already_resolved"] >= 1
        assert row.finished_at == finished_at  # interrupted 不再改写
        decided = [d for d in second["decisions"] if d["run_id"] == str(run.id)]
        assert decided and decided[0]["decision"] == "terminal_noop"

    async def test_fresh_in_progress_row_not_reconciled(self, ledger_db):
        """[chaos] 活跃执行中的 in_progress（新鲜心跳）：不误判孤儿."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        await _make_ledger_row(ledger_db.session, user, run)  # started_at=now
        payload = await AgentRunService(ledger_db.session).recover_inflight_runs(stale_after_seconds=600)
        assert payload["ledger_reconciled"] == 0
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.RUNNING

    async def test_sweep_and_inflight_coexist(self, ledger_db):
        """[chaos] 协同不冲突：inflight pass 先执行，sweep 对同一 run 状态收敛
        （sweep 是兜底——终态 run 被 sweep 跳过）."""
        from app.services.agent_run_service import AgentRunService

        user = await _make_user(ledger_db.session)
        run = await _make_run(ledger_db.session, user)
        stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
        await _make_ledger_row(ledger_db.session, user, run, started_at=stale)

        await AgentRunService(ledger_db.session).recover_inflight_runs(stale_after_seconds=600)
        sweep = await AgentRunService(ledger_db.session).recover_stale_runs(stale_after_seconds=600)
        await ledger_db.session.refresh(run)
        assert run.status is RunStatus.UNKNOWN_OUTCOME  # 双 pass 后单终态
        assert all(a.get("skipped") or not a.get("applied") for a in sweep["actions"] if a.get("run_id") == str(run.id))


# ---------------------------------------------------------------------------
# F. 账本状态词表（X-06 契约的 X-09 增补钉）
# ---------------------------------------------------------------------------


class TestLedgerStatusVocabulary:
    def test_interrupted_in_status_vocabulary(self):
        from app.models.agent_tool_call import TOOL_CALL_STATUSES

        assert TOOL_CALL_STATUSES == ("in_progress", "succeeded", "failed", "interrupted")

    def test_side_effect_state_field_exists(self):
        r = ToolResult(success=False, tool_name="x", error_type="TimeoutError", side_effect_state="unknown")
        assert r.side_effect_state == "unknown"
        # 旧构造（无该字段）仍合法——向后兼容
        assert ToolResult(success=True, tool_name="x").side_effect_state is None
