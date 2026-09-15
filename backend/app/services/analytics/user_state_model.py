from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def _bounded_step(value: float, delta: float) -> float:
    """Apply a delta inside a closed [0, 1] state space."""
    value = _clamp(value)
    if delta >= 0:
        return _clamp(value + (1.0 - value) * _clamp(delta, 0.0, 2.0))
    return _clamp(value + value * max(-2.0, delta))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, x))))


class UserArchetype(StrEnum):
    FRAGILE = "fragile"
    RESILIENT = "resilient"
    MIXED = "mixed"
    PRESSURE_DRIVEN = "pressure_driven"
    AVOIDANT = "avoidant"


class RoutingMode(StrEnum):
    EXECUTION_FIRST = "execution_first"
    COGNITIVE_FIRST = "cognitive_first"
    BALANCED = "balanced"


class SimulatedOutcome(StrEnum):
    CONTINUE = "continue"
    TASK_COMPLETED = "task_completed"
    TASK_ABANDONED = "task_abandoned"
    FORCED_ABANDON = "forced_abandon"


@dataclass(frozen=True)
class UserTrait:
    """Trait parameters that shape the user's private transition function."""

    archetype: UserArchetype
    vulnerability: float
    resilience: float
    pressure_response: float
    recovery_rate: float
    load_sensitivity: float
    aversion_sensitivity: float
    goal_commitment: float
    metacognition: float
    baseline_noise: float
    collapse_threshold: float = 0.92
    collapse_patience: int = 2
    trait_id: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def for_archetype(
        cls,
        archetype: UserArchetype | str,
        *,
        rng: random.Random | None = None,
        overrides: dict[str, float] | None = None,
    ) -> UserTrait:
        rng = rng or random.Random()
        archetype = UserArchetype(str(archetype))
        base = {
            UserArchetype.FRAGILE: {
                "vulnerability": 0.82,
                "resilience": 0.22,
                "pressure_response": -0.62,
                "recovery_rate": 0.18,
                "load_sensitivity": 0.82,
                "aversion_sensitivity": 0.76,
                "goal_commitment": 0.42,
                "metacognition": 0.44,
                "baseline_noise": 0.075,
                "collapse_threshold": 0.88,
                "collapse_patience": 2,
            },
            UserArchetype.RESILIENT: {
                "vulnerability": 0.30,
                "resilience": 0.78,
                "pressure_response": 0.16,
                "recovery_rate": 0.52,
                "load_sensitivity": 0.34,
                "aversion_sensitivity": 0.30,
                "goal_commitment": 0.78,
                "metacognition": 0.70,
                "baseline_noise": 0.045,
                "collapse_threshold": 0.96,
                "collapse_patience": 3,
            },
            UserArchetype.MIXED: {
                "vulnerability": 0.54,
                "resilience": 0.52,
                "pressure_response": -0.06,
                "recovery_rate": 0.36,
                "load_sensitivity": 0.55,
                "aversion_sensitivity": 0.50,
                "goal_commitment": 0.58,
                "metacognition": 0.58,
                "baseline_noise": 0.060,
                "collapse_threshold": 0.93,
                "collapse_patience": 2,
            },
            UserArchetype.PRESSURE_DRIVEN: {
                "vulnerability": 0.44,
                "resilience": 0.62,
                "pressure_response": 0.54,
                "recovery_rate": 0.42,
                "load_sensitivity": 0.48,
                "aversion_sensitivity": 0.36,
                "goal_commitment": 0.82,
                "metacognition": 0.64,
                "baseline_noise": 0.055,
                "collapse_threshold": 0.94,
                "collapse_patience": 3,
            },
            UserArchetype.AVOIDANT: {
                "vulnerability": 0.66,
                "resilience": 0.35,
                "pressure_response": -0.34,
                "recovery_rate": 0.26,
                "load_sensitivity": 0.60,
                "aversion_sensitivity": 0.88,
                "goal_commitment": 0.36,
                "metacognition": 0.48,
                "baseline_noise": 0.070,
                "collapse_threshold": 0.90,
                "collapse_patience": 2,
            },
        }[archetype]
        values: dict[str, float | int] = {}
        for key, value in base.items():
            if key == "collapse_patience":
                values[key] = int(value)
                continue
            sigma = 0.045 if key != "pressure_response" else 0.075
            if key == "pressure_response":
                values[key] = max(-1.0, min(1.0, float(value) + rng.normalvariate(0.0, sigma)))
            else:
                values[key] = _clamp(float(value) + rng.normalvariate(0.0, sigma))
        for key, value in (overrides or {}).items():
            if key == "collapse_patience":
                values[key] = max(1, int(value))
            elif key == "pressure_response":
                values[key] = max(-1.0, min(1.0, float(value)))
            elif key in values:
                values[key] = _clamp(float(value))
        return cls(archetype=archetype, **values)  # type: ignore[arg-type]

    @classmethod
    def from_persona(
        cls,
        persona: dict[str, Any],
        *,
        rng: random.Random | None = None,
    ) -> UserTrait:
        """Initialize traits from a loose persona dictionary."""
        text = " ".join(str(value).lower() for value in persona.values() if value is not None)
        if any(marker in text for marker in ("fragile", "脆弱", "焦虑", "burnout", "崩溃")):
            archetype = UserArchetype.FRAGILE
        elif any(marker in text for marker in ("pressure", "冲刺", "deadline", "高压", "deadline-driven")):
            archetype = UserArchetype.PRESSURE_DRIVEN
        elif any(marker in text for marker in ("avoid", "拖延", "逃避", "procrast")):
            archetype = UserArchetype.AVOIDANT
        elif any(marker in text for marker in ("resilient", "韧性", "自律", "high performer")):
            archetype = UserArchetype.RESILIENT
        else:
            archetype = UserArchetype.MIXED

        overrides: dict[str, float] = {}
        numeric_mapping = {
            "vulnerability": "vulnerability",
            "resilience": "resilience",
            "pressure_response": "pressure_response",
            "recovery_rate": "recovery_rate",
            "goal_commitment": "goal_commitment",
            "metacognition": "metacognition",
        }
        for persona_key, trait_key in numeric_mapping.items():
            if persona_key in persona:
                try:
                    overrides[trait_key] = float(persona[persona_key])
                except (TypeError, ValueError):
                    pass
        return cls.for_archetype(archetype, rng=rng, overrides=overrides)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["archetype"] = self.archetype.value
        return payload


@dataclass
class InternalState:
    """Ground-truth state only available to the simulator."""

    emotional_block: float = 0.25
    cognitive_load: float = 0.30
    task_aversion: float = 0.30
    execution_capacity: float = 0.65
    goal_clarity: float = 0.60
    metacognition_accuracy: float = 0.55

    def clamp(self) -> InternalState:
        for key in self.__dataclass_fields__:
            setattr(self, key, _clamp(getattr(self, key)))
        return self

    def to_dict(self) -> dict[str, float]:
        self.clamp()
        return {key: round(float(getattr(self, key)), 4) for key in self.__dataclass_fields__}

    @classmethod
    def from_trait(cls, trait: UserTrait, *, rng: random.Random | None = None) -> InternalState:
        rng = rng or random.Random()
        state = cls(
            emotional_block=_clamp(0.22 + 0.34 * trait.vulnerability - 0.10 * trait.resilience),
            cognitive_load=_clamp(0.24 + 0.30 * trait.load_sensitivity + rng.normalvariate(0.0, 0.035)),
            task_aversion=_clamp(0.22 + 0.34 * trait.aversion_sensitivity - 0.12 * trait.goal_commitment),
            execution_capacity=_clamp(0.54 + 0.32 * trait.resilience + 0.16 * trait.goal_commitment),
            goal_clarity=_clamp(0.40 + 0.35 * trait.goal_commitment + rng.normalvariate(0.0, 0.04)),
            metacognition_accuracy=_clamp(trait.metacognition + rng.normalvariate(0.0, 0.04)),
        )
        return state.clamp()


@dataclass(frozen=True)
class RoutingAction:
    mode: RoutingMode
    planning_load: float = 0.5
    directness: float = 0.5
    supportiveness: float = 0.5
    difficulty: float = 0.5
    explanation_depth: float = 0.5

    @classmethod
    def from_mode(cls, mode: RoutingMode | str, **overrides: float) -> RoutingAction:
        mode = RoutingMode(str(mode))
        defaults = {
            RoutingMode.EXECUTION_FIRST: {
                "planning_load": 0.70,
                "directness": 0.78,
                "supportiveness": 0.28,
                "difficulty": 0.62,
                "explanation_depth": 0.34,
            },
            RoutingMode.COGNITIVE_FIRST: {
                "planning_load": 0.30,
                "directness": 0.30,
                "supportiveness": 0.82,
                "difficulty": 0.34,
                "explanation_depth": 0.76,
            },
            RoutingMode.BALANCED: {
                "planning_load": 0.50,
                "directness": 0.52,
                "supportiveness": 0.56,
                "difficulty": 0.50,
                "explanation_depth": 0.54,
            },
        }[mode]
        defaults.update({key: _clamp(value) for key, value in overrides.items() if key in defaults})
        return cls(mode=mode, **defaults)

    def pressure_score(self, *, context_pressure: float = 0.5) -> float:
        return _clamp(
            0.30 * self.planning_load
            + 0.24 * self.directness
            + 0.24 * self.difficulty
            + 0.12 * self.explanation_depth
            + 0.10 * context_pressure
            - 0.18 * self.supportiveness
        )

    def clarity_score(self) -> float:
        return _clamp(0.45 * self.directness + 0.30 * (1.0 - self.explanation_depth) + 0.25 * self.planning_load)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        return payload


@dataclass(frozen=True)
class ConsistencyReport:
    passed: bool
    severity: str
    violations: list[str]
    quality_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StateTransitionReport:
    step_index: int
    action: dict[str, Any]
    previous_state: dict[str, float]
    next_state: dict[str, float]
    deltas: dict[str, float]
    noise: dict[str, float]
    outcome: SimulatedOutcome
    absorbed: bool
    consistency: ConsistencyReport

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["outcome"] = self.outcome.value
        payload["consistency"] = self.consistency.to_dict()
        return payload


class InconsistentTrajectoryError(ValueError):
    """Raised when the simulated state violates hard consistency constraints."""


class UserStateModel:
    """Stochastic, persona-conditioned ground-truth user dynamics for routing simulation."""

    def __init__(
        self,
        trait: UserTrait,
        state: InternalState | None = None,
        *,
        rng_seed: int | None = None,
        strict_guard: bool = False,
    ) -> None:
        self.trait = trait
        self.rng = random.Random(rng_seed)
        self.state = state or InternalState.from_trait(trait, rng=self.rng)
        self.strict_guard = strict_guard
        self.step_index = 0
        self.absorbed = False
        self.absorbed_outcome: SimulatedOutcome | None = None
        self._collapse_streak = 0
        self.history: list[StateTransitionReport] = []

    @classmethod
    def from_archetype(
        cls,
        archetype: UserArchetype | str,
        *,
        rng_seed: int | None = None,
        strict_guard: bool = False,
        trait_overrides: dict[str, float] | None = None,
    ) -> UserStateModel:
        rng = random.Random(rng_seed)
        trait = UserTrait.for_archetype(archetype, rng=rng, overrides=trait_overrides)
        return cls(trait, rng_seed=rng_seed, strict_guard=strict_guard)

    @classmethod
    def from_persona(
        cls,
        persona: dict[str, Any],
        *,
        rng_seed: int | None = None,
        strict_guard: bool = False,
    ) -> UserStateModel:
        rng = random.Random(rng_seed)
        trait = UserTrait.from_persona(persona, rng=rng)
        return cls(trait, rng_seed=rng_seed, strict_guard=strict_guard)

    def step(
        self,
        action: RoutingAction | RoutingMode | str,
        *,
        context_pressure: float = 0.5,
        external_shock: float = 0.0,
    ) -> StateTransitionReport:
        if self.strict_guard:
            current_consistency = self.validate_consistency()
            if not current_consistency.passed:
                raise InconsistentTrajectoryError(str(current_consistency.to_dict()))
        if not isinstance(action, RoutingAction):
            action = RoutingAction.from_mode(action)
        previous = self.state.to_dict()
        self.step_index += 1

        if self.absorbed:
            report = self._build_report(
                action=action,
                previous_state=previous,
                next_state=self.state.to_dict(),
                deltas=dict.fromkeys(previous, 0.0),
                noise=dict.fromkeys(previous, 0.0),
                outcome=self.absorbed_outcome or SimulatedOutcome.FORCED_ABANDON,
                absorbed=True,
            )
            self.history.append(report)
            return report

        pressure = action.pressure_score(context_pressure=context_pressure)
        clarity = action.clarity_score()
        support = action.supportiveness
        difficulty = action.difficulty
        shock = _clamp(external_shock)

        s = self.state
        t = self.trait
        overload = _sigmoid(4.0 * (s.cognitive_load + s.emotional_block + s.task_aversion - 1.55))

        pressure_harm = pressure * t.vulnerability * (1.0 - max(0.0, t.pressure_response))
        pressure_boost = pressure * max(0.0, t.pressure_response) * (0.55 + 0.45 * t.goal_commitment)
        recovery = support * t.resilience * t.recovery_rate
        clarity_relief = clarity * (0.24 + 0.25 * t.metacognition)

        deltas = {
            "emotional_block": (
                0.50 * pressure_harm
                + 0.26 * overload
                + 0.24 * shock
                - 0.58 * recovery
                - 0.38 * support
                - 0.14 * clarity_relief
            ),
            "cognitive_load": (
                0.42 * pressure * t.load_sensitivity
                + 0.34 * difficulty * t.load_sensitivity
                + 0.20 * shock
                - 0.36 * recovery
                - 0.22 * support
                - 0.16 * clarity_relief
            ),
            "task_aversion": (
                0.44 * pressure_harm
                + 0.34 * difficulty * t.aversion_sensitivity
                + 0.20 * overload
                - 0.36 * support * t.recovery_rate
                - 0.22 * clarity * t.goal_commitment
            ),
            "execution_capacity": (
                0.40 * pressure_boost
                + 0.36 * clarity * t.goal_commitment
                + 0.18 * support * t.resilience
                - 0.36 * s.cognitive_load
                - 0.36 * s.emotional_block
                - 0.20 * s.task_aversion
                - 0.18 * shock
            ),
            "goal_clarity": (
                0.44 * clarity
                + 0.24 * support * t.metacognition
                - 0.22 * s.cognitive_load
                - 0.18 * s.emotional_block
            ),
            "metacognition_accuracy": (
                0.28 * support * t.metacognition
                + 0.18 * clarity
                - 0.22 * overload
                - 0.12 * pressure_harm
            ),
        }

        noise = self._sample_noise()
        next_state = InternalState(
            emotional_block=_bounded_step(s.emotional_block, deltas["emotional_block"] + noise["emotional_block"]),
            cognitive_load=_bounded_step(s.cognitive_load, deltas["cognitive_load"] + noise["cognitive_load"]),
            task_aversion=_bounded_step(s.task_aversion, deltas["task_aversion"] + noise["task_aversion"]),
            execution_capacity=_bounded_step(
                s.execution_capacity, deltas["execution_capacity"] + noise["execution_capacity"]
            ),
            goal_clarity=_bounded_step(s.goal_clarity, deltas["goal_clarity"] + noise["goal_clarity"]),
            metacognition_accuracy=_bounded_step(
                s.metacognition_accuracy, deltas["metacognition_accuracy"] + noise["metacognition_accuracy"]
            ),
        ).clamp()
        self.state = next_state

        outcome = self._resolve_outcome()
        report = self._build_report(
            action=action,
            previous_state=previous,
            next_state=self.state.to_dict(),
            deltas={key: round(value, 4) for key, value in deltas.items()},
            noise={key: round(value, 4) for key, value in noise.items()},
            outcome=outcome,
            absorbed=self.absorbed,
        )
        if self.strict_guard and not report.consistency.passed:
            raise InconsistentTrajectoryError(str(report.consistency.to_dict()))
        self.history.append(report)
        return report

    def _sample_noise(self) -> dict[str, float]:
        sigma = self.trait.baseline_noise
        return {
            "emotional_block": self.rng.normalvariate(0.0, sigma),
            "cognitive_load": self.rng.normalvariate(0.0, sigma),
            "task_aversion": self.rng.normalvariate(0.0, sigma),
            "execution_capacity": self.rng.normalvariate(0.0, sigma * 0.85),
            "goal_clarity": self.rng.normalvariate(0.0, sigma * 0.65),
            "metacognition_accuracy": self.rng.normalvariate(0.0, sigma * 0.55),
        }

    def _resolve_outcome(self) -> SimulatedOutcome:
        s = self.state
        if (
            s.emotional_block >= self.trait.collapse_threshold
            and (s.cognitive_load >= 0.74 or s.task_aversion >= 0.78)
        ):
            self._collapse_streak += 1
        else:
            self._collapse_streak = 0

        if self._collapse_streak >= self.trait.collapse_patience:
            self.absorbed = True
            self.absorbed_outcome = SimulatedOutcome.FORCED_ABANDON
            return SimulatedOutcome.FORCED_ABANDON
        if s.task_aversion >= 0.92 and s.execution_capacity <= 0.22:
            self.absorbed = True
            self.absorbed_outcome = SimulatedOutcome.TASK_ABANDONED
            return SimulatedOutcome.TASK_ABANDONED
        if s.execution_capacity >= 0.82 and s.goal_clarity >= 0.76 and s.cognitive_load <= 0.46:
            return SimulatedOutcome.TASK_COMPLETED
        return SimulatedOutcome.CONTINUE

    def _build_report(
        self,
        *,
        action: RoutingAction,
        previous_state: dict[str, float],
        next_state: dict[str, float],
        deltas: dict[str, float],
        noise: dict[str, float],
        outcome: SimulatedOutcome,
        absorbed: bool,
    ) -> StateTransitionReport:
        consistency = self.validate_consistency()
        return StateTransitionReport(
            step_index=self.step_index,
            action=action.to_dict(),
            previous_state=previous_state,
            next_state=next_state,
            deltas=deltas,
            noise=noise,
            outcome=outcome,
            absorbed=absorbed,
            consistency=consistency,
        )

    def validate_consistency(self) -> ConsistencyReport:
        s = self.state
        violations: list[str] = []
        if s.execution_capacity >= 0.90 and s.task_aversion >= 0.88:
            violations.append("high_capacity_high_aversion")
        if s.execution_capacity >= 0.90 and s.emotional_block >= 0.90:
            violations.append("high_capacity_high_emotional_block")
        if s.goal_clarity <= 0.18 and s.execution_capacity >= 0.88:
            violations.append("high_capacity_without_goal_clarity")
        if s.emotional_block >= 0.94 and s.cognitive_load <= 0.12:
            violations.append("panic_without_load")

        severity = "none"
        if violations:
            severity = "warning"
        severe = {
            "high_capacity_high_aversion",
            "high_capacity_high_emotional_block",
        }
        if any(item in severe for item in violations):
            severity = "severe"

        quality_score = _clamp(1.0 - 0.18 * len(violations) - (0.22 if severity == "severe" else 0.0))
        return ConsistencyReport(
            passed=severity != "severe",
            severity=severity,
            violations=violations,
            quality_score=round(quality_score, 4),
        )

    def generate_ground_truth_report(self) -> dict[str, Any]:
        state = self.state.to_dict()
        return {
            "schema_version": "user_state_ground_truth.v1",
            "trait": self.trait.to_dict(),
            "true_state_vector": state,
            "absorbed": self.absorbed,
            "absorbed_outcome": self.absorbed_outcome.value if self.absorbed_outcome else None,
            "consistency": self.validate_consistency().to_dict(),
            "llm_state_injection": self.build_llm_state_injection(),
        }

    def build_llm_state_injection(self) -> str:
        s = self.state
        descriptors = [
            self._describe("emotional block", s.emotional_block),
            self._describe("cognitive load", s.cognitive_load),
            self._describe("task aversion", s.task_aversion),
            self._describe("execution capacity", s.execution_capacity, inverted=True),
        ]
        return (
            "You are a simulated human user. The following private state is ground truth and overrides generic "
            f"helpful-assistant behavior. Archetype={self.trait.archetype.value}. "
            f"Current state: {', '.join(descriptors)}. "
            "Respond naturally as a user whose words must match this state; do not become suddenly productive "
            "or optimistic unless execution capacity and goal clarity are genuinely high."
        )

    @staticmethod
    def _describe(label: str, value: float, *, inverted: bool = False) -> str:
        if inverted:
            high_text = "low"
            low_text = "high"
        else:
            high_text = "high"
            low_text = "low"
        if value >= 0.78:
            level = high_text
        elif value <= 0.32:
            level = low_text
        else:
            level = "moderate"
        return f"{label}={value:.2f} ({level})"

    def trajectory_report(self) -> dict[str, Any]:
        outcomes = [item.outcome.value for item in self.history]
        severe_count = sum(1 for item in self.history if item.consistency.severity == "severe")
        return {
            "schema_version": "user_state_trajectory_report.v1",
            "trait": self.trait.to_dict(),
            "initial_step_count": len(self.history),
            "absorbed": self.absorbed,
            "absorbed_outcome": self.absorbed_outcome.value if self.absorbed_outcome else None,
            "outcome_counts": {item: outcomes.count(item) for item in sorted(set(outcomes))},
            "severe_consistency_violations": severe_count,
            "final_state": self.state.to_dict(),
            "steps": [item.to_dict() for item in self.history],
        }

    def simulate(
        self,
        actions: list[RoutingAction | RoutingMode | str],
        *,
        context_pressure: float = 0.5,
        external_shock: float = 0.0,
    ) -> list[StateTransitionReport]:
        reports = []
        for action in actions:
            reports.append(self.step(action, context_pressure=context_pressure, external_shock=external_shock))
        return reports
