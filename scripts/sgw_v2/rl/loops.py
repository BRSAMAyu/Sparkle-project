"""Nested feedback loops: inner/middle/outer/meta loop coordination.

Implements the four-level feedback architecture:
- Inner loop: per-turn expression validation + audit (milliseconds)
- Middle loop: per-run diagnostic + alerting (hours)
- Outer loop: per-iteration diagnose→plan→execute→evaluate (8-18h)
- Meta loop: multi-iteration episode with convergence detection (days)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .spec import (
    StateVector, Action, EpisodeConfig, EpisodeResult,
    PolicyStage, IterationOutcome, EpisodeTerminationReason,
    compute_config_hash, should_explore,
)
from .reward import compute_reward, RewardComponents
from .features import FeatureExtractor
from .policy import PolicyRouter
from .overfitting import (
    HoldoutGuard, ExplorationBudget, TemperatureSchedule,
    AdversarialSelfPlay, DiversityMetrics,
)


# ── Inner Loop (per-turn, called by sgw_orchestrator) ─────
# Already implemented in sgw_orchestrator.py:
#   - validate_expression() → _validate_and_regenerate()
#   - _run_audit() → compliance audit per turn
#   - _run_authenticity_audit() → per-session authenticity
# This module provides the coordination interface.


@dataclass
class InnerLoopResult:
    """Result from inner loop processing."""
    turn_valid: bool
    audit_result: dict[str, Any] | None = None
    authenticity_result: dict[str, Any] | None = None
    violation_recorded: bool = False


# ── Middle Loop (per-run, called after run completes) ──────


@dataclass
class MiddleLoopResult:
    """Result from middle loop processing."""
    run_id: str
    summary_before: dict[str, Any]
    summary_after: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    reward_raw: float = 0.0
    reward_normalized: float = 0.0


# ── Outer Loop (per-iteration) ────────────────────────────


@dataclass
class OuterLoopResult:
    """Result from one outer loop iteration."""
    iteration_number: int
    action: Action
    state_before: StateVector | None
    state_after: StateVector | None
    reward_raw: float
    reward_normalized: float
    outcome: IterationOutcome
    veto_applied: bool = False
    config_changed: bool = False
    new_config: dict[str, Any] | None = None


# ── Meta Loop (episode coordinator) ───────────────────────


class MetaLoopCoordinator:
    """Coordinates all four feedback loops through an RL episode.

    Usage:
        coordinator = MetaLoopCoordinator(run_db, current_config)
        episode = coordinator.run_episode(initial_state)
    """

    def __init__(
        self,
        *,
        feature_extractor: FeatureExtractor,
        policy_router: PolicyRouter,
        episode_config: EpisodeConfig | None = None,
        holdout_guard: HoldoutGuard | None = None,
        exploration_budget: ExplorationBudget | None = None,
        temperature_schedule: TemperatureSchedule | None = None,
        adversarial_play: AdversarialSelfPlay | None = None,
    ):
        self.features = feature_extractor
        self.policy = policy_router
        self.config = episode_config or EpisodeConfig()
        self.holdout = holdout_guard or HoldoutGuard()
        self.exploration = exploration_budget or ExplorationBudget()
        self.temperature = temperature_schedule or TemperatureSchedule()
        self.adversarial = adversarial_play or AdversarialSelfPlay()
        self._iteration_history: list[dict[str, Any]] = []
        self._training_rewards: list[float] = []
        self._holdout_rewards: list[float] = []
        self._consecutive_neutral = 0
        self._consecutive_regressed = 0

    def record_iteration(
        self,
        *,
        iteration_number: int,
        action: Action,
        state_before: StateVector | None,
        state_after: StateVector | None,
        summary_before: dict[str, Any],
        summary_after: dict[str, Any],
        outcome: IterationOutcome,
        current_config: dict[str, Any],
        diversity: DiversityMetrics | None = None,
        auth_z: float | None = None,
    ) -> OuterLoopResult:
        """Record and process an iteration result.

        Called by the meta_loop.py after each run completes.
        """
        # Compute reward
        div_score = diversity.diversity_score if diversity else 0.0
        reward_raw, reward_norm, components, veto, veto_reason = compute_reward(
            summary_before, summary_after,
            weights=self.config.reward_weights,
            diversity_score=div_score,
            auth_z_statistic=auth_z,
        )

        # Determine if config should change
        config_changed = False
        new_config = None
        if outcome in (IterationOutcome.IMPROVED_SIG, IterationOutcome.IMPROVED_NONSIG):
            config_changed = True
            new_config = dict(current_config)
            new_config.update(action.changes)
        elif outcome == IterationOutcome.REGRESSED_SIG:
            # Revert: keep current config
            config_changed = False

        result = OuterLoopResult(
            iteration_number=iteration_number,
            action=action,
            state_before=state_before,
            state_after=state_after,
            reward_raw=reward_raw,
            reward_normalized=reward_norm,
            outcome=outcome,
            veto_applied=veto,
            config_changed=config_changed,
            new_config=new_config,
        )

        # Update exploration tracking
        self.exploration.record(action.exploration)

        # Temperature annealing
        self.temperature.anneal()

        # Record trajectory
        self._record_trajectory(result, current_config)

        # Update policy models
        if state_after is not None:
            self.policy.update(action, state_after, reward_norm)

        # Track convergence/regression for termination
        if outcome == IterationOutcome.NEUTRAL:
            self._consecutive_neutral += 1
        elif outcome == IterationOutcome.IMPROVED_SIG:
            self._consecutive_neutral += 1  # convergence includes improvements
        else:
            self._consecutive_neutral = 0

        if outcome == IterationOutcome.REGRESSED_SIG:
            self._consecutive_regressed += 1
        else:
            self._consecutive_regressed = 0

        return result

    def check_termination(self, iteration: int) -> EpisodeTerminationReason | None:
        """Check if the episode should terminate."""
        # Hard violation → immediate stop
        if self._consecutive_regressed >= 2:
            return EpisodeTerminationReason.CRITICAL_REGRESSION

        # Convergence
        if self._consecutive_neutral >= self.config.convergence_window:
            return EpisodeTerminationReason.CONVERGENCE

        # Budget exhausted
        if iteration >= self.config.max_iterations:
            return EpisodeTerminationReason.BUDGET_EXHAUSTED

        return None

    def get_episode_result(self, initial_state: StateVector | None) -> EpisodeResult:
        """Summarize the episode."""
        if not self._iteration_history:
            return EpisodeResult(
                total_reward=0.0,
                iterations_used=0,
                initial_metrics=PopulationStats() if initial_state is None else initial_state.population_stats,
                final_metrics=PopulationStats() if initial_state is None else initial_state.population_stats,
                termination_reason=EpisodeTerminationReason.BUDGET_EXHAUSTED,
                policy_stage=self.policy.current_stage,
            )

        first = self._iteration_history[0]
        last = self._iteration_history[-1]

        return EpisodeResult(
            total_reward=sum(h.get("reward_normalized", 0) for h in self._iteration_history),
            iterations_used=len(self._iteration_history),
            initial_metrics=initial_state.population_stats if initial_state else PopulationStats(),
            final_metrics=last.get("state_after_stats", PopulationStats()),
            termination_reason=EpisodeTerminationReason.BUDGET_EXHAUSTED,  # Will be overridden
            policy_stage=self.policy.current_stage,
            iteration_history=self._iteration_history,
        )

    def _record_trajectory(self, result: OuterLoopResult, config: dict[str, Any]) -> None:
        """Record iteration to internal history."""
        entry = {
            "iteration": result.iteration_number,
            "action": result.action.to_dict(),
            "reward_raw": result.reward_raw,
            "reward_normalized": result.reward_normalized,
            "outcome": result.outcome.value,
            "veto": result.veto_applied,
            "config_after": dict(config) | result.action.changes if result.config_changed else dict(config),
            "state_after_stats": (
                result.state_after.population_stats if result.state_after else {}
            ),
        }
        self._iteration_history.append(entry)

        # Track holdout vs training
        seed = config.get("random_seed", 0)
        if self.holdout.is_holdout(seed):
            self._holdout_rewards.append(result.reward_normalized)
        else:
            self._training_rewards.append(result.reward_normalized)


# Import PopulationStats for type usage
from .spec import PopulationStats  # noqa: E402
