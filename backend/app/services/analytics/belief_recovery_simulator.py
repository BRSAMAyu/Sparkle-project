from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import settings
from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput
from app.services.analytics.belief_observation_models import BlockDiagonalBeliefFusionEngine
from app.services.analytics.user_state_model import (
    InternalState,
    RoutingAction,
    RoutingMode,
    UserArchetype,
    UserStateModel,
)
from app.services.evidence.belief_state import BeliefState
from app.services.evidence.fusion_engine import FusionEngine
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)

STATE_TARGETS: dict[str, EvidenceTarget] = {
    "emotional_block": EvidenceTarget.EMOTIONAL_BLOCK,
    "cognitive_load": EvidenceTarget.COGNITIVE_LOAD,
    "task_aversion": EvidenceTarget.TASK_AVERSION,
    "execution_capacity": EvidenceTarget.EXECUTION_CAPACITY,
    "goal_clarity": EvidenceTarget.GOAL_CLARITY,
    "metacognition_accuracy": EvidenceTarget.METACOGNITION_ACCURACY,
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


@dataclass(frozen=True)
class ObservationModelConfig:
    """Noisy sensor model from simulator ground truth to UnifiedEvidence."""

    noise_sigma: float = 0.08
    confidence: float = 0.76
    missing_rate: float = 0.0
    bias: dict[str, float] = field(default_factory=dict)
    source_type: EvidenceSourceType = EvidenceSourceType.HEURISTIC_FALLBACK

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_type"] = self.source_type.value
        return payload


@dataclass(frozen=True)
class BeliefRecoveryStep:
    step_index: int
    archetype: str
    policy: str
    true_state: dict[str, float]
    belief_estimate: dict[str, float]
    squared_error: dict[str, float]
    absolute_error: dict[str, float]
    evidence_count: int
    router_mode: str
    outcome: str
    action: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BeliefRecoverySimulator:
    """Numeric wind tunnel for Evidence -> FusionEngine -> BeliefState -> Router.

    This does not validate a policy against real users. It measures whether the
    observation/fusion stack can recover known simulator ground truth from noisy
    evidence, then verifies that the existing DualCoreRouter can consume that
    BeliefState through its feature-flagged signal layer.
    """

    def __init__(
        self,
        *,
        observation_config: ObservationModelConfig | None = None,
        router: DualCoreRouter | None = None,
        fusion_model: str = "independent",
    ) -> None:
        self.observation_config = observation_config or ObservationModelConfig()
        self.router = router or DualCoreRouter()
        self.fusion_model = fusion_model

    def run_batch(
        self,
        *,
        samples_per_archetype: int = 20,
        steps: int = 24,
        seed: int = 31,
        policy: str = "router",
        fusion_model: str | None = None,
        archetypes: list[UserArchetype] | None = None,
    ) -> dict[str, Any]:
        resolved_archetypes = archetypes or list(UserArchetype)
        all_steps: list[BeliefRecoveryStep] = []
        runs: list[dict[str, Any]] = []
        for archetype_index, archetype in enumerate(resolved_archetypes):
            for sample_index in range(samples_per_archetype):
                run_seed = seed + archetype_index * 100_000 + sample_index
                run = self.run_one(
                    archetype=archetype,
                    steps=steps,
                    seed=run_seed,
                    policy=policy,
                    fusion_model=fusion_model,
                )
                runs.append(
                    {
                        "archetype": archetype.value,
                        "seed": run_seed,
                        "steps": len(run),
                        "final_outcome": run[-1].outcome if run else "none",
                    }
                )
                all_steps.extend(run)
        return self._summarize(
            all_steps,
            runs,
            policy=policy,
            seed=seed,
            samples_per_archetype=samples_per_archetype,
            fusion_model=fusion_model or self.fusion_model,
        )

    def run_one(
        self,
        *,
        archetype: UserArchetype | str,
        steps: int = 24,
        seed: int = 31,
        policy: str = "router",
        fusion_model: str | None = None,
    ) -> list[BeliefRecoveryStep]:
        rng = random.Random(seed)
        model = UserStateModel.from_archetype(archetype, rng_seed=seed)
        resolved_fusion_model = fusion_model or self.fusion_model
        user_id = f"sim-{str(archetype)}-{seed}"
        belief_state = BeliefState(user_id=user_id)
        engine = FusionEngine(user_id)
        block_engine: BlockDiagonalBeliefFusionEngine | None = None
        block_state = None
        if resolved_fusion_model == "block_diagonal":
            block_engine = BlockDiagonalBeliefFusionEngine()
            block_state = block_engine.initial_state(user_id)
            belief_state = block_state.belief_state
        elif resolved_fusion_model != "independent":
            raise ValueError(f"unknown fusion_model: {resolved_fusion_model}")
        output: list[BeliefRecoveryStep] = []

        previous_flag = bool(getattr(settings, "SPARKLE_DUAL_CORE_BELIEF_SIGNALS_ENABLED", False))
        try:
            settings.SPARKLE_DUAL_CORE_BELIEF_SIGNALS_ENABLED = True
            for step_index in range(steps):
                true_state = model.state.to_dict()
                evidence_items = self.evidence_from_state(
                    model.state,
                    rng=rng,
                    step_index=step_index,
                    archetype=str(archetype),
                )
                if block_engine is not None and block_state is not None:
                    block_state = block_engine.fuse_many(block_state, evidence_items)
                    belief_state = block_state.belief_state
                else:
                    belief_state = engine.fuse_many(belief_state, evidence_items)
                router_mode = self._select_mode(
                    policy=policy,
                    belief_state=belief_state,
                    true_state=true_state,
                )
                estimate = self._belief_estimate(belief_state)
                squared_error = {
                    key: round((estimate[key] - true_state[key]) ** 2, 6)
                    for key in STATE_TARGETS
                }
                absolute_error = {
                    key: round(abs(estimate[key] - true_state[key]), 6)
                    for key in STATE_TARGETS
                }

                transition = model.step(RoutingAction.from_mode(router_mode))
                output.append(
                    BeliefRecoveryStep(
                        step_index=step_index,
                        archetype=str(archetype),
                        policy=policy,
                        true_state=true_state,
                        belief_estimate=estimate,
                        squared_error=squared_error,
                        absolute_error=absolute_error,
                        evidence_count=len(evidence_items),
                        router_mode=router_mode,
                        outcome=transition.outcome.value,
                        action=transition.action,
                    )
                )
                if transition.absorbed:
                    break
        finally:
            settings.SPARKLE_DUAL_CORE_BELIEF_SIGNALS_ENABLED = previous_flag
        return output

    def evidence_from_state(
        self,
        state: InternalState,
        *,
        rng: random.Random,
        step_index: int,
        archetype: str,
    ) -> list[UnifiedEvidence]:
        state_vector = state.to_dict()
        evidence_items: list[UnifiedEvidence] = []
        for key, target in STATE_TARGETS.items():
            if rng.random() < self.observation_config.missing_rate:
                continue
            observed = _clamp(
                state_vector[key]
                + float(self.observation_config.bias.get(key, 0.0))
                + rng.normalvariate(0.0, self.observation_config.noise_sigma)
            )
            evidence_items.append(
                UnifiedEvidence(
                    source_type=self.observation_config.source_type,
                    target_latent_variable=target,
                    direction=EvidenceDirection.OBSERVE,
                    strength=observed,
                    confidence=self.observation_config.confidence,
                    evidence_text=f"simulated_observation:{key}={observed:.3f}",
                    scope={"simulated": True, "archetype": archetype, "step_index": step_index},
                    metadata={
                        "ground_truth": round(float(state_vector[key]), 4),
                        "noise_sigma": self.observation_config.noise_sigma,
                        "observation_model": "numeric_ground_truth_sensor.v1",
                    },
                    extractor_version="simulated_numeric_sensor.v1",
                )
            )
        return evidence_items

    def _select_mode(self, *, policy: str, belief_state: BeliefState, true_state: dict[str, float]) -> str:
        if policy in {mode.value for mode in RoutingMode}:
            return policy
        if policy == "cycle":
            modes = (RoutingMode.EXECUTION_FIRST.value, RoutingMode.BALANCED.value, RoutingMode.COGNITIVE_FIRST.value)
            return modes[int(sum(true_state.values()) * 1000) % len(modes)]
        if policy != "router":
            raise ValueError(f"unknown simulation policy: {policy}")

        decision = self.router.route(
            DualCoreRoutingInput(
                intent="plan",
                intent_confidence=max(0.35, min(0.95, true_state["goal_clarity"])),
                information_sufficient=True,
                primary_challenge_area="execution",
                recent_sentiment_distribution={"neutral": 1},
                has_active_plan=True,
                plan_health_status="healthy",
                recent_task_feedback_distribution={},
                belief_state=belief_state,
            )
        )
        return decision.mode

    @staticmethod
    def _belief_estimate(belief_state: BeliefState) -> dict[str, float]:
        estimate: dict[str, float] = {}
        for key, target in STATE_TARGETS.items():
            variable = belief_state.peek_variable(target)
            estimate[key] = round(float(variable.mean), 6) if variable is not None else 0.5
        return estimate

    def _summarize(
        self,
        steps: list[BeliefRecoveryStep],
        runs: list[dict[str, Any]],
        *,
        policy: str,
        seed: int,
        samples_per_archetype: int,
        fusion_model: str,
    ) -> dict[str, Any]:
        target_sse: dict[str, float] = defaultdict(float)
        target_ae: dict[str, float] = defaultdict(float)
        target_bias: dict[str, float] = defaultdict(float)
        target_belief_mean: dict[str, float] = defaultdict(float)
        target_true_mean: dict[str, float] = defaultdict(float)
        count = max(1, len(steps))
        for step in steps:
            for key in STATE_TARGETS:
                target_sse[key] += step.squared_error[key]
                target_ae[key] += step.absolute_error[key]
                target_bias[key] += step.belief_estimate[key] - step.true_state[key]
                target_belief_mean[key] += step.belief_estimate[key]
                target_true_mean[key] += step.true_state[key]

        route_counts = Counter(step.router_mode for step in steps)
        outcome_counts = Counter(step.outcome for step in steps)
        per_target = {
            key: {
                "mse": round(target_sse[key] / count, 6),
                "mae": round(target_ae[key] / count, 6),
                "bias": round(target_bias[key] / count, 6),
            }
            for key in STATE_TARGETS
        }
        overall_mse = round(sum(item["mse"] for item in per_target.values()) / len(per_target), 6)
        overall_mae = round(sum(item["mae"] for item in per_target.values()) / len(per_target), 6)
        return {
            "schema_version": "belief_recovery_simulation.v1",
            "policy": policy,
            "fusion_model": fusion_model,
            "seed": seed,
            "samples_per_archetype": samples_per_archetype,
            "run_count": len(runs),
            "step_count": len(steps),
            "observation_model": self.observation_config.to_dict(),
            "overall_mse": overall_mse,
            "overall_mae": overall_mae,
            "per_target": per_target,
            "average_belief_mean_by_target": {
                key: round(target_belief_mean[key] / count, 4)
                for key in STATE_TARGETS
            },
            "average_true_mean_by_target": {
                key: round(target_true_mean[key] / count, 4)
                for key in STATE_TARGETS
            },
            "route_mode_counts": dict(sorted(route_counts.items())),
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "avg_evidence_per_step": round(
                sum(step.evidence_count for step in steps) / count,
                4,
            ),
            "warnings": self._warnings(overall_mse=overall_mse, steps=steps),
            "sample_steps": [step.to_dict() for step in steps[:5]],
            "runs": runs[:20],
        }

    @staticmethod
    def _warnings(*, overall_mse: float, steps: list[BeliefRecoveryStep]) -> list[str]:
        warnings: list[str] = []
        if overall_mse > 0.04:
            warnings.append("overall_mse_above_0.04")
        if steps and sum(step.evidence_count for step in steps) / len(steps) < len(STATE_TARGETS) * 0.7:
            warnings.append("low_evidence_coverage")
        if not any(step.router_mode == RoutingMode.COGNITIVE_FIRST.value for step in steps):
            warnings.append("router_never_selected_cognitive_first")
        return warnings
