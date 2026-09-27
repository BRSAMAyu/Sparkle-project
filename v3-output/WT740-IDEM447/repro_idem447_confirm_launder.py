"""V3-FIX-447 运行级复现探针 · /confirm 面 IdempotencyInterrupted 被自修正环洗白.

触发链全链（HITL 首轮崩溃 → interrupted 账本行 → 同 action_id 重放）：
  attempt1  持意图键 hitl:{action_id}:{tool} 执行，内部 commit 后崩溃
            → X-09 两阶段收敛置账本行 interrupted（效果不可核实）；
  attempt2  用户重放同 action_id confirm → 同键恒拒 IdempotencyInterrupted（闸门正确）；
  漏斗      chat.py /confirm 面（:933/:963）`should_retry(r2)` → 修复前 True
            → handle_tool_error（修正 LLM 回同工具新 id）→ executor 以 fresh 键放行。

判据：修前 RED = entered correction True + execute_count=2 + fresh 键新账本行；
      修后 GREEN = entered correction False + execute_count=1 + 账本零新开行。
正式回归钉：backend/tests/unit/test_v3_fix447_idem_interrupted_confirm_no_launder.py。
运行：SECRET_KEY=x python v3-output/WT740-IDEM447/repro_idem447_confirm_launder.py
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.agent_run import AgentRun  # noqa: F401
from app.models.agent_tool_call import AgentToolCall  # noqa: F401
from app.models.base import Base
from app.models.user import User  # noqa: F401
from app.models.user import User
from app.orchestration import executor as executor_module
from app.orchestration.error_handler import AgentErrorHandler
from app.orchestration.executor import ToolExecutor
from app.tools.base import ToolCategory, ToolResult


class _Params(BaseModel):
    title: str = "t"


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
        if db_session is not None:
            # 内部 commit：把 executor 已 flush 的账本 in_progress 行提前落库
            await db_session.commit()
        if self.execute_count == 1:
            raise RuntimeError("exploded after internal commit (HITL first-round crash)")
        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data={"ok": True})


class _RecordingLLM:
    def __init__(self, tool_name: str):
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


async def main() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        # 只建本场景三表（全量 metadata 有 conftest 之外未互引的零散模型，避免 FK 解析噪声）
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, AgentRun.__table__, AgentToolCall.__table__]
            )
        )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()

    executor_module.tool_registry = SimpleNamespace(  # type: ignore[attr-defined]
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
    executor_module._ledger_session_factory = factory  # type: ignore[attr-defined]
    executor_module._agent_run_session_factory = factory  # type: ignore[attr-defined]

    class _Decision:
        allowed = True
        reason = "stub-allow"

        def to_dict(self):
            return {"allowed": True, "reason": "stub-allow"}

    executor_module.decide_tool_permission = lambda **kw: _Decision()  # type: ignore[attr-defined]

    user = User(id=uuid4(), username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@x.io", hashed_password="t")
    session.add(user)
    await session.commit()

    tool = _StubWriteTool()
    executor = ToolExecutor()
    handler = AgentErrorHandler()
    uid = str(user.id)
    intent_key = "hitl:act-1:stub_create_task"

    # attempt1：HITL 首轮 confirm——持意图键执行，内部 commit 后崩溃
    r1 = await executor.execute_tool_call(
        tool_name=tool.name, arguments={"title": "t"}, user_id=uid, db_session=session, idempotency_key=intent_key
    )
    print(f"attempt1: success={r1.success} error_type={r1.error_type} side_effect_state={r1.side_effect_state}")
    print(f"attempt1: execute_count={tool.execute_count}")

    async with factory() as fresh:
        rows = list((await fresh.execute(select(AgentToolCall))).scalars().all())
    print(f"ledger after attempt1: rows={len(rows)} status={rows[0].status if rows else None}")

    # attempt2：用户重放同 action_id confirm——同意图键
    r2 = await executor.execute_tool_call(
        tool_name=tool.name, arguments={"title": "t"}, user_id=uid, db_session=session, idempotency_key=intent_key
    )
    print(f"attempt2: success={r2.success} error_type={r2.error_type}")
    print(f"attempt2: execute_count={tool.execute_count}")

    # /confirm 面（chat.py :933/:963 形态）错误处理与自我修正
    entered = handler.should_retry(r2)
    final = await handler.handle_tool_error(
        llm_service=_RecordingLLM(tool.name),
        tool_result=r2,
        original_request={"function": {"name": tool.name, "arguments": '{"title":"t"}'}},
        retry_count=0,
        user_id=uid,
        db_session=session,
    )
    await session.commit()

    async with factory() as fresh:
        rows = list((await fresh.execute(select(AgentToolCall).order_by(AgentToolCall.created_at.asc()))).scalars().all())
    print("---")
    print(f"entered correction: {entered}")
    print(f"final: success={final.success} error_type={final.error_type}")
    print(f"execute_count: {tool.execute_count}")
    print(f"ledger rows: {len(rows)} -> {[r.status for r in rows]}")

    verdict = "RED (laundered: interrupted refusal corrected into a second real execution)" if (
        entered and final.success and tool.execute_count >= 2
    ) else "GREEN (interrupted refusal survives: no correction round, no re-execution)"
    print(f"VERDICT: {verdict}")

    await session.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
