from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.orchestration import circuit_breaker as circuit_breaker_module
from app.orchestration.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


@pytest.fixture
def muted_breaker(monkeypatch):
    async def _noop_emit(self, old_state: str, new_state: str, reason: str):
        return None

    monkeypatch.setattr(CircuitBreaker, "_emit_state_change_event", _noop_emit)


@pytest.mark.asyncio
async def test_breaker_starts_closed(muted_breaker):
    breaker = CircuitBreaker("langgraph")

    state = breaker.get_state()

    assert breaker._state == CircuitState.CLOSED
    assert state.state == CircuitState.CLOSED.value
    assert state.failure_count == 0


@pytest.mark.asyncio
async def test_breaker_opens_after_threshold(muted_breaker):
    breaker = CircuitBreaker(
        "langgraph",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout_ms=1000,
            failure_rate_threshold=1.1,
            window_size=10,
        ),
    )

    await breaker.on_failure("boom-1")
    await breaker.on_failure("boom-2")
    assert breaker._state == CircuitState.CLOSED

    await breaker.on_failure("boom-3")

    assert breaker._state == CircuitState.OPEN
    assert breaker.get_state().opened_count == 1


@pytest.mark.asyncio
async def test_breaker_half_open_after_timeout(monkeypatch, muted_breaker):
    now = datetime(2026, 3, 31, 12, 0, 0)
    monkeypatch.setattr(circuit_breaker_module, "_utcnow", lambda: now)
    breaker = CircuitBreaker(
        "langgraph",
        CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            timeout_ms=1000,
            failure_rate_threshold=1.1,
        ),
    )

    await breaker.on_failure("trip")
    assert breaker._state == CircuitState.OPEN

    now = now + timedelta(seconds=2)
    allowed, reason = await breaker.allow_request()

    assert allowed is True
    assert reason == "circuit_half_open_attempting"
    assert breaker._state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_breaker_closes_after_success_in_half_open(monkeypatch, muted_breaker):
    now = datetime(2026, 3, 31, 12, 0, 0)
    monkeypatch.setattr(circuit_breaker_module, "_utcnow", lambda: now)
    breaker = CircuitBreaker(
        "langgraph",
        CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=1,
            timeout_ms=1000,
            failure_rate_threshold=1.1,
        ),
    )

    await breaker.on_failure("trip")
    now = now + timedelta(seconds=2)
    await breaker.allow_request()
    await breaker.on_success()

    assert breaker._state == CircuitState.CLOSED
    assert breaker.get_state().failure_count == 0
    assert breaker.get_state().success_count == 0


@pytest.mark.asyncio
async def test_breaker_sliding_window_rate(monkeypatch, muted_breaker):
    now = datetime(2026, 3, 31, 12, 0, 0)
    monkeypatch.setattr(circuit_breaker_module, "_utcnow", lambda: now)
    breaker = CircuitBreaker(
        "langgraph",
        CircuitBreakerConfig(
            failure_threshold=99,
            success_threshold=1,
            timeout_ms=1000,
            failure_rate_threshold=1.1,
            window_size=4,
        ),
    )

    await breaker.on_success()
    now = now + timedelta(seconds=1)
    await breaker.on_failure("boom-1")
    now = now + timedelta(seconds=1)
    await breaker.on_success()
    now = now + timedelta(seconds=1)
    await breaker.on_failure("boom-2")

    assert breaker._calculate_failure_rate() == pytest.approx(0.5)
    assert len(breaker._result_window) == 4
