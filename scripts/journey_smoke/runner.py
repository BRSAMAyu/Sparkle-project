from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class RecordingPipeline:
    def __init__(self, redis_client: "RecordingRedis") -> None:
        self._redis = redis_client
        self._ops: list[tuple[str, tuple[Any, ...]]] = []

    def lpush(self, key: str, value: str) -> "RecordingPipeline":
        self._ops.append(("lpush", (key, value)))
        return self

    def ltrim(self, key: str, start: int, end: int) -> "RecordingPipeline":
        self._ops.append(("ltrim", (key, start, end)))
        return self

    def lrange(self, key: str, start: int, end: int) -> "RecordingPipeline":
        self._ops.append(("lrange", (key, start, end)))
        return self

    def expire(self, key: str, ttl_seconds: int) -> "RecordingPipeline":
        self._ops.append(("expire", (key, ttl_seconds)))
        return self

    async def execute(self) -> list[Any]:
        results: list[Any] = []
        for name, args in self._ops:
            method = getattr(self._redis, f"_{name}")
            results.append(method(*args))
        return results


class RecordingRedis:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}
        self._sets: dict[str, set[str]] = {}
        self.published: list[dict[str, Any]] = []

    def pipeline(self) -> RecordingPipeline:
        return RecordingPipeline(self)

    async def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        del ttl_seconds
        self._values[key] = value
        return True

    async def set(self, key: str, value: Any, ex: int | None = None, **_kwargs: Any) -> bool:
        del ex
        if isinstance(value, str):
            self._values[key] = value
        else:
            self._values[key] = json.dumps(value, ensure_ascii=True, default=str)
        return True

    async def get(self, key: str) -> str | None:
        return self._values.get(key)

    async def delete(self, key: str) -> int:
        removed = 0
        if key in self._values:
            del self._values[key]
            removed += 1
        if key in self._lists:
            del self._lists[key]
            removed += 1
        if key in self._sets:
            del self._sets[key]
            removed += 1
        return removed

    async def sadd(self, key: str, value: str) -> int:
        self._sets.setdefault(key, set()).add(value)
        return 1

    async def srem(self, key: str, value: str) -> int:
        if key in self._sets:
            self._sets[key].discard(value)
        return 1

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        del key, ttl_seconds
        return True

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self._lists.get(key, [])
        normalized_end = None if end < 0 else end + 1
        return values[start:normalized_end]

    async def ltrim(self, key: str, start: int, end: int) -> bool:
        self._ltrim(key, start, end)
        return True

    async def publish(self, channel: str, message: str) -> int:
        payload: Any = message
        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = message
        self.published.append({"channel": channel, "message": payload})
        return 1

    def _lpush(self, key: str, value: str) -> int:
        self._lists.setdefault(key, [])
        self._lists[key].insert(0, value)
        return len(self._lists[key])

    def _ltrim(self, key: str, start: int, end: int) -> bool:
        values = self._lists.get(key, [])
        normalized_end = None if end < 0 else end + 1
        self._lists[key] = values[start:normalized_end]
        return True

    def _lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self._lists.get(key, [])
        normalized_end = None if end < 0 else end + 1
        return values[start:normalized_end]

    def _expire(self, key: str, ttl_seconds: int) -> bool:
        del key, ttl_seconds
        return True


@dataclass
class EventRecorder:
    events: list[tuple[str, dict[str, Any]]]

    def __init__(self) -> None:
        self.events = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> str:
        self.events.append((event_type, dict(payload)))
        return f"{len(self.events)}-0"

    def pop(self, event_type: str) -> dict[str, Any]:
        for index, (recorded_type, payload) in enumerate(self.events):
            if recorded_type == event_type:
                self.events.pop(index)
                return payload
        raise AssertionError(f"Missing event `{event_type}`")


def assert_system_update(payload: dict[str, Any], *, expected_type: str) -> dict[str, Any]:
    required = {"type", "category", "title", "description", "priority", "metadata", "created_at"}
    missing = required.difference(payload)
    if missing:
        raise AssertionError(f"System update missing keys: {sorted(missing)}")
    if payload["type"] != expected_type:
        raise AssertionError(f"Expected system update `{expected_type}`, got `{payload['type']}`")
    if not isinstance(payload["metadata"], dict):
        raise AssertionError("System update metadata must be a dict")
    if not isinstance(payload["created_at"], int):
        raise AssertionError("System update created_at must be an int timestamp")
    return payload


def assert_pubsub_message(
    redis_client: RecordingRedis,
    *,
    channel: str,
    expected_type: str,
) -> dict[str, Any]:
    for item in redis_client.published:
        if item["channel"] != channel:
            continue
        message = item["message"]
        if isinstance(message, dict) and message.get("type") == expected_type:
            return message
    raise AssertionError(f"Missing pubsub payload `{expected_type}` on channel `{channel}`")


def fail_for_hop(hop_name: str, detail: str) -> AssertionError:
    return AssertionError(f"[{hop_name}] {detail}")
