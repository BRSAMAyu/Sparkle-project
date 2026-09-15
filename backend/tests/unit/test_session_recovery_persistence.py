from __future__ import annotations

import pytest

from app.aurora.runtime_v1.models import AuroraCoreSessionSnapshot, DurableSessionStateSnapshot  # noqa: F401
from app.orchestration.state_manager import STATE_DONE, STATE_GENERATING, SessionStateManager


class _RedisDict:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str) -> bool:
        self.data[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self.data:
                count += 1
                self.data.pop(key, None)
        return count


@pytest.mark.asyncio
async def test_session_state_manager_loads_durable_snapshot_on_redis_miss(db_session) -> None:
    redis = _RedisDict()
    manager = SessionStateManager(redis, db_session=db_session)

    await manager.update_state(
        "session-1",
        STATE_GENERATING,
        "streaming answer",
        request_id="request-1",
        user_id="user-1",
        accumulated_response="partial",
    )
    redis.data.clear()

    recovered = await manager.load_state("session-1")

    assert recovered is not None
    assert recovered.state == STATE_GENERATING
    assert recovered.request_id == "request-1"
    assert recovered.accumulated_response == "partial"
    assert redis.data["session:session-1:state"]


@pytest.mark.asyncio
async def test_session_state_manager_does_not_restore_done_state(db_session) -> None:
    redis = _RedisDict()
    manager = SessionStateManager(redis, db_session=db_session)

    await manager.update_state("session-2", STATE_DONE, "completed", request_id="request-2", user_id="user-1")
    redis.data.clear()

    assert await manager.load_state("session-2") is None
