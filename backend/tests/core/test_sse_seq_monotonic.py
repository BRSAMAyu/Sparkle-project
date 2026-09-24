"""SSE seq 严格单调回归（wt299-p1-pair P1-2）。

背景（wt294 P1-2 交接）：`SSEManager.send_to_user` 以 `int(time.time()*1000)`
生成 seq——同一毫秒内的多条事件 seq 相同。重放契约（`connect` L67
`if seq > last_seq_int`）是严格大于过滤：客户端断线前最后收到 seq=T，
同毫秒的后续事件（seq 同为 T）在重放时全部被判为「已收到」而**静默丢失**。
galaxy 事件桥（galaxy_event_bridge 一轮可连发多条）、plan_review、
expansion_worker 都是同毫秒连发的高发面。

修法：per-user 严格单调 seq——`max(now_ms, last_seq + 1)`，同毫秒自增，
时间回拨也不回退。`broadcast` 同款处理。seq 生成段纯同步（首个 await 之前），
事件循环内天然原子。

本文件用 FakeRedis 替身离线验证存储/重放链路，不依赖真实 Redis。
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from app.core.cache import cache_service
from app.core.sse import SSEManager

FROZEN_MS = 1_790_000_000_000  # 固定「同一毫秒」


class FakeRedis:
    """最小 Redis list 替身：rpush/lrange/ltrim/expire。"""

    def __init__(self):
        self.lists: dict[str, list[str]] = {}

    async def rpush(self, key, *values):
        self.lists.setdefault(key, []).extend(values)
        return len(self.lists[key])

    async def lrange(self, key, start, end):
        data = self.lists.get(key, [])
        if end == -1:
            return list(data[start:])
        return list(data[start : end + 1])

    async def ltrim(self, key, start, end):
        data = self.lists.get(key, [])
        self.lists[key] = data[start:] if end == -1 else data[start : end + 1]
        return True

    async def expire(self, key, ttl):
        return True


@pytest.fixture()
def sse_env(monkeypatch):
    """隔离的 SSEManager + FakeRedis + 冻结时钟（默认停在同一毫秒）。"""
    fake = FakeRedis()
    monkeypatch.setattr(cache_service, "redis", fake)
    clock = {"now_ms": FROZEN_MS}
    monkeypatch.setattr(time, "time", lambda: clock["now_ms"] / 1000.0)
    manager = SSEManager()
    return manager, fake, clock


def _history_seqs(fake: FakeRedis, user_id: str) -> list[int]:
    return [json.loads(raw)["seq"] for raw in fake.lists.get(f"sse:history:{user_id}", [])]


class TestSeqMonotonic:
    @pytest.mark.asyncio
    async def test_same_millisecond_events_get_strictly_increasing_seq(self, sse_env):
        """P1-2 复现：同一毫秒连发多条事件，seq 必须严格递增。"""
        manager, fake, _ = sse_env
        for i in range(3):
            await manager.send_to_user("u1", f"event_{i}", {"i": i})

        seqs = _history_seqs(fake, "u1")
        assert len(seqs) == 3
        assert seqs[0] < seqs[1] < seqs[2], f"同毫秒 seq 未单调递增: {seqs}"
        assert seqs[1] == seqs[0] + 1 and seqs[2] == seqs[1] + 1

    @pytest.mark.asyncio
    async def test_seq_survives_clock_backstep(self, sse_env):
        """时钟回拨（NTP 校正等）后 seq 仍不得回退。"""
        manager, fake, clock = sse_env
        await manager.send_to_user("u1", "before", {})
        clock["now_ms"] = FROZEN_MS - 60_000  # 时钟倒退一分钟
        await manager.send_to_user("u1", "after", {})

        seqs = _history_seqs(fake, "u1")
        assert seqs[0] < seqs[1], f"时钟回拨导致 seq 回退: {seqs}"

    @pytest.mark.asyncio
    async def test_seq_tracks_real_time_forward(self, sse_env):
        """时间正常前进时 seq 跟随毫秒时间戳（保持可观测语义）。"""
        manager, fake, clock = sse_env
        await manager.send_to_user("u1", "e1", {})
        clock["now_ms"] = FROZEN_MS + 5
        await manager.send_to_user("u1", "e2", {})

        seqs = _history_seqs(fake, "u1")
        assert seqs == [FROZEN_MS, FROZEN_MS + 5]

    @pytest.mark.asyncio
    async def test_per_user_seq_independent(self, sse_env):
        """seq 按用户隔离：u2 的高毫秒不得把 u1 顶到未来。"""
        manager, fake, clock = sse_env
        await manager.send_to_user("u1", "e", {})
        clock["now_ms"] = FROZEN_MS + 100
        await manager.send_to_user("u2", "e", {})
        clock["now_ms"] = FROZEN_MS
        await manager.send_to_user("u1", "e", {})

        assert _history_seqs(fake, "u1") == [FROZEN_MS, FROZEN_MS + 1]
        assert _history_seqs(fake, "u2") == [FROZEN_MS + 100]


class TestReplayContract:
    @pytest.mark.asyncio
    async def test_replay_does_not_drop_same_millisecond_events(self, sse_env):
        """P1-2 核心复现：断线重连按 Last-Event-ID 重放，同毫秒事件不得丢。

        场景：同毫秒连发 e0/e1/e2，客户端只收到 e0（seq=T）即断线；
        重连后 `seq > T` 过滤必须命中 e1/e2。修前三者 seq 同为 T，
        重放 0 条——galaxy 星图更新静默丢失。
        """
        manager, fake, _ = sse_env
        for i in range(3):
            await manager.send_to_user("u1", f"event_{i}", {"i": i})

        seqs = _history_seqs(fake, "u1")
        queue = await manager.connect("u1", last_event_id=str(seqs[0]))

        replayed: list[dict] = []
        while not queue.empty():
            replayed.append(queue.get_nowait())
        assert [e["type"] for e in replayed] == ["event_1", "event_2"], (
            f"同毫秒重放丢事件: replayed={[(e['type'], e['seq']) for e in replayed]}, seqs={seqs}"
        )

    @pytest.mark.asyncio
    async def test_event_generator_emits_strictly_increasing_ids(self, sse_env):
        """消费方回归：event_generator 产出的 id: 行严格递增（mobile 断线续传依据）。"""
        manager, _, _ = sse_env
        queue: asyncio.Queue = asyncio.Queue()
        manager.connections["u1"] = {queue}
        for i in range(3):
            await manager.send_to_user("u1", f"event_{i}", {"i": i})

        from app.core.sse import event_generator

        gen = event_generator(queue)
        ids: list[int] = []
        buf = ""
        while len(ids) < 3:
            buf += await asyncio.wait_for(gen.__anext__(), timeout=5.0)
            while "\n\n" in buf:
                frame, buf = buf.split("\n\n", 1)
                for line in frame.splitlines():
                    if line.startswith("id: "):
                        ids.append(int(line[4:]))
        await gen.aclose()
        assert ids[0] < ids[1] < ids[2], f"id: 非严格递增: {ids}"
