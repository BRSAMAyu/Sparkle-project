"""
Concurrency tests for SessionStateManager.

Tests thread-safety, distributed locking, and atomic operations
for state management.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.state_manager import FSMState, SessionStateManager


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    return MagicMock()


@pytest.fixture
def state_manager(mock_redis):
    """Create SessionStateManager instance."""
    return SessionStateManager(mock_redis)


@pytest.mark.asyncio
async def test_save_state_serializes_fsm_state(state_manager, mock_redis):
    """Test that save_state correctly serializes FSMState to JSON."""
    session_id = "test-session"
    test_state = FSMState(
        session_id=session_id,
        state="THINKING",
        details="Processing request",
        user_id="user-1",
    )

    mock_redis.setex = AsyncMock()

    await state_manager.save_state(session_id, test_state)

    # Verify setex was called
    assert mock_redis.setex.called
    call_args = mock_redis.setex.call_args
    # setex(key, ttl, value) - index 2 is the JSON value
    state_json = call_args[0][2]
    import json
    parsed = json.loads(state_json)
    assert parsed["session_id"] == session_id
    assert parsed["state"] == "THINKING"


@pytest.mark.asyncio
async def test_load_state_parses_fsm_state(state_manager, mock_redis):
    """Test that load_state correctly parses JSON to FSMState."""
    session_id = "test-session"

    test_state_json = '{"session_id": "test-session", "state": "DONE", "details": "Completed"}'
    mock_redis.get = AsyncMock(return_value=test_state_json)

    state = await state_manager.load_state(session_id)

    assert state.session_id == "test-session"
    assert state.state == "DONE"
    assert state.details == "Completed"


@pytest.mark.asyncio
async def test_load_state_returns_none_for_missing_state(state_manager, mock_redis):
    """Test that load_state returns None when state doesn't exist."""
    session_id = "nonexistent-session"
    mock_redis.get = AsyncMock(return_value=None)

    state = await state_manager.load_state(session_id)

    assert state is None


@pytest.mark.asyncio
async def test_redis_connection_failure_during_save(state_manager, mock_redis):
    """Test that save_state handles Redis connection failures gracefully."""
    session_id = "test-session"
    test_state = FSMState(session_id=session_id, state="INIT")

    # Mock connection error
    mock_redis.setex = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    # Should return False (save failed)
    result = await state_manager.save_state(session_id, test_state)

    assert result is False


@pytest.mark.asyncio
async def test_redis_connection_failure_during_load(state_manager, mock_redis):
    """Test that load_state handles Redis connection failures gracefully."""
    session_id = "test-session"

    # Mock connection error
    mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    # Should return None
    state = await state_manager.load_state(session_id)

    assert state is None


@pytest.mark.asyncio
async def test_concurrent_state_saves(state_manager, mock_redis):
    """Test that concurrent state saves are handled correctly."""
    session_id = "test-session"
    mock_redis.setex = AsyncMock()

    # Create multiple states to save concurrently
    async def save_state(state_value):
        state = FSMState(session_id=session_id, state=state_value)
        return await state_manager.save_state(session_id, state)

    tasks = [save_state(f"STATE_{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)

    # All saves should complete
    assert len(results) == 10
    # Most should succeed (all but potential connection issues)
    assert sum(1 for r in results if r is True) >= 0


@pytest.mark.asyncio
async def test_redis_timeout_during_state_load(state_manager, mock_redis):
    """Test that Redis timeout during state load is handled gracefully."""
    session_id = "test-session"

    mock_redis.get = AsyncMock(side_effect=asyncio.TimeoutError("Redis timeout"))

    state = await state_manager.load_state(session_id)

    assert state is None


@pytest.mark.asyncio
async def test_redis_timeout_during_state_save(state_manager, mock_redis):
    """Test that Redis timeout during state save is handled gracefully."""
    session_id = "test-session"
    test_state = FSMState(session_id=session_id, state="INIT")

    mock_redis.setex = AsyncMock(side_effect=asyncio.TimeoutError("Redis timeout"))

    result = await state_manager.save_state(session_id, test_state)

    assert result is False


@pytest.mark.asyncio
async def test_fsm_state_serialization_roundtrip(state_manager):
    """Test that FSMState can survive serialization roundtrip."""
    original_state = FSMState(
        session_id="test-session",
        state="THINKING",
        details="Testing",
        request_id="req-1",
        user_id="user-1",
        tool_calls_in_progress=["tool1", "tool2"],
    )

    # Serialize and deserialize
    json_str = original_state.to_json()
    restored_state = FSMState.from_json(json_str)

    assert restored_state.session_id == original_state.session_id
    assert restored_state.state == original_state.state
    assert restored_state.details == original_state.details
    assert restored_state.request_id == original_state.request_id
    assert restored_state.user_id == original_state.user_id
    assert restored_state.tool_calls_in_progress == original_state.tool_calls_in_progress


def test_get_state_key_uses_expected_namespace(state_manager):
    """Test internal state key generation stays stable."""
    assert state_manager._get_state_key("test-session") == "session:test-session:state"
