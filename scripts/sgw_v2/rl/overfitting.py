"""Anti-overfitting defenses: 5 independent mechanisms to prevent policy collapse.

1. Holdout scenario set: metrics on unseen scenarios must not degrade
2. Diversity bonus: reward includes persona/behavior coverage
3. Forced exploration: periodic random perturbation regardless of policy
4. Temperature annealing: gradually shift from exploration to exploitation
5. Adversarial self-play: test against worst-case personas periodically
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from .spec import (
    StateVector, PopulationStats, ACTION_SPECS, BANDIT_ARMS,
    RewardWeights, DEFAULT_REWARD_WEIGHTS, REWARD_SCALE,
    IterationOutcome, clamp_amplitude,
)


# ── Defense 1: Holdout Scenario Set ───────────────────────


@dataclass
class HoldoutResult:
    """Result of evaluating policy on holdout scenarios."""
    holdout_reward: float
    training_reward: float
    gap: float              # holdout - training (negative = overfitting)
    is_overfitting: bool    # gap < -threshold
    details: dict[str, float] = field(default_factory=dict)


class HoldoutGuard:
    """Maintains a holdout set of scenarios never used for training.

    Periodically evaluates policy on holdout to detect overfitting.
    """

    def __init__(self, *, holdout_ratio: float = 0.2, threshold: float = 0.1):
        self.holdout_ratio = holdout_ratio
        self.threshold = threshold
        self._holdout_seeds: set[int] = set()
        self._training_seeds: set[int] = set()

    def assign_seed(self, seed: int) -> str:
        """Assign a seed to holdout or training set."""
        if seed in self._holdout_seeds:
            return "holdout"
        if seed in self._training_seeds:
            return "training"
        # Deterministic assignment using modulo
        if seed % int(1 / self.holdout_ratio) == 0:
            self._holdout_seeds.add(seed)
            return "holdout"
        self._training_seeds.add(seed)
        return "training"

    def is_holdout(self, seed: int) -> bool:
        return seed in self._holdout_seeds

    def check_overfitting(
        self,
        training_rewards: list[float],
        holdout_rewards: list[float],
    ) -> HoldoutResult:
        """Compare training vs holdout performance."""
        if not training_rewards or not holdout_rewards:
            return HoldoutResult(
                holdout_reward=0.0, training_reward=0.0,
                gap=0.0, is_overfitting=False,
            )

        train_mean = sum(training_rewards) / len(training_rewards)
        hold_mean = sum(holdout_rewards) / len(holdout_rewards)
        gap = hold_mean - train_mean

        return HoldoutResult(
            holdout_reward=round(hold_mean, 4),
            training_reward=round(train_mean, 4),
            gap=round(gap, 4),
            is_overfitting=gap < -self.threshold,
            details={
                "train_n": len(training_rewards),
                "holdout_n": len(holdout_rewards),
            },
        )


# ── Defense 2: Diversity Bonus ────────────────────────────


@dataclass
class DiversityMetrics:
    """Coverage metrics for persona axes and behavior classes."""
    unique_personas: int
    unique_behaviors: int
    total_samples: int
    persona_coverage: float     # unique_personas / total_expected
    behavior_coverage: float    # unique_behaviors / 7 (AIBehaviorClass count)
    diversity_score: float      # combined metric [0, 1]

    @classmethod
    def from_counts(
        cls,
        unique_personas: int,
        unique_behaviors: int,
        total_samples: int,
        expected_personas: int = 44,
        expected_behaviors: int = 7,
    ) -> DiversityMetrics:
        persona_cov = min(1.0, unique_personas / max(expected_personas, 1))
        behavior_cov = min(1.0, unique_behaviors / max(expected_behaviors, 1))
        diversity_score = (persona_cov + behavior_cov) / 2
        return cls(
            unique_personas=unique_personas,
            unique_behaviors=unique_behaviors,
            total_samples=total_samples,
            persona_coverage=round(persona_cov, 4),
            behavior_coverage=round(behavior_cov, 4),
            diversity_score=round(diversity_score, 4),
        )

    def bonus(self) -> float:
        """Diversity bonus ∈ [0, 1] for reward shaping."""
        return self.diversity_score


# ── Defense 3: Forced Exploration ─────────────────────────
# (Implemented in spec.py as should_explore() and in policy.py)
# This module provides the exploration budget tracker.


class ExplorationBudget:
    """Tracks exploration vs exploitation ratio and enforces minimum exploration."""

    def __init__(self, *, min_exploration_rate: float = 0.1, window: int = 10):
        self.min_exploration_rate = min_exploration_rate
        self.window = window
        self._exploration_history: list[bool] = []

    def record(self, is_exploration: bool) -> None:
        self._exploration_history.append(is_exploration)
        if len(self._exploration_history) > self.window * 2:
            self._exploration_history = self._exploration_history[-self.window:]

    def current_rate(self) -> float:
        """Exploration rate in the recent window."""
        recent = self._exploration_history[-self.window:]
        if not recent:
            return 1.0  # No data yet, assume exploring
        return sum(recent) / len(recent)

    def should_force_exploration(self) -> bool:
        """Force exploration if rate is below minimum."""
        return self.current_rate() < self.min_exploration_rate


# ── Defense 4: Temperature Annealing ──────────────────────


class TemperatureSchedule:
    """Temperature annealing for exploration-exploitation balance.

    Starts with high temperature (uniform exploration) and gradually
    anneals to low temperature (greedy exploitation).
    """

    def __init__(
        self,
        *,
        t_start: float = 1.0,
        t_end: float = 0.1,
        decay_rate: float = 0.95,
        min_temp: float = 0.05,
    ):
        self.t_start = t_start
        self.t_end = t_end
        self.decay_rate = decay_rate
        self.min_temp = min_temp
        self._current_temp = t_start

    @property
    def temperature(self) -> float:
        return self._current_temp

    def anneal(self) -> float:
        """Decay temperature by one step. Returns new temperature."""
        self._current_temp = max(
            self.t_end,
            self._current_temp * self.decay_rate,
        )
        return self._current_temp

    def should_explore(self, rng: random.Random) -> bool:
        """Stochastic exploration decision based on current temperature."""
        return rng.random() < self._current_temp

    def boltzmann_weights(self, scores: list[float]) -> list[float]:
        """Convert scores to Boltzmann distribution probabilities."""
        if not scores:
            return []
        max_score = max(scores)
        exp_scores = [math.exp((s - max_score) / max(self._current_temp, 0.01)) for s in scores]
        total = sum(exp_scores)
        if total < 1e-10:
            return [1.0 / len(scores)] * len(scores)
        return [e / total for e in exp_scores]

    def to_dict(self) -> dict[str, float]:
        return {
            "current_temp": self._current_temp,
            "t_start": self.t_start,
            "t_end": self.t_end,
            "decay_rate": self.decay_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> TemperatureSchedule:
        sched = cls(
            t_start=data.get("t_start", 1.0),
            t_end=data.get("t_end", 0.1),
            decay_rate=data.get("decay_rate", 0.95),
        )
        sched._current_temp = data.get("current_temp", sched.t_start)
        return sched


# ── Defense 5: Adversarial Self-Play ──────────────────────


class AdversarialSelfPlay:
    """Periodically tests policy against worst-case personas.

    Identifies which persona/behavior combinations the policy handles
    worst and forces additional testing on those.
    """

    def __init__(self, *, worst_k: int = 5, test_every: int = 5):
        self.worst_k = worst_k
        self.test_every = test_every
        self._performance_map: dict[str, list[float]] = {}

    def record(self, persona_id: str, behavior: str, reward: float) -> None:
        """Record performance for a persona-behavior cell."""
        key = f"{persona_id[:16]}_{behavior}"
        if key not in self._performance_map:
            self._performance_map[key] = []
        self._performance_map[key].append(reward)
        # Keep last 10
        if len(self._performance_map[key]) > 10:
            self._performance_map[key] = self._performance_map[key][-10:]

    def should_test(self, iteration: int) -> bool:
        """Whether to run adversarial test this iteration."""
        return iteration > 0 and iteration % self.test_every == 0

    def get_worst_cells(self) -> list[tuple[str, float]]:
        """Return the K worst-performing persona-behavior cells."""
        avg_perf = {}
        for key, rewards in self._performance_map.items():
            if rewards:
                avg_perf[key] = sum(rewards) / len(rewards)

        sorted_cells = sorted(avg_perf.items(), key=lambda x: x[1])
        return sorted_cells[:self.worst_k]

    def get_adversarial_config_overrides(self) -> dict[str, Any]:
        """Suggest config overrides to stress-test worst cells."""
        worst = self.get_worst_cells()
        if not worst:
            return {}

        # Suggest more audit sampling for worst cells
        overrides: dict[str, Any] = {
            "adversarial_cells": [cell for cell, _ in worst],
            "adversiral_min_reward": worst[0][1] if worst else 0.0,
        }
        return overrides
