from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.plan_review_service import PlanReviewService


@pytest.mark.asyncio
async def test_plan_review_service_creates_and_registers_langgraph_breaker(monkeypatch):
    service = PlanReviewService(redis_client=MagicMock())
    registry: dict[str, object] = {}

    initialize_mock = AsyncMock()
    monkeypatch.setattr(
        "app.orchestration.plan_review_service.CircuitBreaker.initialize",
        initialize_mock,
    )
    monkeypatch.setattr(
        "app.orchestration.plan_review_service.circuit_breaker_registry.get",
        lambda name: registry.get(name),
    )
    monkeypatch.setattr(
        "app.orchestration.plan_review_service.circuit_breaker_registry.register",
        lambda breaker: registry.setdefault(breaker.name, breaker),
    )

    breaker = await service._get_langgraph_breaker()

    initialize_mock.assert_awaited_once()
    assert registry["langgraph_planner"] is breaker


@pytest.mark.asyncio
async def test_plan_review_service_reuses_registered_langgraph_breaker(monkeypatch):
    service = PlanReviewService(redis_client=MagicMock())
    existing_breaker = object()

    initialize_mock = AsyncMock()
    monkeypatch.setattr(
        "app.orchestration.plan_review_service.CircuitBreaker.initialize",
        initialize_mock,
    )
    monkeypatch.setattr(
        "app.orchestration.plan_review_service.circuit_breaker_registry.get",
        lambda name: existing_breaker,
    )

    breaker = await service._get_langgraph_breaker()

    initialize_mock.assert_not_awaited()
    assert breaker is existing_breaker
