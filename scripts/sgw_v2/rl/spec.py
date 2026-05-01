"""MDP specification: state, action, reward, guardrails for SGW RL system.

Translates docs/sgw/04_mdp_formalization.md into executable Python types.
All Phase 1-8 code must use these types when interacting with the RL layer.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ──────────────────────────────────────────────────


class IterationOutcome(str, Enum):
    """Outcome of a single meta-iteration."""
    IMPROVED_SIG = "improved_sig"
    IMPROVED_NONSIG = "improved_nonsig"
    REGRESSED_SIG = "regressed_sig"
    REGRESSED_NONSIG = "regressed_nonsig"
    NEUTRAL = "neutral"
    PENDING = "pending"


class PolicyStage(str, Enum):
    """Current policy sophistication level."""
    RULE = "rule"                # Stage 1: deterministic rules
    BANDIT = "bandit"            # Stage 2: Thompson Sampling
    CONTEXTUAL = "contextual"    # Stage 3: LinUCB
    DPO = "dpo"                  # Stage 4: DPO-informed response strategy


class GuardrailId(str, Enum):
    """Identifiers for the four MDP guardrails."""
    CONFIG_HASH_COLLISION = "config_hash_collision"
    CONSECUTIVE_DIRECTION = "consecutive_direction"
    AMPLITUDE_CLAMP = "amplitude_clamp"
    FORCED_EXPLORATION = "forced_exploration"


class EpisodeTerminationReason(str, Enum):
    """Why an episode ended."""
    CONVERGENCE = "convergence"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CRITICAL_REGRESSION = "critical_regression"
    HARD_VIOLATION = "hard_violation"


# ── State ──────────────────────────────────────────────────


@dataclass
class RunContext:
    """Run-level metadata (part of State s_t)."""
    scenario_id: str
    config_hash: str
    iteration_number: int = 0
    turns_completed: int = 0
    sessions_completed: int = 0


@dataclass
class PopulationStats:
    """Aggregated metrics from a completed run (part of State s_t)."""
    soft_violation_rate: float = 0.0
    hard_violations: int = 0
    authenticity_mean: float = 0.0
    authenticity_failure_rate: float = 0.0
    session_completion_rate: float = 0.0
    avg_turns_per_session: float = 0.0

    def to_vector(self) -> list[float]:
        """Convert to feature vector for contextual bandit."""
        return [
            self.soft_violation_rate,
            self.authenticity_mean,
            self.authenticity_failure_rate,
            self.session_completion_rate,
            self.avg_turns_per_session,
        ]


@dataclass
class FailureSignal:
    """Latest diagnostic results (part of State s_t)."""
    active_hypotheses: list[str] = field(default_factory=list)
    critical_alerts: int = 0
    last_outcome: IterationOutcome = IterationOutcome.NEUTRAL


@dataclass
class StateVector:
    """Complete MDP state s_t = (run_context, population_stats, failure_signal)."""
    run_context: RunContext
    population_stats: PopulationStats
    failure_signal: FailureSignal = field(default_factory=FailureSignal)

    def to_feature_vector(self) -> list[float]:
        """Full feature vector for contextual bandit input φ(s_t)."""
        stats_vec = self.population_stats.to_vector()
        context_vec = [
            float(self.run_context.iteration_number),
            float(self.failure_signal.critical_alerts),
            1.0 if self.failure_signal.last_outcome == IterationOutcome.REGRESSED_SIG else 0.0,
            1.0 if self.failure_signal.last_outcome == IterationOutcome.IMPROVED_SIG else 0.0,
        ]
        return stats_vec + context_vec


# ── Action ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ActionSpec:
    """Definition of a single adjustable parameter."""
    parameter: str
    param_type: str               # "float" | "int"
    range_min: float
    range_max: float
    step_size: float              # allowed increment
    default: float
    bandit_arm: bool = True       # whether this param has bandit arms


# Complete parameter table from 04_mdp_formalization.md Section 3
ACTION_SPECS: dict[str, ActionSpec] = {
    "soft_violation_threshold": ActionSpec(
        parameter="soft_violation_threshold",
        param_type="float",
        range_min=0.80, range_max=0.95,
        step_size=0.05, default=0.85,
    ),
    "audit_sample_rate": ActionSpec(
        parameter="audit_sample_rate",
        param_type="float",
        range_min=0.10, range_max=0.50,
        step_size=0.05, default=0.25,
    ),
    "authenticity_sample_rate": ActionSpec(
        parameter="authenticity_sample_rate",
        param_type="float",
        range_min=0.10, range_max=0.50,
        step_size=0.10, default=0.20,
    ),
    "turn_target": ActionSpec(
        parameter="turn_target",
        param_type="int",
        range_min=8, range_max=20,
        step_size=2, default=12,
    ),
    "claude_timeout_seconds": ActionSpec(
        parameter="claude_timeout_seconds",
        param_type="int",
        range_min=30, range_max=120,
        step_size=15, default=45,
    ),
    "claude_failure_backoff_seconds": ActionSpec(
        parameter="claude_failure_backoff_seconds",
        param_type="int",
        range_min=10, range_max=120,
        step_size=10, default=30,
    ),
    "expression_validation_retries": ActionSpec(
        parameter="expression_validation_retries",
        param_type="int",
        range_min=0, range_max=5,
        step_size=1, default=2,
    ),
    "max_history_pairs": ActionSpec(
        parameter="max_history_pairs",
        param_type="int",
        range_min=2, range_max=10,
        step_size=2, default=6,
    ),
    "session_turn_slice": ActionSpec(
        parameter="session_turn_slice",
        param_type="int",
        range_min=1, range_max=3,
        step_size=1, default=1,
    ),
}

# Parameters that require human approval to change
PROTECTED_PARAMETERS: set[str] = {
    "websocket_url", "api_base_url", "llm_provider", "api_model",
    "random_seed", "wall_clock_hours", "min_sessions", "min_turns",
    "soft_violation_rate_limit", "authenticity_threshold",
}

# Bandit arms: (parameter_name, direction) where direction = +1 or -1
# 9 parameters × 2 directions = 18 arms
BANDIT_ARMS: list[tuple[str, int]] = [
    (spec.parameter, direction)
    for spec in ACTION_SPECS.values()
    if spec.bandit_arm
    for direction in (+1, -1)
]


@dataclass
class Action:
    """A concrete action: parameter adjustments to apply."""
    changes: dict[str, float]    # {parameter_name: new_value}
    source: PolicyStage          # which policy produced this action
    exploration: bool = False    # was this a forced exploration?

    def to_dict(self) -> dict[str, Any]:
        return {
            "changes": self.changes,
            "source": self.source.value,
            "exploration": self.exploration,
        }

    @property
    def parameter_count(self) -> int:
        return len(self.changes)


@dataclass
class StrategyRecommendation:
    """Output of DPO policy: recommended response strategy for current context."""
    recommended_behavior: str              # AIBehaviorClass value
    confidence: float = 0.5                # [0, 1]
    strategy_scores: dict[str, float] = field(default_factory=dict)
    context_vector: list[float] = field(default_factory=list)
    source: str = "dpo"

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_behavior": self.recommended_behavior,
            "confidence": self.confidence,
            "strategy_scores": self.strategy_scores,
            "source": self.source,
        }

# ── Reward ─────────────────────────────────────────────────


@dataclass(frozen=True)
class RewardWeights:
    """Weights for the multi-dimensional reward function."""
    w_soft: float = 0.30
    w_auth: float = 0.35
    w_hard: float = 0.20
    w_session: float = 0.10
    w_diversity: float = 0.05


DEFAULT_REWARD_WEIGHTS = RewardWeights()

# Reward scaling for tanh normalization
REWARD_SCALE: float = 0.3


@dataclass
class RewardSignal:
    """Computed reward for one iteration."""
    raw_reward: float
    normalized_reward: float     # tanh(raw / REWARD_SCALE)
    components: dict[str, float] # individual dimension rewards
    veto_applied: bool = False   # was a one-vote veto triggered?
    veto_reason: str | None = None


# ── Episode ────────────────────────────────────────────────


@dataclass
class EpisodeConfig:
    """Configuration for a single RL episode."""
    max_iterations: int = 20
    convergence_window: int = 5
    explore_every_n: int = 10
    critical_regression_limit: int = 2  # consecutive regressed_sig before abort
    policy_stage: PolicyStage = PolicyStage.RULE
    reward_weights: RewardWeights = field(default_factory=RewardWeights)


@dataclass
class EpisodeResult:
    """Result of a completed episode."""
    total_reward: float
    iterations_used: int
    initial_metrics: PopulationStats
    final_metrics: PopulationStats
    termination_reason: EpisodeTerminationReason
    policy_stage: PolicyStage
    iteration_history: list[dict[str, Any]] = field(default_factory=list)


# ── Guardrails ─────────────────────────────────────────────


def compute_config_hash(config: dict[str, Any]) -> str:
    """Deterministic SHA-256 hash of configuration."""
    serialized = json.dumps(config, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def check_config_novelty(new_hash: str, recent_hashes: list[str]) -> bool:
    """Guardrail 1: reject config that duplicates a recent iteration."""
    return new_hash not in recent_hashes


def check_direction_history(
    parameter: str,
    direction: float,
    history: list[dict[str, Any]],
    window: int = 3,
) -> bool:
    """Guardrail 2: reject if same parameter moved same direction N times in a row.

    Supports two history encodings used across the RL layer:
      1) Flat: entry["changes"] = {param: new_value} — direction is inferred
         by diffing against the preceding entry's config_after or changes.
      2) Nested: entry["changes"] = {param: {"previous": x, "current": y}}

    Returns True if the action is ALLOWED (no violation).
    """
    recent: list[int] = []
    # Walk from oldest→newest so we can use prior entries as the baseline.
    prior_value: float | None = None
    tail = history[-(window + 1):] if len(history) > window else history
    for entry in tail:
        changes = entry.get("changes", {}) or {}
        config_after = entry.get("config_after", {}) or {}

        if parameter in changes:
            raw = changes[parameter]
            if isinstance(raw, dict) and "previous" in raw and "current" in raw:
                prev_val = float(raw["previous"])
                curr_val = float(raw["current"])
            else:
                curr_val = float(raw)
                prev_val = float(prior_value) if prior_value is not None else curr_val
            delta = curr_val - prev_val
            if delta != 0:
                recent.append(1 if delta > 0 else -1)
            prior_value = curr_val
        elif parameter in config_after:
            prior_value = float(config_after[parameter])

    # Only the last `window` direction changes matter for the guardrail.
    recent = recent[-window:]
    if len(recent) >= window:
        return not all(d == direction for d in recent)
    return True


def clamp_amplitude(
    parameter: str,
    current_value: float,
    proposed_value: float,
) -> float:
    """Guardrail 3: clamp single-iteration change to 15% of range or step_size (whichever is larger).

    For int parameters the result is coerced back to int so downstream config
    consumers that expect ints (e.g. turn_target, claude_timeout_seconds) never
    receive floats from the guardrail layer.
    """
    spec = ACTION_SPECS.get(parameter)
    if spec is None:
        return proposed_value  # Unknown parameter, pass through

    range_size = spec.range_max - spec.range_min
    # Spec step_size represents the smallest meaningful unit of change;
    # 15% of range is the hard safety cap. Use the larger so one step is always allowed.
    max_step = max(range_size * 0.15, spec.step_size)
    delta = proposed_value - current_value

    # Clamp delta
    delta = max(-max_step, min(max_step, delta))

    # Apply and clamp to valid range
    result = current_value + delta
    result = max(spec.range_min, min(spec.range_max, result))

    if spec.param_type == "int":
        # Round toward current_value to avoid runaway bias, then re-clamp
        rounded = int(round(result))
        return max(int(spec.range_min), min(int(spec.range_max), rounded))
    return result


def should_explore(iteration_number: int, explore_every: int = 10) -> bool:
    """Guardrail 4: force random exploration every N iterations."""
    return iteration_number > 0 and iteration_number % explore_every == 0


# ── State helpers ──────────────────────────────────────────


def state_from_summary(
    summary: dict[str, Any],
    scenario_id: str = "",
    config_hash: str = "",
    iteration_number: int = 0,
    active_hypotheses: list[str] | None = None,
    critical_alerts: int = 0,
    last_outcome: IterationOutcome = IterationOutcome.NEUTRAL,
) -> StateVector:
    """Construct StateVector from RunDB.run_summary() output."""
    sessions_total = summary.get("sessions_total", 0) or 1
    sessions_completed = summary.get("sessions_completed", 0)

    return StateVector(
        run_context=RunContext(
            scenario_id=scenario_id,
            config_hash=config_hash,
            iteration_number=iteration_number,
            turns_completed=summary.get("turns_total", 0),
            sessions_completed=sessions_completed,
        ),
        population_stats=PopulationStats(
            soft_violation_rate=summary.get("soft_violation_rate", 0.0),
            hard_violations=summary.get("hard_violations", 0),
            authenticity_mean=summary.get("authenticity_mean", 0.0),
            authenticity_failure_rate=(
                summary.get("authenticity_failures", 0)
                / max(summary.get("authenticity_total", 1), 1)
            ),
            session_completion_rate=sessions_completed / max(sessions_total, 1),
            avg_turns_per_session=(
                summary.get("turns_total", 0) / max(sessions_completed, 1)
            ),
        ),
        failure_signal=FailureSignal(
            active_hypotheses=active_hypotheses or [],
            critical_alerts=critical_alerts,
            last_outcome=last_outcome,
        ),
    )


def validate_action(action: Action) -> list[str]:
    """Validate an action against all constraints. Returns list of violations."""
    violations: list[str] = []

    # Constraint: max 3 parameters per action
    if action.parameter_count > 3:
        violations.append(f"Too many parameters: {action.parameter_count} > 3")

    for param, value in action.changes.items():
        spec = ACTION_SPECS.get(param)
        if spec is None:
            violations.append(f"Unknown parameter: {param}")
            continue

        # Range check
        if value < spec.range_min or value > spec.range_max:
            violations.append(
                f"{param}={value} out of range [{spec.range_min}, {spec.range_max}]"
            )

        # Protected parameter check
        if param in PROTECTED_PARAMETERS:
            violations.append(f"Protected parameter requires human approval: {param}")

    return violations
