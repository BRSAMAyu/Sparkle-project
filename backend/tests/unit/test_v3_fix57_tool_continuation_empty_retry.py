"""V3-FIX-57 · 工具轮续写空文本 —— 单次重试 + tool_result 摘要兜底 红绿锁.

wt400 FIX-53 复验暴露的新达路径（v3-output/WT400-FIX53-REVERIFY/raw/
{GJ15,GJ20}_local.jsonl）：REST /api/v1/chat/stream 工具轮协议链
tool_start→tool_result→(widget)→text→done 完整，但续写 LLM
（``continue_with_tool_results``）偶发返回 ``content=""``（finish 正常、
非异常非超时）——text 帧空，用户看到工具卡片后无 assistant 文本，
driver ``nonempty_text`` 判 FAIL。

同族对照：gRPC/WS 面（``execution_engine._continue_after_tool_result``）
已有"空 content → 兜底文案 + ``RESPONSE_FALLBACK_GENERATED_TOTAL`` 指标"
先例；REST 面（chat.py 三处续写调用点）两者皆无。

红测（base 上红）：
1. /stream 工具轮续写首轮空 → 单次重试取到非空文本（base 无重试：红）。
2. /stream 工具轮续写两轮皆空 → tool_result 摘要兜底文案下发
   （base 无兜底：红），且重试次数有界（恰 2 次）。
3. 非流式 POST /api/v1/chat 工具轮同族：续写两轮皆空 → 兜底文案
   （base：红）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.api.v1.chat import router as chat_router
from app.db.session import get_db
from app.models.user import User
from app.orchestration.executor import ToolExecutor
from app.services.llm_service import LLMResponse, StreamChunk
from app.tools.base import ToolResult

_FALLBACK_MARK = "已执行完成"

# --- 基建 ----------------------------------------------------------------------


@pytest.fixture(name="chat_app")
async def chat_app_fixture(db_session, test_user: User, monkeypatch: pytest.MonkeyPatch):
    """chat router + 覆盖依赖 + 脚本化工具边界（/stream 与非流式 / 共用）。"""
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

    async def _fake_execute_tool_calls(self, **kwargs):  # noqa: ANN001, ANN003
        calls = kwargs.get("tool_calls") or []
        return [
            ToolResult(
                success=True,
                tool_name=str(tc.get("function", {}).get("name") or ""),
                tool_call_id=str(tc.get("id") or ""),
                data={"ok": True},
            )
            for tc in calls
        ]

    monkeypatch.setattr(ToolExecutor, "execute_tool_call", _fake_execute_tool_call)
    monkeypatch.setattr(ToolExecutor, "execute_tool_calls", _fake_execute_tool_calls)

    # 记忆后台写 lane：单测隔离
    from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService

    monkeypatch.setattr(
        MemoryInferredWriteLaneService,
        "enqueue_from_chat_turn",
        staticmethod(lambda **kwargs: None),
    )

    yield app
    app.dependency_overrides.clear()


def _script_llm_stream(monkeypatch: pytest.MonkeyPatch, chunks: list[StreamChunk]) -> None:
    from app.api.v1 import chat as chat_module

    async def _scripted(**kwargs) -> AsyncIterator[StreamChunk]:
        for chunk in chunks:
            yield chunk

    monkeypatch.setattr(chat_module.llm_service, "chat_stream_with_tools", _scripted)


def _script_llm_chat_with_tools(monkeypatch: pytest.MonkeyPatch, tool_name: str = "get_situation_brief") -> None:
    """非流式面：首轮 LLM 直接给出一个工具调用。"""
    from app.api.v1 import chat as chat_module

    async def _scripted(**kwargs):
        return LLMResponse(
            content="",
            tool_calls=[
                {
                    "id": "call_ns1",
                    "type": "function",
                    "function": {"name": tool_name, "arguments": "{}"},
                }
            ],
            finish_reason="tool_calls",
        )

    monkeypatch.setattr(chat_module.llm_service, "chat_with_tools", _scripted)


def _script_continue(monkeypatch: pytest.MonkeyPatch, contents: list[str]) -> list[int]:
    """把续写调用脚本化为按序返回 contents；返回调用次数记录器。"""
    from app.api.v1 import chat as chat_module

    calls: list[int] = []

    async def _continue(**kwargs):
        idx = len(calls)
        calls.append(idx)
        text = contents[idx] if idx < len(contents) else contents[-1]
        return LLMResponse(content=text, tool_calls=None, finish_reason="stop")

    monkeypatch.setattr(chat_module.llm_service, "continue_with_tool_results", _continue)
    return calls


def _parse_sse_frames(raw: str) -> list[dict]:
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
    StreamChunk(type="tool_call_chunk", tool_call_id="call_r1", tool_name="get_situation_brief"),
    StreamChunk(type="tool_call_chunk", tool_call_id="call_r1", arguments="{}"),
    StreamChunk(
        type="tool_call_end",
        tool_call_id="call_r1",
        tool_name="get_situation_brief",
        full_arguments={},
    ),
]


# --- 红测 1：/stream 续写首轮空 → 单次重试 --------------------------------------


@pytest.mark.asyncio
async def test_stream_empty_continuation_retries_once(chat_app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    _script_llm_stream(monkeypatch, _TOOL_TURN_CHUNKS)
    calls = _script_continue(monkeypatch, ["", "根据查询结果，你已经完成过一步，下一步是……"])

    async with AsyncClient(
        transport=ASGITransport(app=chat_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "我卡住了"})

    frames = _parse_sse_frames(resp.text)
    text_frames = [f for f in frames if f.get("type") == "text"]
    joined = "".join(f.get("content") or "" for f in text_frames)

    assert len(calls) == 2, f"续写首轮空必须恰好重试一次（共 2 次调用），实际 {len(calls)} 次"
    assert joined.strip(), f"重试成功后 text 帧必须非空，实际帧: {text_frames}"
    assert "根据查询结果" in joined, f"必须下发重试取回的文本，实际: {joined!r}"
    assert frames and frames[-1].get("type") == "done", "流必须以 done 帧收尾"


# --- 红测 2：/stream 两轮皆空 → tool_result 摘要兜底 -----------------------------


@pytest.mark.asyncio
async def test_stream_empty_continuation_falls_back_to_tool_summary(
    chat_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    _script_llm_stream(monkeypatch, _TOOL_TURN_CHUNKS)
    calls = _script_continue(monkeypatch, ["", ""])

    async with AsyncClient(
        transport=ASGITransport(app=chat_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "帮我规划周末学习"})

    frames = _parse_sse_frames(resp.text)
    joined = "".join(f.get("content") or "" for f in frames if f.get("type") == "text")

    assert len(calls) == 2, f"重试必须有界（恰 2 次调用），实际 {len(calls)} 次"
    assert joined.strip(), f"兜底后 text 帧必须非空，实际事件链: {[f.get('type') for f in frames]}"
    assert _FALLBACK_MARK in joined, f"兜底文案必须是 tool_result 摘要同族文案，实际: {joined!r}"
    assert "get_situation_brief" in joined, f"兜底文案应携带工具名，实际: {joined!r}"
    assert frames and frames[-1].get("type") == "done", "流必须以 done 帧收尾"


# --- 红测 3：非流式面同族兜底 ----------------------------------------------------


@pytest.mark.asyncio
async def test_nonstream_empty_continuation_falls_back_to_tool_summary(
    chat_app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    _script_llm_chat_with_tools(monkeypatch)
    calls = _script_continue(monkeypatch, ["", ""])

    async with AsyncClient(
        transport=ASGITransport(app=chat_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat", json={"message": "我卡住了"})

    assert resp.status_code == 200, f"非流式 chat 应 200，实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert len(calls) == 2, f"续写重试必须有界（恰 2 次），实际 {len(calls)} 次"
    content = str(body.get("message") or "")
    assert content.strip(), f"兜底后回复必须非空，实际 body keys: {list(body)}"
    assert _FALLBACK_MARK in content, f"兜底文案必须是 tool_result 摘要同族文案，实际: {content!r}"
