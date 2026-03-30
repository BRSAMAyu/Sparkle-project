from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.state_manager import FSMState, SessionStateManager


@pytest.fixture
def redis_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def state_manager(redis_client: MagicMock) -> SessionStateManager:
    return SessionStateManager(redis_client)


@pytest.mark.asyncio
async def test_save_state_uses_stable_redis_key_and_ttl(state_manager: SessionStateManager, redis_client: MagicMock):
    redis_client.setex = AsyncMock()
    state = FSMState(session_id="session-1", state="THINKING", details="processing")

    result = await state_manager.save_state("session-1", state)

    assert result is True
    redis_client.setex.assert_awaited_once()
    key, ttl, payload = redis_client.setex.call_args.args
    assert key == "session:session-1:state"
    assert ttl == state_manager.ttl
    assert '"session_id": "session-1"' in payload
    assert '"state": "THINKING"' in payload


@pytest.mark.asyncio
async def test_load_state_contract_round_trips_fsm_shape(state_manager: SessionStateManager, redis_client: MagicMock):
    redis_client.get = AsyncMock(
        return_value='{"session_id":"session-2","state":"DONE","details":"ok","tool_calls_in_progress":[]}'
    )

    state = await state_manager.load_state("session-2")

    assert state is not None
    assert state.session_id == "session-2"
    assert state.state == "DONE"
    assert state.details == "ok"


@pytest.mark.asyncio
async def test_acquire_lock_allows_same_request_to_reenter(state_manager: SessionStateManager, redis_client: MagicMock):
    redis_client.set = AsyncMock(return_value=None)
    redis_client.get = AsyncMock(return_value="request-123")

    acquired = await state_manager.acquire_lock("session-3", "request-123")

    assert acquired is True
    redis_client.set.assert_awaited_once_with(
        "session:session-3:lock",
        "request-123",
        nx=True,
        ex=state_manager.lock_ttl,
    )


@pytest.mark.asyncio
async def test_release_lock_uses_atomic_eval_contract(state_manager: SessionStateManager, redis_client: MagicMock):
    redis_client.eval = AsyncMock(return_value=1)

    released = await state_manager.release_lock("session-4", "request-456")

    assert released is True
    redis_client.eval.assert_awaited_once()
    lua_script, key_count, lock_key, request_id = redis_client.eval.call_args.args
    assert 'redis.call("get", KEYS[1])' in lua_script
    assert key_count == 1
    assert lock_key == "session:session-4:lock"
    assert request_id == "request-456"
