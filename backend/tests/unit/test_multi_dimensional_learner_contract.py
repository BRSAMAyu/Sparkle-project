from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.core.cache import cache_service
from app.core.celery_tasks import save_learning_state
from app.learning.multi_dimensional_learner import (
    MULTI_DIMENSIONAL_LEARNER_TTL_SECONDS,
    MultiDimensionalLearner,
    build_multi_dimensional_learner_key,
)


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.data.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.data[key] = value
        self.ttls[key] = ttl


@pytest.mark.asyncio
async def test_multi_dimensional_save_state_round_trips_explicit_payload():
    redis = FakeRedis()
    learner = MultiDimensionalLearner(redis, user_id="u1")
    payload = {
        "success": {"stats": {"source->target": {"alpha": 4, "beta": 1}}},
        "latency": {"stats": {}},
        "cost": {"stats": {}},
        "user_satisfaction": {"stats": {}},
        "config": {"weights": {"success": 0.4, "latency": 0.3, "cost": 0.1, "user_satisfaction": 0.2}},
    }

    await learner.save_state(payload)

    reloaded = MultiDimensionalLearner(redis, user_id="u1")
    breakdown = await reloaded.get_dimension_breakdown("source", "target")

    assert breakdown["success"]["alpha"] == 4
    assert breakdown["success"]["beta"] == 1
    assert redis.ttls[build_multi_dimensional_learner_key("u1")] == MULTI_DIMENSIONAL_LEARNER_TTL_SECONDS


def test_save_learning_state_task_persists_payload_without_missing_save_state_api():
    redis = FakeRedis()
    payload = {
        "success": {"stats": {"planner->tool": {"alpha": 2, "beta": 1}}},
        "latency": {"stats": {}},
        "cost": {"stats": {}},
        "user_satisfaction": {"stats": {}},
        "config": {"weights": {"success": 0.4, "latency": 0.3, "cost": 0.1, "user_satisfaction": 0.2}},
    }

    with patch.object(cache_service, "redis", redis):
        result = save_learning_state.run("u2", payload)

    saved = json.loads(redis.data[build_multi_dimensional_learner_key("u2")])
    assert result == {"status": "success", "user_id": "u2"}
    assert saved["success"]["stats"]["planner->tool"]["alpha"] == 2.0
