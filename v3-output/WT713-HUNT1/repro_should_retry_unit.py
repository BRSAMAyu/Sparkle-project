"""WT713 hunt1 TEMP evidence probe — DELETE AFTER RUN.

Claim: the AgentErrorHandler self-correction loop launders idempotency-gate
rejections into executed writes. Chain:
  1. executor rejects with IdempotencyConflict (concurrent duplicate guard);
  2. chat.py retry filter only excludes BudgetExceeded/IdempotencyInterrupted,
     and AgentErrorHandler.should_retry defaults to True for these messages;
  3. handle_tool_error asks the LLM for a "corrected" call and executes it
     with a FRESH model-generated tool_call_id and NO idempotency_key —
     executor line 517 accepts tool_call_id alone as key, no ledger row
     exists for it, so the write executes while the first attempt is still
     in progress (the exact duplicate the conflict rejection prevents).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.orchestration.error_handler import AgentErrorHandler
from app.tools.base import ToolResult


async def main() -> int:
    handler = AgentErrorHandler()

    # Step 1+2: conflict rejection message passes the retry filter?
    conflict = ToolResult(
        success=False,
        tool_name="task_create",
        error_type="IdempotencyConflict",
        error_message=(
            "Idempotency key 'hitl:abc:task_create' was already used ... still in progress "
            "for tool 'task_create'; side effect not re-executed"
        ),
    )
    retries = handler.should_retry(conflict)
    print("should_retry(IdempotencyConflict):", retries)

    mismatch = ToolResult(
        success=False,
        tool_name="task_create",
        error_type="IdempotencyArgsMismatch",
        error_message="Idempotency key 'k' was already used with different arguments for tool 'task_create'",
    )
    print("should_retry(IdempotencyArgsMismatch):", handler.should_retry(mismatch))

    keyreq = ToolResult(
        success=False,
        tool_name="task_create",
        error_type="IdempotencyKeyRequired",
        error_message="Tool 'task_create' has side effects; an idempotency key (or tool_call_id) is required",
    )
    print("should_retry(IdempotencyKeyRequired):", handler.should_retry(keyreq))

    # Step 3: fake LLM returns a corrected call with a fresh id; count executions.
    executions: list[dict] = []

    class FakeExecutor:
        def __init__(self):
            pass

        async def execute_tool_call(self, *, tool_name, arguments, user_id, db_session, tool_call_id=None, **kw):
            executions.append({"tool": tool_name, "tool_call_id": tool_call_id, "idempotency_key": kw.get("idempotency_key")})
            from app.tools.base import ToolResult as TR

            return TR(success=True, tool_name=tool_name, data={"ok": True})

    class FakeLLM:
        async def chat_with_tools(self, **kw):
            class R:
                content = ""
                tool_calls = [
                    {
                        "id": "fresh-model-id-xyz",
                        "function": {"name": "task_create", "arguments": '{"title":"fixed"}'},
                    }
                ]

            return R()

    import app.orchestration.executor as executor_module

    original_executor = executor_module.ToolExecutor
    executor_module.ToolExecutor = FakeExecutor
    try:
        corrected = await handler.handle_tool_error(
            llm_service=FakeLLM(),
            tool_result=conflict,
            original_request={
                "id": "orig-call-id",
                "function": {"name": "task_create", "arguments": '{"title":"t"}'},
            },
            retry_count=0,
            user_id="00000000-0000-0000-0000-000000000001",
            db_session=object(),
        )
    finally:
        executor_module.ToolExecutor = original_executor

    print("corrected.success:", corrected.success)
    print("executions:", executions)
    leaked_key = any(e["idempotency_key"] for e in executions)
    fresh_key = any(e["tool_call_id"] == "fresh-model-id-xyz" for e in executions)
    if retries and executions and fresh_key and not leaked_key:
        print("RED: conflict rejection laundered into a fresh-key execution (no intent key carried)")
        return 1
    print("GREEN: gate held")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
