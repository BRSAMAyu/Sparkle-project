"""TTFT-PROBE: reasoning progress status emission in generation_node.

背景：qwen3 混合模型流式下默认先产出 reasoning_content（实测 13-43s 才见
首个可见 token），此前 generation_node 把 reasoning 块整段丢弃——前端只拿到
一次静态“思考中”状态后长时间无任何帧（S18 假卡主害）。本组用例锁定：
  1. reasoning 块按节流窗口触发 THINKING 进度状态帧（不透传思考正文）；
  2. 节流窗口未到时不得发送进度帧；
  3. 进度帧失败绝不阻断文本生成主链。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.standard_workflow import generation_node
from app.orchestration.statechart_engine import WorkflowState


class _ReasoningThenTextLLM:
    """先吐若干 reasoning 块再吐正文，模拟 qwen3 思考档流式行为。"""

    def __init__(self, reasoning_chunks=6):
        self.reasoning_chunks = reasoning_chunks

    def is_thinking_mode(self):
        return True

    def get_current_selection(self):
        return SimpleNamespace(
            model_key="dashscope_standard_thinking",
            is_fallback=False,
            estimated_cost_per_1k=0.0003,
            config=SimpleNamespace(
                model_name="qwen3.8-flash",
                provider=SimpleNamespace(value="dashscope"),
                tier=SimpleNamespace(value="standard"),
            ),
        )

    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        for i in range(self.reasoning_chunks):
            yield SimpleNamespace(type="reasoning", reasoning_content=f"思考步骤{i}")
        yield SimpleNamespace(type="text", content="这是思考完成后的正式回答。")


def _make_state(stream_callback) -> WorkflowState:
    return WorkflowState(
        messages=[{"role": "user", "content": "帮我系统讲解一下拓扑排序。"}],
        context_data={
            "chat_mode": "standard",
            "reasoning_mode": "balanced",
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
            "stream_callback": stream_callback,
        },
    )


def _patch_llm(monkeypatch, fake_llm) -> None:
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service", AsyncMock(return_value=fake_llm)
    )
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service_for_tier",
        AsyncMock(return_value=fake_llm),
    )
    monkeypatch.setattr(
        "app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM"
    )


def _status_frames(callback):
    return [
        call.args[0]
        for call in callback.await_args_list
        if call.args and getattr(call.args[0], "HasField", None) and call.args[0].HasField("status_update")
    ]


@pytest.mark.asyncio
async def test_reasoning_chunks_emit_throttled_thinking_progress(monkeypatch):
    monkeypatch.setattr(
        "app.agents.standard_workflow._REASONING_PROGRESS_STATUS_INTERVAL_SECONDS", 0.0
    )
    fake_llm = _ReasoningThenTextLLM(reasoning_chunks=5)
    _patch_llm(monkeypatch, fake_llm)
    stream_callback = AsyncMock()

    new_state = await generation_node(_make_state(stream_callback))

    statuses = _status_frames(stream_callback)
    # 初始 THINKING（is_thinking_mode）+ 每个 reasoning 块触发的进度帧
    progress = [s for s in statuses if "已思考" in (s.status_update.details or "")]
    assert len(progress) == 5
    assert all(
        s.status_update.state == s.status_update.THINKING for s in progress
    )
    # 思考正文绝不透传：文本输出恰为 text 块内容（reasoning 不入 delta/full_response）
    assert new_state.messages[-1]["content"] == "这是思考完成后的正式回答。"


@pytest.mark.asyncio
async def test_reasoning_progress_silent_within_throttle_window(monkeypatch):
    monkeypatch.setattr(
        "app.agents.standard_workflow._REASONING_PROGRESS_STATUS_INTERVAL_SECONDS", 999.0
    )
    fake_llm = _ReasoningThenTextLLM(reasoning_chunks=6)
    _patch_llm(monkeypatch, fake_llm)
    stream_callback = AsyncMock()

    new_state = await generation_node(_make_state(stream_callback))

    statuses = _status_frames(stream_callback)
    # 窗口未到：不得出现任何“已思考 …秒”进度帧（其余既有状态帧不受此约束）
    assert not [s for s in statuses if "已思考" in (s.status_update.details or "")]
    assert new_state.messages[-1]["content"] == "这是思考完成后的正式回答。"


@pytest.mark.asyncio
async def test_reasoning_progress_failure_does_not_break_generation(monkeypatch):
    monkeypatch.setattr(
        "app.agents.standard_workflow._REASONING_PROGRESS_STATUS_INTERVAL_SECONDS", 0.0
    )
    fake_llm = _ReasoningThenTextLLM(reasoning_chunks=3)
    _patch_llm(monkeypatch, fake_llm)

    async def flaky_callback(resp):
        if (
            getattr(resp, "HasField", None)
            and resp.HasField("status_update")
            and "已思考" in (resp.status_update.details or "")
        ):
            raise RuntimeError("ws write failed")
        return None

    state = _make_state(flaky_callback)
    new_state = await generation_node(state)

    assert new_state.messages[-1]["content"] == "这是思考完成后的正式回答。"
