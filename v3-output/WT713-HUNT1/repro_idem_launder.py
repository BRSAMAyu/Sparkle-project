"""WT713 hunt1 TEMP evidence probe v2 — DELETE AFTER RUN.

End-to-end through the REAL ToolExecutor gate with a stub write tool:
  1. write tool executes with idempotency key K, ledger row forced back to
     in_progress (simulating an in-flight attempt);
  2. second call with SAME key K → IdempotencyConflict (gate works);
  3. that failure is fed to AgentErrorHandler.handle_tool_error (chat.py's
     real retry path — only BudgetExceeded/IdempotencyInterrupted are filtered);
  4. correction LLM returns same tool with fresh id → real executor accepts
     fresh id as key (executor.py:517) → tool EXECUTES a second time while
     attempt 1 is still in_progress.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models.theater_candidate_bundle  # noqa: F401  (FK target tables must register)
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
    async def chat_with_tools(self, **kw):
        return SimpleNamespace(
            tool_calls=[
                {
                    "id": "fresh-correction-id",
                    "type": "function",
                    "function": {"name": "stub_write_thing", "arguments": '{"title":"t"}'},
                }
            ],
            content=None,
        )


async def main() -> int:
    tool = _StubWriteTool()
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
    executor_module.tool_registry = namespace
    error_handler_module.tool_registry = namespace
    class _Decision:
        allowed = True
        reason = "stub-allow"

        def to_dict(self):
            return {"allowed": True, "reason": "stub-allow"}

    executor_module.decide_tool_permission = lambda **kw: _Decision()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    db = factory()

    user = User(id=uuid4(), username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@x.io", hashed_password="t")
    db.add(user)
    await db.commit()
    uid = str(user.id)

    executor = ToolExecutor()

    # Attempt 1: real write through the gate with key K; then force its ledger
    # row back to in_progress to represent an in-flight concurrent attempt.
    r1 = await executor.execute_tool_call(
        tool_name="stub_write_thing",
        arguments={"title": "t"},
        user_id=uid,
        db_session=db,
        idempotency_key="K",
    )
    await db.commit()
    print("attempt1:", r1.success, "error:", r1.error_type, "count:", tool.execute_count)
    if not r1.success:
        print("ABORT: attempt1 did not execute; probe invalid")
        return 2

    rows = (await db.execute(select(AgentToolCall))).scalars().all()
    rows[0].status = "in_progress"
    await db.commit()

    # Attempt 2: same key → concurrent-duplicate guard.
    r2 = await executor.execute_tool_call(
        tool_name="stub_write_thing",
        arguments={"title": "t"},
        user_id=uid,
        db_session=db,
        idempotency_key="K",
    )
    print("attempt2 (same key):", r2.success, "error_type:", r2.error_type, "count:", tool.execute_count)

    # Feed the conflict through chat.py's retry path.
    handler = AgentErrorHandler()
    went_into_correction = handler.should_retry(r2)
    final = await handler.handle_tool_error(
        llm_service=_RecordingLLM(),
        tool_result=r2,
        original_request={"id": "orig", "function": {"name": "stub_write_thing", "arguments": '{"title":"t"}'}},
        retry_count=0,
        user_id=uid,
        db_session=db,
    )
    await db.commit()
    print("entered correction:", went_into_correction, "final.success:", final.success)
    print("tool execute_count after correction:", tool.execute_count)

    await db.close()
    await engine.dispose()

    if r2.error_type == "IdempotencyConflict" and went_into_correction and tool.execute_count == 2:
        print("RED: IdempotencyConflict laundered into a second real execution (count=2)")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
