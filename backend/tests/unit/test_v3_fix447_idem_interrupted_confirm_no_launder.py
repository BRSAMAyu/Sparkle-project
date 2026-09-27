"""V3-FIX-447 · /confirm 两面 IdempotencyInterrupted 被自修正环洗成新键真执行.

危害定性（V3-FIX-417 收口顺审登记，wt732；本文件 wt740 运行级复现+收口）：
- X-09 修法（FIX-40 P3-6）只在 /task 批量面（chat.py :566/:573 过滤集）与
  /stream 面（:797 行内过滤）排除了 IdempotencyInterrupted；/confirm 两面
  （:933/:963）无任何 error_type 过滤；
- ``should_retry`` 对 Interrupted 错误文（executor X-09 闸门原文「was interrupted
  ... retrying requires a NEW idempotency key (this key will never re-execute)」）
  关键词全不匹配 → 默认 ``return True``；417 排除集按裁决只含三闸门类；
- ``handle_tool_error`` 修正轮以 LLM 新 tool_call_id 重调 executor（不带
  idempotency_key）→ fresh 键无账本行 → 放行。触发链：HITL 首轮 confirm 持
  意图键 ``hitl:{action_id}:{tool_name}`` 执行中崩溃（内部 commit 工具两阶段
  收敛把账本行置 interrupted）→ pending action 未清理 → 用户重放同 action_id
  confirm → IdempotencyInterrupted 恒拒（正确）→ 自动修正环换新键真执行——
  恰违背 executor X-09 注释「重试必须换新幂等键——那是显式决策，不是自动行为」。

修法（与 417 同面统一）：``IdempotencyInterrupted`` 本就是 executor 幂等闸门的
第四类拒绝（executor.py X-09 分支），并入
``error_handler.IDEMPOTENCY_GATE_ERROR_TYPES``——
- /stream（:797 行内过滤）与 /task（:566/:573 过滤集）既有排除语义零变化
  （Interrupted 在这两面进不了漏斗，排除集扩展对其不可达 = 纵深防御）；
- /confirm 两面经 ``should_retry`` 短路 + ``handle_tool_error`` 早期拒绝双重
  覆盖，与其余面对齐 X-09 设计（确定结局修正轮不进自修正环）；
- BudgetExceeded 在 /confirm 面不可达（该面不传 runtime_context → 无 run 行 →
  预算闸门跳过），无须引入 :797 行内过滤形态，chat.py 保持零改动。

前序：tests/unit/test_x09_failure_recovery.py（interrupted 行构造 + 同键恒拒）、
tests/unit/test_v3_fix417_idem_gate_no_launder.py（三闸门类洗白收口）。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.user import User
from app.orchestration import error_handler as error_handler_module
from app.orchestration import executor as executor_module
from app.orchestration.error_handler import AgentErrorHandler
from app.orchestration.executor import ToolExecutor
from app.tools.base import ToolCategory, ToolResult


class _WriteParams(BaseModel):
    title: str = "t"


class _StubWriteTool:
    """HITL write 工具桩：可选「中途 commit」+「前 N 次执行崩溃」模拟内部 commit
    服务首轮中断（修正轮若被放行则成功——正是「洗白」要凑出的第二次真执行）."""

    name = "stub_create_task"
    description = "stub write tool"
    category = ToolCategory.TASK
    parameters_schema = _WriteParams
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "write"
    risk = "medium"
    reversible = True
    required_permission = "task.write"
    cost_usd = 0.0

    def __init__(self, *, commit_midway: bool = False, raise_times: int = 1):
        self.execute_count = 0
        self.commit_midway = commit_midway
        self.raise_times = raise_times

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        if self.commit_midway and db_session is not None:
            # 模拟内部 commit 服务：把 executor 已 flush 的账本 in_progress 行
            # 提前落库——崩溃后两阶段收敛把它置 interrupted 的前提。
            await db_session.commit()
        if self.execute_count <= self.raise_times:
            raise RuntimeError("exploded after internal commit")
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


class _RecordingLLM:
    """修正轮 LLM 桩：恒回「同工具、新 id」的修正调用；实录被调次数。"""

    def __init__(self, tool_name: str = "stub_create_task"):
        self.calls = 0
        self._tool_name = tool_name

    async def chat_with_tools(self, **kw):
        self.calls += 1
        return SimpleNamespace(
            tool_calls=[
                {
                    "id": "fresh-correction-id",
                    "type": "function",
                    "function": {"name": self._tool_name, "arguments": '{"title":"t"}'},
                }
            ],
            content=None,
        )


def _install_write_registry(monkeypatch, tool: _StubWriteTool):
    namespace = SimpleNamespace(
        get_tool=lambda name: tool if name == tool.name else None,
        get_tool_metadata=lambda name: (
            SimpleNamespace(
                name=tool.name,
                effect="write",
                risk="medium",
                reversible=True,
                required_permission="task.write",
                cost_usd=0.0,
                is_side_effect=True,
            )
            if name == tool.name
            else None
        ),
        get_openai_tools_schema=lambda: [],
    )
    monkeypatch.setattr(executor_module, "tool_registry", namespace)
    monkeypatch.setattr(error_handler_module, "tool_registry", namespace)

    class _Decision:
        allowed = True
        reason = "stub-allow"

        def to_dict(self):
            return {"allowed": True, "reason": "stub-allow"}

    monkeypatch.setattr(executor_module, "decide_tool_permission", lambda **kw: _Decision())


@pytest.fixture
async def ledger_db():
    """独立 sqlite 引擎（executor 账本 + 两阶段收敛会话工厂共用；x09 同构）."""
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


async def _ledger_rows(factory) -> list[AgentToolCall]:
    """读账本真值：新会话裸读（x09 同款）——两阶段收敛由独立会话提交，调用方
    会话的 identity map（expire_on_commit=False）不自动失效，直读会看到陈旧残影."""
    async with factory() as fresh:
        stmt = select(AgentToolCall).order_by(AgentToolCall.created_at.asc())
        return list((await fresh.execute(stmt)).scalars().all())


def _interrupted_result() -> ToolResult:
    """executor X-09 闸门（executor.py :571-583）对 interrupted 行的原文拒绝体."""
    return ToolResult(
        success=False,
        tool_name="stub_create_task",
        error_type="IdempotencyInterrupted",
        error_message=(
            "Previous attempt with idempotency key 'hitl:act-1:stub_create_task' for tool 'stub_create_task' "
            "was interrupted and its side-effect outcome could not be verified; "
            "retrying requires a NEW idempotency key (this key will never re-execute)"
        ),
    )


# ---------------------------------------------------------------------------
# 1. 运行级主战场：/confirm 重放面 interrupted 恒拒 → 修正环不得洗白
# ---------------------------------------------------------------------------


class TestConfirmInterruptedNotLaundered:
    async def test_confirm_replay_interrupted_not_laundered(self, monkeypatch, ledger_db):
        """红→绿主场景（HITL 首轮崩溃→重放全链，chat.py /confirm 单工具面 :963 形态）：

        红（447 定性运行级化）：attempt1 持意图键 ``hitl:{action_id}:{tool}``
        内部 commit 后崩溃 → 两阶段收敛置 interrupted（execute_count=1）→
        用户重放同 action_id → IdempotencyInterrupted 恒拒（闸门正确）→
        /confirm 漏斗 ``should_retry`` True → handle_tool_error（修正 LLM 回
        同工具新 id）→ 真 executor 以 fresh 键放行 → execute_count=2——
        「重试必须换新幂等键=显式决策」被自动环代行。

        绿（本修复）：Interrupted 并入 417 排除集——漏斗不进，execute_count
        恒 1，原始拒绝原样上报，LLM 修正轮零调用，账本零新开行。
        """
        tool = _StubWriteTool(commit_midway=True, raise_times=1)
        _install_write_registry(monkeypatch, tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        user = await _make_user(ledger_db.session)
        uid = str(user.id)
        executor = ToolExecutor()
        handler = AgentErrorHandler()
        intent_key = "hitl:act-1:stub_create_task"

        # attempt1（HITL 首轮 confirm）：持意图键执行，内部 commit 后崩溃
        # → 账本行两阶段收敛 interrupted（效果不可核实）
        r1 = await executor.execute_tool_call(
            tool_name=tool.name,
            arguments={"title": "t"},
            user_id=uid,
            db_session=ledger_db.session,
            idempotency_key=intent_key,
        )
        assert r1.success is False  # 崩溃失败原样上报（首请求随之死亡，无修正机会）
        assert tool.execute_count == 1
        rows = await _ledger_rows(ledger_db.factory)
        assert len(rows) == 1
        assert rows[0].status == "interrupted"  # X-09 两阶段收敛产物
        assert rows[0].idempotency_key == intent_key

        # attempt2（用户重放同 action_id confirm）：同意图键 → IdempotencyInterrupted
        # 恒拒（闸门本体正确，duplicate side effect=0）
        r2 = await executor.execute_tool_call(
            tool_name=tool.name,
            arguments={"title": "t"},
            user_id=uid,
            db_session=ledger_db.session,
            idempotency_key=intent_key,
        )
        assert r2.success is False
        assert r2.error_type == "IdempotencyInterrupted"
        assert "NEW idempotency key" in (r2.error_message or "")
        assert tool.execute_count == 1

        # /confirm 面 :963 的真实漏斗形态
        llm = _RecordingLLM()
        went_into_correction = handler.should_retry(r2)
        final = await handler.handle_tool_error(
            llm_service=llm,
            tool_result=r2,
            original_request={"function": {"name": tool.name, "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=uid,
            db_session=ledger_db.session,
        )
        await ledger_db.session.commit()

        assert went_into_correction is False  # 排除集命中：修正轮不进
        assert llm.calls == 0  # 不烧 LLM 修正轮
        assert tool.execute_count == 1  # 不洗白成第二次真执行
        assert final.success is False  # 原始拒绝原样上报
        assert final.error_type == "IdempotencyInterrupted"
        assert "自动修正已跳过" in (final.suggestion or "")
        rows = await _ledger_rows(ledger_db.factory)
        assert len(rows) == 1  # 账本零新开行（fresh 键行不存在）
        assert rows[0].status == "interrupted"  # interrupted 行原样保留

    async def test_confirm_plan_face_shares_same_funnel(self, monkeypatch, ledger_db):
        """/confirm 计划面（chat.py :933，__plan__ 循环内）与单工具面（:963）走
        同一 ``should_retry`` + ``handle_tool_error`` 漏斗——单工具面主场景收口
        即两面同批收口；本用例钉计划面形态同参语义（handler 面直证）。"""
        handler = AgentErrorHandler()
        llm = _RecordingLLM()
        result = _interrupted_result()
        user = await _make_user(ledger_db.session)

        went_into_correction = handler.should_retry(result)
        final = await handler.handle_tool_error(
            llm_service=llm,
            tool_result=result,
            original_request={"function": {"name": "stub_create_task", "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=str(user.id),
            db_session=ledger_db.session,
        )
        assert went_into_correction is False
        assert llm.calls == 0
        assert final.success is False
        assert final.error_type == "IdempotencyInterrupted"


# ---------------------------------------------------------------------------
# 2. 排除集统一语义钉（error_handler 面）
# ---------------------------------------------------------------------------


class TestExclusionSetUnification:
    def test_should_retry_false_for_idempotency_interrupted(self):
        """Interrupted：should_retry 恒 False（原行为默认 True=洗白入口）。"""
        assert AgentErrorHandler().should_retry(_interrupted_result()) is False

    def test_should_retry_still_true_for_safe_transient_failures(self):
        """对照（不过宽）：干净回滚类失败（X-09 side_effect_state=none 语义、
        可安全自动重试）不因本扩展被误伤。"""
        handler = AgentErrorHandler()
        timeout_failure = ToolResult(
            success=False,
            tool_name="stub_create_task",
            error_type="TimeoutError",
            error_message="工具执行超时（>5s）",
        )
        clean_runtime_failure = ToolResult(
            success=False,
            tool_name="stub_create_task",
            error_type="RuntimeError",
            error_message="exploded before commit",
        )
        assert handler.should_retry(timeout_failure) is True
        assert handler.should_retry(clean_runtime_failure) is True

    async def test_handle_tool_error_skips_and_reports_honestly(self, monkeypatch, ledger_db):
        """handler 面直证：Interrupted 进 handle_tool_error → 修正轮零调用、
        原始拒绝原样上报、suggestion 明示换新键=显式决策。"""
        monkeypatch.setattr(error_handler_module, "tool_registry", SimpleNamespace(get_openai_tools_schema=lambda: []))
        llm = _RecordingLLM()
        user = await _make_user(ledger_db.session)
        final = await AgentErrorHandler().handle_tool_error(
            llm_service=llm,
            tool_result=_interrupted_result(),
            original_request={"function": {"name": "stub_create_task", "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=str(user.id),
            db_session=ledger_db.session,
        )
        assert llm.calls == 0
        assert final.success is False
        assert final.error_type == "IdempotencyInterrupted"
        suggestion = final.suggestion or ""
        assert "自动修正已跳过" in suggestion
        assert "新幂等键" in suggestion  # 显式决策语义如实透传


# ---------------------------------------------------------------------------
# 3. 对照：干净失败（无 interrupted 行）的 /confirm 修正链照常可用
# ---------------------------------------------------------------------------


class TestCleanFailureCorrectionUnaffected:
    async def test_clean_rollback_failure_still_auto_corrected(self, monkeypatch, ledger_db):
        """绿回归对照：attempt 崩溃但账本行随事务回滚（无内部 commit）→ 无
        interrupted 行、无键中毒——/confirm 漏斗照常进修正环并重试成功
        （X-09「可安全自动重试」语义原样，排除集不过宽的运行级证明）。"""
        tool = _StubWriteTool(commit_midway=False, raise_times=1)
        _install_write_registry(monkeypatch, tool)
        monkeypatch.setattr(executor_module, "_ledger_session_factory", ledger_db.factory)
        monkeypatch.setattr(executor_module, "_agent_run_session_factory", ledger_db.factory)
        user = await _make_user(ledger_db.session)
        uid = str(user.id)
        executor = ToolExecutor()
        handler = AgentErrorHandler()

        r1 = await executor.execute_tool_call(
            tool_name=tool.name,
            arguments={"title": "t"},
            user_id=uid,
            db_session=ledger_db.session,
            idempotency_key="hitl:act-2:stub_create_task",
        )
        assert r1.success is False
        assert r1.side_effect_state == "none"  # 干净回滚：可安全自动重试
        assert tool.execute_count == 1
        assert await _ledger_rows(ledger_db.factory) == []  # 行随事务回滚

        # /confirm 面 :963 漏斗：修正轮照常进入（LLM 回同工具新 id）→ 成功
        llm = _RecordingLLM()
        went_into_correction = handler.should_retry(r1)
        final = await handler.handle_tool_error(
            llm_service=llm,
            tool_result=r1,
            original_request={"function": {"name": tool.name, "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=uid,
            db_session=ledger_db.session,
        )
        await ledger_db.session.commit()

        assert went_into_correction is True
        assert llm.calls == 1
        assert final.success is True
        assert tool.execute_count == 2  # 修正轮真执行——干净失败下这正是设计语义
