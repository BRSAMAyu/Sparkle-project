from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
from app.orchestration.schemas import RouteDecision
from app.services.bayesian_routing_wire_service import BayesianRoutingWireService


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.data[key] = value
        self.ttls[key] = ttl


@pytest.mark.asyncio
async def test_bayesian_router_integration_off_mode_is_passthrough() -> None:
    service = BayesianRoutingWireService(None)
    service.kill_switch.get_mode = AsyncMock(return_value="off")

    original = RouteDecision(execution_mode="direct", reason="fallback", risk_level="low", confidence=0.8)
    updated, result = await service.apply(user_id="u1", route_decision=original, source_state_key="state")

    assert updated.execution_mode == "direct"
    assert result.mode == "off"
    assert result.recommended_target is None


@pytest.mark.asyncio
async def test_bayesian_router_integration_shadow_reports_divergence() -> None:
    redis = FakeRedis()
    learner = PersistentBayesianLearner(redis, user_id="u2")
    for _ in range(4):
        await learner.update("state", "langgraph", True)
    await learner.drain_pending_saves()

    service = BayesianRoutingWireService(redis)
    service.kill_switch.get_mode = AsyncMock(return_value="shadow")
    original = RouteDecision(execution_mode="direct", reason="fallback", risk_level="medium", confidence=0.7)

    updated, result = await service.apply(user_id="u2", route_decision=original, source_state_key="state")

    assert updated.execution_mode == "direct"
    assert result.recommended_target == "langgraph"
    assert result.divergence is True


@pytest.mark.asyncio
async def test_bayesian_router_integration_live_mode_applies_recommendation(monkeypatch) -> None:
    redis = FakeRedis()
    learner = PersistentBayesianLearner(redis, user_id="u3")
    for _ in range(5):
        await learner.update("state", "hybrid", True)
    await learner.drain_pending_saves()

    service = BayesianRoutingWireService(redis)
    service.kill_switch.get_mode = AsyncMock(return_value="live")
    monkeypatch.setattr(service, "_in_canary_bucket", lambda _user_id: True)
    original = RouteDecision(execution_mode="direct", reason="fallback", risk_level="medium", confidence=0.7)

    updated, result = await service.apply(user_id="u3", route_decision=original, source_state_key="state")

    assert updated.execution_mode == "hybrid"
    assert result.applied_target == "hybrid"


@pytest.mark.asyncio
async def test_bayesian_router_integration_live_mode_respects_bucket(monkeypatch) -> None:
    redis = FakeRedis()
    learner = PersistentBayesianLearner(redis, user_id="u4")
    for _ in range(5):
        await learner.update("state", "hybrid", True)
    await learner.drain_pending_saves()

    service = BayesianRoutingWireService(redis)
    service.kill_switch.get_mode = AsyncMock(return_value="live")
    monkeypatch.setattr(service, "_in_canary_bucket", lambda _user_id: False)
    original = RouteDecision(execution_mode="direct", reason="fallback", risk_level="medium", confidence=0.7)

    updated, result = await service.apply(user_id="u4", route_decision=original, source_state_key="state")

    assert updated.execution_mode == "direct"
    assert result.recommended_target == "hybrid"
