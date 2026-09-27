"""V3-FIX-417 · AgentErrorHandler 自修正环把幂等闸门拒绝「洗白」成新键真执行.

危害定性（wt713 猎缺第一轮运行级实录 + wt719 worktree 复核 CONFIRMED）：
- ``should_retry``（error_handler.py）对 IdempotencyConflict/IdempotencyArgsMismatch/
  IdempotencyKeyRequired 三类闸门拒绝按 error_message 关键词全不匹配 → 默认
  ``return True``；
- ``handle_tool_error`` 修正轮以 LLM 新生成的 tool_call_id 重调
  ``executor.execute_tool_call`` 且不带 ``idempotency_key``；
- executor（X-06）``key = idempotency_key or tool_call_id`` → 新键无账本行 →
  写副作用照常放行。并发冲突拒绝被自动环换成第二次真执行——恰是冲突闸要防的
  duplicate side effect；IdempotencyKeyRequired 的 fail-closed 同理可被洗成执行
  （X-06「重试换键=显式决策」被自动环代行）。
- 修法（X-09 同族最小面）：error_handler 重试排除集补三类闸门异常——同键重放
  恒拒、换键重试是显式决策（executor X-09 注释自证），不由自动环代行；诚实
  跳过自修正并原样上报。chat.py 四喂入面（:583/:804/:935/:967）全部经
  handle_tool_error/handle_batch_errors 漏斗，handler 内闸门即全覆盖。
- 运行级探针与日志：v3-output/WT713-HUNT1/repro_idem_launder.py
  + repro_idem_launder.log.txt；本文件为正式回归钉。
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
    """write 工具桩（与 repro_idem_launder.py 同构；execute 计数器暴露重复执行）。"""

    name = "stub_write_thing"
    description = "stub write tool"
    category = ToolCategory.TASK
    parameters_schema = _WriteParams
    requires_confirmation = False
    timeout_seconds = 5.0
    effect = "write"
    risk = "low"
    reversible = True
    required_permission = "task.write"
    cost_usd = 0.0

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


class _RecordingLLM:
    """修正轮 LLM 桩：恒回「同工具、新 id」的修正调用；实录被调次数。"""

    def __init__(self, tool_name: str = "stub_write_thing"):
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


class _ReadParams(BaseModel):
    title: str = "t"


class _StubReadTool:
    """read 工具桩（绿回归对照用：非闸门失败的修正链路须原样可用）。"""

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


def _install_write_registry(monkeypatch, tool: _StubWriteTool):
    namespace = SimpleNamespace(
        get_tool=lambda name: tool if name == tool.name else None,
        get_tool_metadata=lambda name: (
            SimpleNamespace(
                name=tool.name,
                effect="write",
                risk="low",
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
async def idem_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _make_user(session) -> User:
    user = User(id=uuid4(), username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@x.io", hashed_password="t")
    session.add(user)
    await session.commit()
    return user


async def _ledger_rows(session) -> list[AgentToolCall]:
    return (await session.execute(select(AgentToolCall))).scalars().all()


def _gate_result(error_type: str, error_message: str) -> ToolResult:
    return ToolResult(
        success=False,
        tool_name="stub_write_thing",
        error_message=error_message,
        error_type=error_type,
    )


# ---------------------------------------------------------------------------
# 1. 运行级主战场：真 executor 闸门 + 真账本 → 自修正环不得洗白
# ---------------------------------------------------------------------------


class TestIdempotencyConflictNotLaundered:
    async def test_conflict_refusal_survives_self_correction_loop(self, monkeypatch, idem_db):
        """红→绿主场景（repro_idem_launder.py 固化）：

        红（wt713 实录）：attempt1 持键 K 真执行 → 账本行回写 in_progress 模拟
        在飞 → attempt2 同键恒拒 IdempotencyConflict → 失败喂 handle_tool_error
        （修正 LLM 回同工具新 id）→ 真 executor 以 fresh id 放行 →
        execute_count=2——并发冲突拒绝被洗白成第二次真执行。

        绿（本修复）：闸门拒绝不进修正环——execute_count 恒 1，原始
        IdempotencyConflict 原样上报，LLM 修正轮零调用，账本零新开行。
        """
        tool = _StubWriteTool()
        _install_write_registry(monkeypatch, tool)
        user = await _make_user(idem_db)
        uid = str(user.id)
        executor = ToolExecutor()
        handler = AgentErrorHandler()

        # attempt1：持键 K 真执行（count=1）
        r1 = await executor.execute_tool_call(
            tool_name=tool.name, arguments={"title": "t"}, user_id=uid, db_session=idem_db, idempotency_key="K"
        )
        await idem_db.commit()
        assert r1.success is True
        assert tool.execute_count == 1

        # 账本行回写 in_progress，模拟并发在飞
        rows = await _ledger_rows(idem_db)
        assert len(rows) == 1
        rows[0].status = "in_progress"
        await idem_db.commit()

        # attempt2：同键 → IdempotencyConflict（闸门本体正确）
        r2 = await executor.execute_tool_call(
            tool_name=tool.name, arguments={"title": "t"}, user_id=uid, db_session=idem_db, idempotency_key="K"
        )
        assert r2.success is False
        assert r2.error_type == "IdempotencyConflict"
        assert tool.execute_count == 1

        # 失败喂自修正环（chat.py 四面的真实漏斗）
        llm = _RecordingLLM()
        went_into_correction = handler.should_retry(r2)
        final = await handler.handle_tool_error(
            llm_service=llm,
            tool_result=r2,
            original_request={"id": "orig", "function": {"name": tool.name, "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=uid,
            db_session=idem_db,
        )
        await idem_db.commit()

        assert went_into_correction is False  # 排除集命中：修正轮不进
        assert llm.calls == 0  # 不烧 LLM 修正轮
        assert tool.execute_count == 1  # 不洗白成第二次真执行
        assert final.success is False  # 原始拒绝原样上报
        assert final.error_type == "IdempotencyConflict"
        assert "自动修正已跳过" in (final.suggestion or "")
        rows = await _ledger_rows(idem_db)
        assert len(rows) == 1  # 账本零新开行

    async def test_key_required_fail_closed_not_laundered(self, monkeypatch, idem_db):
        """IdempotencyKeyRequired（fail-closed）同样不得被洗成执行。

        红：write 工具无键无 tool_call_id 被拒后喂修正环 → LLM 新 id 充当键 →
        执行放行（X-06「重试换键=显式决策」被自动环代行）。
        绿：拒绝原样上报，执行零发生，账本零开行。
        """
        tool = _StubWriteTool()
        _install_write_registry(monkeypatch, tool)
        user = await _make_user(idem_db)
        uid = str(user.id)
        executor = ToolExecutor()
        handler = AgentErrorHandler()

        r = await executor.execute_tool_call(
            tool_name=tool.name, arguments={"title": "t"}, user_id=uid, db_session=idem_db
        )
        assert r.success is False
        assert r.error_type == "IdempotencyKeyRequired"
        assert tool.execute_count == 0
        assert await _ledger_rows(idem_db) == []

        llm = _RecordingLLM()
        assert handler.should_retry(r) is False
        final = await handler.handle_tool_error(
            llm_service=llm,
            tool_result=r,
            original_request={"id": "orig", "function": {"name": tool.name, "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=uid,
            db_session=idem_db,
        )
        assert llm.calls == 0
        assert tool.execute_count == 0  # fail-closed 保持：执行零发生
        assert final.success is False
        assert final.error_type == "IdempotencyKeyRequired"
        assert await _ledger_rows(idem_db) == []

    async def test_args_mismatch_not_laundered(self, monkeypatch, idem_db):
        """IdempotencyArgsMismatch：同键已绑定不同参数 → 拒绝不进修正环。

        红：修正轮以新 id 携带原参数重调 → 新键无账本行 → 放行第二次执行。
        绿：拒绝原样上报，execute_count 恒 1。
        """
        tool = _StubWriteTool()
        _install_write_registry(monkeypatch, tool)
        user = await _make_user(idem_db)
        uid = str(user.id)
        executor = ToolExecutor()
        handler = AgentErrorHandler()

        r1 = await executor.execute_tool_call(
            tool_name=tool.name, arguments={"title": "t"}, user_id=uid, db_session=idem_db, idempotency_key="K"
        )
        await idem_db.commit()
        assert r1.success is True

        r2 = await executor.execute_tool_call(
            tool_name=tool.name,
            arguments={"title": "different"},
            user_id=uid,
            db_session=idem_db,
            idempotency_key="K",
        )
        assert r2.success is False
        assert r2.error_type == "IdempotencyArgsMismatch"
        assert tool.execute_count == 1

        llm = _RecordingLLM()
        assert handler.should_retry(r2) is False
        final = await handler.handle_tool_error(
            llm_service=llm,
            tool_result=r2,
            original_request={"id": "orig", "function": {"name": tool.name, "arguments": '{"title":"t"}'}},
            retry_count=0,
            user_id=uid,
            db_session=idem_db,
        )
        assert llm.calls == 0
        assert tool.execute_count == 1
        assert final.success is False
        assert final.error_type == "IdempotencyArgsMismatch"


# ---------------------------------------------------------------------------
# 2. 闸门面逐类钉死（should_retry / handle_batch_errors 漏斗）
# ---------------------------------------------------------------------------


class TestGateExclusionSet:
    @pytest.mark.parametrize(
        ("error_type", "error_message"),
        [
            ("IdempotencyConflict", "Previous attempt with idempotency key 'K' is still in progress"),
            ("IdempotencyArgsMismatch", "Idempotency key 'K' was already used with different arguments"),
            ("IdempotencyKeyRequired", "Tool 'stub_write_thing' has side effects; an idempotency key is required"),
        ],
        ids=["conflict", "args-mismatch", "key-required"],
    )
    def test_should_retry_false_for_gate_rejections(self, error_type, error_message):
        """三类幂等闸门拒绝：should_retry 恒 False（原行为默认 True=洗白入口）。"""
        assert AgentErrorHandler().should_retry(_gate_result(error_type, error_message)) is False

    def test_should_retry_still_true_for_ordinary_failures(self):
        """对照：非闸门失败走原有关键词/默认语义，不因排除集收窄而误伤。"""
        handler = AgentErrorHandler()
        assert handler.should_retry(_gate_result("ValidationError", "参数验证失败: title 缺失")) is True
        assert handler.should_retry(_gate_result("UnknownError", "something broke")) is True  # 默认重试语义保留
        assert handler.should_retry(_gate_result("PermissionDenied", "permission denied")) is False  # 既有排除项保留
        assert handler.should_retry(_gate_result("NoError", "")) is False  # 无错误信息不重试

    async def test_batch_funnel_gate_refusal_passes_through_unchanged(self, monkeypatch, idem_db):
        """/task 批量面漏斗（handle_batch_errors 不经 should_retry）：闸门拒绝原样通过。"""
        monkeypatch.setattr(error_handler_module, "tool_registry", SimpleNamespace(get_openai_tools_schema=lambda: []))
        user = await _make_user(idem_db)
        llm = _RecordingLLM()
        results = await AgentErrorHandler().handle_batch_errors(
            llm_service=llm,
            tool_results=[_gate_result("IdempotencyConflict", "still in progress")],
            original_requests=[{"function": {"name": "stub_write_thing", "arguments": '{"title":"t"}'}}],
            user_id=str(user.id),
            db_session=idem_db,
        )
        assert llm.calls == 0
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_type == "IdempotencyConflict"

    async def test_non_gate_failure_still_corrected(self, monkeypatch, idem_db):
        """绿回归对照：非闸门失败的自修正链路不受排除集影响（read 工具修正成功）。"""
        read_tool = _StubReadTool()
        namespace = SimpleNamespace(
            get_tool=lambda name: read_tool if name == read_tool.name else None,
            get_tool_metadata=lambda name: (
                SimpleNamespace(
                    name=read_tool.name,
                    effect="read",
                    risk="low",
                    reversible=True,
                    required_permission="task.read",
                    cost_usd=0.0,
                    is_side_effect=False,
                )
                if name == read_tool.name
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

        user = await _make_user(idem_db)
        llm = _RecordingLLM(tool_name="stub_get_task")
        failed = ToolResult(
            success=False,
            tool_name="stub_get_task",
            error_message="参数验证失败: title 缺失",
            error_type="ValidationError",
        )
        final = await AgentErrorHandler().handle_tool_error(
            llm_service=llm,
            tool_result=failed,
            original_request={"id": "orig", "function": {"name": "stub_get_task", "arguments": "{}"}},
            retry_count=0,
            user_id=str(user.id),
            db_session=idem_db,
        )
        assert llm.calls == 1  # 修正轮照常进入
        assert final.success is True
        assert read_tool.execute_count == 1
