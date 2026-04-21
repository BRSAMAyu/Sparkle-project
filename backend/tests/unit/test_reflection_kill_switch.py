from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.reflection_agent import TriggeredReflectionResult
from app.core.cache import cache_service
from app.services.aurora_stage25_reflection_kill_switch_service import AuroraStage25ReflectionKillSwitchService
from app.services.task_reflection_service import TaskReflectionService


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str):
        self.store[key] = value

    async def exists(self, key: str):
        return 1 if key in self.store else 0

    async def setex(self, key: str, ttl: int, value: str):
        del ttl
        self.store[key] = value

    async def incr(self, key: str):
        value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(value)
        return value

    async def expire(self, key: str, ttl: int):
        del key, ttl

    async def delete(self, key: str):
        self.store.pop(key, None)


class _FakeReflector:
    async def reflect(self, **kwargs):
        return TriggeredReflectionResult(
            reflection_id="reflection-1",
            user_id=str(kwargs["user_id"]),
            category=str(kwargs["trigger_category"]),
            summary="最近一段时间计划推进反复停住，说明当前推进颗粒度仍然偏重。",
            confidence=0.9,
            reasoning="Repeated stall outcomes were present in the route history slice.",
            evidence=["e1", "e2"],
            llm_latency_ms=120,
            estimated_cost_usd=0.001,
            context_tokens=64,
            context_truncated=False,
            raw_payload={"summary": "ok"},
        )


@pytest.mark.asyncio
async def test_reflection_kill_switch_off_returns_skip(db_session, monkeypatch) -> None:
    service = TaskReflectionService(db_session)
    monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="off"))
    monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))

    result = await service.handle_triggered_reflection(
        user_id=uuid4(),
        category="plan_stall",
        trigger_payload={},
    )

    assert result["reason"] == "off"


@pytest.mark.asyncio
async def test_reflection_kill_switch_shadow_generates_without_writing(db_session, monkeypatch) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(cache_service, "redis", redis)
    service = TaskReflectionService(db_session, redis=redis)
    write_mock = AsyncMock()
    monkeypatch.setattr("app.services.task_reflection_service.get_reflection_agent", lambda: _FakeReflector())
    monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="shadow"))
    monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))
    monkeypatch.setattr(
        "app.services.memory_inferred_write_lane.MemoryInferredWriteLaneService.write_candidate_to_l1",
        write_mock,
    )

    result = await service.handle_triggered_reflection(
        user_id=uuid4(),
        category="plan_stall",
        trigger_payload={},
    )

    assert result["status"] == "shadowed"
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reflection_kill_switch_live_writes_memory(db_session, monkeypatch) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(cache_service, "redis", redis)
    service = TaskReflectionService(db_session, redis=redis)
    monkeypatch.setattr("app.services.task_reflection_service.get_reflection_agent", lambda: _FakeReflector())
    monkeypatch.setattr(service.kill_switch, "is_trigger_enabled", AsyncMock(return_value=True))
    monkeypatch.setattr(service.kill_switch, "get_mode", AsyncMock(return_value="live"))
    monkeypatch.setattr(service, "_trigger_on_cooldown", AsyncMock(return_value=False))
    monkeypatch.setattr(
        "app.services.memory_inferred_write_lane.MemoryInferredWriteLaneService.write_candidate_to_l1",
        AsyncMock(return_value=type("MemoryRecord", (), {"id": uuid4()})()),
    )
    publish_mock = AsyncMock()
    monkeypatch.setattr("app.services.task_reflection_service.event_bus.publish", publish_mock)

    result = await service.handle_triggered_reflection(
        user_id=uuid4(),
        category="plan_stall",
        trigger_payload={},
    )

    assert result["status"] == "written"
    assert "memory_id" in result
    publish_mock.assert_awaited()


@pytest.mark.asyncio
async def test_reflection_kill_switch_service_roundtrip(monkeypatch) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(cache_service, "redis", redis)
    service = AuroraStage25ReflectionKillSwitchService()

    await service.set_mode("live")
    assert await service.get_mode() == "live"
    await service.set_mode("off")
    assert await service.get_mode() == "off"
