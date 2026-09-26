"""V3-FIX-155（=台账 SSE EOF 缺哨兵行，owner T-stream-eof-sentinel-validation）红绿锁.

wt460 真栈 chaos S4b 实锤：上游 provider 优雅断连（SSE 流结束但无 ``[DONE]``
哨兵、无 ``finish_reason``）时，``chat_stream_with_tools`` 的消费循环正常退出，
部分上游内容被静默当作完整答案交付——无 error 帧、无截断标记、不换道、
照常落库（8/8 探针「成功」，答案恰为 mock 前 2 段 43 字节）。

根因：OpenAI 兼容流经 SDK 抽象后，「收到 [DONE] 正常收尾」与「连接被掐断」
坍缩成同一种「迭代正常结束」；唯一可用的区分信号是流末尾的
``finish_reason``。缺哨兵校验 ⇒ 截断不可见。

协议形态决策（对齐 FIX-53/63 六帧契约）：**不新增帧型**——done 帧携带
``completed`` 字段（缺省 true；false = 流被上游中断，``reason`` 给出原因）。
六帧枚举（text/tool_start/tool_result/widget/error/done）冻结不变，
docstring/OpenAPI 契约化（V3-FIX-63 同法）。

红测（base 上红）：
1. service 层：provider 流无 finish_reason 正常结束 → 必须产出
   ``stream_truncated`` 终止标记（base 上缺失 → 红）。
2. service 层：截断流里的完整 tool_call 桶不得触发 tool_call_end（截断轮
   不执行工具，对齐 V3-FIX-61「禁止以不完整参数静默执行工具」同向保守）。
3. 路由层：llm 流以 stream_truncated 收尾 → 客户端 done 帧 completed=false
   且本轮不落库（base 上 clean done + 照常落库 → 双红）。
4. 契约锁：/stream docstring（=OpenAPI description）声明 done completed 语义；
   generation_node（/ws/chat 面）显式处理 stream_truncated（可见 error 帧）
   而非静默吞掉（V3-FIX-63 源码契约锁同法）。
"""

from __future__ import annotations

import inspect
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

# --- service 层基建（对齐 test_v3_fix53_tool_call_stream_correlation.py）-------


def _make_selection() -> LLMSelection:
    return LLMSelection(
        model_key="fix155-test-primary",
        config=ModelConfig(
            provider=ModelProvider.DEEPSEEK,
            model_name="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
        ),
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="v3-fix155 service test",
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
        user_context={"user_id": "fix155-user"},
    ):
        events.append(chunk)
    return events


# --- 红测 1：优雅断连（无 finish_reason 正常收尾）必须产出截断标记 -------------


@pytest.mark.asyncio
async def test_graceful_eof_without_finish_reason_yields_truncation_marker(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """wt460 S4b 形态：文本 2 段后上游静默断连——不得冒充完整答案。"""
    chunks = [
        _raw_chunk(content="这是mock回复。模型qwen3.7-flash在模式broken_all下的"),
        _raw_chunk(content="第二句。"),  # 43 字节前 2 段后 EOF，无 [DONE]/finish_reason
    ]
    service = _make_service(_ScriptedRawStreamProvider(chunks))

    events = await _collect(service)
    markers = [e for e in events if e.type == "stream_truncated"]

    assert markers, (
        "上游流无 finish_reason 正常收尾必须产出 stream_truncated 截断标记，"
        f"实际事件链: {[e.type for e in events]}（base 上部分内容被静默当作完整答案）"
    )


@pytest.mark.asyncio
async def test_completed_stream_with_finish_reason_has_no_truncation_marker(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """正常收尾（finish_reason=stop）不误标——哨兵校验只对缺失闭流的形态触发。"""
    chunks = [
        _raw_chunk(content="第一段。"),
        _raw_chunk(content="第三句收尾。", finish_reason="stop"),
    ]
    service = _make_service(_ScriptedRawStreamProvider(chunks))

    events = await _collect(service)

    assert not [
        e for e in events if e.type == "stream_truncated"
    ], "带 finish_reason 的完整流不得产出截断标记，实际事件链: {[e.type for e in events]}"
    assert "".join(e.content or "" for e in events if e.type == "text") == "第一段。第三句收尾。"


@pytest.mark.asyncio
async def test_truncated_tool_call_bucket_suppresses_tool_call_end(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """截断轮不执行工具：无 finish_reason 时完整参数桶也不产出 tool_call_end。"""
    chunks = [
        _raw_chunk(
            tool_calls=[_tool_delta_chunk(index=0, call_id="call_x", name="get_situation_brief", arguments="{}")]
        ),
        # 上游在 finish_reason 前断连
    ]
    service = _make_service(_ScriptedRawStreamProvider(chunks))

    events = await _collect(service)
    types = [e.type for e in events]

    assert "stream_truncated" in types, f"截断流必须带截断标记，实际: {types}"
    assert "tool_call_end" not in types, f"截断轮不得触发工具执行（tool_call_end 在场），实际: {types}"


@pytest.mark.asyncio
async def test_mid_stream_exception_still_raises_without_truncation_marker(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    """异常断开走既有异常链（FIX-53 error 帧），不冒充截断标记也不静默。"""

    class _ExplodingProvider(_ScriptedRawStreamProvider):
        async def _boom(self):  # pragma: no cover - helper
            raise RuntimeError("boom")

    async def create(**params):
        async def gen() -> AsyncIterator:
            yield _raw_chunk(content="开头")
            raise RuntimeError("fix155 simulated upstream crash")

        return gen()

    provider = _ExplodingProvider([])
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    service = _make_service(provider)

    with pytest.raises(RuntimeError):
        await _collect(service)


# --- 红测 2：路由层 —— done.completed=false + 不落库 --------------------------


@pytest.fixture(name="sse_app")
async def sse_app_fixture(db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch):
    """chat router + 覆盖依赖（对齐 test_v3_fix53_chat_stream_route_sse.py）。"""
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
async def test_truncated_llm_stream_yields_done_completed_false_and_skips_persistence(
    sse_app: FastAPI, db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """llm 流截断 → done 帧 completed=false（显式中断哨兵）且不落库。

    base 上：stream_truncated 块被路由静默忽略 → clean done + 部分文本照常
    落库为完整助手消息（双红）。
    """
    _script_llm_stream(
        monkeypatch,
        [
            StreamChunk(type="text", content="这是mock回复。模型qwen3.7-flash在模式broken_all下的第二句。"),
            StreamChunk(type="stream_truncated", content="upstream stream ended without finish_reason"),
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
    ), f"截断轮 done 帧必须携带 completed=false（显式中断哨兵），实际: {done_frame}"
    assert done_frame.get("reason"), f"截断轮 done 帧必须携带 reason，实际: {done_frame}"

    result = await db_session.execute(select(ChatMessage).where(ChatMessage.user_id == test_user.id))
    assert result.scalars().all() == [], "截断轮不得把部分文本落库为完整助手消息（诚实性：不冒充完整轮）"


@pytest.mark.asyncio
async def test_normal_llm_stream_yields_done_completed_true(
    sse_app: FastAPI, db_session: AsyncSession, test_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """正常轮 done.completed=true —— completed 字段全轮显式，客户端单一判据。"""
    _script_llm_stream(monkeypatch, [StreamChunk(type="text", content="你好，我在")])

    async with AsyncClient(
        transport=ASGITransport(app=sse_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/chat/stream", json={"message": "你好"})

    frames = _parse_sse_frames(resp.text)
    done_frame = next((f for f in frames if f.get("type") == "done"), None)

    assert done_frame is not None, f"流必须以 done 帧收尾，实际: {[f.get('type') for f in frames]}"
    assert done_frame.get("completed") is True, f"正常轮 done 帧必须 completed=true，实际: {done_frame}"

    result = await db_session.execute(select(ChatMessage).where(ChatMessage.user_id == test_user.id))
    assert len(result.scalars().all()) == 2, "正常轮 user+assistant 消息照常落库"


# --- 红测 3：契约锁（docstring/OpenAPI + /ws/chat 面处理） ---------------------


def test_stream_route_docstring_declares_done_completed_contract() -> None:
    """done 帧 completed/reason 语义必须在 docstring 契约块声明（=OpenAPI）。"""
    from app.api.v1.chat import chat_stream

    doc = inspect.getdoc(chat_stream) or ""
    done_lines = [line.strip() for line in doc.splitlines() if line.strip().startswith("- done:")]
    assert done_lines, "docstring 契约块必须保留 done 帧声明"
    done_decl = " ".join(done_lines)
    assert "completed" in done_decl, f"done 帧契约必须声明 completed 字段语义，实际: {done_decl}"
    assert "终止" in done_decl, "done 帧契约必须声明终止语义（V3-FIX-63 契约锁不回归）"

    # 契约锁：帧型枚举仍为六帧（本修复不新增帧型）
    source = inspect.getsource(chat_stream)
    import re

    emitted = set(re.findall(r"\{'type': '(\w+)'", source))
    assert emitted == {
        "text",
        "tool_start",
        "tool_result",
        "widget",
        "error",
        "done",
    }, f"六帧契约被破坏: {sorted(emitted)}——新增帧型必须走契约变更而非字段扩展"


def test_ws_chat_generation_node_handles_truncation_explicitly() -> None:
    """/ws/chat 面定界（同病修）：generation_node 必须显式处理 stream_truncated——
    置可见中断标记（context flag + error 帧下行），不得静默吞掉继续装完整轮。
    """
    from app.agents import standard_workflow

    source = inspect.getsource(standard_workflow.WorkflowState)  # noqa: F841 (guard import shape)
    node_source = inspect.getsource(standard_workflow.generation_node)
    assert 'chunk.type == "stream_truncated"' in node_source, (
        "/ws/chat 面同病：generation_node 必须处理 stream_truncated 块（wt460 S4b 实锤面），"
        "否则截断标记在 workflow 层被重新静默"
    )
    assert "stream_truncated" in inspect.getsource(standard_workflow), "截断标记必须进 workflow 模块契约"
    from app.orchestration import response_builder

    assert "generation_stream_truncated" in inspect.getsource(
        response_builder
    ), "截断旗标必须透传进最终响应 metadata（gRPC 面审计可见）"


def test_llm_service_stream_truncated_chunk_is_declared_contract() -> None:
    """StreamChunk 契约面：stream_truncated 是 llm_service 流的声明终结形态之一。"""
    from app.services import llm_service as mod

    src = inspect.getsource(mod.LLMService.chat_stream_with_tools)
    assert '"stream_truncated"' in src, "chat_stream_with_tools 必须产出 stream_truncated 终止标记"
    assert "finish_reason" in src, "哨兵校验必须基于 finish_reason 闭环判定"
