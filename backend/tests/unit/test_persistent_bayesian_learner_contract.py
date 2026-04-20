from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.celery_tasks import persist_bayesian_data
from app.core.cache import cache_service
from app.learning.persistent_bayesian_learner import (
    PERSISTENT_BAYESIAN_TTL_SECONDS,
    PersistentBayesianLearner,
    build_legacy_persistent_bayesian_key,
    build_persistent_bayesian_key,
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
async def test_persistent_learner_reads_legacy_helper_key_and_promotes_to_canonical_key():
    redis = FakeRedis()
    legacy_key = build_legacy_persistent_bayesian_key("u1")
    canonical_key = build_persistent_bayesian_key("u1")
    seeded_payload = {"planner->tool": {"alpha": 3.0, "beta": 1.0}}

    await redis.setex(legacy_key, PERSISTENT_BAYESIAN_TTL_SECONDS, json.dumps(seeded_payload))
    assert canonical_key not in redis.data

    learner = PersistentBayesianLearner(redis, user_id="u1")
    stats = await learner.get_stats()

    assert stats["planner->tool"]["alpha"] == 3.0
    assert stats["planner->tool"]["beta"] == 1.0
    assert canonical_key in redis.data
    assert json.loads(redis.data[canonical_key]) == seeded_payload


def test_persist_bayesian_data_uses_canonical_key_and_stage12_ttl():
    redis = FakeRedis()

    with patch.object(cache_service, "redis", redis):
        result = persist_bayesian_data.run("u2", {"route": {"alpha": 2.0, "beta": 1.0}})

    canonical_key = build_persistent_bayesian_key("u2")
    assert result == {"status": "success", "user_id": "u2"}
    assert canonical_key in redis.data
    assert build_legacy_persistent_bayesian_key("u2") not in redis.data
    assert redis.ttls[canonical_key] == PERSISTENT_BAYESIAN_TTL_SECONDS


@pytest.mark.asyncio
async def test_persistent_learner_save_path_round_trips_on_canonical_key():
    redis = FakeRedis()
    learner = PersistentBayesianLearner(redis, user_id="u3")

    await learner.update("source", "target", True)
    await learner.drain_pending_saves()

    reloaded = PersistentBayesianLearner(redis, user_id="u3")
    assert await reloaded.get_probability("source", "target") > 0.5
