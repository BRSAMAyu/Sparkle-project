from __future__ import annotations

# rule-bj: exempt v1 未接线组件（评估器/分类器/工具），保留待接线——见 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from app.services.analytics.contextual_bandit import BeliefContextEncoder
from app.services.analytics.user_state_model import (
    RoutingAction as SimRoutingAction,
)
from app.services.analytics.user_state_model import (
    RoutingMode,
    SimulatedOutcome,
    StateTransitionReport,
    UserArchetype,
    UserStateModel,
)
from app.services.evidence.belief_state import BeliefState
from app.services.evidence.fusion_engine import FusionEngine
from app.services.evidence.reward_model import RewardSignalType
from app.services.evidence.unified_evidence import EvidenceTarget

ROUTING_TARGETS: tuple[EvidenceTarget, ...] = (
    EvidenceTarget.EMOTIONAL_BLOCK,
    EvidenceTarget.TASK_AVERSION,
    EvidenceTarget.COGNITIVE_LOAD,
    EvidenceTarget.GOAL_CLARITY,
    EvidenceTarget.EXECUTION_CAPACITY,
    EvidenceTarget.METACOGNITION_ACCURACY,
    EvidenceTarget.SYSTEM_DISSATISFACTION,
)


class RoutingPolicyStage(StrEnum):
    RULE = "rule"
    BANDIT = "bandit"
    CONTEXTUAL = "contextual"
    RL_DATA_COLLECTION = "rl_data_collection"


class RoutingArm(StrEnum):
    EXECUTION_FIRST = "execution_first"
    BALANCED = "balanced"
    COGNITIVE_FIRST = "cognitive_first"


class RoutingRewardSource(StrEnum):
    REAL_OUTCOME = "real_outcome"
    SIMULATED_WIND_TUNNEL = "simulated_wind_tunnel"
    UNKNOWN = "unknown"


def _safe_float(value: Any, *, default: float = 0.5) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.0, min(1.0, parsed))


def _safe_variance(value: Any, *, default: float = 0.25) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0.01, min(0.25, parsed))


@dataclass(frozen=True)
class RoutingStateVector:
    """Routing-specialized MDP state.

    This is the bridge from production BeliefState into the existing SGW-style
    RL scaffolding. It keeps the state explicit and serializable so Policy Zoo,
    holdout, and rollout tooling can consume it without knowing production
    model classes.
    """

    belief_means: dict[str, float]
    belief_variances: dict[str, float]
    support_pressure: float
    execution_readiness: float
    max_uncertainty: float
    user_archetype: str = "unknown"
    step_index: int = 0
    context_bucket: str = ""

    @classmethod
    def from_belief_state(
        cls,
        belief_state: BeliefState,
        *,
        user_archetype: str = "unknown",
        step_index: int = 0,
    ) -> RoutingStateVector:
        context = BeliefContextEncoder.encode(belief_state)
        means: dict[str, float] = {}
        variances: dict[str, float] = {}
        for target in ROUTING_TARGETS:
            variable = belief_state.peek_variable(target)
            means[target.value] = round(float(variable.mean), 6) if variable is not None else 0.5
            variances[target.value] = round(float(variable.variance), 6) if variable is not None else 0.25
        return cls(
            belief_means=means,
            belief_variances=variances,
            support_pressure=context.support_pressure,
            execution_readiness=context.execution_readiness,
            max_uncertainty=context.uncertainty,
            user_archetype=str(user_archetype or "unknown"),
            step_index=max(0, int(step_index)),
            context_bucket=context.bucket,
        )

    def to_feature_vector(self) -> list[float]:
        """Stable numeric vector for contextual bandits and future offline RL."""
        means = [self.belief_means.get(target.value, 0.5) for target in ROUTING_TARGETS]
        variances = [self.belief_variances.get(target.value, 0.25) for target in ROUTING_TARGETS]
        return [
            *means,
            *variances,
            self.support_pressure,
            self.execution_readiness,
            self.max_uncertainty,
        ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutingMDPAction:
    arm: RoutingArm
    pressure: float
    support: float
    difficulty: float
    directness: float
    explanation_depth: float
    source: RoutingPolicyStage = RoutingPolicyStage.RULE
    exploration: bool = False

    @classmethod
    def from_mode(
        cls,
        mode: RoutingMode | RoutingArm | str,
        *,
        source: RoutingPolicyStage = RoutingPolicyStage.RULE,
        exploration: bool = False,
    ) -> RoutingMDPAction:
        sim_action = SimRoutingAction.from_mode(str(mode))
        return cls(
            arm=RoutingArm(str(sim_action.mode.value)),
            pressure=sim_action.pressure_score(),
            support=sim_action.supportiveness,
            difficulty=sim_action.difficulty,
            directness=sim_action.directness,
            explanation_depth=sim_action.explanation_depth,
            source=source,
            exploration=exploration,
        )

    def to_sim_action(self) -> SimRoutingAction:
        return SimRoutingAction.from_mode(
            self.arm.value,
            supportiveness=self.support,
            difficulty=self.difficulty,
            directness=self.directness,
            explanation_depth=self.explanation_depth,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["arm"] = self.arm.value
        payload["source"] = self.source.value
        return payload


@dataclass(frozen=True)
class RoutingRewardSignal:
    reward: float
    source: RoutingRewardSource
    outcome_label: str
    training_eligible: bool
    simulated_only: bool = False
    components: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_simulated_outcome(
        cls,
        outcome: SimulatedOutcome | str,
        *,
        next_state: dict[str, float] | None = None,
    ) -> RoutingRewardSignal:
        resolved = SimulatedOutcome(str(outcome))
        if resolved == SimulatedOutcome.TASK_COMPLETED:
            reward = 1.0
        elif resolved == SimulatedOutcome.TASK_ABANDONED:
            reward = -1.0
        elif resolved == SimulatedOutcome.FORCED_ABANDON:
            reward = -2.0
        else:
            state = next_state or {}
            progress = 0.38 * _safe_float(state.get("execution_capacity")) + 0.28 * _safe_float(
                state.get("goal_clarity")
            )
            cost = 0.18 * _safe_float(state.get("emotional_block")) + 0.16 * _safe_float(
                state.get("task_aversion")
            )
            reward = max(-0.4, min(0.6, progress - cost))
        return cls(
            reward=round(float(reward), 6),
            source=RoutingRewardSource.SIMULATED_WIND_TUNNEL,
            outcome_label=resolved.value,
            training_eligible=False,
            simulated_only=True,
            components={"simulated_reward": round(float(reward), 6)},
        )

    @classmethod
    def from_trace(cls, trace: dict[str, Any]) -> RoutingRewardSignal:
        reward = trace.get("reward")
        if not isinstance(reward, dict):
            return cls.unknown()
        signal_type = str(reward.get("signal_type") or RewardSignalType.UNKNOWN.value)
        if signal_type in {RewardSignalType.UNKNOWN.value, "no_negative_followup_signal"}:
            return cls.unknown()
        if bool(reward.get("is_censored")):
            return cls.unknown()
        try:
            total_reward = float(reward.get("total_reward"))
        except (TypeError, ValueError):
            return cls.unknown()
        return cls(
            reward=round(total_reward, 6),
            source=RoutingRewardSource.REAL_OUTCOME,
            outcome_label=str(reward.get("outcome_label") or trace.get("outcome") or signal_type),
            training_eligible=bool(trace.get("training_eligible", True)),
            simulated_only=False,
            components={
                key: round(float(reward.get(key) or 0.0), 6)
                for key in (
                    "immediate_interaction_reward",
                    "task_progress_reward",
                    "sustainability_cost",
                    "long_horizon_reward",
                    "information_gain_reward",
                )
            },
        )

    @classmethod
    def unknown(cls) -> RoutingRewardSignal:
        return cls(
            reward=0.0,
            source=RoutingRewardSource.UNKNOWN,
            outcome_label="unknown",
            training_eligible=False,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source"] = self.source.value
        return payload


@dataclass(frozen=True)
class RoutingEpisodeStep:
    state: RoutingStateVector
    action: RoutingMDPAction
    reward: RoutingRewardSignal
    next_state: RoutingStateVector | None = None
    transition: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "action": self.action.to_dict(),
            "reward": self.reward.to_dict(),
            "next_state": self.next_state.to_dict() if self.next_state else None,
            "transition": self.transition,
        }


@dataclass(frozen=True)
class RoutingScenarioRecipe:
    recipe_id: str
    description: str
    archetype: UserArchetype
    seed: int = 31
    steps: int = 24
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["archetype"] = self.archetype.value
        return payload


class RoutingMDPBridge:
    """Adapter between production BeliefState and routing-specific MDP records."""

    @staticmethod
    def state_from_belief(
        belief_state: BeliefState,
        *,
        user_archetype: str = "unknown",
        step_index: int = 0,
    ) -> RoutingStateVector:
        return RoutingStateVector.from_belief_state(
            belief_state,
            user_archetype=user_archetype,
            step_index=step_index,
        )

    @staticmethod
    def action_from_mode(
        mode: RoutingMode | RoutingArm | str,
        *,
        source: RoutingPolicyStage = RoutingPolicyStage.RULE,
        exploration: bool = False,
    ) -> RoutingMDPAction:
        return RoutingMDPAction.from_mode(mode, source=source, exploration=exploration)

    @staticmethod
    def step_from_simulation(
        *,
        belief_state: BeliefState,
        action: RoutingMDPAction,
        transition: StateTransitionReport,
        user_archetype: str,
        next_belief_state: BeliefState | None = None,
    ) -> RoutingEpisodeStep:
        state = RoutingStateVector.from_belief_state(
            belief_state,
            user_archetype=user_archetype,
            step_index=transition.step_index - 1,
        )
        next_state = (
            RoutingStateVector.from_belief_state(
                next_belief_state,
                user_archetype=user_archetype,
                step_index=transition.step_index,
            )
            if next_belief_state is not None
            else None
        )
        return RoutingEpisodeStep(
            state=state,
            action=action,
            reward=RoutingRewardSignal.from_simulated_outcome(
                transition.outcome,
                next_state=transition.next_state,
            ),
            next_state=next_state,
            transition=transition.to_dict(),
        )

    @staticmethod
    def step_from_trace(trace: dict[str, Any]) -> RoutingEpisodeStep | None:
        belief_vector = trace.get("belief_state_vector")
        if not isinstance(belief_vector, dict):
            return None
        belief_state = BeliefState(user_id=str(trace.get("user_id") or "trace-user"))
        for target in ROUTING_TARGETS:
            mean = belief_vector.get(f"{target.value}_mean")
            variance = belief_vector.get(f"{target.value}_variance")
            variable = belief_state.get_variable(target)
            variable.mean = _safe_float(mean)
            variable.unbounded_mean = variable.mean
            variable.variance = _safe_variance(variance)
        mode = trace.get("actual_router_mode") or "balanced"
        action = RoutingMDPAction.from_mode(str(mode))
        return RoutingEpisodeStep(
            state=RoutingStateVector.from_belief_state(belief_state),
            action=action,
            reward=RoutingRewardSignal.from_trace(trace),
            transition={"trace_id": trace.get("trace_id"), "outcome": trace.get("outcome")},
        )

    @staticmethod
    def adversarial_recipes(*, steps: int = 24, seed: int = 31) -> list[RoutingScenarioRecipe]:
        return [
            RoutingScenarioRecipe(
                recipe_id="fragile_high_pressure",
                description="Fragile user under repeated pressure.",
                archetype=UserArchetype.FRAGILE,
                seed=seed,
                steps=steps,
                tags=["adversarial", "fragile", "pressure"],
            ),
            RoutingScenarioRecipe(
                recipe_id="avoidant_high_aversion",
                description="Avoidant user with high task aversion.",
                archetype=UserArchetype.AVOIDANT,
                seed=seed + 1,
                steps=steps,
                tags=["adversarial", "avoidant"],
            ),
            RoutingScenarioRecipe(
                recipe_id="pressure_driven_edge",
                description="Pressure-driven user to test over-support.",
                archetype=UserArchetype.PRESSURE_DRIVEN,
                seed=seed + 2,
                steps=steps,
                tags=["adversarial", "pressure_driven"],
            ),
        ]

    @staticmethod
    def run_wind_tunnel_recipe(
        recipe: RoutingScenarioRecipe,
        *,
        action_mode: RoutingMode | str = RoutingMode.EXECUTION_FIRST,
    ) -> dict[str, Any]:
        model = UserStateModel.from_archetype(recipe.archetype, rng_seed=recipe.seed)
        action = RoutingMDPAction.from_mode(action_mode)
        outcomes: dict[str, int] = {}
        severe_consistency_violations = 0
        for _ in range(recipe.steps):
            transition = model.step(action.to_sim_action())
            outcomes[transition.outcome.value] = outcomes.get(transition.outcome.value, 0) + 1
            if transition.consistency.severity == "severe":
                severe_consistency_violations += 1
            if transition.absorbed:
                break
        final_projection = FusionEngine().project_router_signals(BeliefState(user_id=f"recipe-{recipe.recipe_id}"))
        return {
            "schema_version": "routing_wind_tunnel_recipe.v1",
            "recipe": recipe.to_dict(),
            "action": action.to_dict(),
            "outcomes": outcomes,
            "steps_run": len(model.history),
            "absorbed": model.absorbed,
            "severe_consistency_violations": severe_consistency_violations,
            "final_ground_truth": model.generate_ground_truth_report(),
            "router_projection_shape": list(final_projection.keys()),
            "simulated_only": True,
        }
