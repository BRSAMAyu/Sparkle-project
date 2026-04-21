from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.orchestration.schemas import RouteDecision
from app.services.bayesian_routing_wire_service import BayesianRoutingWireService


@pytest.mark.asyncio
async def test_bayesian_rollback_parity_keeps_fallback_when_no_signal() -> None:
    service = BayesianRoutingWireService(None)
    service.kill_switch.get_mode = AsyncMock(return_value="live_canary")

    original = RouteDecision(execution_mode="langgraph", reason="fallback", risk_level="medium", confidence=0.7)
    updated, result = await service.apply(user_id="u1", route_decision=original, source_state_key="unknown")

    assert updated.execution_mode == "langgraph"
    assert result.applied_target == "langgraph"


@pytest.mark.asyncio
async def test_bayesian_rollback_parity_off_and_shadow_match_without_data() -> None:
    shadow = BayesianRoutingWireService(None)
    off = BayesianRoutingWireService(None)
    shadow.kill_switch.get_mode = AsyncMock(return_value="shadow")
    off.kill_switch.get_mode = AsyncMock(return_value="off")

    direct = RouteDecision(execution_mode="direct", reason="fallback", risk_level="low", confidence=0.8)
    updated_shadow, _ = await shadow.apply(user_id="u1", route_decision=direct, source_state_key="unknown")
    updated_off, _ = await off.apply(
        user_id="u1",
        route_decision=RouteDecision(execution_mode="direct", reason="fallback", risk_level="low", confidence=0.8),
        source_state_key="unknown",
    )

    assert updated_shadow.execution_mode == updated_off.execution_mode == "direct"
