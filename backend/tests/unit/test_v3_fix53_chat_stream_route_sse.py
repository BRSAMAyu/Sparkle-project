"""V3-FIX-53 · chat 工具意图轮次流中断 —— HTTP 面（/api/v1/chat/stream）红绿锁.

wt394 Q-02 终验（GJ04/08/09/10/15/20 同根因）：工具意图轮 200+空体 /
ECONNRESET，纯文本轮"看似正常"。真栈异常栈钉死两处叠加缺陷：

1. **根因**：``event_generator`` 收尾 ``save_chat_message(conversation_id=...)``
   —— 函数签名只收 ``session_id``（``_normalize_conversation_id`` 形态），
   TypeError 打断流：工具轮（此前零 yield）= 200+空体；文本轮 = 正文后
   断尾（无 done、消息不落库）。
2. **沉默放大**：生成器无 try/except、无 log.exception —— 任何异常都是
   静默断流；且首个工具调用的 tool_start 条件要求 ``collected_tool_calls_raw``
   非空，首个工具调用永远不宣布开始。

红测（base 上红）：
1. 工具轮：SSE 全事件链 tool_start→tool_result→text→done 正确成帧（``\\n\\n``）
   且消息落库；base 上 TypeError 直接打断（红）。
2. 文本轮：流必须以 done 帧收尾且消息落库；base 上 done 永不到达（红）。
3. 上游生成器中途异常：客户端必须收到 error 事件而非裸断连（红）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.chat import router as chat_router
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.orchestration.executor import ToolExecutor
from app.services.llm_service import LLMResponse, StreamChunk
from app.tools.base import ToolResult

# --- 基建 ----------------------------------------------------------------------


@pytest.fixture(name="sse_app")
async def sse_app_fixture(db_session, test_user: User, monkeypatch: pytest.MonkeyPatch):
    """chat router + 覆盖依赖 + 脚本化 llm/工具边界（真 save_chat_message 落 sqlite）。"""
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")

    async def _override_db():
        yield db_session

    async def _override_user():
        return test_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    # 工具执行边界：成功 ToolResult（避免真实工具的 Redis/外部依赖）
    async def _fake_execute_tool_call(self, **kwargs):  # noqa: ANN001, ANN003
        return ToolResult(
            success=True,
            tool_name=str(kwargs.get("tool_name") or ""),
            tool_call_id=str(kwargs.get("tool_call_id") or ""),
            data={"ok": True},
        )

    monkeypatch.setattr(ToolExecutor, "execute_tool_call", _fake_execute_tool_call)

    # 记忆后台写 lane：单测隔离（fire-and-forget 后台任务不入断言面）
    from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

    monkeypatch.setattr(
        MemoryInferredWriteLaneService,
        "enqueue_from_chat_turn",
        staticmethod(lambda **kwargs: None),
    )

    yield app
    app.dependency_overrides.clear()


def _script_llm_stream(
    monkeypatch: pytest.MonkeyPatch,
    chunks: list[StreamChunk] | Exception,
) -> None:
    """把路由面用的 llm_service 单例流式方法替换为脚本化生成器。"""
    from app.api.v1 import chat as chat_module

    async def _scripted(**kwargs) -> AsyncIterator[StreamChunk]:
        if isinstance(chunks, Exception):
            raise chunks
        for chunk in chunks:
            yield chunk

    monkeypatch.setattr(chat_module.llm_service, "chat_stream_with_tools", _scripted)


def _script_continue(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    from app.api.v1 import chat as chat_module

    async def _continue(**kwargs):
        return LLMResponse(content=text, tool_calls=None, finish_reason="stop")

    monkeypatch.setattr(chat_module.llm_service, "continue_with_tool_results", _continue)


def _parse_sse_frames(raw: str) -> list[dict]:
    """按 SSE 规范以空行分隔帧解析 data 载荷（\\n\\n 成帧 = 本卡协议锁）。"""
    frames = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        for line in block.splitlines():
            if line.startswith("data: "):
                frames.append(json.loads(line[6:]))
    return frames


_TOOL_TURN_CHUNKS = [
    StreamChunk(type="text", content="让我看看你的情况"),
    StreamChunk(type="tool_call_chunk", tool_call_id="call_r1", tool_name="get_situation_brief"),
    StreamChunk(type="tool_call_chunk", tool_call_id="call_r1", arguments="{}"),
    StreamChunk(
        type="tool_call_end",
        tool_call_id="call_r1",
        tool_name="get_situation_brief",
        full_arguments={},
    ),
]


# --- 红测 1：工具轮全事件链 + 成帧 + 落库 --------------------------------------


@pytest.mark.asyncio
async def test_tool_turn_emits_full_event_chain(
    sse_app: FastAPI, db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    _script_llm_stream(monkeypatch, _TOOL_TURN_CHUNKS)
    _script_continue(monkeypatch, "根据查询结果，你已经完成过一步，下一步是……")

    async with AsyncClient(
        transport=ASGITransport(app=sse_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "我卡住了"})

    frames = _parse_sse_frames(resp.text)
    types = [f.get("type") for f in frames]

    assert "tool_start" in types, f"首个工具调用必须宣布 tool_start，实际事件链: {types}"
    assert "tool_result" in types, f"工具执行结果必须下发，实际事件链: {types}"
    assert "text" in types, f"续写文本必须下发，实际事件链: {types}"
    assert types and types[-1] == "done", f"流必须以 done 帧收尾，实际事件链: {types}"

    # 单个工具调用恰宣布一次 tool_start（chunk 帧 + end 帧不重复）
    assert types.count("tool_start") == 1, f"单工具调用应恰一次 tool_start，实际事件链: {types}"

    # 首个 tool_start 出现在 tool_result 之前（客户端先见"开始"）
    assert types.index("tool_start") < types.index("tool_result")

    # tool_result 携带工具名（下游客户端可渲染卡片）
    tool_result_frame = next(f for f in frames if f.get("type") == "tool_result")
    assert tool_result_frame["result"]["tool_name"] == "get_situation_brief"

    # 消息落库（save_chat_message 修复锁：user+assistant 两行）
    result = await db_session.execute(select(ChatMessage).where(ChatMessage.user_id == test_user.id))
    rows = result.scalars().all()
    assert len(rows) == 2, f"本轮 user+assistant 消息必须落库，实际 {len(rows)} 行"
    assert {r.role.value for r in rows} == {"user", "assistant"}


# --- 红测 2：文本轮以 done 收尾 + 落库 -----------------------------------------


@pytest.mark.asyncio
async def test_text_turn_completes_with_done(
    sse_app: FastAPI, db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    _script_llm_stream(
        monkeypatch, [StreamChunk(type="text", content="你好"), StreamChunk(type="text", content="，我在")]
    )

    async with AsyncClient(
        transport=ASGITransport(app=sse_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "你好"})

    frames = _parse_sse_frames(resp.text)
    types = [f.get("type") for f in frames]

    assert types == ["text", "text", "done"], f"文本轮事件链必须为 text×N+done，实际: {types}"
    assert "".join(f.get("content") or "" for f in frames if f.get("type") == "text") == "你好，我在"

    result = await db_session.execute(select(ChatMessage).where(ChatMessage.user_id == test_user.id))
    assert len(result.scalars().all()) == 2


# --- 红测 3：上游生成器异常 → error 事件而非静默断流 ---------------------------


@pytest.mark.asyncio
async def test_upstream_failure_emits_error_event(
    sse_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    _script_llm_stream(monkeypatch, RuntimeError("fix53 simulated upstream failure"))

    async with AsyncClient(
        transport=ASGITransport(app=sse_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "我卡住了"})

    frames = _parse_sse_frames(resp.text)
    types = [f.get("type") for f in frames]

    assert "error" in types, f"客户端必须收到 error 事件（本轮失败可见），实际事件链: {types}"
    assert types and types[-1] == "done", f"error 后仍需 done 帧收尾让客户端收束，实际事件链: {types}"
