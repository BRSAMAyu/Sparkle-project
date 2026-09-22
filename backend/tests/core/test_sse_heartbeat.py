"""SSE 心跳测试（SSE-HB）。

galaxy 事件流（app/core/sse.py::event_generator）空闲期必须周期性产出
SSE 注释帧 ``: heartbeat\\n\\n``，让全链路（engine → gateway ReverseProxy →
mobile Dio stream）保持字节流动，防止中间层读空闲超时掐断连接。

形态选择依据：
- 注释帧（以 ``:`` 开头）是 SSE 规范推荐的心跳形态，不触发任何客户端事件语义；
- gateway 用 httputil.ReverseProxy(FlushInterval=-1) 逐字节透传、不解析 SSE，
  注释帧原样到达客户端（gateway 零改动）；
- mobile GalaxyRepository._parseSSE 按 ``\\n\\n`` 分帧后逐行解析 ``event:``/``data:``，
  纯注释帧两字段皆 None → 返回 None，事件被静默忽略（mobile 零改动）。
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.config.phase5_config import phase5_config
from app.core.sse import event_generator

HEARTBEAT_FRAME = ": heartbeat\n\n"


async def _collect_frames(queue: asyncio.Queue, count: int, timeout: float = 5.0) -> list[str]:
    """从 event_generator 收集 count 个完整 SSE 帧（以 ``\\n\\n`` 结尾）。

    与 mobile 端 _parseSSE 的分帧方式一致：generator 逐行 yield 片段，
    在这里按帧边界拼接，便于对完整事件帧做逐字节断言。
    """
    gen = event_generator(queue)
    frames: list[str] = []
    buf = ""
    try:
        while len(frames) < count:
            buf += await asyncio.wait_for(gen.__anext__(), timeout=timeout)
            while "\n\n" in buf:
                idx = buf.index("\n\n")
                frames.append(buf[: idx + 2])
                buf = buf[idx + 2 :]
    finally:
        await gen.aclose()
    return frames


@pytest.mark.asyncio
async def test_event_generator_emits_heartbeat_when_idle(monkeypatch):
    """空闲期（queue 无事件）必须在心跳间隔内产出注释帧（SSE-HB 核心）。"""
    monkeypatch.setattr(phase5_config, "SSE_HEARTBEAT_INTERVAL", 0.05)
    queue: asyncio.Queue = asyncio.Queue()

    start = time.monotonic()
    frames = await _collect_frames(queue, count=1)
    elapsed = time.monotonic() - start

    assert frames == [HEARTBEAT_FRAME]
    # 心跳应按配置间隔出现（留调度余量），而不是立即或远超间隔
    assert 0.03 <= elapsed < 2.0


@pytest.mark.asyncio
async def test_heartbeat_is_safe_comment_frame(monkeypatch):
    """心跳必须是纯注释帧：无 event:/data: 行，mobile _parseSSE 才会静默忽略。"""
    monkeypatch.setattr(phase5_config, "SSE_HEARTBEAT_INTERVAL", 0.05)
    queue: asyncio.Queue = asyncio.Queue()

    frames = await _collect_frames(queue, count=1)

    frame = frames[0]
    assert frame.startswith(":")
    assert frame.endswith("\n\n")
    assert "event:" not in frame
    assert "data:" not in frame


@pytest.mark.asyncio
async def test_real_events_frame_order_untouched_and_heartbeat_only_when_idle(monkeypatch):
    """红线面：有数据时帧序与旧实现逐字节一致；事件清空后才出现心跳。"""
    monkeypatch.setattr(phase5_config, "SSE_HEARTBEAT_INTERVAL", 0.2)
    queue: asyncio.Queue = asyncio.Queue()
    await queue.put({"type": "nodes_expanded", "data": {"x": 1}, "seq": 42})
    await queue.put({"type": "node_sparked", "data": {"y": 2}, "seq": 43})

    frames = await _collect_frames(queue, count=3)

    # 前两帧是完整事件帧，与无心跳版本的输出逐字节一致（帧序不变）
    assert frames[0] == 'id: 42\nevent: nodes_expanded\ndata: {"x": 1}\n\n'
    assert frames[1] == 'id: 43\nevent: node_sparked\ndata: {"y": 2}\n\n'
    # 队列清空后（空闲期）才出现心跳
    assert frames[2] == HEARTBEAT_FRAME


@pytest.mark.asyncio
async def test_event_during_heartbeat_wait_is_not_lost(monkeypatch):
    """心跳等待期间到达的事件不丢、不被心跳截断。"""
    monkeypatch.setattr(phase5_config, "SSE_HEARTBEAT_INTERVAL", 0.05)
    queue: asyncio.Queue = asyncio.Queue()

    async def late_put():
        await asyncio.sleep(0.02)  # 在心跳超时之前到达
        await queue.put({"type": "decay_warning", "data": {"n": 1}, "seq": 7})

    task = asyncio.create_task(late_put())
    try:
        frames = await _collect_frames(queue, count=1)
    finally:
        await task

    assert frames == ['id: 7\nevent: decay_warning\ndata: {"n": 1}\n\n']


@pytest.mark.asyncio
async def test_heartbeat_interval_is_configurable(monkeypatch):
    """间隔可配置：调大间隔则首帧推迟。"""
    monkeypatch.setattr(phase5_config, "SSE_HEARTBEAT_INTERVAL", 0.3)
    queue: asyncio.Queue = asyncio.Queue()

    start = time.monotonic()
    await _collect_frames(queue, count=1)
    elapsed = time.monotonic() - start

    assert elapsed >= 0.25


def test_default_heartbeat_interval_is_twenty_seconds():
    """默认 20s：小于常见中间层空闲超时（nginx 60s / 客户端历史 30s），又不至于过频。"""
    assert phase5_config.SSE_HEARTBEAT_INTERVAL == 20.0
