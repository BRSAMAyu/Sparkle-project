from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.event_publishers.srl_events import publish_srl_event
from app.services.aurora_stage29_srl_kill_switch_service import (
    AuroraStage29SRLKillSwitchService,
)


@pytest.mark.asyncio
async def test_publish_srl_event_skips_when_main_mode_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    # V3-FIX-120：经 monkeypatch 注入（原裸赋值残留 settings 单例，跨文件污染整个
    # SRL 族——无 Redis 时 read_mode 回落 settings，"off" 使后续所有 tracker 用例
    # 得到 UNKNOWN/DID NOT RAISE）
    monkeypatch.setattr(settings, "AURORA_SRL_MODE", "off")
    publish_mock = AsyncMock()
    monkeypatch.setattr(
        "app.event_publishers.srl_events.event_bus.publish", publish_mock
    )

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="task.started",
        evidence_id="task:1",
    )

    assert result is None
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_srl_event_skips_when_bridge_mode_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    # V3-FIX-120：无 Redis 时 set_bridge_mode 写入被忽略、读取回落 settings——
    # 显式注入本用例所需模式（原先依赖上一用例泄漏的 mode=off 才成立）
    monkeypatch.setattr(settings, "AURORA_SRL_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_SRL_BRIDGE_MODE", "off")
    service = AuroraStage29SRLKillSwitchService()
    await service.set_mode("live")
    await service.set_bridge_mode("off")
    publish_mock = AsyncMock()
    monkeypatch.setattr(
        "app.event_publishers.srl_events.event_bus.publish", publish_mock
    )

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="task.started",
        evidence_id="task:1",
    )

    assert result is None
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_srl_event_publishes_transition_payload(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    # V3-FIX-120：ordered_startup 的 Redis 写在 redis=None 时被忽略，读取回落
    # settings——显式注入 live，避免依赖进程内残留状态
    monkeypatch.setattr(settings, "AURORA_SRL_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_SRL_BRIDGE_MODE", "live")
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    publish_mock = AsyncMock(return_value="1-0")
    monkeypatch.setattr(
        "app.event_publishers.srl_events.event_bus.publish", publish_mock
    )

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="task.completed",
        evidence_id="task:2",
        metadata={"plan_id": "plan-1"},
    )

    assert result == "1-0"
    publish_mock.assert_awaited()
    payload = publish_mock.await_args.args[1]
    assert payload["event_type"] == "srl.phase.transition"
    assert payload["trigger_event_type"] == "task.completed"
    assert payload["metadata"]["plan_id"] == "plan-1"


@pytest.mark.asyncio
async def test_publish_srl_event_keeps_shadow_mode_active(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    # V3-FIX-120：同上——无 Redis 时模式读取回落 settings，显式注入 live/shadow
    monkeypatch.setattr(settings, "AURORA_SRL_MODE", "live")
    monkeypatch.setattr(settings, "AURORA_SRL_BRIDGE_MODE", "shadow")
    service = AuroraStage29SRLKillSwitchService()
    await service.set_mode("live")
    await service.set_bridge_mode("shadow")
    publish_mock = AsyncMock(return_value="2-0")
    monkeypatch.setattr(
        "app.event_publishers.srl_events.event_bus.publish", publish_mock
    )

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="plan.created",
        evidence_id="plan:2",
    )

    assert result == "2-0"
    publish_mock.assert_awaited_once()
