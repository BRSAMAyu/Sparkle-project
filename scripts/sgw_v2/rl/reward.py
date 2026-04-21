"""Reward computation: multi-dimensional reward signal for SGW RL.

Computes r_t from before/after metric deltas with weighted dimensions,
one-vote veto, diversity bonus, and tanh normalization.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .spec import (
    RewardWeights, DEFAULT_REWARD_WEIGHTS, REWARD_SCALE,
    IterationOutcome,
)


@dataclass
class RewardComponents:
    """Individual dimension rewards for transparency."""
    soft_violation: float = 0.0    # Δ(-soft_violation_rate)
    authenticity: float = 0.0      # Δ(authenticity_mean)
    hard_violation: float = 0.0    # -hard_violations_delta * 10
    session: float = 0.0           # Δ(session_completion_rate)
    diversity: float = 0.0         # diversity bonus

    @property
    def total_raw(self) -> float:
        return (
            self.soft_violation
            + self.authenticity
            + self.hard_violation
            + self.session
            + self.diversity
        )


def compute_reward(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    weights: RewardWeights = DEFAULT_REWARD_WEIGHTS,
    diversity_score: float = 0.0,
    auth_z_statistic: float | None = None,
    alpha: float = 1.96,
) -> tuple[float, float, RewardComponents, bool, str | None]:
    """Compute reward signal from before/after metrics.

    Returns:
        (raw_reward, normalized_reward, components, veto_applied, veto_reason)
    """
    # Delta calculations
    delta_soft = -(after.get("soft_violation_rate", 0) - before.get("soft_violation_rate", 0))
    delta_auth = after.get("authenticity_mean", 0) - before.get("authenticity_mean", 0)
    delta_hard = after.get("hard_violations", 0) - before.get("hard_violations", 0)
    delta_session = after.get("session_completion_rate", 0) - before.get("session_completion_rate", 0)

    # Weighted components
    components = RewardComponents(
        soft_violation=weights.w_soft * delta_soft,
        authenticity=weights.w_auth * delta_auth,
        hard_violation=weights.w_hard * (-delta_hard * 10),
        session=weights.w_session * delta_session,
        diversity=weights.w_diversity * diversity_score,
    )

    # One-vote veto checks
    if delta_hard > 0:
        return (-1.0, math.tanh(-1.0 / REWARD_SCALE), components, True, "hard_violation_increase")

    if auth_z_statistic is not None and auth_z_statistic > alpha:
        return (-0.8, math.tanh(-0.8 / REWARD_SCALE), components, True, "authenticity_sig_regression")

    raw = components.total_raw
    normalized = math.tanh(raw / REWARD_SCALE)
    return (raw, normalized, components, False, None)
