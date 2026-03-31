from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from app.orchestration.state_manager import (
    FSMState,
    STATE_DONE,
    STATE_FAILED,
    STATE_GENERATING,
    STATE_INIT,
    STATE_THINKING,
    STATE_TOOL_CALLING,
    SessionStateManager,
)


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def setex(self, key: str, ttl: int, value: str):
        self.values[key] = value
        self.ttls[key] = ttl
        return True

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def eval(self, script: str, numkeys: int, key: str, *args):
        if "del" in script:
            request_id = args[0]
            if self.values.get(key) == request_id:
                self.values.pop(key, None)
                self.ttls.pop(key, None)
                return 1
            return 0

        request_id = args[0]
        ttl = int(args[1])
        if self.values.get(key) == request_id:
            self.ttls[key] = ttl
            return 1
        return 0

    async def delete(self, *keys: str):
        deleted = 0
        for key in keys:
            if key in self.values:
                deleted += 1
                self.values.pop(key, None)
                self.ttls.pop(key, None)
        return deleted

    async def keys(self, pattern: str):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.values if key.startswith(prefix)]

    async def ttl(self, key: str):
        return self.ttls.get(key, -1)


def test_fsm_state_roundtrip_json():
    state = FSMState(
        session_id="session-1",
        state=STATE_TOOL_CALLING,
        details="calling tool",
        request_id="req-1",
        user_id="user-1",
        last_processed_message="hello",
        accumulated_response="partial answer",
        tool_calls_in_progress=[{"name": "search"}],
    )

    restored = FSMState.from_json(state.to_json())

    assert asdict(restored) == asdict(state)


@pytest.mark.asyncio
async def test_session_state_manager_save_load():
    redis = FakeRedis()
    manager = SessionStateManager(redis, ttl=120)
    state = FSMState(session_id="session-1", state=STATE_THINKING, details="thinking hard")

    assert await manager.save_state(state.session_id, state) is True

    restored = await manager.load_state(state.session_id)
    assert restored is not None
    assert asdict(restored) == asdict(state)
    assert redis.ttls[manager._get_state_key(state.session_id)] == 120


@pytest.mark.asyncio
async def test_fsm_legal_transitions():
    redis = FakeRedis()
    manager = SessionStateManager(redis)
    session_id = "session-legal"

    assert await manager.update_state(session_id, STATE_INIT, details="start") is True
    assert (await manager.load_state(session_id)).state == STATE_INIT

    for next_state in [STATE_THINKING, STATE_GENERATING, STATE_TOOL_CALLING, STATE_DONE]:
        assert await manager.update_state(session_id, next_state, details=f"to {next_state}") is True
        current = await manager.load_state(session_id)
        assert current is not None
        assert current.state == next_state
        assert current.details == f"to {next_state}"

    for origin_state in [STATE_INIT, STATE_THINKING, STATE_GENERATING, STATE_TOOL_CALLING, STATE_DONE]:
        assert await manager.update_state(session_id, origin_state, details=f"origin {origin_state}") is True
        assert await manager.update_state(session_id, STATE_FAILED, details="boom") is True
        failed = await manager.load_state(session_id)
        assert failed is not None
        assert failed.state == STATE_FAILED
        assert failed.details == "boom"


@pytest.mark.asyncio
async def test_session_state_manager_lock_acquire_release():
    redis = FakeRedis()
    manager = SessionStateManager(redis)

    assert await manager.acquire_lock("session-1", "req-1") is True
    assert await manager.acquire_lock("session-1", "req-1") is True
    assert await manager.acquire_lock("session-1", "req-2") is False
    assert await manager.release_lock("session-1", "req-2") is False
    assert await manager.release_lock("session-1", "req-1") is True
    assert await manager.acquire_lock("session-1", "req-2") is True


@pytest.mark.asyncio
async def test_session_state_manager_duplicate_request_detection():
    redis = FakeRedis()
    manager = SessionStateManager(redis)
    response = {
        "message": "hello",
        "metadata": {"route": "orchestrator"},
    }

    assert await manager.is_duplicate_request("session-1", "req-1") is False
    assert await manager.cache_response("session-1", "req-1", response, ttl=90) is True
    assert await manager.is_duplicate_request("session-1", "req-1") is True
    assert await manager.get_cached_response("session-1", "req-1") == response
    stored_json = redis.values[manager._get_response_key("session-1", "req-1")]
    assert json.loads(stored_json) == response
