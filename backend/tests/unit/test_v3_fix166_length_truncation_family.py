"""V3-FIX-166（owner T-length-finish-reason-surface）红绿锁.

wt468 审查轮7A 探针实锤：``finish_reason="length"``（provider 侧 max_tokens
上限截断）在 FIX-155 哨兵处与 ``"stop"`` 同判完成——llm_service 只留布尔
``_saw_finish_reason``（值面丢弃），REST /stream 面 done.completed=true、部分
回答照常落库为完整轮、无任何截断标记。用户症状与 FIX-155/160 同族（答案中途
戛然而止冒充完整答案），差异仅是 provider 授权截断。

契约决策（对齐 FIX-155 六帧冻结纪律）：**不新增帧型**——``length`` 视为截断族：
service 层照发 ``stream_truncated`` 终止标记（新增结构化字段
``truncation_reason="length"`` 区分截断亚型），路由层 done 帧
``completed=false + reason="length_truncated"``，本轮不落库；缺哨兵亚型
``reason`` 保持 ``"upstream_stream_truncated"`` 不变。
/redone 同族保守语义：截断族轮（含 length）不产出 tool_call_end（部分指令
不得静默执行，对齐 V3-FIX-61/155）。

红测（base 上红）：
1. service 层：provider 流末帧 finish_reason="length" → 必须产出
   ``stream_truncated``（truncation_reason="length"）——base 上无任何标记（红）。
2. service 层：length 流里的完整 tool_call 桶不得触发 tool_call_end——base 上
   照常产出（红）。
3. 路由层：length 截断流 → done.completed=false 且 reason="length_truncated"
   且本轮不落库——base 上 clean done(completed=true)+照常落库（红）。
4. 回归守卫：finish_reason="stop" 不误标（既有 155 锁同向）；缺哨兵亚型 reason
   保持 "upstream_stream_truncated" 不变。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.llm_service as llm_service_module
from app.api.deps import get_current_user
from app.api.v1.chat import router as chat_router
from app.core.agent_profiles import AgentRole
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider
from app.db.session import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.services.llm.base import LLMProvider
from app.services.llm_service import LLMService, StreamChunk

# --- service 层基建（对齐 test_v3_fix155_stream_eof_sentinel.py）-----------------


def _make_selection() -> LLMSelection:
    return LLMSelection(
        model_key="fix166-test-primary",
        config=ModelConfig(
            provider=ModelProvider.DEEPSEEK,
            model_name="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
        ),
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="v3-fix166 service test",
    )


def _make_service(provider: LLMProvider) -> LLMService:
    service = LLMService(enable_dynamic_routing=False)
    service.demo_mode = False
    service._current_selection = _make_selection()
    service._provider = provider
    return service


def _raw_chunk(*, content: str | None = None, tool_calls=None, finish_reason: str | None = None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish_reason)])


def _tool_delta_chunk(*, index: int, call_id: str | None, name: str | None, arguments: str | None):
    return SimpleNamespace(
        id=call_id,
        index=index,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class _ScriptedRawStreamProvider(LLMProvider):
    """暴露 .client.chat.completions.create 的脚本化原始流 provider。"""

    def __init__(self, chunks: list):
        self._chunks = chunks
        provider = self

        async def create(**params):
            async def gen() -> AsyncIterator:
                for chunk in provider._chunks:
                    yield chunk

            return gen()

        self.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    async def chat(self, messages, model, temperature: float = 0.7, **kwargs) -> str:
        return ""

    async def stream_chat(self, messages, model, temperature: float = 0.7, **kwargs):
        yield "unused"


class _PassthroughFallbackStub:
    async def execute_stream_with_fallback(
        self, selection, stream_fn, operation_type="stream_chat", require_tools=False
    ):
        async for chunk in stream_fn(selection):
            yield chunk


@pytest.fixture(name="passthrough_fallback")
def passthrough_fallback_fixture(monkeypatch: pytest.MonkeyPatch) -> _PassthroughFallbackStub:
    stub = _PassthroughFallbackStub()
    monkeypatch.setattr(llm_service_module, "llm_fallback_manager", stub)
    return stub


async def _collect(service: LLMService) -> list[StreamChunk]:
    events = []
    async for chunk in service.chat_stream_with_tools(
        system_prompt="sys",
        user_message="讲讲连续两天学习的方法",
        tools=[{"type": "function", "function": {"name": "get_situation_brief", "parameters": {}}}],
        conversation_history=[],
        user_context={"user_id": "fix166-user"},
    ):
        events.append(chunk)
    return events


# --- 红测 1：finish_reason="length" 是截断族，必须产出截断标记 -------------------


@pytest.mark.asyncio
async def test_length_finish_reason_yields_truncation_marker(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """provider 授权截断（max_tokens 掐断）：部分回答不得冒充完整答案。

    base 红：值面丢弃 finish_reason，'length' 与 'stop' 同判完成——无任何截断
    标记（wt468 审查轮7A 探针 P6 形态）。
    """
    chunks = [
        _raw_chunk(content="线性规划的第一步是确定目标函数，第二步是"),
        _raw_chunk(content="", finish_reason="length"),  # max_tokens 上限截断
    ]
    service = _make_service(_ScriptedRawStreamProvider(chunks))

    events = await _collect(service)
    markers = [e for e in events if e.type == "stream_truncated"]

    assert markers, (
        "finish_reason='length' 是 provider 授权截断（截断族），必须产出 "
        f"stream_truncated 标记，实际事件链: {[e.type for e in events]}"
    )
    assert (
        markers[0].truncation_reason == "length"
    ), f"length 截断亚型必须经结构化字段 truncation_reason 区分，实际: {markers[0]}"


@pytest.mark.asyncio
async def test_length_finish_reason_suppresses_tool_call_end(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """截断族同族保守语义：length 轮的完整 tool_call 桶也不产出 tool_call_end
    （max_tokens 掐断时工具参数可能不完整，部分指令不得静默执行）。

    base 红：'length' 被当作完整收尾，tool_call_end 照常产出（工具照常执行）。
    """
    chunks = [
        _raw_chunk(
            tool_calls=[_tool_delta_chunk(index=0, call_id="call_len", name="get_situation_brief", arguments="{}")]
        ),
        _raw_chunk(content="", finish_reason="length"),
    ]
    service = _make_service(_ScriptedRawStreamProvider(chunks))

    events = await _collect(service)
    types = [e.type for e in events]

    assert "stream_truncated" in types, f"length 轮必须带截断标记，实际: {types}"
    assert "tool_call_end" not in types, f"length 截断轮不得触发工具执行（tool_call_end 在场），实际: {types}"


@pytest.mark.asyncio
async def test_stop_finish_reason_is_not_truncation_family(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """回归守卫：'stop'（真正常收尾）不误标——截断族判定不扩面。"""
    chunks = [
        _raw_chunk(content="完整回答。"),
        _raw_chunk(content="", finish_reason="stop"),
    ]
    service = _make_service(_ScriptedRawStreamProvider(chunks))

    events = await _collect(service)

    assert not [
        e for e in events if e.type == "stream_truncated"
    ], f"finish_reason='stop' 不得误标截断，实际事件链: {[e.type for e in events]}"


# --- 红测 2：路由层 —— done.completed=false + reason=length_truncated + 不落库 ---


@pytest.fixture(name="sse_app")
async def sse_app_fixture(db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch):
    """chat router + 覆盖依赖（对齐 FIX-155 路由测）。"""
    app = FastAPI()
    app.include_router(chat_router, prefix="/api/v1/chat")

    async def _override_db():
        yield db_session

    async def _override_user():
        return test_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

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


@pytest.mark.asyncio
async def test_length_truncated_stream_yields_done_completed_false_and_skips_persistence(
    sse_app: FastAPI, db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """length 截断流 → done 帧 completed=false + reason=length_truncated 且不落库。

    base 红：无 length 感知——clean done(completed=true) + 部分文本照常落库为
    完整助手消息（部分回答冒充完整轮）。
    """
    _script_llm_stream(
        monkeypatch,
        [
            StreamChunk(type="text", content="线性规划的第一步是确定目标函数，第二步是"),
            StreamChunk(type="stream_truncated", truncation_reason="length"),
        ],
    )

    async with AsyncClient(
        transport=ASGITransport(app=sse_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "讲讲方法"})

    frames = _parse_sse_frames(resp.text)
    types = [f.get("type") for f in frames]
    done_frame = next((f for f in frames if f.get("type") == "done"), None)

    assert done_frame is not None, f"流必须以 done 帧收尾，实际事件链: {types}"
    assert (
        done_frame.get("completed") is False
    ), f"length 截断轮 done 帧必须 completed=false（截断族哨兵），实际: {done_frame}"
    assert (
        done_frame.get("reason") == "length_truncated"
    ), f"length 截断轮 done 帧 reason 必须为 length_truncated（亚型可观测），实际: {done_frame}"

    result = await db_session.execute(select(ChatMessage).where(ChatMessage.user_id == test_user.id))
    assert result.scalars().all() == [], "length 截断轮不得把部分文本落库为完整助手消息"


@pytest.mark.asyncio
async def test_missing_sentinel_truncation_keeps_upstream_reason(
    sse_app: FastAPI, db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """回归守卫：缺哨兵亚型（truncation_reason=None）reason 保持
    upstream_stream_truncated 不变——FIX-155 契约零回退。"""
    _script_llm_stream(
        monkeypatch,
        [
            StreamChunk(type="text", content="部分文本"),
            StreamChunk(type="stream_truncated"),
        ],
    )

    async with AsyncClient(
        transport=ASGITransport(app=sse_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "讲讲方法"})

    frames = _parse_sse_frames(resp.text)
    done_frame = next((f for f in frames if f.get("type") == "done"), None)

    assert done_frame is not None, "流必须以 done 帧收尾"
    assert done_frame.get("completed") is False, f"缺哨兵截断轮必须 completed=false，实际: {done_frame}"
    assert (
        done_frame.get("reason") == "upstream_stream_truncated"
    ), f"缺哨兵亚型 reason 必须保持 upstream_stream_truncated，实际: {done_frame}"


# --- 契约锁：docstring 声明 length_truncated 亚型 --------------------------------


def test_stream_route_docstring_declares_length_truncated_reason() -> None:
    """done 帧 reason 枚举契约必须在 docstring 契约块声明 length_truncated 亚型。"""
    import inspect

    from app.api.v1.chat import chat_stream

    doc = inspect.getdoc(chat_stream) or ""
    lines = [line.strip() for line in doc.splitlines()]
    # 捕获 "- done:" 条目及其缩进续行（reason 枚举跨行声明）
    done_block: list[str] = []
    in_done = False
    for line in lines:
        if line.startswith("- done:"):
            in_done = True
            done_block.append(line)
            continue
        if in_done:
            if line.startswith("- ") or not line:
                in_done = False
            else:
                done_block.append(line)
    done_decl = " ".join(done_block)
    assert done_block, "docstring 契约块必须保留 done 帧声明"
    assert (
        "length_truncated" in done_decl
    ), f"done 帧 docstring 契约必须声明 length_truncated 亚型（FIX-166），实际: {done_decl}"
