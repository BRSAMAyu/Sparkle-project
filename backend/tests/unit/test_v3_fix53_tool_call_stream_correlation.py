"""V3-FIX-53 · chat 工具意图轮次流中断 —— service 层红绿锁.

缺陷（wt394 Q-02 终验 6 条黄金旅程同根因，真栈 10+ 次复现）：

``chat_stream_with_tools`` 对 provider 流式 tool_call 增量按 ``tc_chunk.id``
关联。OpenAI 流式契约（GLM 兼容层实测遵守）是**以 ``index`` 关联同一
tool call 的增量**：首帧带 ``id`` + ``function.name``，后续增量帧
``id=None``、``function.name=None``、只带 ``arguments``。按 id 关联后
name 与 arguments 被拆进不同桶，流末尾 ``data["name"] and data["args_str"]``
恒假 → ``tool_call_end`` 永不产出 → 工具永不执行、客户端 200+空体。

红测（base 上红）：
1. index 关联：首帧带 id/name、后续帧 id=None 只带 arguments —— 必须产出
   恰一个 ``tool_call_end``（name + full_arguments 正确），且全部
   ``tool_call_chunk`` 帧携带稳定非空 ``tool_call_id``（路由层依赖它聚合并
   触发 tool_start）。
2. id 回显型 provider（每帧都带同一 id）不回归 —— 仍恰一个 tool_call_end。
3. 无参工具（arguments 为 "{}"/""）也必须产出 tool_call_end（full_arguments={}）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

import app.services.llm_service as llm_service_module
from app.core.agent_profiles import AgentRole
from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider
from app.services.llm.base import LLMProvider
from app.services.llm_service import LLMService

# --- 基建：脚本化 provider 原始流（对齐 tests/test_m2_stream_variance_guards.py）---


def _make_selection() -> LLMSelection:
    return LLMSelection(
        model_key="fix53-test-primary",
        config=ModelConfig(
            provider=ModelProvider.DEEPSEEK,
            model_name="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
        ),
        agent_role=AgentRole.GENERATION,
        task_type=None,
        reason="v3-fix53 service test",
    )


def _make_service(provider: LLMProvider) -> LLMService:
    service = LLMService(enable_dynamic_routing=False)
    service.demo_mode = False
    service._current_selection = _make_selection()
    service._provider = provider
    return service


def _tool_delta_chunk(
    *,
    index: int | None,
    call_id: str | None,
    name: str | None,
    arguments: str | None,
):
    """OpenAI 流式 tool_call 增量帧（SimpleNamespace 形态，字段同 openai SDK）。"""
    return SimpleNamespace(
        id=call_id,
        index=index,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _raw_chunk(*, content: str | None = None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


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


def _provider_with(chunks: list) -> _ScriptedRawStreamProvider:
    return _ScriptedRawStreamProvider(chunks)


class _PassthroughFallbackStub:
    """直通 stub：镜像 execute_stream_with_fallback 的健康路径（M-2 同法）。"""

    def __init__(self) -> None:
        self.attempts = 0

    async def execute_stream_with_fallback(
        self, selection, stream_fn, operation_type="stream_chat", require_tools=False
    ):
        self.attempts += 1
        async for chunk in stream_fn(selection):
            yield chunk


@pytest.fixture(name="passthrough_fallback")
def passthrough_fallback_fixture(monkeypatch: pytest.MonkeyPatch) -> _PassthroughFallbackStub:
    stub = _PassthroughFallbackStub()
    monkeypatch.setattr(llm_service_module, "llm_fallback_manager", stub)
    return stub


# --- 红测 1：OpenAI/GLM 契约 —— 增量帧 id=None，须按 index 关联 ----------------


@pytest.mark.asyncio
async def test_index_correlated_tool_call_yields_single_tool_call_end(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    chunks = [
        _raw_chunk(content="让我先查一下"),
        # 首帧：带 id + name（GLM 实测形态）
        _raw_chunk(tool_calls=[_tool_delta_chunk(index=0, call_id="call_fix53", name="get_situation_brief", arguments="")]),
        # 后续增量帧：id=None、name=None、只带 arguments（OpenAI 流式契约）
        _raw_chunk(tool_calls=[_tool_delta_chunk(index=0, call_id=None, name=None, arguments='{"include_actions"')]),
        _raw_chunk(tool_calls=[_tool_delta_chunk(index=0, call_id=None, name=None, arguments=": true}")]),
    ]
    service = _make_service(_provider_with(chunks))

    events = []
    async for chunk in service.chat_stream_with_tools(
        system_prompt="sys",
        user_message="我卡住了",
        tools=[{"type": "function", "function": {"name": "get_situation_brief", "parameters": {}}}],
        conversation_history=[],
        user_context={"user_id": "fix53-user"},
    ):
        events.append(chunk)

    chunk_events = [e for e in events if e.type == "tool_call_chunk"]
    end_events = [e for e in events if e.type == "tool_call_end"]
    text = "".join(e.content or "" for e in events if e.type == "text")

    # 全部 tool_call_chunk 帧携带稳定非空 tool_call_id（路由层聚合依赖）
    assert chunk_events, "tool_call_chunk 增量帧必须下发（客户端可见工具开始）"
    assert all(e.tool_call_id for e in chunk_events), (
        f"tool_call_chunk 帧的 tool_call_id 必须稳定非空，实际: "
        f"{[(e.tool_call_id, e.tool_name, e.arguments) for e in chunk_events]}"
    )
    assert {e.tool_call_id for e in chunk_events} == {"call_fix53"}

    # 恰一个 tool_call_end，name/arguments 正确聚合（base 上为 0 个 → 红）
    assert len(end_events) == 1, (
        f"必须恰好产出 1 个 tool_call_end，实际 {len(end_events)} 个；"
        "id=None 的增量帧按 id 关联会拆进不同桶导致 tool_call_end 永不产出"
    )
    assert end_events[0].tool_call_id == "call_fix53"
    assert end_events[0].tool_name == "get_situation_brief"
    assert end_events[0].full_arguments == {"include_actions": True}

    # 文本帧不受影响
    assert "让我先查一下" in text
    assert passthrough_fallback.attempts == 1


# --- 红测 2：id 回显型 provider 不回归 ---------------------------------------


@pytest.mark.asyncio
async def test_id_echoing_provider_still_yields_single_tool_call_end(
    passthrough_fallback: _PassthroughFallbackStub,
) -> None:
    chunks = [
        _raw_chunk(tool_calls=[_tool_delta_chunk(index=0, call_id="call_echo", name="suggest_quick_task", arguments='{"t')]),
        _raw_chunk(tool_calls=[_tool_delta_chunk(index=0, call_id="call_echo", name="suggest_quick_task", arguments='itle":"复习"}')]),
    ]
    service = _make_service(_provider_with(chunks))

    end_events = []
    async for chunk in service.chat_stream_with_tools(
        system_prompt="sys",
        user_message="帮我建个任务",
        tools=[],
        conversation_history=[],
        user_context={"user_id": "fix53-user"},
    ):
        if chunk.type == "tool_call_end":
            end_events.append(chunk)

    assert len(end_events) == 1, f"id 回显型 provider 也必须恰产出 1 个 tool_call_end，实际 {len(end_events)}"
    assert end_events[0].tool_call_id == "call_echo"
    assert end_events[0].tool_name == "suggest_quick_task"
    assert end_events[0].full_arguments == {"title": "复习"}


# --- 红测 3：无参工具（空/{}参数）必须产出 tool_call_end ----------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_args", ["{}", ""])
async def test_no_arg_tool_call_still_yields_tool_call_end(
    passthrough_fallback: _PassthroughFallbackStub, raw_args: str
) -> None:
    chunks = [
        _raw_chunk(tool_calls=[_tool_delta_chunk(index=0, call_id="call_noarg", name="get_situation_brief", arguments=raw_args)]),
    ]
    service = _make_service(_provider_with(chunks))

    end_events = []
    async for chunk in service.chat_stream_with_tools(
        system_prompt="sys",
        user_message="我卡住了",
        tools=[],
        conversation_history=[],
        user_context={"user_id": "fix53-user"},
    ):
        if chunk.type == "tool_call_end":
            end_events.append(chunk)

    assert len(end_events) == 1, (
        f"无参工具调用（arguments={raw_args!r}）也必须产出 tool_call_end，实际 {len(end_events)}；"
        "静默丢弃会让工具轮零事件收场"
    )
    assert end_events[0].full_arguments == {}
