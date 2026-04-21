from __future__ import annotations

import pytest

from app.learning.persistent_bayesian_learner import PersistentBayesianLearner


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
async def test_multidim_learner_accepts_dict_source_state() -> None:
    redis = FakeRedis()
    learner = PersistentBayesianLearner(redis, user_id="u1")

    await learner.update_for_state({"tool_category": "plan", "sufficiency_level": "high"}, "direct", True)
    await learner.drain_pending_saves()

    probability = await learner.get_probability_for_state(
        {"sufficiency_level": "high", "tool_category": "plan"},
        "direct",
    )
    assert probability > 0.5


@pytest.mark.asyncio
async def test_multidim_learner_ranks_targets_by_probability_and_support() -> None:
    redis = FakeRedis()
    learner = PersistentBayesianLearner(redis, user_id="u2")

    for _ in range(4):
        await learner.update_for_state({"tool_category": "plan"}, "direct", True)
    for _ in range(2):
        await learner.update_for_state({"tool_category": "plan"}, "langgraph", False)

    ranked = await learner.rank_targets({"tool_category": "plan"}, ["langgraph", "direct", "hybrid"])

    assert ranked[0]["target"] == "direct"
    assert ranked[0]["observations"] >= 4
