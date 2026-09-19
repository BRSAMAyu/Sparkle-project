from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.models.memory import EpisodicMemory
from app.services.accountability_notification_service import accountability_notification_service
from app.services.aurora_stage24_policy_kill_switch_service import AuroraStage24PolicyKillSwitchService
class _InMemoryKillSwitchRedis:
    """Hermetic stand-in: kill switches use get/set/delete/incr/expire only."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str) -> int:
        self._store[key] = str(int(self._store.get(key, "0")) + 1)
        return int(self._store[key])

    async def expire(self, key: str, ttl: int) -> None:
        pass


from app.services.policy_scheduler_service import PolicySchedulerService


@pytest.mark.asyncio
async def test_policy_kill_switch_defaults_to_off(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "unexpected")

    mode = await AuroraStage24PolicyKillSwitchService().get_mode()

    assert mode == "off"


@pytest.mark.asyncio
async def test_policy_kill_switch_round_trips_modes(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "off")
    # Without Redis the mode write is dropped and the read falls back to
    # settings; stub the store so the round trip is actually observable.
    monkeypatch.setattr(cache_service, "redis", _InMemoryKillSwitchRedis())
    service = AuroraStage24PolicyKillSwitchService()

    await service.set_mode("live")
    assert await service.get_mode() == "live"
    await service.set_mode("shadow")
    assert await service.get_mode() == "shadow"


@pytest.mark.asyncio
async def test_policy_scheduler_respects_off_mode(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_POLICY_COMPILER_MODE", "off")
    commitment = EpisodicMemory(
        id=uuid4(),
        user_id=uuid4(),
        summary="整理复盘",
        source_type="chat",
        source_id="session-1",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime(2026, 4, 20, 9, 0, 0),
        due_at=datetime(2026, 4, 24, 9, 0, 0),
        evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
    )
    db_session.add(commitment)
    await db_session.commit()
    notify = AsyncMock()
    monkeypatch.setattr(accountability_notification_service, "send_policy_notification", notify)

    scheduler = PolicySchedulerService(db_session)
    await scheduler.ensure_policies_for_user(user_id=commitment.user_id, now=datetime(2026, 4, 21, 9, 0, 0))
    result = await scheduler.process_due_policies(now=datetime(2026, 4, 21, 9, 0, 0))

    assert result == {"due_count": 0, "triggered_count": 0}
    assert notify.await_count == 0
