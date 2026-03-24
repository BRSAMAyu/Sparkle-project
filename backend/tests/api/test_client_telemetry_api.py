from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_superuser, get_current_user
from app.api.v1.client_telemetry import router as client_telemetry_router
from app.core.cache import cache_service


class _FakeRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, object]] = {}
        self._lists: dict[str, list[str]] = {}

    async def hincrby(self, key: str, field: str, value: int) -> None:
        bucket = self._hashes.setdefault(key, {})
        bucket[field] = int(bucket.get(field, 0) or 0) + value

    async def hset(self, key: str, mapping: dict[str, object]) -> None:
        bucket = self._hashes.setdefault(key, {})
        bucket.update(mapping)

    async def expire(self, key: str, seconds: int) -> None:
        del seconds
        _ = key

    async def lpush(self, key: str, value: str) -> None:
        bucket = self._lists.setdefault(key, [])
        bucket.insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        bucket = self._lists.setdefault(key, [])
        self._lists[key] = bucket[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        bucket = self._lists.get(key, [])
        if end == -1:
            return bucket[start:]
        return bucket[start : end + 1]

    async def hgetall(self, key: str) -> dict[str, object]:
        return dict(self._hashes.get(key, {}))

    async def scan_iter(self, pattern: str):
        prefix = pattern.rstrip("*")
        for key in list(self._hashes):
            if key.startswith(prefix):
                yield key


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(client_telemetry_router)
    return app


def test_client_telemetry_batch_ingest_returns_accepted_events():
    app = _build_app()
    fake_redis = _FakeRedis()
    original_redis = cache_service.redis
    cache_service.redis = fake_redis

    async def _override_user():
        return SimpleNamespace(id=uuid4())

    app.dependency_overrides[get_current_user] = _override_user

    try:
        with TestClient(app) as client:
            response = client.post(
                "/client-telemetry/events/batch",
                json={
                    "events": [
                        {
                            "event_type": "api_request",
                            "category": "network",
                            "route": "/chat/stream",
                            "status": "ok",
                            "severity": "info",
                            "duration_ms": 320,
                            "metadata": {"platform": "ios"},
                        },
                        {
                            "event_type": "crash",
                            "category": "stability",
                            "status": "error",
                            "severity": "critical",
                            "metadata": {"platform": "ios"},
                        },
                    ]
                },
            )
    finally:
        cache_service.redis = original_redis

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["storage"] == "redis"
    assert body["accepted_count"] == 2
    assert [item["event_type"] for item in body["events"]] == ["api_request", "crash"]


def test_client_telemetry_summary_includes_daily_totals():
    app = _build_app()
    fake_redis = _FakeRedis()
    original_redis = cache_service.redis
    cache_service.redis = fake_redis

    async def _override_user():
        return SimpleNamespace(id=uuid4())

    async def _override_superuser():
        return SimpleNamespace(id=uuid4(), is_superuser=True)

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_current_active_superuser] = _override_superuser

    try:
        with TestClient(app) as client:
            ingest = client.post(
                "/client-telemetry/events/batch",
                json={
                    "events": [
                        {
                            "event_type": "api_request",
                            "category": "network",
                            "route": "/predictive/analytics",
                            "status": "ok",
                            "severity": "info",
                            "duration_ms": 180,
                            "metadata": {"platform": "ios"},
                        },
                        {
                            "event_type": "api_request",
                            "category": "network",
                            "route": "/predictive/analytics",
                            "status": "error",
                            "severity": "warning",
                            "duration_ms": 410,
                            "metadata": {"platform": "android"},
                        },
                    ]
                },
            )
            assert ingest.status_code == 200
            response = client.get("/client-telemetry/summary?days=7")
    finally:
        cache_service.redis = original_redis

    assert response.status_code == 200
    body = response.json()
    assert body["days"] == 7
    assert body["overall"]["count"] == 2
    assert body["overall"]["error_count"] == 1
    assert body["daily_totals"]
    assert body["by_event_type"]
    assert any(item["event_type"] == "all" for item in body["by_event_type"])
    assert any(item["event_type"] == "api_request" for item in body["by_event_type"])
    assert body["recent_events"]
    first_recent = body["recent_events"][0]
    assert first_recent["event_type"] == "api_request"
    assert first_recent["route"] == "/predictive/analytics"
    assert json.loads(json.dumps(body))
