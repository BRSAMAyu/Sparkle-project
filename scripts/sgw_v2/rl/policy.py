"""Policy system: rule-based, Thompson Sampling bandit, LinUCB contextual bandit, and DPO.

Four-stage policy progression for SGW RL:
  Stage 1 (RULE): Deterministic rules from diagnostic hypotheses
  Stage 2 (BANDIT): Thompson Sampling with Beta posterior per arm
  Stage 3 (CONTEXTUAL): LinUCB with state-conditioned linear models
  Stage 4 (DPO): DPO-informed response strategy selection
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import Any

from .dpo_policy import DPOPolicy, StrategyPreference
from .spec import (
    Action, ActionSpec, ACTION_SPECS, BANDIT_ARMS,
    StateVector, PolicyStage, StrategyRecommendation, clamp_amplitude,
    check_direction_history, check_config_novelty,
    should_explore, compute_config_hash,
)


# ── Stage 1: Rule-based Policy ────────────────────────────


# Maps diagnostic hypothesis_id → parameter adjustments
_RULE_ADJUSTMENTS: dict[str, list[tuple[str, float]]] = {
    "high_soft_violation_rate": [
        ("soft_violation_threshold", +0.05),
    ],
    "low_authenticity_mean": [
        ("turn_target", +2),
        ("audit_sample_rate", +0.05),
    ],
    "high_authenticity_failure_rate": [
        ("authenticity_sample_rate", +0.10),
    ],
    "low_session_completion_rate": [
        ("claude_timeout_seconds", +15),
        ("claude_failure_backoff_seconds", +10),
    ],
    "low_turn_volume": [
        ("turn_target", +2),
    ],
}


@dataclass
class RulePolicy:
    """Stage 1: deterministic rule-based parameter adjustment."""

    def select_action(
        self,
        state: StateVector,
        hypotheses: list[str],
        current_config: dict[str, Any],
        history: list[dict[str, Any]],
        *,
        rng: random.Random | None = None,
    ) -> Action:
        """Select action based on diagnostic hypothesis rules."""
        rng = rng or random.Random()
        changes: dict[str, float] = {}

        for hypothesis_id in hypotheses:
            adjustments = _RULE_ADJUSTMENTS.get(hypothesis_id, [])
            for param_name, delta in adjustments:
                if param_name in changes:
                    continue  # Don't double-adjust
                spec = ACTION_SPECS.get(param_name)
                if spec is None:
                    continue
                current = current_config.get(param_name, spec.default)
                proposed = current + delta
                # Clamp amplitude
                proposed = clamp_amplitude(param_name, current, proposed)
                # Direction check
                direction = 1 if proposed > current else -1
                if not check_direction_history(param_name, direction, history):
                    continue
                changes[param_name] = proposed

        # Limit to 3 parameters
        if len(changes) > 3:
            changes = dict(list(changes.items())[:3])

        return Action(changes=changes, source=PolicyStage.RULE)


# ── Stage 2: Thompson Sampling Bandit ─────────────────────


@dataclass
class BanditArm:
    """A single arm in the Thompson Sampling bandit."""
    parameter: str
    direction: int    # +1 or -1
    alpha: float = 1.0  # Beta distribution alpha (successes + 1)
    beta: float = 1.0   # Beta distribution beta (failures + 1)
    pulls: int = 0
    total_reward: float = 0.0

    @property
    def arm_id(self) -> str:
        sign = "up" if self.direction > 0 else "down"
        return f"{self.parameter}_{sign}"

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

    def sample(self, rng: random.Random) -> float:
        """Sample from Beta posterior."""
        a = max(0.1, self.alpha)
        b = max(0.1, self.beta)
        x = rng.gammavariate(a, 1.0)
        y = rng.gammavariate(b, 1.0)
        return x / (x + y)

    def update(self, reward: float) -> None:
        """Update posterior with observed reward."""
        self.pulls += 1
        self.total_reward += reward
        # Map reward to success/failure for Beta update
        # reward ∈ [-1, 1], map to [0, 1]
        normalized = (reward + 1) / 2
        self.alpha += normalized
        self.beta += (1 - normalized)


class ThompsonSamplingBandit:
    """Stage 2: multi-armed bandit with Thompson Sampling.

    Arms = (parameter, direction) pairs.
    Selects by sampling from Beta posterior, picking highest sample.
    """

    def __init__(self, *, rng_seed: int | None = None):
        self.rng = random.Random(rng_seed)
        self.arms: dict[str, BanditArm] = {}
        self._init_arms()

    def _init_arms(self) -> None:
        for param, direction in BANDIT_ARMS:
            arm_id = f"{param}_{'up' if direction > 0 else 'down'}"
            self.arms[arm_id] = BanditArm(
                parameter=param,
                direction=direction,
            )

    def select_action(
        self,
        current_config: dict[str, Any],
        history: list[dict[str, Any]],
        *,
        n_params: int = 2,
        exploration: bool = False,
    ) -> Action:
        """Select action by Thompson Sampling."""
        if exploration:
            return self._random_action(current_config, n_params)

        # Sample from each arm's posterior
        samples = []
        for arm_id, arm in self.arms.items():
            sample = arm.sample(self.rng)
            samples.append((sample, arm))

        # Sort by sample value descending
        samples.sort(key=lambda x: x[0], reverse=True)

        # Pick top arms that pass constraints
        changes: dict[str, float] = {}
        for _, arm in samples:
            if len(changes) >= n_params:
                break
            if arm.parameter in changes:
                continue  # Don't adjust same param twice

            spec = ACTION_SPECS.get(arm.parameter)
            if spec is None:
                continue
            current = current_config.get(arm.parameter, spec.default)
            proposed = current + arm.direction * spec.step_size
            proposed = clamp_amplitude(arm.parameter, current, proposed)

            # Direction check
            if not check_direction_history(arm.parameter, arm.direction, history):
                continue

            changes[arm.parameter] = proposed

        return Action(changes=changes, source=PolicyStage.BANDIT)

    def _random_action(self, current_config: dict[str, Any], n_params: int) -> Action:
        """Forced exploration: random parameter selection."""
        params = list(ACTION_SPECS.keys())
        self.rng.shuffle(params)
        changes: dict[str, float] = {}
        for param in params[:n_params]:
            spec = ACTION_SPECS[param]
            current = current_config.get(param, spec.default)
            direction = self.rng.choice([-1, +1])
            proposed = current + direction * spec.step_size
            proposed = clamp_amplitude(param, current, proposed)
            changes[param] = proposed
        return Action(changes=changes, source=PolicyStage.BANDIT, exploration=True)

    def update(self, action: Action, reward: float, *, prior_config: dict[str, Any] | None = None) -> None:
        """Update arms based on action and observed reward.

        If `prior_config` is supplied, only the arm matching the actual
        direction of each change is updated. Otherwise we fall back to updating
        every arm for the parameter with half credit so callers that cannot
        supply the prior state do not corrupt arm statistics.
        """
        prior_config = prior_config or {}
        for param, new_value in action.changes.items():
            prior = prior_config.get(param)
            direction: int | None = None
            if prior is not None:
                try:
                    delta = float(new_value) - float(prior)
                    if delta != 0:
                        direction = 1 if delta > 0 else -1
                except (TypeError, ValueError):
                    direction = None

            for arm in self.arms.values():
                if arm.parameter != param:
                    continue
                if direction is None:
                    # Unknown direction: split credit evenly across both arms.
                    arm.update(reward * 0.5)
                elif arm.direction == direction:
                    arm.update(reward)

    def get_arm_stats(self) -> list[dict[str, Any]]:
        """Return statistics for all arms."""
        return [
            {
                "arm_id": arm.arm_id,
                "parameter": arm.parameter,
                "direction": arm.direction,
                "pulls": arm.pulls,
                "mean_reward": round(arm.mean_reward, 4),
                "alpha": round(arm.alpha, 2),
                "beta": round(arm.beta, 2),
            }
            for arm in self.arms.values()
        ]

    def to_dict(self) -> dict[str, Any]:
        """Serialize bandit state for persistence."""
        return {
            "arms": {
                arm_id: {
                    "alpha": arm.alpha,
                    "beta": arm.beta,
                    "pulls": arm.pulls,
                    "total_reward": arm.total_reward,
                }
                for arm_id, arm in self.arms.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, rng_seed: int | None = None) -> ThompsonSamplingBandit:
        """Restore bandit state from serialized data."""
        bandit = cls(rng_seed=rng_seed)
        for arm_id, arm_data in data.get("arms", {}).items():
            if arm_id in bandit.arms:
                bandit.arms[arm_id].alpha = arm_data.get("alpha", 1.0)
                bandit.arms[arm_id].beta = arm_data.get("beta", 1.0)
                bandit.arms[arm_id].pulls = arm_data.get("pulls", 0)
                bandit.arms[arm_id].total_reward = arm_data.get("total_reward", 0.0)
        return bandit


# ── Stage 3: LinUCB Contextual Bandit ─────────────────────


@dataclass
class LinUCBArm:
    """A single arm in the LinUCB contextual bandit."""
    arm_id: str
    parameter: str
    direction: int
    d: int = 9  # feature dimension

    # LinUCB parameters
    A: list[list[float]] = field(default_factory=list)  # d × d matrix
    b: list[float] = field(default_factory=list)         # d × 1 vector
    pulls: int = 0
    total_reward: float = 0.0

    def __post_init__(self) -> None:
        if not self.A:
            # Initialize A = I_d (identity matrix)
            self.A = [[1.0 if i == j else 0.0 for j in range(self.d)] for i in range(self.d)]
        if not self.b:
            self.b = [0.0] * self.d

    @property
    def theta(self) -> list[float]:
        """Compute θ = A^{-1} b using simple matrix solve."""
        return _solve_linear(self.A, self.b)

    def ucb(self, context: list[float], alpha: float = 1.0) -> float:
        """Compute UCB = θ^T x + α √(x^T A^{-1} x)."""
        theta = self.theta
        # θ^T x
        mean = sum(t * x for t, x in zip(theta, context))

        # x^T A^{-1} x (approximate via diagonal)
        inv_diag = [1.0 / max(self.A[i][i], 0.01) for i in range(len(context))]
        variance = sum(x * x * inv for x, inv in zip(context, inv_diag))

        return mean + alpha * math.sqrt(max(0, variance))

    def update(self, context: list[float], reward: float) -> None:
        """Update A and b with new observation."""
        self.pulls += 1
        self.total_reward += reward

        # A += x x^T
        for i in range(len(context)):
            for j in range(len(context)):
                self.A[i][j] += context[i] * context[j]
        # b += r x
        for i in range(len(context)):
            self.b[i] += reward * context[i]


class LinUCBBandit:
    """Stage 3: contextual bandit using LinUCB algorithm.

    Uses state vector as context to make parameter adjustment decisions
    conditioned on the current system state.
    """

    def __init__(self, *, alpha: float = 1.0, rng_seed: int | None = None):
        self.alpha = alpha
        self.rng = random.Random(rng_seed)
        self.arms: dict[str, LinUCBArm] = {}
        self._init_arms()

    def _init_arms(self) -> None:
        for param, direction in BANDIT_ARMS:
            arm_id = f"{param}_{'up' if direction > 0 else 'down'}"
            self.arms[arm_id] = LinUCBArm(
                arm_id=arm_id,
                parameter=param,
                direction=direction,
            )

    def select_action(
        self,
        state: StateVector,
        current_config: dict[str, Any],
        history: list[dict[str, Any]],
        *,
        n_params: int = 2,
    ) -> Action:
        """Select action using LinUCB with state context."""
        context = state.to_feature_vector()
        if not context:
            return Action(changes={}, source=PolicyStage.CONTEXTUAL)

        # Compute UCB for each arm
        scores = []
        for arm_id, arm in self.arms.items():
            try:
                score = arm.ucb(context, self.alpha)
            except Exception:  # noqa: BLE001
                score = 0.0
            scores.append((score, arm))

        scores.sort(key=lambda x: x[0], reverse=True)

        changes: dict[str, float] = {}
        for _, arm in scores:
            if len(changes) >= n_params:
                break
            if arm.parameter in changes:
                continue

            spec = ACTION_SPECS.get(arm.parameter)
            if spec is None:
                continue
            current = current_config.get(arm.parameter, spec.default)
            proposed = current + arm.direction * spec.step_size
            proposed = clamp_amplitude(arm.parameter, current, proposed)

            if not check_direction_history(arm.parameter, arm.direction, history):
                continue

            changes[arm.parameter] = proposed

        return Action(changes=changes, source=PolicyStage.CONTEXTUAL)

    def update(self, action: Action, state: StateVector, reward: float) -> None:
        """Update arm models with observation."""
        context = state.to_feature_vector()
        if not context:
            return

        for param in action.changes:
            for arm in self.arms.values():
                if arm.parameter == param:
                    arm.update(context, reward)


def _solve_linear(A: list[list[float]], b: list[float]) -> list[float]:
    """Simple Gaussian elimination for small systems (d ≤ 20)."""
    n = len(b)
    # Augmented matrix
    M = [row[:] + [b[i]] for i, row in enumerate(A)]

    for col in range(n):
        # Pivot
        max_row = col
        for row in range(col + 1, n):
            if abs(M[row][col]) > abs(M[max_row][col]):
                max_row = row
        M[col], M[max_row] = M[max_row], M[col]

        if abs(M[col][col]) < 1e-10:
            continue

        # Eliminate
        for row in range(col + 1, n):
            factor = M[row][col] / M[col][col]
            for j in range(col, n + 1):
                M[row][j] -= factor * M[col][j]

    # Back substitute
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(M[i][i]) < 1e-10:
            continue
        x[i] = M[i][n]
        for j in range(i + 1, n):
            x[i] -= M[i][j] * x[j]
        x[i] /= M[i][i]

    return x


# ── Policy Router ─────────────────────────────────────────


class PolicyRouter:
    """Routes between rule/bandit/contextual/dpo based on data availability.

    Transition criteria:
    - Rule → Bandit: ≥ 20 iterations, rule success rate < 60%
    - Bandit → Contextual: ≥ 50 iterations, ≥ 3 state clusters identified
    - Contextual → +DPO: ≥ 30 iterations, trained DPO model available
    """

    def __init__(
        self,
        *,
        rule: RulePolicy | None = None,
        bandit: ThompsonSamplingBandit | None = None,
        contextual: LinUCBBandit | None = None,
        dpo: DPOPolicy | None = None,
        rng_seed: int | None = None,
    ):
        self.rule = rule or RulePolicy()
        self.bandit = bandit or ThompsonSamplingBandit(rng_seed=rng_seed)
        self.contextual = contextual or LinUCBBandit(rng_seed=rng_seed)
        self.dpo = dpo or DPOPolicy()
        self.rng = random.Random(rng_seed)
        self._current_stage = PolicyStage.RULE

    @property
    def current_stage(self) -> PolicyStage:
        return self._current_stage

    def select_action(
        self,
        state: StateVector,
        hypotheses: list[str],
        current_config: dict[str, Any],
        history: list[dict[str, Any]],
        *,
        iteration_number: int = 0,
    ) -> Action:
        """Route to appropriate policy and select action."""
        # Check for forced exploration (Guardrail 4)
        exploration = should_explore(iteration_number)

        # Determine stage
        stage = self._determine_stage(iteration_number, history)

        if stage == PolicyStage.RULE:
            action = self.rule.select_action(state, hypotheses, current_config, history, rng=self.rng)
        elif stage == PolicyStage.BANDIT:
            action = self.bandit.select_action(
                current_config, history,
                exploration=exploration,
            )
        else:
            action = self.contextual.select_action(state, current_config, history)

        # Validate action novelty (Guardrail 1). Try up to 3 random fallbacks
        # before giving up; tight parameter spaces could otherwise loop.
        recent_hashes = [
            compute_config_hash(h.get("config_after", {}))
            for h in history[-10:]
            if h.get("config_after")
        ]

        def _is_novel(candidate: Action) -> bool:
            if not candidate.changes:
                return True
            merged = dict(current_config)
            merged.update(candidate.changes)
            return check_config_novelty(compute_config_hash(merged), recent_hashes)

        if not _is_novel(action):
            for _ in range(3):
                action = self.bandit.select_action(
                    current_config, history, exploration=True,
                )
                if _is_novel(action):
                    break
            else:
                # Surrender: emit an empty no-op action rather than duplicating history.
                action = Action(changes={}, source=action.source, exploration=True)

        return action

    def select_strategy(self, context_vector: list[float]) -> StrategyPreference | None:
        """Select AI behavior strategy via DPO policy (Stage 4).

        Returns None when DPO is not available (no trained model, or
        iteration count too low to enable Stage 4).
        """
        if self._current_stage != PolicyStage.DPO and not self.dpo.is_available:
            return None
        return self.dpo.select_strategy(context_vector)

    def update(
        self,
        action: Action,
        state: StateVector,
        reward: float,
        *,
        prior_config: dict[str, Any] | None = None,
    ) -> None:
        """Update all policy models with observation."""
        self.bandit.update(action, reward, prior_config=prior_config)
        self.contextual.update(action, state, reward)

    def _determine_stage(self, iteration: int, history: list[dict[str, Any]]) -> PolicyStage:
        """Determine which policy stage to use."""
        # Stage 4 (DPO) is additive: if the model is trained and iteration
        # count is sufficient, DPO runs in parallel with config-stage policies.
        dpo_ready = iteration >= 30 and self.dpo.is_available

        if iteration < 20:
            self._current_stage = PolicyStage.DPO if dpo_ready else PolicyStage.RULE
            return self._current_stage

        # Check rule success rate
        recent = history[-20:] if len(history) >= 20 else history
        if recent:
            successes = sum(1 for h in recent if h.get("outcome") in ("improved_sig", "improved_nonsig"))
            rule_rate = successes / len(recent)
            if rule_rate < 0.6:
                if iteration >= 50:
                    self._current_stage = PolicyStage.DPO if dpo_ready else PolicyStage.CONTEXTUAL
                    return self._current_stage
                self._current_stage = PolicyStage.DPO if dpo_ready else PolicyStage.BANDIT
                return self._current_stage

        self._current_stage = PolicyStage.DPO if dpo_ready else PolicyStage.RULE
        return self._current_stage
