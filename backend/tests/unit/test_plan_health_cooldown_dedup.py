"""IDEM-GAPS 缺口B：plan.health.alerted 冷却提醒的重投递幂等门。

- 服务面：SystemUpdateService.enqueue 可选 dedup_key（Redis SET NX EX 天然查重），
  默认 600s 窗口——覆盖总线热重试+XAUTOCLAIM 秒~分钟级重投递，远小于发布侧
  同签名 2h 冷却，不误吞合法重发；
- 消费面：同一事件重投 → 提醒不双发；不同 plan / 标记过期（不同日）→ 正常发。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import fakeredis
import pytest

from app.core.cache import cache_service
from app.services.plan_health_event_consumer import PlanHealthEventConsumer
from app.services.system_update_service import SystemUpdateService


def _alert_event(user_id: str, plan_id: str, signature: str = "warning|none|pace_drop") -> dict:
    return {
        "event_type": "plan.health.alerted",
        "user_id": user_id,
        "plan_id": plan_id,
        "severity": "warning",
        "recommended_action": "none",
        "reasons": ["pace_drop"],
        "action_taken": "none_cooldown_active",
        "signature": signature,
        "emitted_at": "2026-09-23T00:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_enqueue_dedup_key_semantics():
    """dedup_key 基础语义：同键窗口内不双发；跨用户隔离；过期可再发；缺省行为不变。"""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    svc = SystemUpdateService(redis_client=fake)

    assert await svc.enqueue("u1", {"t": 1}, dedup_key="k") is True
    # 同键窗口内 → 跳过
    assert await svc.enqueue("u1", {"t": 1}, dedup_key="k") is False
    # dedup 键按用户命名空间隔离，互不影响
    assert await svc.enqueue("u2", {"t": 1}, dedup_key="k") is True
    # 默认 TTL 600（< 2h 发布侧同签名冷却）
    ttl = await fake.ttl("system_updates:dedup:u1:k")
    assert 0 < ttl <= SystemUpdateService.DEFAULT_DEDUP_TTL_SECONDS
    # 无 dedup_key → 旧行为不变（不去重）
    assert await svc.enqueue("u1", {"t": 2}) is True

    # 标记过期（不同日机制面）→ 可再次入队
    await fake.delete("system_updates:dedup:u1:k")
    assert await svc.enqueue("u1", {"t": 1}, dedup_key="k") is True

    stored = await fake.lrange("system_updates:u1", 0, -1)
    assert len(stored) == 3  # 首次 k + 无键一次 + 过期后 k；窗口内重复未入队


@pytest.mark.asyncio
async def test_cooldown_reminder_not_duplicated_on_event_redelivery():
    """同一 plan.health.alerted 事件重投 → 冷却提醒恰一条；不同 plan → 正常发。"""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    consumer = PlanHealthEventConsumer(event_bus=AsyncMock())
    bridge_stub = MagicMock(on_plan_health_signal=AsyncMock(return_value=None))
    session_mock = MagicMock()

    plan_id = str(uuid4())
    user_id = str(uuid4())
    event = _alert_event(user_id, plan_id)
    updates_key = f"system_updates:{user_id}"

    def _run(event_body: dict):
        return consumer._handle_plan_health_alerted(event_body)

    with (
        patch("app.services.plan_health_event_consumer.AsyncSessionLocal", return_value=session_mock.return_value),
        patch(
            "app.services.card_protocol.health_intervention_bridge.PlanHealthInterventionBridge",
            return_value=bridge_stub,
        ),
        patch.object(cache_service, "redis", fake),
    ):
        await _run(event)
        # at-least-once 重投递：同一事件再消费一次
        await _run(event)
        items = await fake.lrange(updates_key, 0, -1)
        assert len(items) == 1
        stored = json.loads(items[0])
        assert stored["title"] == "计划状态观察中"
        assert stored["metadata"]["plan_id"] == plan_id

        # 不同 plan → 不同 dedup 键 → 正常发第二条
        await _run(_alert_event(user_id, str(uuid4())))
        items = await fake.lrange(updates_key, 0, -1)
        assert len(items) == 2

        # 不同日机制面：标记过期后同一 plan 同签名可再次提醒
        await fake.delete(f"system_updates:dedup:{user_id}:plan_health_cooldown:{plan_id}:warning|none|pace_drop")
        await _run(event)
        items = await fake.lrange(updates_key, 0, -1)
        assert len(items) == 3


@pytest.mark.asyncio
async def test_cooldown_dedup_key_derives_from_event_signature():
    """消费点按事件 signature 构键；payload 缺 signature 时回退 severity|action。"""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    consumer = PlanHealthEventConsumer(event_bus=AsyncMock())
    bridge_stub = MagicMock(on_plan_health_signal=AsyncMock(return_value=None))
    session_mock = MagicMock()

    event = _alert_event(str(uuid4()), str(uuid4()))
    event_without_signature = {k: v for k, v in event.items() if k != "signature"}

    with (
        patch("app.services.plan_health_event_consumer.AsyncSessionLocal", return_value=session_mock.return_value),
        patch(
            "app.services.card_protocol.health_intervention_bridge.PlanHealthInterventionBridge",
            return_value=bridge_stub,
        ),
        patch.object(cache_service, "redis", fake),
    ):
        await consumer._handle_plan_health_alerted(event_without_signature)
        await consumer._handle_plan_health_alerted(event_without_signature)
        items = await fake.lrange(f"system_updates:{event['user_id']}", 0, -1)
        assert len(items) == 1  # 回退键同样幂等

        marker_keys = []
        async for key in fake.scan_iter(match=f"system_updates:dedup:{event['user_id']}:*"):
            marker_keys.append(str(key))
        assert marker_keys == [
            f"system_updates:dedup:{event['user_id']}:plan_health_cooldown:{event['plan_id']}:warning|none_cooldown_active"
        ]
