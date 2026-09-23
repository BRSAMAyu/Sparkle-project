"""B-02 MIDSTREAM-HEARTBEAT 单测。

验证图执行静默段（建模图长工具/LLM 思考段，实测 50s+ 无帧）的周期心跳帧：
- 长静默下心跳帧按配置周期出现，内容诚实（仍在处理 + 已耗时，不伪造阶段进度）；
- 正常流（帧间隔 < 心跳间隔）不多发任何心跳帧；
- 帧身份（response/request/session/trace）与回合同源；
- 开关关闭或缺帧身份时不发心跳（行为与基线完全一致）。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from app.config import settings
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.execution_engine import ExecutionEngineMixin

FRAME_IDENTITY: dict[str, str] = {
    "response_id": "resp-1",
    "request_id": "req-1",
    "session_id": "sess-1",
    "workflow_id": "standard_chat",
    "prompt_version": "v2",
    "trace_id": "trace-1",
}


class _HeartbeatHarness(ExecutionEngineMixin):
    """Minimal orchestrator carrying only what _execute_graph needs."""

    def __init__(self, graph: Any) -> None:
        self.graph = graph
        self.token_tracker = None


class _FakeGraph:
    """Graph stub whose invoke() blocks for `delay` seconds (long LLM/tool segment)."""

    def __init__(self, delay: float, result: dict[str, Any] | None = None) -> None:
        self.delay = delay
        self.result = result if result is not None else {"messages": ["done"]}

    async def invoke(self, state: Any, resume_policy: str | None = None) -> dict[str, Any]:
        await asyncio.sleep(self.delay)
        return self.result


def _make_text_frame(text: str) -> agent_service_pb2.ChatResponse:
    return agent_service_pb2.ChatResponse(delta=text)


async def _feed(queue: asyncio.Queue, count: int, interval: float) -> None:
    for index in range(count):
        await asyncio.sleep(interval)
        await queue.put(_make_text_frame(f"chunk-{index}"))


async def _collect(harness: _HeartbeatHarness, queue: asyncio.Queue) -> tuple[list[Any], dict[str, Any]]:
    holder: dict[str, Any] = {}
    out: list[Any] = []
    async for item in harness._execute_graph(
        state=None,
        user_id="user-1",
        queue=queue,
        result_holder=holder,
        frame_identity=FRAME_IDENTITY,
    ):
        out.append(item)
    return out, holder


async def _collect_no_identity(harness: _HeartbeatHarness, queue: asyncio.Queue) -> list[Any]:
    holder: dict[str, Any] = {}
    out: list[Any] = []
    async for item in harness._execute_graph(
        state=None,
        user_id="user-1",
        queue=queue,
        result_holder=holder,
        frame_identity=None,
    ):
        out.append(item)
    return out


def _split_heartbeats(frames: list[Any]) -> tuple[list[Any], list[Any]]:
    heartbeats = [
        f for f in frames if f.WhichOneof("content") == "status_update" and f.metadata.get("stream_heartbeat") == "true"
    ]
    others = [f for f in frames if f not in heartbeats]
    return heartbeats, others


@pytest.mark.asyncio
async def test_heartbeat_frame_shape_is_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    """心跳帧内容诚实：THINKING + 已耗时，带 stream_heartbeat 标记与帧身份。"""
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", True)
    harness = _HeartbeatHarness(_FakeGraph(delay=0.0))
    frame = harness._build_stream_heartbeat_response(FRAME_IDENTITY, elapsed_seconds=23.4)

    assert frame.WhichOneof("content") == "status_update"
    assert frame.status_update.state == agent_service_pb2.AgentStatus.THINKING
    assert "23" in frame.status_update.details  # 已耗时，诚实
    assert "Still working" in frame.status_update.details
    # 帧身份与回合同源（网关/mobile 按 request_id 归组）
    assert frame.response_id == "resp-1"
    assert frame.request_id == "req-1"
    assert frame.session_id == "sess-1"
    assert frame.trace_id == "trace-1"
    assert frame.workflow_id == "standard_chat"
    assert frame.prompt_version == "v2"
    # metadata：ux_progress 可解析且不伪造阶段进度
    assert frame.metadata.get("stream_heartbeat") == "true"
    ux = json.loads(frame.metadata.get("ux_progress") or "{}")
    assert ux["heartbeat"] is True
    assert ux["is_blocked"] is False
    assert ux["stage"] == "processing"
    assert "elapsed" in ux["detail"]


@pytest.mark.asyncio
async def test_heartbeat_appears_periodically_during_long_silence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """长静默（mock 长任务 0.6s，心跳间隔 0.15s）下心跳按周期出现。"""
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", True)
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_INTERVAL_SECONDS", 0.15)

    harness = _HeartbeatHarness(_FakeGraph(delay=0.6))
    queue: asyncio.Queue = asyncio.Queue()
    frames, holder = await _collect(harness, queue)

    heartbeats, others = _split_heartbeats(frames)
    assert not others, "静默段除心跳外不应有其它帧"
    assert len(heartbeats) >= 2, f"0.6s 静默 + 0.15s 周期应产生 >=2 心跳，实际 {len(heartbeats)}"
    for hb in heartbeats:
        assert hb.request_id == "req-1"
        assert hb.session_id == "sess-1"
        assert hb.WhichOneof("content") == "status_update"
    # 心跳不代表终局：终局仍由 graph result 给出
    assert holder.get("final_state") == {"messages": ["done"]}
    assert holder.get("total_prompt_tokens") == 0


@pytest.mark.asyncio
async def test_no_extra_heartbeat_when_frames_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """正常流（帧间隔 0.08s < 心跳间隔 0.3s）零新增心跳帧。"""
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", True)
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_INTERVAL_SECONDS", 0.3)

    harness = _HeartbeatHarness(_FakeGraph(delay=0.55))
    queue: asyncio.Queue = asyncio.Queue()
    feeder = asyncio.create_task(_feed(queue, count=6, interval=0.08))
    frames, holder = await _collect(harness, queue)
    await feeder

    heartbeats, others = _split_heartbeats(frames)
    assert not heartbeats, f"帧流正常时不应有心跳，实际 {len(heartbeats)}"
    assert [f.delta for f in others] == [f"chunk-{i}" for i in range(6)]
    assert holder.get("final_state") == {"messages": ["done"]}
    assert holder.get("total_prompt_tokens") == 0


@pytest.mark.asyncio
async def test_usage_frames_still_aggregated_without_heartbeat_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """usage 帧照常累加，心跳不混入 usage/文本统计面。

    静默总长（0.25s）< 心跳间隔（0.3s）→ 不应有任何心跳；
    usage 帧的出队计账路径与心跳完全正交。
    """
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", True)
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_INTERVAL_SECONDS", 0.3)

    usage_frame = agent_service_pb2.ChatResponse(usage=agent_service_pb2.Usage(prompt_tokens=11, completion_tokens=7))
    harness = _HeartbeatHarness(_FakeGraph(delay=0.25))
    queue: asyncio.Queue = asyncio.Queue()
    await queue.put(usage_frame)
    frames, holder = await _collect(harness, queue)

    heartbeats, _others = _split_heartbeats(frames)
    assert not heartbeats, "静默未达阈值时不应触发心跳"
    assert holder.get("total_prompt_tokens") == 11
    assert holder.get("total_completion_tokens") == 7


@pytest.mark.asyncio
async def test_heartbeat_silent_without_frame_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """缺帧身份（未传 frame_identity 的调用方）行为与基线一致：零心跳。"""
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", True)
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_INTERVAL_SECONDS", 0.15)

    harness = _HeartbeatHarness(_FakeGraph(delay=0.4))
    queue: asyncio.Queue = asyncio.Queue()
    frames = await _collect_no_identity(harness, queue)
    heartbeats, others = _split_heartbeats(frames)
    assert not heartbeats and not others


@pytest.mark.asyncio
async def test_heartbeat_disabled_via_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """总开关关闭：长静默也不发心跳（回退基线行为）。"""
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", False)
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_INTERVAL_SECONDS", 0.15)

    harness = _HeartbeatHarness(_FakeGraph(delay=0.4))
    queue: asyncio.Queue = asyncio.Queue()
    frames, holder = await _collect(harness, queue)
    heartbeats, others = _split_heartbeats(frames)
    assert not heartbeats and not others
    assert holder.get("final_state") == {"messages": ["done"]}


@pytest.mark.asyncio
async def test_heartbeat_disabled_by_non_positive_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    """间隔 <=0 视为关闭。"""
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_ENABLED", True)
    monkeypatch.setattr(settings, "STREAM_HEARTBEAT_INTERVAL_SECONDS", 0)

    harness = _HeartbeatHarness(_FakeGraph(delay=0.4))
    queue: asyncio.Queue = asyncio.Queue()
    frames, _holder = await _collect(harness, queue)
    heartbeats, others = _split_heartbeats(frames)
    assert not heartbeats and not others
