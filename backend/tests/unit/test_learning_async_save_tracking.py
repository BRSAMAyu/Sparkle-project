from unittest.mock import AsyncMock

import pytest

from app.learning.multi_dimensional_learner import MultiDimensionalLearner
from app.learning.persistent_bayesian_learner import PersistentBayesianLearner


@pytest.mark.asyncio
async def test_persistent_learner_drains_pending_save_tasks():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()

    learner = PersistentBayesianLearner(redis, user_id="u1")
    await learner.update("source", "target", True)
    await learner.drain_pending_saves()

    assert len(learner._pending_saves) == 0
    redis.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_multi_dimensional_learner_drains_pending_save_tasks():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()

    learner = MultiDimensionalLearner(redis, user_id="u2")
    await learner.update("source", "target", {"success": True, "latency": 0.2})
    await learner.drain_pending_saves()

    assert len(learner._pending_saves) == 0
    redis.setex.assert_awaited_once()
