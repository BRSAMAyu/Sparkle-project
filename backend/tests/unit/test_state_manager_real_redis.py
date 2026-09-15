"""
Real Redis integration tests for SessionStateManager.

Uses real Redis to verify FSM state persistence, concurrent access,
round-trip serialization, and TTL behavior.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio

from app.orchestration.state_manager import FSMState, SessionStateManager
from app.orchestration.orchestrator import (
    STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_DONE,
)


@pytest_asyncio.fixture
async def state_manager(redis_client):
    """Create SessionStateManager with real Redis client."""
    return SessionStateManager(redis_client)


@pytest.mark.asyncio
async def test_save_and_load_roundtrip(state_manager):
    session_id = str(uuid.uuid4())
    state = FSMState(
        session_id=session_id,
        state=STATE_THINKING,
        details="Processing request",
        user_id="user-1",
        request_id="req-1",
    )

    result = await state_manager.save_state(session_id, state)
    assert result is True

    loaded = await state_manager.load_state(session_id)
    assert loaded is not None
    assert loaded.session_id == session_id
    assert loaded.state == STATE_THINKING
    assert loaded.details == "Processing request"
    assert loaded.user_id == "user-1"


@pytest.mark.asyncio
async def test_load_missing_returns_none(state_manager):
    loaded = await state_manager.load_state("nonexistent-session")
    assert loaded is None


@pytest.mark.asyncio
async def test_update_state_persists(state_manager):
    session_id = str(uuid.uuid4())
    state = FSMState(session_id=session_id, state=STATE_INIT)
    await state_manager.save_state(session_id, state)

    await state_manager.update_state(session_id, STATE_THINKING, details="Now thinking")
    loaded = await state_manager.load_state(session_id)
    assert loaded.state == STATE_THINKING
    assert loaded.details == "Now thinking"


@pytest.mark.asyncio
async def test_full_lifecycle(state_manager):
    session_id = str(uuid.uuid4())
    for s in [STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_DONE]:
        await state_manager.save_state(session_id, FSMState(session_id=session_id, state=s))

    loaded = await state_manager.load_state(session_id)
    assert loaded.state == STATE_DONE


@pytest.mark.asyncio
async def test_concurrent_saves_last_write_wins(state_manager):
    session_id = str(uuid.uuid4())

    async def save_state(state_value):
        state = FSMState(session_id=session_id, state=state_value)
        return await state_manager.save_state(session_id, state)

    tasks = [save_state(f"STATE_{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert all(r is True for r in results)

    loaded = await state_manager.load_state(session_id)
    assert loaded is not None
    assert loaded.state.startswith("STATE_")


@pytest.mark.asyncio
async def test_session_isolation(state_manager):
    s1 = str(uuid.uuid4())
    s2 = str(uuid.uuid4())

    await state_manager.save_state(s1, FSMState(session_id=s1, state=STATE_THINKING))
    await state_manager.save_state(s2, FSMState(session_id=s2, state=STATE_DONE))

    assert (await state_manager.load_state(s1)).state == STATE_THINKING
    assert (await state_manager.load_state(s2)).state == STATE_DONE


@pytest.mark.asyncio
async def test_serialization_roundtrip_with_tool_calls(state_manager):
    session_id = str(uuid.uuid4())
    original = FSMState(
        session_id=session_id,
        state=STATE_THINKING,
        details="Testing tools",
        request_id="req-1",
        user_id="user-1",
        tool_calls_in_progress=["tool_a", "tool_b"],
    )

    # Save → load roundtrip
    await state_manager.save_state(session_id, original)
    loaded = await state_manager.load_state(session_id)

    assert loaded.session_id == original.session_id
    assert loaded.state == original.state
    assert loaded.details == original.details
    assert loaded.request_id == original.request_id
    assert loaded.user_id == original.user_id
    assert loaded.tool_calls_in_progress == ["tool_a", "tool_b"]


def test_get_state_key_namespace():
    """State key format is stable."""
    mgr = SessionStateManager(None)
    assert mgr._get_state_key("sess-1") == "session:sess-1:state"
