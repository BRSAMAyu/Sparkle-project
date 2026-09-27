"""V3-FIX-336 · per-tool-call 幂等键意图稳定（wt634 round-2 CONFIRMED 修复）.

问题（台账 v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-336）：幂等键以「尝试」
为唯一性来源（chat 轨 uuid 回落 / bridge 轨 fresh uuid）而非「意图」稳定——
同一逻辑工具调用跨尝试（重试/恢复重入）生成不同键 → 写副作用重复执行。

本文件红测（wt634 运行级实证的单元化）：
- chat 轨：同 session/request 锚点下两次尝试（模拟 LLM 重发、无模型 call id
  的 uuid 回落路径），断言幂等键相等 + 副作用恰一次；
- bridge 轨：同 request 两次短路调用，断言到达 executor 的有效键相等。

修前：两测全红（键不等 / 副作用 2 次）；修后：全绿。
X-06「同键重放恰一次」既有语义零放松（test_x06_tool_call_safety.py 护栏）。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents.standard_workflow import tool_execution_node
from app.models.agent_tool_call import AgentToolCall
from app.models.base import Base
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.execution_engine import ExecutionEngineMixin
from app.orchestration.statechart_engine import WorkflowState
from app.tools.base import ToolCategory, ToolResult
from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel, derive_tool_intent_idempotency_key


class _WriteParams(BaseModel):
    title: str = "t"


class _StubWriteTool:
    """side-effect 工具桩（与 test_x06_tool_call_safety 同构）。"""

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

    def __init__(self):
        self.execute_count = 0

    async def execute(self, params, user_id, db_session, tool_call_id=None, locale="en"):
        self.execute_count += 1
        return ToolResult(
            success=True,
            tool_name=self.name,
            tool_call_id=tool_call_id,
            data={"title": getattr(params, "title", None), "attempt": self.execute_count},
        )


_WRITE_METADATA = ToolMetadata(
    name="stub_create_task",
    effect=ToolEffect.WRITE,
    risk=ToolRiskLevel.MEDIUM,
    reversible=True,
    required_permission="task.write",
    cost_usd=0.0,
)


@pytest.fixture
async def guard_db():
    """独立 sqlite 引擎（executor 账本共用；test_x06_tool_call_safety 同款）。"""
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


def _install_registry(monkeypatch, tool: _StubWriteTool):
    monkeypatch.setattr(
        executor_module,
        "tool_registry",
        SimpleNamespace(
            get_tool=lambda name: tool if name == tool.name else None,
            get_tool_metadata=lambda name: _WRITE_METADATA if name == tool.name else None,
        ),
    )


async def _ledger_rows(session) -> list[AgentToolCall]:
    rows = (await session.execute(select(AgentToolCall).order_by(AgentToolCall.created_at))).scalars().all()
    return list(rows)


def _chat_state(user_id: str, *, request_id: str, tool_call_id: str | None) -> WorkflowState:
    state = WorkflowState()
    state.context_data.update(
        {
            "user_id": user_id,
            "session_id": "sess-fix336",
            "request_id": request_id,
            "db_session": None,  # 由测试注入点替换（见用例内 update）
            "redis_client": None,
            "tool_calls": [
                SimpleNamespace(
                    tool_call_id=tool_call_id,  # None = uuid 回落路径（尝试唯一键源头）
                    tool_name="stub_create_task",
                    full_arguments={"title": "a"},
                )
            ],
        }
    )
    return state


class TestChatTrackIntentStableKey:
    async def test_same_intent_retry_reuses_key_and_executes_once(self, monkeypatch, guard_db):
        """同一意图两次尝试（重试模拟）→ 幂等键相等、写副作用恰一次。

        模拟重试：同一 request 锚点、同参数；模型 call id 缺失（uuid 回落路径
        = wt634 亲证的尝试唯一键源）。修前：两次尝试键不等、副作用 2 次（红）。
        """
        user = await _make_user(guard_db.session)
        tool = _StubWriteTool()
        _install_registry(monkeypatch, tool)

        # attempt 1
        state1 = _chat_state(str(user.id), request_id="req-fix336-1", tool_call_id=None)
        state1.context_data["db_session"] = guard_db.session
        await tool_execution_node(state1)
        rows1 = await _ledger_rows(guard_db.session)
        assert len(rows1) == 1
        key1 = rows1[0].idempotency_key
        assert key1
        assert tool.execute_count == 1

        # attempt 2（模拟重试：同锚点同参数，新尝试 uuid 回落）
        state2 = _chat_state(str(user.id), request_id="req-fix336-1", tool_call_id=None)
        state2.context_data["db_session"] = guard_db.session
        await tool_execution_node(state2)

        rows2 = await _ledger_rows(guard_db.session)
        assert len(rows2) == 1, f"expected replay on same intent, got {len(rows2)} ledger rows"
        assert rows2[0].idempotency_key == key1, "same intent across attempts must reuse one idempotency key"
        assert tool.execute_count == 1, "duplicate side effect: write executed twice for same intent"
        assert rows2[0].status == "succeeded"

    async def test_different_request_is_new_intent_new_key(self, monkeypatch, guard_db):
        """显式再执行（新 request 锚点）= 新意图 → 新键、再次执行（X-06 语义不吞）。"""
        user = await _make_user(guard_db.session)
        tool = _StubWriteTool()
        _install_registry(monkeypatch, tool)

        state1 = _chat_state(str(user.id), request_id="req-A", tool_call_id=None)
        state1.context_data["db_session"] = guard_db.session
        await tool_execution_node(state1)

        state2 = _chat_state(str(user.id), request_id="req-B", tool_call_id=None)
        state2.context_data["db_session"] = guard_db.session
        await tool_execution_node(state2)

        rows = await _ledger_rows(guard_db.session)
        assert len(rows) == 2, "new explicit request must be a new execution decision"
        assert rows[0].idempotency_key != rows[1].idempotency_key
        assert tool.execute_count == 2


class TestBridgeTrackIntentStableKey:
    async def test_same_request_retry_produces_equal_keys(self):
        """bridge 短路：同 request 两次调用（进程内重试）→ 有效幂等键相等。

        有效键 = idempotency_key or tool_call_id（executor 闸门 :517 同一回落）。
        修前 bridge 键源为 fresh uuid → 两调不等（红）；修后 intent 键相等（绿）。
        """
        engine = _BridgeStubEngine()
        kwargs_list = []
        for _ in range(2):
            await engine._maybe_short_circuit_bridge_tool(
                active_tools=["launch_prediction"],
                user_message="Will I succeed in learning Python?",
                user_id="00000000-0000-0000-0000-000000000001",
                session_id="session-1",
                response_id="resp-1",
                request_id="req-1",
                trace_id="trace-1",
                workflow_id="workflow-1",
                prompt_version="v1",
                active_db=None,
            )
            call = engine.tool_executor.execute_tool_call.call_args_list[-1]
            kwargs_list.append(call.kwargs)

        def _effective_key(kwargs) -> str | None:
            return kwargs.get("idempotency_key") or kwargs.get("tool_call_id")

        key1 = _effective_key(kwargs_list[0])
        key2 = _effective_key(kwargs_list[1])
        assert key1 is not None, "bridge call must carry an idempotency key"
        assert key1 == key2, f"same request retried in-process must reuse one key, got {key1!r} vs {key2!r}"

    async def test_different_request_gets_different_key(self):
        """不同 request（用户显式重发）→ 新键（不吞合法再执行）。"""
        engine = _BridgeStubEngine()
        keys = []
        for req in ("req-1", "req-2"):
            await engine._maybe_short_circuit_bridge_tool(
                active_tools=["launch_prediction"],
                user_message="Will I succeed in learning Python?",
                user_id="00000000-0000-0000-0000-000000000001",
                session_id="session-1",
                response_id="resp-1",
                request_id=req,
                trace_id="trace-1",
                workflow_id="workflow-1",
                prompt_version="v1",
                active_db=None,
            )
            call = engine.tool_executor.execute_tool_call.call_args_list[-1]
            keys.append(call.kwargs.get("idempotency_key") or call.kwargs.get("tool_call_id"))

        assert keys[0] != keys[1]


class TestIntentKeyDerivation:
    """V3-FIX-336 · 派生助手纯函数契约。"""

    def test_deterministic_and_key_order_insensitive(self):
        a = derive_tool_intent_idempotency_key(
            tool_name="create_task", arguments={"title": "x", "priority": 1}, anchor="req-1"
        )
        b = derive_tool_intent_idempotency_key(
            tool_name="create_task", arguments={"priority": 1, "title": "x"}, anchor="req-1"
        )
        assert a == b
        assert a.startswith("intent:req-1:create_task:")

    def test_different_intent_yields_different_key(self):
        base = {"tool_name": "create_task", "arguments": {"title": "x"}, "anchor": "req-1"}
        same = derive_tool_intent_idempotency_key(**base)
        diff_args = derive_tool_intent_idempotency_key(**{**base, "arguments": {"title": "y"}})
        diff_tool = derive_tool_intent_idempotency_key(**{**base, "tool_name": "delete_task"})
        diff_anchor = derive_tool_intent_idempotency_key(**{**base, "anchor": "req-2"})
        assert len({same, diff_args, diff_tool, diff_anchor}) == 4

    def test_missing_or_blank_anchor_returns_none(self):
        assert derive_tool_intent_idempotency_key(tool_name="t", arguments={}, anchor=None) is None
        assert derive_tool_intent_idempotency_key(tool_name="t", arguments={}, anchor="  ") is None

    def test_key_fits_column_budget(self):
        key = derive_tool_intent_idempotency_key(
            tool_name="t" * 100, arguments={"k": "v"}, anchor="a" * 80
        )
        assert key is not None and len(key) <= 255


class _BridgeStubEngine(ExecutionEngineMixin):
    """最小 mixin 宿主（镜像 tests/unit/orchestrator/mixins 既有桩式）。"""

    def __init__(self):
        self.redis = None
        self.tool_executor = MagicMock(execute_tool_call=AsyncMock())
        self._persist_assistant_message = AsyncMock()
        self._cache_response = AsyncMock()
        self.tool_executor.execute_tool_call.return_value = MagicMock(
            success=True,
            data={"topic": "Will I succeed in learning Python?", "source_chat_session_id": "session-1"},
            model_dump=lambda: {"tool_name": "launch_prediction"},
        )
