"""P2-F (daily-flow R2): the Home greeting line must not freeze until midnight.

The daily context line used to be cached with ``ttl=seconds_until_next_day``,
so the context baked into it (streak, days_to_deadline, ...) stayed at the
first generation of the day and contradicted the live dashboard for the rest
of the day (eval: greeting said streak=1 while the dashboard showed 3;
only force_refresh would correct it). The TTL is now bounded.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.growth_dashboard_service import GrowthDashboardService


@pytest.mark.asyncio
async def test_daily_context_line_ttl_is_bounded(monkeypatch):
    captured: dict = {}

    async def _fake_set(key, payload, ttl=None):
        captured["ttl"] = ttl

    monkeypatch.setattr("app.core.cache.cache_service.get", AsyncMock(return_value=None))
    monkeypatch.setattr("app.core.cache.cache_service.set", _fake_set)

    service = GrowthDashboardService(db=None)
    service._build_daily_context_line_context = AsyncMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(
            target_day=datetime.now().date(),
            display_name="测试者",
            plan_name="冲刺计划",
            subject=None,
            days_to_deadline=3,
            yesterday_total=2,
            yesterday_completed=1,
            completed_yesterday=1,
            bottleneck=None,
            streak_days=3,
            next_action_title=None,
        )
    )
    service._get_recent_daily_context_lines = AsyncMock(return_value=[])  # type: ignore[method-assign]
    service._generate_daily_context_line_with_ai = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service._remember_daily_context_line = AsyncMock()  # type: ignore[method-assign]

    payload = await service.get_daily_context_line(uuid4())

    assert payload["source"] == "rule"
    ttl = captured.get("ttl")
    assert ttl is not None
    # The whole point of P2-F: a bounded TTL, not "until midnight".
    assert ttl <= GrowthDashboardService.DAILY_CONTEXT_LINE_TTL_SECONDS


@pytest.mark.asyncio
async def test_daily_context_line_regenerates_with_fresh_context_after_ttl(monkeypatch):
    """After the bounded TTL the line must pick up the new context value —
    a regenerated payload reflects the new streak instead of the frozen one."""

    async def _fake_set(key, payload, ttl=None):
        return None

    monkeypatch.setattr("app.core.cache.cache_service.get", AsyncMock(return_value=None))
    monkeypatch.setattr("app.core.cache.cache_service.set", _fake_set)

    service = GrowthDashboardService(db=None)
    seen_streaks: list[int] = []
    for streak in (1, 3):
        service._build_daily_context_line_context = AsyncMock(  # type: ignore[method-assign]
            return_value=SimpleNamespace(
                target_day=datetime.now().date(),
                display_name="测试者",
                plan_name=None,
                subject=None,
                days_to_deadline=None,
                yesterday_total=0,
                yesterday_completed=0,
                completed_yesterday=0,
                bottleneck=None,
                streak_days=streak,
                next_action_title=None,
            )
        )
        service._get_recent_daily_context_lines = AsyncMock(return_value=[])  # type: ignore[method-assign]
        service._generate_daily_context_line_with_ai = AsyncMock(return_value=None)  # type: ignore[method-assign]
        service._remember_daily_context_line = AsyncMock()  # type: ignore[method-assign]

        payload = await service.get_daily_context_line(uuid4())
        seen_streaks.append(payload["context"]["streak_days"])

    assert seen_streaks == [1, 3], "regeneration must re-read the live context, not replay the first one"
