"""PROD-FIX-2 缺陷 #3：事件总线幂等锁/去重标记必须按消费组隔离。

生产实证（PROD-LOG REPORT ②-3）：``event_bus.py`` 的幂等键
``evt:{stream}:{effective_id}`` 仅按 stream 作用域；``sparkle_events`` 上 30+
个消费组每条消息各投递一份，却在同一把锁 / 同一个 done 标记上互斥——
后果：① 抢锁失败方 return 不 ACK，消息滞留本组 PEL 等 5s autoclaim（扇出延迟）；
② 组 A 完成处理后组 B 命中 done 标记被误判"重复"直接跳过，回调永不执行；
③ 每条消息放大出 ~129 条 "Could not acquire lock" 假告警。

红证（修复前全部失败）：
- test_two_groups_both_consume_same_event            —— 误判重复面
- test_two_groups_concurrent_same_event_no_mutual_block —— 锁互斥面
- test_lock_failure_log_is_not_warning               —— 告警噪音面
绿证（语义不回退）：
- test_same_group_duplicate_still_skipped            —— 组内幂等语义保持
- test_idempotency_keys_are_group_scoped             —— 键形状钉死
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from loguru import logger as loguru_logger

from app.core.event_bus import EventBus

STREAM = "sparkle_events"
MSG_ID = "1790115091978-0"
_EVENT_DATA = {"event_type": "task.completed", "user_id": "user-1"}


class _GroupAwareStore:
    """按真实 RedisIdempotencyStore 语义建模的幂等存储（SET NX 锁 + TTL done 标记）。"""

    def __init__(self) -> None:
        self._done: dict[str, dict] = {}
        self._locks: set[str] = set()
        self.keys_seen: list[str] = []

    async def get(self, key: str):
        self.keys_seen.append(key)
        return self._done.get(key)

    async def set(self, key: str, value: dict, ttl: int) -> None:
        self._done[key] = value

    async def lock(self, key: str) -> bool:
        if key in self._locks:
            return False
        self._locks.add(key)
        return True

    async def unlock(self, key: str) -> None:
        self._locks.discard(key)


def _make_bus(store: _GroupAwareStore) -> EventBus:
    bus = EventBus()
    bus.redis = SimpleNamespace(xack=AsyncMock())
    bus._get_idempotency_store = AsyncMock(return_value=store)  # type: ignore[method-assign]
    return bus


def _process(bus: EventBus, store: _GroupAwareStore, group: str, callback, message_id: str = MSG_ID):
    return bus._process_stream_message(
        stream=STREAM,
        group_name=group,
        consumer_name=f"{group}-consumer",
        callback=callback,
        message_id=message_id,
        data=dict(_EVENT_DATA),
    )


# ---------------------------------------------------------------------------
# 红证 ①：组 A 完成 → 组 B 不得被 done 标记误判为"重复"而跳过
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_groups_both_consume_same_event() -> None:
    store = _GroupAwareStore()
    bus = _make_bus(store)

    calls: dict[str, int] = {"group_a": 0, "group_b": 0}

    async def cb_a(event: dict) -> None:
        calls["group_a"] += 1

    async def cb_b(event: dict) -> None:
        calls["group_b"] += 1

    await _process(bus, store, "group_a", cb_a)
    await _process(bus, store, "group_b", cb_b)

    assert calls["group_a"] == 1, "group A 应正常消费"
    assert calls["group_b"] == 1, (
        "group B 必须独立消费同一事件：组 A 的 done 标记不得跨组判重（修复前 "
        "idempotency 键仅按 stream 作用域，B 被误判 duplicate 直接跳过）"
    )


# ---------------------------------------------------------------------------
# 红证 ②：组 A 持锁处理中 → 组 B 不得在同一把锁上被阻塞/拒斥
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_groups_concurrent_same_event_no_mutual_block() -> None:
    store = _GroupAwareStore()
    bus = _make_bus(store)

    group_a_entered = asyncio.Event()
    calls = {"group_a": 0, "group_b": 0}

    async def cb_a(event: dict) -> None:
        calls["group_a"] += 1
        group_a_entered.set()
        await asyncio.sleep(0.05)  # 模拟慢回调：持锁窗口

    async def cb_b(event: dict) -> None:
        calls["group_b"] += 1

    task_a = asyncio.create_task(_process(bus, store, "group_a", cb_a))
    await group_a_entered.wait()  # group A 已拿锁并进入回调

    # group B 在 A 持锁期间处理自己的投递副本：必须不被共享锁拒斥
    await _process(bus, store, "group_b", cb_b)
    await task_a

    assert calls["group_a"] == 1
    assert calls["group_b"] == 1, (
        "group B 在 group A 持锁期间不得被共享锁拒斥（修复前锁键仅按 stream，"
        "B 抢锁失败 return 不 ACK，滞留 PEL 等 5s autoclaim）"
    )
    # B 处理成功后必须 ACK 自己的投递（修复前拒斥路径不 ACK）
    assert bus.redis.xack.await_count == 2


# ---------------------------------------------------------------------------
# 红证 ③：抢锁失败降为 DEBUG（同组竞争是正常态，不进告警基线）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_failure_log_is_not_warning() -> None:
    store = _GroupAwareStore()
    bus = _make_bus(store)

    entered = asyncio.Event()

    async def cb_slow(event: dict) -> None:
        entered.set()
        await asyncio.sleep(0.05)

    async def cb_fast(event: dict) -> None:
        pass

    task = asyncio.create_task(_process(bus, store, "group_a", cb_slow))
    await entered.wait()

    records: list[str] = []
    sink_id = loguru_logger.add(lambda msg: records.append(str(msg)), level="DEBUG", format="{level}|{message}")
    try:
        await _process(bus, store, "group_a", cb_fast)
    finally:
        loguru_logger.remove(sink_id)
    await task

    warnings = [r for r in records if r.startswith("WARNING") and "Could not acquire lock" in r]
    assert not warnings, "组内抢锁失败是正常竞争态，不得以 WARNING 进告警基线（生产 ~129 条假告警）"


# ---------------------------------------------------------------------------
# 绿证：组内幂等语义不回退（同组重复投递仍跳过 + ACK）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_group_duplicate_still_skipped() -> None:
    store = _GroupAwareStore()
    bus = _make_bus(store)

    calls = 0

    async def cb(event: dict) -> None:
        nonlocal calls
        calls += 1

    # 首次投递（原始 id 1-0）
    await _process(bus, store, "group_a", cb, message_id="1-0")
    # 同组重投递：autoclaim/重试副本携带 _original_message_id 指回原始 id
    bus.redis.xack.reset_mock()
    await bus._process_stream_message(
        stream=STREAM,
        group_name="group_a",
        consumer_name="group_a-consumer",
        callback=cb,
        message_id="9-9",
        data={"event_type": "task.completed", "user_id": "user-1", "_original_message_id": "1-0"},
    )

    assert calls == 1, "同组重复投递必须仍被幂等跳过（at-least-once 去重语义不回退）"
    bus.redis.xack.assert_awaited_once_with(STREAM, "group_a", "9-9")


# ---------------------------------------------------------------------------
# 绿证：幂等键形状钉死为组作用域（跨组键互不相同）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotency_keys_are_group_scoped() -> None:
    store = _GroupAwareStore()
    bus = _make_bus(store)

    async def cb(event: dict) -> None:
        pass

    await _process(bus, store, "group_a", cb)
    keys_a = list(store.keys_seen)
    store.keys_seen.clear()
    await _process(bus, store, "group_b", cb)
    keys_b = list(store.keys_seen)

    assert keys_a and keys_b
    assert all(k.startswith(f"evt:{STREAM}:group_a:") for k in keys_a), f"group A 键应含组维度: {keys_a}"
    assert all(k.startswith(f"evt:{STREAM}:group_b:") for k in keys_b), f"group B 键应含组维度: {keys_b}"
    assert not set(keys_a) & set(keys_b), "两消费组的幂等键集合不得相交"
