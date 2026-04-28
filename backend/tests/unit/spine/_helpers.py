"""Shared test helpers: FakeRedis, mock factories."""

from __future__ import annotations

from unittest.mock import AsyncMock


class FakeRedis:
    """Minimal Redis fake for unit tests."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._expires: dict[str, int] = {}
        self._lists: dict[str, list[str]] = {}
        self._sets: dict[str, set[str]] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> None | bool:
        if nx and key in self._store:
            return False
        self._store[key] = value
        if ex is not None:
            self._expires[key] = ex
        if nx:
            return True
        return None

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def lpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).insert(0, value)

    async def rpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).append(value)

    async def lpop(self, key: str) -> str | None:
        data = self._lists.get(key, [])
        if data:
            return data.pop(0)
        return None

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        data = self._lists.get(key, [])
        if stop == -1:
            return data[start:]
        return data[start:stop + 1]

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        data = self._lists.get(key, [])
        self._lists[key] = data[start:stop + 1]

    async def expire(self, key: str, seconds: int) -> None:
        pass

    async def lrem(self, key: str, count: int, value: str) -> None:
        data = self._lists.get(key, [])
        try:
            data.remove(value)
        except ValueError:
            pass

    async def smembers(self, key: str) -> set[str]:
        return self._sets.get(key, set())

    async def sismember(self, key: str, member: str) -> bool:
        return member in self._sets.get(key, set())

    async def sadd(self, key: str, *members: str) -> int:
        s = self._sets.setdefault(key, set())
        before = len(s)
        for m in members:
            s.add(m)
        return len(s) - before

    async def srem(self, key: str, *members: str) -> int:
        s = self._sets.get(key, set())
        before = len(s)
        for m in members:
            s.discard(m)
        return before - len(s)

    async def incrby(self, key: str, amount: int = 1) -> int:
        current = int(self._store.get(key, "0"))
        current += amount
        self._store[key] = str(current)
        return current

    async def incrbyfloat(self, key: str, amount: float = 1.0) -> float:
        current = float(self._store.get(key, "0"))
        current += amount
        self._store[key] = str(current)
        return current

    async def exists(self, key: str) -> bool:
        return key in self._store or key in self._sets or key in self._lists

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, "0")) + 1
        self._store[key] = str(val)
        return val

    async def setex(self, key: str, seconds: int, value: str) -> None:
        self._store[key] = value
        self._expires[key] = seconds

    async def ttl(self, key: str) -> int | None:
        return self._expires.get(key)

    async def hset(self, key: str, mapping: dict | None = None, **kwargs) -> int:
        raise NotImplementedError

    async def hgetall(self, key: str) -> dict:
        return {}


class FakeRedisWithHset(FakeRedis):
    """Extended fake Redis with hash operations for M2 tests."""

    def __init__(self):
        super().__init__()
        self._hashes: dict[str, dict[str, str]] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self._hashes.setdefault(key, {})[field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return self._hashes.get(key, {})


def _make_redis_mock():
    """Create an AsyncMock-based Redis mock with functional get/set/incr."""
    redis = AsyncMock()
    redis._store: dict[str, str] = {}
    redis._sets: dict[str, set] = {}

    async def _set(key, value, ex=None):
        redis._store[key] = value

    async def _get(key):
        return redis._store.get(key)

    async def _delete(key):
        redis._store.pop(key, None)

    async def _smembers(key):
        return redis._sets.get(key, set())

    async def _sadd(key, *members):
        s = redis._sets.setdefault(key, set())
        for m in members:
            s.add(m)

    async def _srem(key, *members):
        s = redis._sets.get(key, set())
        for m in members:
            s.discard(m)

    async def _incr(key):
        val = int(redis._store.get(key, "0")) + 1
        redis._store[key] = str(val)
        return val

    async def _expire(key, seconds):
        redis._store[f"__expire__{key}"] = str(seconds)

    redis.set = _set
    redis.get = _get
    redis.delete = _delete
    redis.smembers = _smembers
    redis.sadd = _sadd
    redis.srem = _srem
    redis.incr = _incr
    redis.expire = _expire
    redis.lpush = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.ltrim = AsyncMock()
    return redis


# ── Signal Factory (v2 — keyword-arg style) ───────────────────────────

import itertools as _it

_make_signal_counter = _it.count()


def _make_signal(state_key: str, priority: str = "medium", confidence: float = 0.8,
                 scope: str = "sprint", possible_effects: list[str] | None = None,
                 claim: str | None = None) -> ActionableSignal:
    from app.signals.types import ActionableSignal
    return ActionableSignal(
        signal_id=f"sig_{state_key}_{next(_make_signal_counter)}",
        source_event_ids=["evt_1"],
        source_system="test",
        state_key=state_key,
        claim=claim or f"test_{state_key}",
        confidence=confidence,
        evidence_summary="test",
        scope=scope,
        ttl_hours=24,
        possible_effects=possible_effects if possible_effects is not None else ["effect_1"],
        priority=priority,
    )


def _make_lifecycle_skill(
    *,
    skill_id: str = "skill_life_1",
    scope: str = "personal",
    effective_count: int = 5,
    sample_size: int = 6,
    applicable_when: dict | None = None,
):
    from app.signals.types import SkillEntry
    return SkillEntry(
        skill_id=skill_id,
        scope=scope,
        source_policy_key="repair_knowledge_bottleneck",
        strategy={"intervention_summary": "Show a worked example before the drill."},
        applicable_when=applicable_when or {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
        evidence={"effective_count": effective_count, "total_observed": sample_size, "avg_confidence": 0.84},
        privacy={"contains_personal_data": scope == "personal", "shareable": scope != "personal"},
        effective_count=effective_count,
        sample_size=sample_size,
    )
