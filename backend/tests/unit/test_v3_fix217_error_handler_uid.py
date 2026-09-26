"""V3-FIX-217 · error_handler 自修正链 user_id=None 流入 execute_tool_call 身份参数.

危害定性（110131f8 探针实录，wt509）：
- 生产调用面（app/api/v1/chat.py 4 处）均传 ``str(current_user.id)``；None 的唯一
  来源是 ``handle_tool_error``/``handle_batch_errors`` 的 ``user_id: str = None``
  隐式 Optional 默认值——任何省略身份的调用方都会把 None 顶替进
  ``execute_tool_call`` 的身份参数（executor.py:658，契约 ``user_id: str``）。
- None 到达 executor 后的两条实录路径（均不越权：权限判定输入不含身份，账本
  闸门 fail-closed，工具执行不发生）：
  ① 无幂等键（read 工具 / LLM 未回 id）：账本开行 ``uuid.UUID(str(None))`` →
     ValueError 被捕获 → 以**伪造的 IdempotencyConflict（"并发重复调用"）**拒绝
     ——自修正恒死且错误归因说谎；
  ② 有幂等键（write 工具 + tool_call_id）：``_find_ledger_row`` 同源 ValueError
     被 re-raise → 直调面裸抛（链上面被 handler 兜底 except 吞成"修正失败"）。
  另有工具事件 payload ``user_id: "None"`` 日志/事件污染。
- 修法（身份面红线，禁静默吞/默认值顶替）：handler 缺真实身份 → 拒绝自修正并
  诚实上报（不调 LLM、不进执行面、suggestion 明示跳过原因）；executor 身份参数
  保持 ``str`` 非 Optional——None 源头消除，wt504 注解位无需 Optional 化。
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


class _ReadParams(BaseModel):
    title: str = "t"


class _StubReadTool:
    """read 工具桩（与 test_x06 同构；execute 计数器暴露"执行是否发生"）。"""

    name = "stub_get_task"
    description = "stub read tool"
    category = ToolCategory.TASK
    parameters_schema = _ReadParams
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


def _install_read_registry(monkeypatch, tool: _StubReadTool):
    namespace = SimpleNamespace(
        get_tool=lambda name: tool if name == tool.name else None,
        get_tool_metadata=lambda name: (
            SimpleNamespace(
                name=tool.name,
                effect="read",
                risk="low",
                reversible=True,
                required_permission="task.read",
                cost_usd=0.0,
                is_side_effect=False,
            )
            if name == tool.name
            else None
        ),
        get_openai_tools_schema=lambda: [],
    )
    monkeypatch.setattr(executor_module, "tool_registry", namespace)
    monkeypatch.setattr(error_handler_module, "tool_registry", namespace)


def _failed_result() -> ToolResult:
    return ToolResult(
        success=False,
        tool_name="stub_get_task",
        error_message="参数验证失败: title 缺失",
        error_type="ValidationError",
        suggestion="请检查参数格式是否正确",
    )


class _RecordingLLM:
    """chat_with_tools 计数桩：每次调用弹出一个响应；耗尽后返回无 tool_calls。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def chat_with_tools(self, *, system_prompt=None, user_message=None, tools=None):
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return SimpleNamespace(tool_calls=None, content="无法修正")


def _corrected_call(tool_name: str = "stub_get_task") -> SimpleNamespace:
    return SimpleNamespace(
        tool_calls=[{"id": "call_retry_1", "type": "function", "function": {"name": tool_name, "arguments": "{}"}}],
        content=None,
    )


class _ExecutorSpy:
    """替换 ToolExecutor.execute_tool_call：只实录（身份, 次数），恒返回失败。"""

    def __init__(self):
        self.seen_user_ids: list[object] = []
        self.calls = 0

    async def __call__(self, *, tool_name, arguments, user_id, db_session, tool_call_id=None, **_kwargs):
        self.calls += 1
        self.seen_user_ids.append(user_id)
        return ToolResult(
            success=False,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            error_message="参数验证失败: 仍未通过",
            error_type="ValidationError",
        )


# ---------------------------------------------------------------------------
# 1. 危害面探针（executor 直调实录——钉住 fail-closed 边界，修后仍须成立）
# ---------------------------------------------------------------------------


class TestHarmProbeExecutorDirect:
    async def test_none_uid_read_tool_rejected_as_fake_idempotency_conflict(self, monkeypatch, guard_db):
        """探针①：user_id=None + read 工具（无幂等键）→ 伪造 IdempotencyConflict 拒绝。

        实录（110131f8）：不崩溃、不越权（工具零执行、账本零开行），但错误类型
        与消息说谎（"并发重复调用"——实际是身份缺失），自修正链据此被静默判死。
        """
        tool = _StubReadTool()
        _install_read_registry(monkeypatch, tool)
        executor = ToolExecutor()
        result = await executor.execute_tool_call(tool.name, {"title": "x"}, None, guard_db.session)
        assert result.success is False
        assert tool.execute_count == 0  # 执行未发生（fail-closed，非越权）
        assert result.error_type == "IdempotencyConflict"  # 归因说谎：非并发冲突
        assert "Concurrent duplicate call" in (result.error_message or "")
        rows = (await guard_db.session.execute(select(AgentToolCall))).scalars().all()
        assert rows == []  # 账本零开行

    async def test_none_uid_with_idempotency_key_raises_valueerror(self, monkeypatch, guard_db):
        """探针②：user_id=None + tool_call_id（幂等键）→ ValueError 裸抛。

        实录（110131f8）：``_find_ledger_row`` 的 uuid 解析失败被 re-raise，
        直调面得不到 ToolResult 而是异常；自修正链上面靠 handler 的兜底
        except 把它吞成"修正失败"——失效被掩盖为修正不可用。
        """
        tool = _StubReadTool()
        _install_read_registry(monkeypatch, tool)
        executor = ToolExecutor()
        with pytest.raises(ValueError):
            await executor.execute_tool_call(tool.name, {"title": "x"}, None, guard_db.session, tool_call_id="c9")
        assert tool.execute_count == 0

    async def test_real_uid_same_call_succeeds(self, monkeypatch, guard_db):
        """对照组：同一调用换真实身份 → 成功。拒绝确由 None 身份引起，非工具本身。"""
        tool = _StubReadTool()
        _install_read_registry(monkeypatch, tool)
        user = await _make_user(guard_db.session)
        executor = ToolExecutor()
        result = await executor.execute_tool_call(tool.name, {"title": "x"}, str(user.id), guard_db.session)
        assert result.success is True
        assert tool.execute_count == 1


# ---------------------------------------------------------------------------
# 2. 自修正链身份红线（红→绿主战场）
# ---------------------------------------------------------------------------


class TestSelfCorrectionIdentityGate:
    @pytest.mark.parametrize("missing_uid", [None, "", "   "], ids=["none", "empty", "blank"])
    async def test_missing_uid_refuses_self_correction_and_reports_honestly(self, monkeypatch, guard_db, missing_uid):
        """红线：缺真实身份 → 拒绝自修正并诚实上报（不调 LLM、不进执行面）。

        红（110131f8 实录）：user_id=None 时 handler 照常调 LLM 并把 None 顶替进
        execute_tool_call 身份参数——实录 llm×2 / executor×2 / seen=[None×2]
        （MAX_RETRY_COUNT=2 → retry_count 0,1 两轮修正全烧在缺身份的死路上），
        最终以伪造 IdempotencyConflict 类失效收场。
        """
        llm = _RecordingLLM(responses=[_corrected_call(), _corrected_call(), _corrected_call()])
        spy = _ExecutorSpy()
        monkeypatch.setattr(executor_module.ToolExecutor, "execute_tool_call", spy)
        original = _failed_result()

        result = await AgentErrorHandler().handle_tool_error(
            llm_service=llm,
            tool_result=original,
            original_request={"id": "call_orig", "function": {"name": "stub_get_task", "arguments": "{}"}},
            retry_count=0,
            user_id=missing_uid,
            db_session=guard_db.session,
        )

        assert llm.calls == 0  # 缺身份不烧 LLM 修正轮
        assert spy.calls == 0  # None 永不进入执行面身份参数
        assert spy.seen_user_ids == []
        assert result.success is False
        assert result.error_message == original.error_message  # 诚实保留原始错误
        suggestion = result.suggestion or ""
        assert "自动修正已跳过" in suggestion
        assert "缺少用户身份" in suggestion

    async def test_batch_entry_same_gate(self, monkeypatch, guard_db):
        """handle_batch_errors（另一处隐式 Optional 源头）同受身份闸门约束。"""
        llm = _RecordingLLM(responses=[_corrected_call()])
        spy = _ExecutorSpy()
        monkeypatch.setattr(executor_module.ToolExecutor, "execute_tool_call", spy)

        results = await AgentErrorHandler().handle_batch_errors(
            llm_service=llm,
            tool_results=[_failed_result()],
            original_requests=[{"function": {"name": "stub_get_task", "arguments": "{}"}}],
            user_id=None,
            db_session=guard_db.session,
        )

        assert llm.calls == 0
        assert spy.calls == 0
        assert len(results) == 1 and results[0].success is False
        assert "自动修正已跳过" in (results[0].suggestion or "")

    async def test_real_uid_correction_chain_still_executes(self, monkeypatch, guard_db):
        """绿回归：真实身份沿链完整传递——修正调用以该身份执行并记账（真 executor）。"""
        tool = _StubReadTool()
        _install_read_registry(monkeypatch, tool)
        user = await _make_user(guard_db.session)
        llm = _RecordingLLM(responses=[_corrected_call()])

        result = await AgentErrorHandler().handle_tool_error(
            llm_service=llm,
            tool_result=_failed_result(),
            original_request={"id": "call_orig", "function": {"name": "stub_get_task", "arguments": "{}"}},
            retry_count=0,
            user_id=str(user.id),
            db_session=guard_db.session,
        )

        assert llm.calls == 1
        assert result.success is True
        assert result.data == {"ok": True}
        assert tool.execute_count == 1
        rows = (await guard_db.session.execute(select(AgentToolCall))).scalars().all()
        assert len(rows) == 1
        assert str(rows[0].user_id) == str(user.id)  # 账本锚定真实身份
        assert rows[0].tool_name == "stub_get_task"
        assert rows[0].status == "succeeded"
