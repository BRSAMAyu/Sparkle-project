"""PROD-LOG2 ②-4（PROD-FIX-4）契约测试：安全告警必须走 300s 冷却通道.

缺陷：``_check_system_security`` 直调 ``_send_alert_notification``，绕过
``trigger_security_alert`` 内现成的冷却机制（``security:alert_cooldown:{type}``
+ ALERT_COOLDOWN=300s）→ DEBUG 开发环境下「DEBUG mode is enabled」高危告警
每分钟重发（生产实测 88 分钟 90+90 条）。

钉住的契约：
1. _check_system_security 告警经冷却通道：查冷却键、只发一次、写冷却键；
2. _check_abnormal_patterns 的 brute_force / admin 告警同规（同型扫描补钉）；
3. redis 不可用时退回直发（无冷却通道可吃，保持基线可观测）；
4. DEBUG 常态说明不再以 WARNING 级每分钟刷屏（降 DEBUG，由告警通道承载）。
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from loguru import logger

from app.config import settings
from app.core.security_monitor import SecurityMonitor


def _monitor_with_redis(redis: AsyncMock) -> SecurityMonitor:
    monitor = SecurityMonitor()
    monitor.redis = redis
    return monitor


@pytest.fixture
def no_warning_noise():
    """捕获 WARNING 级日志（用后清理 sink）。"""
    records: list = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="WARNING")
    yield records
    logger.remove(sink_id)


@pytest.mark.asyncio
async def test_system_security_alert_goes_through_cooldown_channel(monkeypatch):
    """system_security 告警必须查/写冷却键且冷却期内只发一次."""
    monkeypatch.setattr(settings, "DEBUG", True, raising=False)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)  # 首次：无冷却键
    monitor = _monitor_with_redis(redis)
    sends = AsyncMock()
    monitor._send_alert_notification = sends

    await monitor._check_system_security()

    cooldown_key = "security:alert_cooldown:system_security_issue"
    redis.get.assert_awaited_with(cooldown_key)
    assert sends.await_count == 1, "无冷却时应恰好发送一次"
    redis.setex.assert_awaited_once()
    assert redis.setex.await_args.args[0] == cooldown_key
    assert redis.setex.await_args.args[1] == monitor.ALERT_COOLDOWN

    # 冷却期内第二次检查：不再发送
    redis.get = AsyncMock(return_value="1")
    await monitor._check_system_security()
    assert sends.await_count == 1, "300s 冷却期内不得重发"


@pytest.mark.asyncio
async def test_abnormal_pattern_alerts_go_through_cooldown_channel(monkeypatch):
    """brute_force / admin 异常告警同走冷却通道（同型扫描补钉）."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.llen = AsyncMock(return_value=25)  # 同时超 brute(10)/admin(20) 阈值
    monitor = _monitor_with_redis(redis)
    sends = AsyncMock()
    monitor._send_alert_notification = sends

    await monitor._check_abnormal_patterns()

    cooldown_prefix = "security:alert_cooldown:"
    checked_keys = [call.args[0] for call in redis.get.await_args_list]
    assert f"{cooldown_prefix}brute_force_attempt" in checked_keys
    assert f"{cooldown_prefix}unusual_admin_activity" in checked_keys
    assert sends.await_count == 2, "无冷却时 brute+admin 各发一次"
    assert redis.setex.await_count == 2, "每类告警各自写冷却键"


@pytest.mark.asyncio
async def test_system_security_alert_falls_back_to_direct_send_without_redis(monkeypatch):
    """redis 不可用：退回直发（无冷却通道可吃），保持基线可观测不抛错."""
    monkeypatch.setattr(settings, "DEBUG", True, raising=False)
    monitor = SecurityMonitor()
    monitor.redis = None
    sends = AsyncMock()
    monitor._send_alert_notification = sends

    await monitor._check_system_security()  # 不得抛 AttributeError

    assert sends.await_count == 1


@pytest.mark.asyncio
async def test_debug_mode_notice_not_emitted_at_warning_level(monkeypatch, no_warning_noise):
    """DEBUG 常态说明不得以 WARNING 级每分钟刷屏——状态由冷却后的告警承载."""
    monkeypatch.setattr(settings, "DEBUG", True, raising=False)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="1")  # 冷却命中：告警静默
    monitor = _monitor_with_redis(redis)

    await monitor._check_system_security()

    warning_texts = [str(r["message"]) for r in no_warning_noise]
    debug_on = [t for t in warning_texts if "DEBUG mode is ON" in t]
    assert debug_on == [], (
        f"DEBUG 常态说明不得打 WARNING（生产每分钟一条）: {debug_on[:3]}"
    )
