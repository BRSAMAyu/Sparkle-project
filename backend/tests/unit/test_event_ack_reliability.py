"""EVENT-ACK 回归测试：事件消费 blanket-except 恒 ack 静默丢失修复。

覆盖三层语义：
1. **失败不 ack**：galaxy 消费域回调（event_listener / outcome_absorption /
   streaming / galaxy_execution）处理失败必须上抛——``EventBus._process_stream_message``
   据此走「有界重试 → DLQ」；requeue 自身失败时消息留在 PEL（不 ack）。
2. **pending 回收**：graph_sync_worker / preference_event_consumer 的
   XAUTOCLAIM 回收——失败/崩溃遗留的 pending 在恢复后被重处理并 ack。
3. **良性路径零行为变化**：路由过滤（非本组事件）仍是无异常的良性 ack。
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import fakeredis.aioredis as fakeredis_aioredis
import pytest

from app.core.event_bus import EventBus
from app.services.galaxy.event_listener import TaskEventListener
from app.services.galaxy.outcome_absorption_service import OutcomeAbsorptionConsumer
from app.services.galaxy.streaming_service import GalaxyStreamingService
from app.services.galaxy_execution_consumer import GalaxyExecutionConsumer
from app.services.preference_event_consumer import PreferenceEventConsumer
from app.workers.graph_sync_worker import GraphSyncWorker


class _FakeIdempotencyStore:
    async def get(self, key: str):
        return None

    async def lock(self, key: str) -> bool:
        return True

    async def set(self, key: str, value, ttl: int) -> None:
        return None

    async def unlock(self, key: str) -> None:
        return None


# ---------------------------------------------------------------------------
# 1a. TaskEventListener：失败上抛 + 总线「失败重排队 → 恢复 ack」
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_listener_surfaces_session_failure():
    """session_factory 直接失败 → on_task_completed 上抛（不再吞成恒 ack）。"""

    def broken_factory():
        raise RuntimeError("db down")

    listener = TaskEventListener(broken_factory, AsyncMock())
    event = {"event_type": "task.completed", "task_id": str(uuid4()), "user_id": str(uuid4())}

    with pytest.raises(RuntimeError, match="db down"):
        await listener._on_event(event)


@pytest.mark.asyncio
async def test_event_listener_unknown_event_type_is_benign_ack():
    """非本组事件类型：无异常返回（良性路由 ack，行为不变）。"""

    listener = TaskEventListener(Mock(), AsyncMock())
    await listener._on_event({"event_type": "some.other.event", "data": "x"})


@pytest.mark.asyncio
async def test_event_listener_failure_requeues_then_recovery_acks(monkeypatch: pytest.MonkeyPatch):
    """总线视角：第一次处理失败 → requeue（事件不丢）；重试成功 → ack。"""
    bus = EventBus()
    bus.redis = SimpleNamespace(xack=AsyncMock(), xadd=AsyncMock(return_value="2-0"))
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(bus, "_move_to_dlq", move_to_dlq)
    monkeypatch.setattr(bus, "_get_idempotency_store", AsyncMock(return_value=_FakeIdempotencyStore()))

    listener = TaskEventListener(Mock(), AsyncMock())
    attempts = 0

    async def flaky_handler(event: dict) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient db failure")

    with patch.object(listener, "on_task_completed", flaky_handler):
        await bus._process_stream_message(
            stream="sparkle_events",
            group_name="galaxy_listeners",
            consumer_name="task_event_listener",
            callback=listener._on_event,
            message_id="1-0",
            data={"event_type": "task.completed", "task_id": str(uuid4()), "user_id": str(uuid4())},
        )

    # 失败面：requeue 了重试副本（xadd），原始消息被 ack（事件未丢失——
    # 内容已带 _retry_count 重进 stream；而 requeue 自身失败时不 ack 的
    # 分支由下一条测试覆盖）
    bus.redis.xadd.assert_awaited_once()
    bus.redis.xack.assert_awaited_once_with("sparkle_events", "galaxy_listeners", "1-0")
    move_to_dlq.assert_not_awaited()

    # 恢复面：重试副本成功 → ack，不进 DLQ
    with patch.object(listener, "on_task_completed", flaky_handler):
        await bus._process_stream_message(
            stream="sparkle_events",
            group_name="galaxy_listeners",
            consumer_name="task_event_listener",
            callback=listener._on_event,
            message_id="2-0",
            data={
                "event_type": "task.completed",
                "task_id": str(uuid4()),
                "user_id": str(uuid4()),
                "_retry_count": "1",
            },
        )

    assert attempts == 2
    assert bus.redis.xack.await_count == 2
    move_to_dlq.assert_not_awaited()


@pytest.mark.asyncio
async def test_event_bus_requeue_failure_leaves_message_pending(monkeypatch: pytest.MonkeyPatch):
    """红线：requeue 自身失败 → 消息不 ack（留在 pending，天然重试面）。"""
    bus = EventBus()
    bus.redis = SimpleNamespace(
        xack=AsyncMock(),
        xadd=AsyncMock(side_effect=RuntimeError("redis requeue down")),
    )
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(bus, "_move_to_dlq", move_to_dlq)
    monkeypatch.setattr(bus, "_get_idempotency_store", AsyncMock(return_value=_FakeIdempotencyStore()))

    async def failing_callback(event: dict) -> None:
        raise RuntimeError("consumer failed")

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="g",
        consumer_name="c",
        callback=failing_callback,
        message_id="1-0",
        data={"event_type": "task.completed", "user_id": "u-1"},
    )

    bus.redis.xack.assert_not_awaited()  # 未 ack → 留 PEL
    move_to_dlq.assert_not_awaited()


# ---------------------------------------------------------------------------
# 1b. OutcomeAbsorptionConsumer：吸收失败上抛；非目标事件良性跳过
# ---------------------------------------------------------------------------


def _absorption_session_factory(db: AsyncMock):
    return Mock(return_value=db)


@pytest.mark.asyncio
async def test_outcome_absorption_consumer_surfaces_failure():
    """absorb_outcome 失败 → _on_event 上抛（总线据此重试/DLQ，不再恒 ack）。"""
    db = AsyncMock()
    db.__aenter__.return_value = db
    with patch(
        "app.services.galaxy.outcome_absorption_service.GalaxyOutcomeAbsorber"
    ) as absorber_cls:
        absorber_cls.return_value.absorb_outcome = AsyncMock(side_effect=RuntimeError("absorb boom"))
        consumer = OutcomeAbsorptionConsumer(
            session_factory=_absorption_session_factory(db), event_bus=None
        )
        with pytest.raises(RuntimeError, match="absorb boom"):
            await consumer._on_event({"event_type": "outcome.recorded", "outcome_id": "outc_x"})


@pytest.mark.asyncio
async def test_outcome_absorption_consumer_ignores_non_outcome_events():
    """非 outcome.recorded 事件：直接返回（良性路由 ack，不触达 DB）。"""
    db = AsyncMock()
    consumer = OutcomeAbsorptionConsumer(session_factory=_absorption_session_factory(db), event_bus=None)

    await consumer._on_event({"event_type": "task.completed", "task_id": "t"})

    db.__aenter__.assert_not_awaited()


# ---------------------------------------------------------------------------
# 1c. GalaxyStreamingService：推送面失败上抛；正常推送零变化
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_streaming_service_surfaces_malformed_event():
    """malformed 事件（user_id 缺失）→ 上抛（此前被 blanket-except 吞成恒 ack）。"""
    service = GalaxyStreamingService(AsyncMock(), AsyncMock())

    with pytest.raises(TypeError):
        await service._on_event({"event_type": "node_mastery_updated"})


@pytest.mark.asyncio
async def test_streaming_service_happy_path_unchanged():
    """正常掌握度事件 → 推送成功、无异常（良性路径零行为变化）。"""
    ws_manager = AsyncMock()
    service = GalaxyStreamingService(ws_manager, AsyncMock())

    await service._on_event(
        {
            "event_type": "node_mastery_updated",
            "user_id": str(UUID(int=1)),
            "node_id": str(UUID(int=2)),
            "old_mastery": 50,
            "new_mastery": 95,
            "reason": "quiz",
        }
    )

    assert ws_manager.send_personal_message.await_count >= 1  # mastery + level_up


# ---------------------------------------------------------------------------
# 1d. GalaxyExecutionConsumer：同步失败上抛；过滤路径不变
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_galaxy_execution_consumer_surfaces_failure():
    consumer = GalaxyExecutionConsumer(AsyncMock())

    async def boom(event: dict) -> None:
        raise RuntimeError("graph sync boom")

    with patch.object(consumer, "_handle_execution_result", boom):
        with pytest.raises(RuntimeError, match="graph sync boom"):
            await consumer.handle_event(
                {"event_type": "execution.result_ingested", "success": True}
            )


@pytest.mark.asyncio
async def test_galaxy_execution_consumer_filter_unchanged():
    """非目标事件 / 失败的执行结果：良性跳过（行为不变）。"""
    consumer = GalaxyExecutionConsumer(AsyncMock())

    await consumer.handle_event({"event_type": "other.event", "success": True})
    await consumer.handle_event({"event_type": "execution.result_ingested", "success": False})


# ---------------------------------------------------------------------------
# 2a. GraphSyncWorker：失败留 pending → 回收重试成功
# ---------------------------------------------------------------------------


def _graph_message() -> dict:
    return {
        "type": "node_created",
        "data": json.dumps(
            {
                "id": "node-1",
                "name": "Node",
                "description": "d",
                "importance": 5,
                "sector": "math",
                "keywords": "a,b",
                "source_type": "manual",
            }
        ),
    }


def _make_worker(redis_client) -> GraphSyncWorker:
    worker = GraphSyncWorker.__new__(GraphSyncWorker)
    worker.age_client = AsyncMock()
    worker.redis = redis_client
    worker.running = False
    worker.stream_key = "stream:graph_sync"
    worker.group_name = "graph_sync_group"
    worker.consumer_name = "worker_1"
    worker.pending_reclaim_idle_ms = 0  # 测试立即可认领
    return worker


@pytest.mark.asyncio
async def test_graph_sync_worker_failure_stays_pending_then_recover_acks():
    """红线全链路：处理失败 → 未 ack 留 PEL → 回收重试成功 → ack 清空 PEL。"""
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    worker = _make_worker(redis)
    await redis.xgroup_create(worker.stream_key, worker.group_name, id="0", mkstream=True)
    await redis.xadd(worker.stream_key, _graph_message())

    # 模拟投递后处理失败（或进程崩溃）：xreadgroup 已交付进 PEL、无 ack
    worker.age_client.add_vertex = AsyncMock(side_effect=RuntimeError("age down"))
    await redis.xreadgroup(
        worker.group_name,
        worker.consumer_name,
        {worker.stream_key: ">"},
        count=10,
    )
    pending = await redis.xpending(worker.stream_key, worker.group_name)
    assert pending["pending"] == 1

    await worker._recover_pending()  # 认领重处理，仍失败 → 留 pending
    pending = await redis.xpending(worker.stream_key, worker.group_name)
    assert pending["pending"] == 1  # 失败不丢：留在 pending

    # 恢复后再次回收：重试成功 → ack → PEL 清空
    worker.age_client.add_vertex = AsyncMock(return_value=None)
    await worker._recover_pending()
    pending = await redis.xpending(worker.stream_key, worker.group_name)
    assert pending["pending"] == 0
    assert worker.age_client.add_vertex.await_count >= 1


@pytest.mark.asyncio
async def test_graph_sync_worker_recover_pending_is_noop_when_no_pending():
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    worker = _make_worker(redis)
    await redis.xgroup_create(worker.stream_key, worker.group_name, id="0", mkstream=True)

    await worker._recover_pending()  # 空 PEL：无异常、无副作用

    pending = await redis.xpending(worker.stream_key, worker.group_name)
    assert pending["pending"] == 0


# ---------------------------------------------------------------------------
# 2b. PreferenceEventConsumer：崩溃遗留 pending 回收；失败路由 requeue
# ---------------------------------------------------------------------------


def _preference_event() -> dict:
    inner = json.dumps({"user_id": str(UUID(int=42)), "preference_version": 3, "timestamp": 1.0})
    return {"type": "user.preferences.updated", "payload": json.dumps({"data": inner})}


def _make_preference_consumer(redis_client) -> tuple[PreferenceEventConsumer, AsyncMock]:
    user_service = AsyncMock()
    consumer = PreferenceEventConsumer(redis_client, user_service)
    consumer.pending_reclaim_idle_ms = 0  # 测试立即可认领
    return consumer, user_service


@pytest.mark.asyncio
async def test_preference_consumer_recovers_crash_left_pending():
    """崩溃遗留（投递后未 ack）→ _recover_pending 处理并 ack，PEL 清空。"""
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    consumer, user_service = _make_preference_consumer(redis)
    await redis.xgroup_create(consumer.stream_key, consumer.consumer_group, id="0", mkstream=True)
    await redis.xadd(consumer.stream_key, _preference_event())

    # 模拟崩溃：投递进 PEL 但没来得及 ack
    await redis.xreadgroup(
        consumer.consumer_group,
        consumer.consumer_name,
        {consumer.stream_key: ">"},
        count=10,
    )
    pending = await redis.xpending(consumer.stream_key, consumer.consumer_group)
    assert pending["pending"] == 1

    await consumer._recover_pending()

    pending = await redis.xpending(consumer.stream_key, consumer.consumer_group)
    assert pending["pending"] == 0
    user_service.invalidate_user_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_preference_consumer_recover_failure_routes_to_requeue():
    """回收重处理失败 → 走既有 requeue 语义（_retry_count=1 副本 + 原 ack）。"""
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    consumer, user_service = _make_preference_consumer(redis)
    user_service.invalidate_user_cache = AsyncMock(side_effect=RuntimeError("cache down"))
    await redis.xgroup_create(consumer.stream_key, consumer.consumer_group, id="0", mkstream=True)
    await redis.xadd(consumer.stream_key, _preference_event())

    await redis.xreadgroup(
        consumer.consumer_group,
        consumer.consumer_name,
        {consumer.stream_key: ">"},
        count=10,
    )

    await consumer._recover_pending()

    # 原始条目已 ack（PEL 空），重试副本带 _retry_count=1 重进 stream
    pending = await redis.xpending(consumer.stream_key, consumer.consumer_group)
    assert pending["pending"] == 0
    assert await redis.xlen(consumer.stream_key) == 2
    entries = await redis.xrange(consumer.stream_key)
    retry_payload = entries[-1][1]
    assert retry_payload.get("_retry_count") == "1"


@pytest.mark.asyncio
async def test_preference_consumer_benign_routing_unchanged():
    """非偏好事件：无异常直接返回、不触达 user_service（良性 ack 不变）。"""
    redis = fakeredis_aioredis.FakeRedis(decode_responses=True)
    consumer, user_service = _make_preference_consumer(redis)

    await consumer._handle_event("0-1", {"type": "user.other.event", "payload": "{}"})

    user_service.invalidate_user_cache.assert_not_awaited()


# ---------------------------------------------------------------------------
# 2c. EventBus 既有 pending 回收面：XAUTOCLAIM 认领 stale 消息（回归护栏）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_bus_claim_stale_messages_returns_claimed(monkeypatch: pytest.MonkeyPatch):
    """EventBus 自带 XAUTOCLAIM 回收：认领结果原样进入重处理管线（不回退）。"""
    bus = EventBus()
    claimed = [("1-0", {"event_type": "task.completed"})]
    bus.redis = SimpleNamespace(
        xautoclaim=AsyncMock(return_value=("0-0", claimed, [])),
    )

    messages = await bus._claim_stale_messages("sparkle_events", "g", "c")

    assert messages == claimed
    bus.redis.xautoclaim.assert_awaited_once()


@pytest.mark.asyncio
async def test_event_bus_claim_stale_messages_survives_response_error():
    """stream/group 尚不存在（ResponseError）→ 返回空、不炸消费循环。"""
    from redis.exceptions import ResponseError

    bus = EventBus()
    bus.redis = SimpleNamespace(
        xautoclaim=AsyncMock(side_effect=ResponseError("NOGROUP")),
    )

    messages = await bus._claim_stale_messages("sparkle_events", "g", "c")

    assert messages == []
