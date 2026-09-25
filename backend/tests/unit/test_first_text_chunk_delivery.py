"""WT373 缺陷扫雷 #1 红绿契约：首块文本必须以 delta 帧送达客户端.

`_flush_stream_text_buffer`（及同文件同型的 memory/rescue/fallback 下发帧）
曾把 delta 文本与 GENERATING status 同置一个 proto ``content`` oneof——oneof
语义后写者覆盖先写者，delta 被 status 顶掉，首个文本块静默丢失（客户端永远
收不到第一个文字块）。修复后钉住两点契约：

1. 假 LLM 流首块必须以 delta 帧原文到达客户端（oneof 顶字回归守卫）；
2. GENERATING 状态信号不得回退丢失（网关 stage=answering 转换依赖它，
   修法不得走「只置 delta」捷径——拆两帧：status 先行，delta 随后）。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.standard_workflow import generation_node
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.statechart_engine import WorkflowState

_FIRST_CHUNK = "首块文本必须原样送达客户端。"


class _SingleChunkLLM:
    """只吐一个 text 块的假生成模型：隔离出「首块 flush 帧」这一条路径。"""

    agent_role = "deep_analyst"

    def is_thinking_mode(self):
        return False

    def get_current_selection(self):
        return SimpleNamespace(
            model_key="dashscope_fast",
            is_fallback=False,
            estimated_cost_per_1k=0.0001,
            config=SimpleNamespace(
                model_name="first-chunk-model",
                provider=SimpleNamespace(value="dashscope"),
                tier=SimpleNamespace(value="fast"),
            ),
        )

    async def chat_stream_with_tools(self, system_prompt, user_message, tools, user_context):
        yield SimpleNamespace(type="text", content=_FIRST_CHUNK)

    async def chat(self, messages, temperature=0.35):
        return _FIRST_CHUNK


@pytest.mark.asyncio
async def test_first_text_chunk_reaches_client_as_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = _SingleChunkLLM()
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service",
        AsyncMock(return_value=fake_llm),
    )
    monkeypatch.setattr(
        "app.agents.standard_workflow.get_configured_llm_service_for_tier",
        AsyncMock(return_value=fake_llm),
    )
    monkeypatch.setattr("app.agents.standard_workflow.build_system_prompt", lambda *args, **kwargs: "SYSTEM")

    captured: list[agent_service_pb2.ChatResponse] = []

    async def stream_callback(resp: agent_service_pb2.ChatResponse) -> None:
        captured.append(resp)

    state = WorkflowState(
        messages=[{"role": "user", "content": "请深度分析这个问题"}],
        context_data={
            "chat_mode": "deep_analysis",
            "selected_experts": ["deep_analyst"],
            "user_context": {},
            "conversation_context": {"messages": []},
            "tools_schema": [],
            "stream_callback": stream_callback,
        },
    )

    new_state = await generation_node(state)

    frame_dump = [(r.WhichOneof("content"), r.delta or r.status_update.details) for r in captured]
    assert captured, f"流应产生下发帧，实际为空: {frame_dump}"

    # 契约 1：首块文本必须以 delta 帧原文到达（缺陷下首 flush 帧只剩
    # status_update，delta 被 oneof 静默顶掉，本断言红）。
    delta_frames = [r for r in captured if r.WhichOneof("content") == "delta"]
    assert delta_frames, (
        f"首块文本必须以 delta 帧送达客户端，oneof 顶字缺陷下被 status 顶掉，实际帧序列: {frame_dump}"
    )
    assert delta_frames[0].delta == _FIRST_CHUNK, (
        f"客户端收到的首个 delta 应为首块原文 {_FIRST_CHUNK!r}，实际 {delta_frames[0].delta!r}"
    )

    # 契约 2：GENERATING 状态帧不得在修复中丢失（网关 GENERATING→answering
    # stage 转换依赖它），即修法须保留状态信号而非简单删掉 status。
    generating_frames = [
        r
        for r in captured
        if r.WhichOneof("content") == "status_update"
        and r.status_update.state == agent_service_pb2.AgentStatus.GENERATING
    ]
    assert generating_frames, (
        f"GENERATING 状态帧仍须先行下发（网关 answering stage 转换），实际帧序列: {frame_dump}"
    )

    # 主链不受影响：完整正文仍进入 state.messages。
    assert new_state.messages[-1]["content"] == _FIRST_CHUNK
