from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from app.services.analytics.belief_recovery_simulator import BeliefRecoverySimulator, ObservationModelConfig
from app.services.analytics.user_state_model import (
    RoutingAction,
    RoutingMode,
    SimulatedOutcome,
    UserArchetype,
    UserStateModel,
)
from app.services.evidence.belief_state import BeliefState
from app.services.evidence.fusion_engine import FusionEngine
from app.services.evidence.unified_evidence import EvidenceTarget

BANDIT_ARMS: tuple[str, ...] = (
    RoutingMode.EXECUTION_FIRST.value,
    RoutingMode.BALANCED.value,
    RoutingMode.COGNITIVE_FIRST.value,
)


@dataclass(frozen=True)
class BeliefContext:
    support_pressure: float
    execution_readiness: float
    uncertainty: float
    bucket: str
    features: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BetaPosterior:
    alpha: float = 1.0
    beta: float = 1.0

    @property
    def mean(self) -> float:
        total = self.alpha + self.beta
        return self.alpha / total if total else 0.5

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    def update(self, reward: float) -> None:
        bounded = max(0.0, min(1.0, float(reward)))
        self.alpha += bounded
        self.beta += 1.0 - bounded

    def to_dict(self) -> dict[str, float]:
        return {
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "mean": round(self.mean, 4),
        }


class BeliefContextEncoder:
    """Convert BeliefState into a finite context for low-data Thompson Sampling."""

    @staticmethod
    def encode(belief_state: BeliefState) -> BeliefContext:
        values = {
            target.value: BeliefContextEncoder._mean(belief_state, target)
            for target in (
                EvidenceTarget.EMOTIONAL_BLOCK,
                EvidenceTarget.TASK_AVERSION,
                EvidenceTarget.COGNITIVE_LOAD,
                EvidenceTarget.GOAL_CLARITY,
                EvidenceTarget.EXECUTION_CAPACITY,
                EvidenceTarget.METACOGNITION_ACCURACY,
                EvidenceTarget.SYSTEM_DISSATISFACTION,
            )
        }
        variances = {
            target.value: BeliefContextEncoder._variance(belief_state, target)
            for target in (
                EvidenceTarget.EMOTIONAL_BLOCK,
                EvidenceTarget.TASK_AVERSION,
                EvidenceTarget.COGNITIVE_LOAD,
                EvidenceTarget.GOAL_CLARITY,
                EvidenceTarget.EXECUTION_CAPACITY,
                EvidenceTarget.METACOGNITION_ACCURACY,
                EvidenceTarget.SYSTEM_DISSATISFACTION,
            )
        }
        support_pressure = min(
            1.0,
            0.24 * values["emotional_block"]
            + 0.21 * values["task_aversion"]
            + 0.19 * values["cognitive_load"]
            + 0.13 * (1.0 - values["metacognition_accuracy"])
            + 0.11 * (1.0 - values["execution_capacity"])
            + 0.12 * values["system_dissatisfaction"],
        )
        execution_readiness = max(
            0.0,
            0.34 * values["goal_clarity"]
            + 0.30 * values["execution_capacity"]
            + 0.18 * (1.0 - values["cognitive_load"])
            + 0.10 * values["metacognition_accuracy"]
            + 0.08 * (1.0 - values["task_aversion"]),
        )
        uncertainty = max(variances.values()) if variances else 0.25
        bucket = "|".join(
            (
                f"pressure:{BeliefContextEncoder._bucket(support_pressure)}",
                f"readiness:{BeliefContextEncoder._bucket(execution_readiness)}",
                f"uncertainty:{BeliefContextEncoder._bucket_uncertainty(uncertainty)}",
            )
        )
        return BeliefContext(
            support_pressure=round(support_pressure, 6),
            execution_readiness=round(execution_readiness, 6),
            uncertainty=round(uncertainty, 6),
            bucket=bucket,
            features={**values, **{f"{key}_variance": value for key, value in variances.items()}},
        )

    @staticmethod
    def _mean(belief_state: BeliefState, target: EvidenceTarget) -> float:
        variable = belief_state.peek_variable(target)
        return float(variable.mean) if variable is not None else 0.5

    @staticmethod
    def _variance(belief_state: BeliefState, target: EvidenceTarget) -> float:
        variable = belief_state.peek_variable(target)
        return float(variable.variance) if variable is not None else 0.25

    @staticmethod
    def _bucket(value: float) -> str:
        if value < 0.38:
            return "low"
        if value < 0.66:
            return "mid"
        return "high"

    @staticmethod
    def _bucket_uncertainty(value: float) -> str:
        if value < 0.08:
            return "low"
        if value < 0.18:
            return "mid"
        return "high"


class ContextualThompsonBandit:
    """Finite-context Thompson Sampling for route-mode selection."""

    def __init__(self, *, arms: tuple[str, ...] = BANDIT_ARMS, seed: int = 23) -> None:
        self.arms = arms
        self.rng = random.Random(seed)
        self.global_posteriors = {arm: BetaPosterior() for arm in arms}
        self.context_posteriors: dict[str, dict[str, BetaPosterior]] = {}

    def select_arm(self, context: BeliefContext) -> str:
        posteriors = self._posteriors_for_context(context.bucket)
        samples = {
            arm: 0.72 * posteriors[arm].sample(self.rng) + 0.28 * self.global_posteriors[arm].sample(self.rng)
            for arm in self.arms
        }
        return max(samples, key=lambda k: samples[k])

    def update(self, context: BeliefContext, arm: str, reward: float) -> None:
        if arm not in self.arms:
            raise ValueError(f"unknown arm: {arm}")
        posteriors = self._posteriors_for_context(context.bucket)
        posteriors[arm].update(reward)
        self.global_posteriors[arm].update(reward)

    def _posteriors_for_context(self, bucket: str) -> dict[str, BetaPosterior]:
        if bucket not in self.context_posteriors:
            self.context_posteriors[bucket] = {arm: BetaPosterior() for arm in self.arms}
        return self.context_posteriors[bucket]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "contextual_thompson_bandit.v1",
            "arms": list(self.arms),
            "global_posteriors": {arm: posterior.to_dict() for arm, posterior in self.global_posteriors.items()},
            "context_count": len(self.context_posteriors),
            "context_posteriors": {
                bucket: {arm: posterior.to_dict() for arm, posterior in posteriors.items()}
                for bucket, posteriors in sorted(self.context_posteriors.items())
            },
        }


class BanditSimulationRunner:
    """Run the bandit through the numeric wind tunnel for algorithm debugging only."""

    def __init__(
        self,
        *,
        observation_config: ObservationModelConfig | None = None,
        fusion_model: str = "independent",
        seed: int = 23,
    ) -> None:
        self.simulator = BeliefRecoverySimulator(
            observation_config=observation_config or ObservationModelConfig(),
            fusion_model=fusion_model,
        )
        self.bandit = ContextualThompsonBandit(seed=seed)
        self.seed = seed
        self.fusion_model = fusion_model

    def run(
        self,
        *,
        episodes_per_archetype: int = 10,
        steps: int = 16,
        archetypes: list[UserArchetype] | None = None,
    ) -> dict[str, Any]:
        resolved_archetypes = archetypes or list(UserArchetype)
        rewards: list[float] = []
        arm_counts: Counter[str] = Counter()
        outcome_counts: Counter[str] = Counter()
        for archetype_index, archetype in enumerate(resolved_archetypes):
            for episode_index in range(episodes_per_archetype):
                episode_seed = self.seed + archetype_index * 100_000 + episode_index
                rewards.extend(self._run_episode(archetype=archetype, steps=steps, seed=episode_seed, arm_counts=arm_counts, outcome_counts=outcome_counts))
        total = max(1, len(rewards))
        return {
            "schema_version": "bandit_simulation_report.v1",
            "fusion_model": self.fusion_model,
            "episodes": episodes_per_archetype * len(resolved_archetypes),
            "steps": len(rewards),
            "average_reward": round(sum(rewards) / total, 6),
            "arm_counts": dict(sorted(arm_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "bandit": self.bandit.to_dict(),
            "simulated_only": True,
            "warning": "Simulator rewards are for algorithm debugging, not product effectiveness proof.",
        }

    def _run_episode(
        self,
        *,
        archetype: UserArchetype,
        steps: int,
        seed: int,
        arm_counts: Counter[str],
        outcome_counts: Counter[str],
    ) -> list[float]:
        rng = random.Random(seed)
        model = UserStateModel.from_archetype(archetype, rng_seed=seed)
        belief_state = BeliefState(user_id=f"bandit-sim-{archetype.value}-{seed}")
        engine = FusionEngine(belief_state.user_id)
        rewards: list[float] = []
        for step_index in range(steps):
            evidence = self.simulator.evidence_from_state(
                model.state,
                rng=rng,
                step_index=step_index,
                archetype=archetype.value,
            )
            belief_state = engine.fuse_many(belief_state, evidence)
            context = BeliefContextEncoder.encode(belief_state)
            arm = self.bandit.select_arm(context)
            transition = model.step(RoutingAction.from_mode(arm))
            reward = self._simulated_reward(transition.outcome, transition.next_state)
            self.bandit.update(context, arm, reward)
            rewards.append(reward)
            arm_counts[arm] += 1
            outcome_counts[transition.outcome.value] += 1
            if transition.absorbed:
                break
        return rewards

    @staticmethod
    def _simulated_reward(outcome: SimulatedOutcome, next_state: dict[str, float]) -> float:
        if outcome == SimulatedOutcome.TASK_COMPLETED:
            return 1.0
        if outcome in {SimulatedOutcome.TASK_ABANDONED, SimulatedOutcome.FORCED_ABANDON}:
            return 0.0
        progress_proxy = 0.38 * next_state["execution_capacity"] + 0.28 * next_state["goal_clarity"]
        cost_proxy = 0.18 * next_state["emotional_block"] + 0.16 * next_state["task_aversion"]
        return max(0.0, min(1.0, 0.45 + progress_proxy - cost_proxy))
