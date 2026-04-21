from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.event_publishers.srl_events import publish_srl_event
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService


@pytest.mark.asyncio
async def test_publish_srl_event_skips_when_main_mode_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    settings.AURORA_SRL_MODE = "off"
    publish_mock = AsyncMock()
    monkeypatch.setattr("app.event_publishers.srl_events.event_bus.publish", publish_mock)

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="task.started",
        evidence_id="task-1",
    )

    assert result is None
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_srl_event_skips_when_bridge_mode_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.set_mode("live")
    await service.set_bridge_mode("off")
    publish_mock = AsyncMock()
    monkeypatch.setattr("app.event_publishers.srl_events.event_bus.publish", publish_mock)

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="task.started",
        evidence_id="task-1",
    )

    assert result is None
    publish_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_srl_event_publishes_transition_payload(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    service = AuroraStage29SRLKillSwitchService()
    await service.ordered_startup("live")
    publish_mock = AsyncMock(return_value="1-0")
    monkeypatch.setattr("app.event_publishers.srl_events.event_bus.publish", publish_mock)

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="task.completed",
        evidence_id="task-2",
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
    service = AuroraStage29SRLKillSwitchService()
    await service.set_mode("live")
    await service.set_bridge_mode("shadow")
    publish_mock = AsyncMock(return_value="2-0")
    monkeypatch.setattr("app.event_publishers.srl_events.event_bus.publish", publish_mock)

    result = await publish_srl_event(
        user_id=uuid4(),
        trigger_event_type="plan.created",
        evidence_id="plan-2",
    )

    assert result == "2-0"
    publish_mock.assert_awaited_once()
