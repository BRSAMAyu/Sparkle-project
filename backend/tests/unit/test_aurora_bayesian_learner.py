from __future__ import annotations

import json

import pytest

from app.aurora.bayesian import (
    AURORA_TARGET_VISIBLE_INTERVENTION,
    AuroraBayesianLearner,
)
from app.aurora.runtime_v1.correction_feedback import CorrectionFeedbackProcessor
from app.aurora.runtime_v1.self_model import DEFAULT_STRATEGY_CONFIDENCE, SparkleSelfModelService


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def set(self, key: str, value: str) -> bool:
        self.kv[key] = value
        return True

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.kv[key] = value
        self.ttl[key] = ttl

    async def expire(self, key: str, ttl: int) -> None:
        self.ttl[key] = ttl


@pytest.mark.asyncio
async def test_aurora_bayesian_learner_sequential_updates_change_posterior() -> None:
    redis = _FakeRedis()
    learner = AuroraBayesianLearner(redis)

    initial = await learner.get_posterior(user_id="user-seq")
    assert initial.alpha == pytest.approx(1.0)
    assert initial.beta == pytest.approx(1.0)
    assert initial.mean == pytest.approx(0.5)

    await learner.record_outcome(user_id="user-seq", action="emit_message", outcome="task_completed")
    after_success = await learner.get_posterior(user_id="user-seq")
    assert after_success.alpha == pytest.approx(2.0)
    assert after_success.beta == pytest.approx(1.0)
    assert after_success.mean > initial.mean

    await learner.record_outcome(user_id="user-seq", action="emit_message", outcome="user_corrected")
    after_correction = await learner.get_posterior(user_id="user-seq")
    assert after_correction.alpha == pytest.approx(2.0)
    assert after_correction.beta == pytest.approx(2.0)
    assert after_correction.mean < after_success.mean
    assert after_correction.observations == 2


@pytest.mark.asyncio
async def test_aurora_bayesian_posterior_survives_new_service_instance() -> None:
    redis = _FakeRedis()
    first = AuroraBayesianLearner(redis)

    await first.record_outcome(user_id="user-persist", action="soft_return_topic", outcome="task_completed")
    await first.record_outcome(user_id="user-persist", action="soft_return_topic", outcome="task_completed")

    second = AuroraBayesianLearner(redis)
    posterior = await second.get_posterior(user_id="user-persist")

    assert posterior.target == AURORA_TARGET_VISIBLE_INTERVENTION
    assert posterior.alpha == pytest.approx(3.0)
    assert posterior.beta == pytest.approx(1.0)
    assert posterior.observations == 2


@pytest.mark.asyncio
async def test_self_model_uses_bayesian_uncertainty_to_calibrate_strategy_confidence() -> None:
    redis = _FakeRedis()
    learner = AuroraBayesianLearner(redis)
    await learner.record_outcome(user_id="user-policy", action="emit_message", outcome="task_completed")

    summary = await SparkleSelfModelService(redis).get_readout_summary(user_id="user-policy")
    bayesian_policy = summary["bayesian_policy"]

    assert bayesian_policy["posterior_mean"] == pytest.approx(0.6667)
    assert bayesian_policy["posterior_uncertainty"] > 0.5
    assert summary["strategy_confidence"] != pytest.approx(DEFAULT_STRATEGY_CONFIDENCE)
    assert summary["strategy_confidence"] == pytest.approx(bayesian_policy["applied_strategy_confidence"])
    assert summary["strategy_confidence"] < bayesian_policy["posterior_mean"]


@pytest.mark.asyncio
async def test_correction_feedback_updates_aurora_bayesian_failure_signal() -> None:
    redis = _FakeRedis()
    processor = CorrectionFeedbackProcessor(redis)

    await processor.process(
        user_id="user-correction-bayes",
        semantic_value="freeform_correction",
        is_freeform=True,
        freeform_text="Aurora guessed the blocker wrong.",
        telemetry_id="telemetry-freeform",
    )

    stored = json.loads(redis.kv["learner:user-correction-bayes"])
    stats = stored["aurora_runtime_policy->visible_intervention"]
    assert stats["alpha"] == pytest.approx(1.0)
    assert stats["beta"] == pytest.approx(2.0)
