"""Aurora Stage 23 Bayesian learner.

The generic persistent learner stores Beta/Bernoulli route statistics. This
wrapper gives Aurora a small domain vocabulary: visible interventions versus
holding back, with outcomes coming from runtime telemetry and correction chips.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.learning.persistent_bayesian_learner import PersistentBayesianLearner

AURORA_POLICY_SOURCE_STATE = "aurora_runtime_policy"
AURORA_TARGET_VISIBLE_INTERVENTION = "visible_intervention"
AURORA_TARGET_HOLD = "hold"

# Warm-started prior: assumes moderate initial success (mean ≈ 0.67)
# This accelerates cold-start by making the posterior respond faster to early observations.
_COLD_START_ALPHA = 2.0
_COLD_START_BETA = 1.0

_VISIBLE_ACTIONS = {
    "emit_message",
    "soft_return_topic",
    "schedule_wake",
    "ask_user",
    "start_core_session",
    "continue_session",
}
_HOLD_ACTIONS = {"", "wait", "drop_thread", "none"}
_SUCCESS_OUTCOMES = {"task_completed", "completed", "success", "confirmed", "accepted"}
_FAILURE_OUTCOMES = {
    "timeout",
    "timed_out",
    "skipped",
    "skip",
    "user_corrected",
    "corrected",
    "correction",
    "disconfirmed",
    "freeform_correction",
}


@dataclass(frozen=True)
class AuroraPosterior:
    """Beta posterior for one Aurora policy target."""

    target: str
    alpha: float
    beta: float

    @property
    def observations(self) -> int:
        return max(0, int(round((self.alpha + self.beta) - 2)))

    @property
    def mean(self) -> float:
        denominator = self.alpha + self.beta
        return round(self.alpha / denominator, 4) if denominator > 0 else 0.5

    @property
    def variance(self) -> float:
        denominator = (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        return round((self.alpha * self.beta) / denominator, 6) if denominator > 0 else 0.0

    @property
    def uncertainty(self) -> float:
        # Beta(1, 1) has variance 1/12. Normalize against that uniform prior.
        return round(min(1.0, self.variance / (1.0 / 12.0)), 4)


class AuroraBayesianLearner:
    """Persisted Beta/Bernoulli learner for Aurora intervention calibration."""

    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client

    async def record_outcome(
        self,
        *,
        user_id: str,
        action: str,
        outcome: str,
        source_state: str = AURORA_POLICY_SOURCE_STATE,
    ) -> AuroraPosterior | None:
        """Update the posterior for an Aurora action after an observed outcome."""

        success = self._success_from_outcome(outcome)
        if success is None:
            return None

        target = self.target_for_action(action)
        learner = PersistentBayesianLearner(self.redis, user_id=user_id)
        await learner.update(source_state, target, success)
        await learner.drain_pending_saves()
        return await self.get_posterior(user_id=user_id, target=target, source_state=source_state)

    async def record_correction(
        self,
        *,
        user_id: str,
        is_disconfirming: bool,
        is_freeform: bool,
        source_state: str = AURORA_POLICY_SOURCE_STATE,
    ) -> AuroraPosterior:
        """Treat user corrections as feedback on the latest visible intervention."""

        success = not (is_disconfirming or is_freeform)
        learner = PersistentBayesianLearner(self.redis, user_id=user_id)
        await learner.update(source_state, AURORA_TARGET_VISIBLE_INTERVENTION, success)
        await learner.drain_pending_saves()
        posterior = await self.get_posterior(
            user_id=user_id,
            target=AURORA_TARGET_VISIBLE_INTERVENTION,
            source_state=source_state,
        )
        return posterior

    async def get_posterior(
        self,
        *,
        user_id: str,
        target: str = AURORA_TARGET_VISIBLE_INTERVENTION,
        source_state: str = AURORA_POLICY_SOURCE_STATE,
    ) -> AuroraPosterior:
        learner = PersistentBayesianLearner(self.redis, user_id=user_id)
        ranked = await learner.rank_targets(source_state, [target])
        if not ranked:
            return AuroraPosterior(target=target, alpha=_COLD_START_ALPHA, beta=_COLD_START_BETA)
        stats = ranked[0]
        return AuroraPosterior(
            target=target,
            alpha=float(stats["alpha"]),
            beta=float(stats["beta"]),
        )

    async def policy_calibration(self, *, user_id: str) -> dict[str, Any]:
        """Return uncertainty-adjusted policy confidence for downstream wake policy."""

        posterior = await self.get_posterior(user_id=user_id)
        if posterior.observations <= 0:
            warm_mean = _COLD_START_ALPHA / (_COLD_START_ALPHA + _COLD_START_BETA)
            return {
                "target": posterior.target,
                "observations": 0,
                "posterior_mean": posterior.mean,
                "posterior_uncertainty": posterior.uncertainty,
                "calibrated_confidence": round(warm_mean * 0.85, 4),
            }

        calibrated = posterior.mean * (1.0 - 0.35 * posterior.uncertainty)
        return {
            "target": posterior.target,
            "observations": posterior.observations,
            "posterior_mean": posterior.mean,
            "posterior_variance": posterior.variance,
            "posterior_uncertainty": posterior.uncertainty,
            "calibrated_confidence": round(max(0.0, min(1.0, calibrated)), 4),
        }

    @staticmethod
    def target_for_action(action: str) -> str:
        normalized = str(action or "").strip().lower()
        if normalized in _HOLD_ACTIONS:
            return AURORA_TARGET_HOLD
        if normalized in _VISIBLE_ACTIONS:
            return AURORA_TARGET_VISIBLE_INTERVENTION
        return AURORA_TARGET_VISIBLE_INTERVENTION

    @staticmethod
    def _success_from_outcome(outcome: str) -> bool | None:
        normalized = str(outcome or "").strip().lower()
        if normalized in _SUCCESS_OUTCOMES:
            return True
        if normalized in _FAILURE_OUTCOMES:
            return False
        return None
