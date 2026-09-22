"""EVENT-ACK-2 回归测试：事件消费吞异常同族 8 点清偿。

三层语义：
1. **失败上抛**（本卡修复点）：plan_health 整事件、achievement 两 handler、
   capsule 再生请求、aurora `_on_bus_event` —— 失败必须逃逸到总线，
   走「失败 metric → 有界重试 → DLQ」；吞掉即恒 ack 静默丢失。
2. **既有合规契约回归护栏**：nudge 上抛、task_event `_safe_run` 单项隔离、
   journey 错误路径的用户失败通知（UX 语义 contain）、profile 缓存失效
   best-effort —— 均为显式设计，本卡注释化并锁定。
3. **总线管线通用性**：修复域的回调失败同样进入既有 requeue 管线（不丢）。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.nudge_event_consumer import NudgeEventConsumer
from app.services.plan_health_event_consumer import PlanHealthEventConsumer
from app.services.task_event_consumer import TaskEventConsumer


def _broken_session_factory_patch(target: str, message: str = "DB connection lost"):
    """AsyncSessionLocal 替身：__aenter__ 直接抛（模拟会话建立即失败）。"""
    mock_session = MagicMock()
    mock_session.return_value.__aenter__ = AsyncMock(side_effect=Exception(message))
    mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
    return patch(target, return_value=mock_session.return_value)


# ---------------------------------------------------------------------------
# 1a. plan_health_event_consumer：整事件失败上抛（修前：error 日志后恒 ack）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_health_consumer_surfaces_whole_event_failure():
    consumer = PlanHealthEventConsumer(event_bus=MagicMock())
    event = {
        "event_type": "plan.health.alerted",
        "user_id": str(uuid4()),
        "plan_id": str(uuid4()),
        "severity": "critical",
        "action_taken": "adjustment_cooldown_active",
    }

    with _broken_session_factory_patch("app.services.plan_health_event_consumer.AsyncSessionLocal"):
        with pytest.raises(Exception, match="DB connection lost"):
            await consumer._handle_plan_health_alerted(event)


@pytest.mark.asyncio
async def test_plan_health_consumer_bridge_failure_stays_contained():
    """显式单项 best-effort：card_protocol 桥失败 → rollback + 不上抛（白名单注释化）。"""
    fake_db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    consumer = PlanHealthEventConsumer(event_bus=MagicMock())

    class FakeBridge:
        def __init__(self, db, event_bus=None):
            pass

        async def on_plan_health_signal(self, **kwargs):
            raise RuntimeError("bridge down")

    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=fake_db)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.plan_health_event_consumer.AsyncSessionLocal", return_value=session_mock.return_value):
        with patch(
            "app.services.card_protocol.health_intervention_bridge.PlanHealthInterventionBridge",
            FakeBridge,
        ):
            await consumer._handle_plan_health_alerted(
                {
                    "event_type": "plan.health.alerted",
                    "user_id": str(uuid4()),
                    "plan_id": str(uuid4()),
                    "severity": "critical",
                    "action_taken": "none",
                }
            )

    fake_db.rollback.assert_awaited()


# ---------------------------------------------------------------------------
# 1b. achievement_event_consumer：两个吞点修复（:278 执行结果 / :390 成就解锁）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_achievement_unlocked_surfaces_whole_event_failure():
    from app.services.achievement_event_consumer import AchievementEventConsumer

    consumer = AchievementEventConsumer.__new__(AchievementEventConsumer)
    event = {"event_type": "achievement.unlocked", "user_id": str(uuid4()), "achievement_id": str(uuid4())}

    with _broken_session_factory_patch("app.services.achievement_event_consumer.AsyncSessionLocal"):
        with pytest.raises(Exception, match="DB connection lost"):
            await consumer._handle_achievement_unlocked(event)


@pytest.mark.asyncio
async def test_execution_result_achievement_surfaces_failure():
    from app.services.achievement_event_consumer import AchievementEventConsumer

    consumer = AchievementEventConsumer.__new__(AchievementEventConsumer)
    event = {
        "event_type": "execution.result_ingested",
        "success": True,
        "execution_intent_id": str(uuid4()),
        "execution_record_id": str(uuid4()),
        "user_id": str(uuid4()),
    }

    with _broken_session_factory_patch("app.services.achievement_event_consumer.AsyncSessionLocal"):
        with pytest.raises(Exception, match="DB connection lost"):
            await consumer._handle_execution_result(event)


# ---------------------------------------------------------------------------
# 1c. capsule_event_consumer：显式再生请求失败上抛（修前：error 日志后恒 ack）
# ---------------------------------------------------------------------------


def _capsule_consumer():
    from app.services.capsule_event_consumer import CapsuleEventConsumer

    consumer = CapsuleEventConsumer.__new__(CapsuleEventConsumer)
    consumer.event_bus = MagicMock()
    consumer.capsule_generation_service = MagicMock()
    consumer.capsule_generation_service.generate_capsules_batch = AsyncMock(
        side_effect=RuntimeError("generation infra down")
    )
    return consumer


@pytest.mark.asyncio
async def test_capsule_regenerate_surfaces_batch_failure():
    consumer = _capsule_consumer()
    fake_db = SimpleNamespace()
    session_mock = MagicMock()
    session_mock.return_value.__aenter__ = AsyncMock(return_value=fake_db)
    session_mock.return_value.__aexit__ = AsyncMock(return_value=False)

    prefs = SimpleNamespace(inferred={}, explicit={})
    pref_service = MagicMock()
    pref_service.get_preferences = AsyncMock(return_value=prefs)

    with patch("app.services.capsule_event_consumer.AsyncSessionLocal", return_value=session_mock.return_value):
        with patch("app.services.capsule_event_consumer.PreferenceService", return_value=pref_service):
            with pytest.raises(RuntimeError, match="generation infra down"):
                await consumer._handle_regenerate_request(
                    {"event_type": "capsule.regenerate_requested", "user_id": str(uuid4())}
                )

    consumer.capsule_generation_service.generate_capsules_batch.assert_awaited_once()


# ---------------------------------------------------------------------------
# 1d. aurora proactive pipeline：`_on_bus_event` 上抛（修前：blanket-except +
# 事实错误的 "失败走 DLQ 语义" 注释——吞掉恰使 DLQ 永不触发）
# ---------------------------------------------------------------------------


def _aurora_pipeline():
    from app.aurora.proactive.pipeline import ProactiveEventPipeline

    return ProactiveEventPipeline(redis=None, shadow=True)


@pytest.mark.asyncio
async def test_aurora_on_bus_event_surfaces_failure():
    pipeline = _aurora_pipeline()
    pipeline.handle_event = AsyncMock(side_effect=RuntimeError("unexpected pipeline crash"))

    with pytest.raises(RuntimeError, match="unexpected pipeline crash"):
        await pipeline._on_bus_event({"event_type": "task.completed", "user_id": str(uuid4())})


@pytest.mark.asyncio
async def test_aurora_on_bus_event_benign_path_unchanged():
    """白名单外事件：无异常静默忽略（良性 ack，行为不变）。"""
    pipeline = _aurora_pipeline()
    await pipeline._on_bus_event({"event_type": "not.in.whitelist", "user_id": str(uuid4())})


# ---------------------------------------------------------------------------
# 2. 既有合规契约回归护栏（本卡核查合规/注释化，锁定防回退）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nudge_consumer_surfaces_failure():
    """nudge 修前已是 raise 契约（EVENT-ACK C 清单该点过期）——锁定之。"""
    consumer = NudgeEventConsumer(event_bus=MagicMock())

    with _broken_session_factory_patch("app.services.nudge_event_consumer.AsyncSessionLocal"):
        with pytest.raises(Exception, match="DB connection lost"):
            await consumer._handle_nudge_triggered({"event_type": "nudge.triggered", "user_id": str(uuid4())})


@pytest.mark.asyncio
async def test_task_event_safe_run_containment_unchanged():
    """`_safe_run` 单项隔离契约：子处理器失败 warning 留痕、不上抛（显式白名单）。"""
    from loguru import logger as _logger  # noqa: F401  确保日志面已初始化

    async def boom():
        raise RuntimeError("sub-handler failed")

    await TaskEventConsumer._safe_run(boom, "Probe", "ctx-1")  # 不得上抛


@pytest.mark.asyncio
async def test_journey_consumer_error_path_emits_failure_update():
    """journey UX 语义 contain 契约：失败 → metric + 用户失败通知，不上抛。

    （上抛会使每次总线重试重复发送失败通知；改动需产品裁决——见基类白名单注释。）
    """
    from app.consumers.journey_consumer_base import JourneyEventConsumerBase

    class _BrokenJourneyConsumer(JourneyEventConsumerBase):
        EVENT_TYPE = "test.journey.event"
        CONSUMER_LABEL = "test_journey"

        async def _process_event(self, event, user_id):
            raise RuntimeError("journey processing failed")

    consumer = _BrokenJourneyConsumer(event_bus=MagicMock(), redis_client=AsyncMock())
    enqueue = AsyncMock()

    with patch("app.consumers.journey_consumer_base.SystemUpdateService") as mock_svc:
        mock_svc.return_value.enqueue = enqueue
        await consumer.handle_event({"event_type": "test.journey.event", "user_id": str(uuid4())})

    enqueue.assert_awaited_once()
    assert enqueue.await_args.args[1]["type"] == "journey_consumer_error"


@pytest.mark.asyncio
async def test_profile_cache_invalidation_best_effort_unchanged():
    """profile 缓存失效单项 best-effort：redis 失败 → warning，不阻断事件处理。"""
    from app.services.profile_event_consumer import ProfileEventConsumer

    consumer = ProfileEventConsumer.__new__(ProfileEventConsumer)
    consumer.redis = AsyncMock()
    consumer.redis.delete = AsyncMock(side_effect=RuntimeError("redis down"))
    consumer.event_bus = MagicMock()

    await consumer._invalidate_context_cache(str(uuid4()))  # 不得上抛
    await consumer._invalidate_profile_context_cache(str(uuid4()))  # 不得上抛


# ---------------------------------------------------------------------------
# 3. 总线管线通用性：修复域回调失败同样进入既有 requeue（不丢），不进 DLQ
# ---------------------------------------------------------------------------


class _FakeIdempotencyStore:
    async def get(self, key: str):
        return None

    async def lock(self, key: str) -> bool:
        return True

    async def set(self, key: str, value, ttl: int) -> None:
        return None

    async def unlock(self, key: str) -> None:
        return None


@pytest.mark.asyncio
async def test_bus_requeues_fixed_domain_callback_failure(monkeypatch: pytest.MonkeyPatch):
    """总线级：plan_health 回调第一次失败 → requeue（事件不丢）；重试成功 → ack。"""
    from app.core.event_bus import EventBus

    bus = EventBus()
    bus.redis = SimpleNamespace(xack=AsyncMock(), xadd=AsyncMock(return_value="2-0"))
    move_to_dlq = AsyncMock()
    monkeypatch.setattr(bus, "_move_to_dlq", move_to_dlq)
    monkeypatch.setattr(bus, "_get_idempotency_store", AsyncMock(return_value=_FakeIdempotencyStore()))

    attempts = 0

    async def flaky_callback(event: dict) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient plan_health failure")

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="plan_health_event_consumer",
        consumer_name="plan-health-test",
        callback=flaky_callback,
        message_id="1-0",
        data={"event_type": "plan.health.alerted", "user_id": str(uuid4())},
    )

    bus.redis.xadd.assert_awaited_once()  # 重试副本已重进 stream
    bus.redis.xack.assert_awaited_once_with("sparkle_events", "plan_health_event_consumer", "1-0")
    move_to_dlq.assert_not_awaited()

    await bus._process_stream_message(
        stream="sparkle_events",
        group_name="plan_health_event_consumer",
        consumer_name="plan-health-test",
        callback=flaky_callback,
        message_id="2-0",
        data={
            "event_type": "plan.health.alerted",
            "user_id": str(uuid4()),
            "_retry_count": "1",
        },
    )

    assert attempts == 2
    assert bus.redis.xack.await_count == 2
    move_to_dlq.assert_not_awaited()
