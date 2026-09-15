"""
Redis failure scenario tests.

Tests that the system handles Redis connection failures gracefully
and recovers properly when Redis becomes available again.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.state_manager import FSMState, SessionStateManager
from app.orchestration.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


@pytest.mark.asyncio
async def test_state_load_fallback_on_redis_disconnect():
    """Test that state loading falls back gracefully when Redis is disconnected."""
    # Create state manager with mock Redis that simulates disconnect
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=ConnectionError("Connection lost"))

    manager = SessionStateManager(mock_redis)

    # Should not raise exception, return None
    state = await manager.load_state("test-session")

    assert state is None


@pytest.mark.asyncio
async def test_state_save_handles_redis_disconnect():
    """Test that state save handles Redis disconnection gracefully."""
    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock(side_effect=ConnectionError("Connection lost"))

    manager = SessionStateManager(mock_redis)

    result = await manager.save_state("test-session", FSMState(session_id="test-session", state="INIT"))
    assert result is False


@pytest.mark.asyncio
async def test_circuit_breaker_recovers_after_redis_restart():
    """Test that circuit breaker recovers after Redis restart."""
    # Create circuit breaker with mock Redis
    mock_redis = MagicMock()
    breaker = CircuitBreaker(
        name="test_breaker",
        config=CircuitBreakerConfig(timeout_ms=100),
        redis_client=mock_redis,
    )

    # Set to OPEN state
    from app.orchestration.circuit_breaker import CircuitState
    breaker._state = CircuitState.OPEN
    breaker._last_failure_time = None

    # Mock Redis to return old persisted state
    from datetime import datetime, timezone, timedelta
    old_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=5)
    import json
    mock_redis.get = AsyncMock(return_value=json.dumps({
        "state": "open",
        "failure_count": 5,
        "success_count": 0,
        "opened_count": 1,
        "last_failure_time": old_time.isoformat(),
        "last_state_change": old_time.isoformat(),
    }))

    # Initialize should load persisted state
    await breaker.initialize()

    # Check if request is allowed after timeout
    allowed, reason = await breaker.allow_request()

    # Should transition to HALF_OPEN and allow request
    assert allowed is True
    assert breaker.get_state().state == "half_open"


@pytest.mark.asyncio
async def test_state_manager_with_intermittent_redis():
    """Test state manager behavior with intermittent Redis connectivity."""
    mock_redis = MagicMock()

    # Simulate intermittent failures
    call_count = [0]

    async def inconsistent_get(key):
        call_count[0] += 1
        if call_count[0] % 2 == 0:
            raise ConnectionError("Redis down")
        return '{"session_id":"session-1","state":"INIT","details":"ok"}'

    mock_redis.get = inconsistent_get

    manager = SessionStateManager(mock_redis)

    # First call succeeds
    state1 = await manager.load_state("session-1")
    assert state1.session_id == "session-1"
    assert state1.state == "INIT"

    # Second call fails
    state2 = await manager.load_state("session-1")
    assert state2 is None

    # Third call succeeds again
    state3 = await manager.load_state("session-1")
    assert state3.session_id == "session-1"
    assert state3.state == "INIT"


@pytest.mark.asyncio
async def test_concurrent_operations_with_redis_failure():
    """Test concurrent state operations during Redis failure."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
    mock_redis.setex = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    manager = SessionStateManager(mock_redis)

    # Run multiple concurrent operations
    async def operation(session_id):
        await manager.save_state(session_id, FSMState(session_id=session_id, state="INIT"))
        return await manager.load_state(session_id)

    tasks = [operation(f"session-{i}") for i in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # All operations should complete without propagating exceptions.
    assert len(results) == 10
    for result in results:
        assert result is None


@pytest.mark.asyncio
async def test_redis_timeout_during_state_load():
    """Test that Redis timeout during state load is handled gracefully."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=asyncio.TimeoutError("Redis timeout"))

    manager = SessionStateManager(mock_redis)

    # Should not raise exception
    state = await manager.load_state("test-session")

    assert state is None


@pytest.mark.asyncio
async def test_redis_timeout_during_state_save():
    """Test that Redis timeout during state save is handled gracefully."""
    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock(side_effect=asyncio.TimeoutError("Redis timeout"))

    manager = SessionStateManager(mock_redis)

    result = await manager.save_state("test-session", FSMState(session_id="test-session", state="INIT"))
    assert result is False


@pytest.mark.asyncio
async def test_lock_fallback_on_redis_failure():
    """Test that lock operations fall back gracefully when Redis fails."""
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
    mock_redis.eval = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    manager = SessionStateManager(mock_redis)

    # Lock acquisition should fail gracefully (return False)
    acquired = await manager.acquire_lock("lock-key", "request-1")

    assert acquired is False

    # Lock release should not raise exception
    released = await manager.release_lock("lock-key", "request-1")
    assert released is False


@pytest.mark.asyncio
async def test_circuit_breaker_saves_state_on_redis_failure():
    """Test that circuit breaker handles save_state failures gracefully."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    breaker = CircuitBreaker(
        name="test_breaker",
        config=CircuitBreakerConfig(timeout_ms=100),
        redis_client=mock_redis,
    )

    # Initialize (load will fail, uses defaults)
    await breaker.initialize()

    # Record failure (save will fail silently)
    await breaker.on_failure("Test error")

    # Should still be in OPEN state locally
    from app.orchestration.circuit_breaker import CircuitState
    assert breaker._state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_multiple_components_with_shared_redis_failure():
    """Test multiple components handling shared Redis failure."""
    mock_redis = MagicMock()

    # All Redis operations fail
    async def failing_redis(*args, **kwargs):
        raise ConnectionError("Redis down")

    mock_redis.get = failing_redis
    mock_redis.set = failing_redis
    mock_redis.setex = failing_redis
    mock_redis.eval = failing_redis

    # Create multiple components
    state_manager = SessionStateManager(mock_redis)
    breaker = CircuitBreaker(
        name="test_breaker",
        config=CircuitBreakerConfig(),
        redis_client=mock_redis,
    )

    # All should initialize without error
    await breaker.initialize()

    # Operations should fail gracefully
    state = await state_manager.load_state("session-1")
    assert state is None

    result = await state_manager.save_state("session-1", FSMState(session_id="session-1", state="INIT"))
    assert result is False

    await breaker.on_failure("Test error")
    # No exception raised
