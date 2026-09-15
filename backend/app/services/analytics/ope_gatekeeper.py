from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

POSITIVE_SIGNAL_TYPES = {
    "task.completed",
    "task_feedback.positive",
    "explicit.gratitude",
    "user_correction.resolved",
}
NEGATIVE_SIGNAL_TYPES = {
    "task.abandoned",
    "task_feedback.negative",
    "explicit.complaint",
    "user_correction.filed",
    "session.timeout",
}
EXCLUDED_SIGNAL_TYPES = {
    "unknown",
    "no_negative_followup_signal",
}


def _loads(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _actual_mode(trace: dict[str, Any]) -> str | None:
    mode = trace.get("actual_router_mode")
    if mode:
        return str(mode)
    snapshot = trace.get("router_snapshot")
    if isinstance(snapshot, dict) and snapshot.get("actual_router_mode"):
        return str(snapshot["actual_router_mode"])
    action = trace.get("action_taken")
    if isinstance(action, dict) and action.get("mode"):
        return str(action["mode"])
    return None


def _shadow_mode(trace: dict[str, Any]) -> str | None:
    projection = trace.get("router_shadow_projection")
    if isinstance(projection, dict) and projection.get("shadow_mode"):
        return str(projection["shadow_mode"])
    return None


def _mode_rank(mode: str) -> int:
    return {
        "cognitive_first": 0,
        "balanced": 1,
        "execution_first": 2,
    }.get(mode, 1)


def _one_sided_binomial_p_value(*, successes: int, trials: int, p0: float = 0.5) -> float:
    if trials <= 0 or successes < 0 or successes > trials:
        return 1.0
    probability = 0.0
    for value in range(successes, trials + 1):
        probability += math.comb(trials, value) * (p0**value) * ((1.0 - p0) ** (trials - value))
    return min(1.0, max(0.0, probability))


@dataclass(frozen=True)
class DivergenceOutcomePoint:
    trace_id: str | None
    actual_mode: str
    shadow_mode: str
    winner: str
    signal_type: str
    reward: float
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OPEGateReport:
    total_traces: int
    comparable_traces: int
    divergence_points: int
    labeled_divergence_points: int
    shadow_wins: int
    production_wins: int
    ties: int
    shadow_win_rate: float
    shadow_p_value: float
    production_p_value: float
    recommendation: str
    blockers: list[str] = field(default_factory=list)
    disagreement_type_counts: dict[str, int] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ope_gatekeeper.v1",
            "total_traces": self.total_traces,
            "comparable_traces": self.comparable_traces,
            "divergence_points": self.divergence_points,
            "labeled_divergence_points": self.labeled_divergence_points,
            "shadow_wins": self.shadow_wins,
            "production_wins": self.production_wins,
            "ties": self.ties,
            "shadow_win_rate": self.shadow_win_rate,
            "shadow_p_value": self.shadow_p_value,
            "production_p_value": self.production_p_value,
            "recommendation": self.recommendation,
            "blockers": self.blockers,
            "disagreement_type_counts": self.disagreement_type_counts,
            "examples": self.examples,
            "caveat": (
                "This is a disagreement-bound proxy gate over observed outcomes, not a causal counterfactual estimate."
            ),
        }


class OPEGatekeeper:
    """Offline policy gate over real, outcome-labeled disagreement traces."""

    def __init__(
        self,
        *,
        min_labeled_divergence: int = 50,
        alpha: float = 0.05,
    ) -> None:
        self.min_labeled_divergence = min_labeled_divergence
        self.alpha = alpha

    def evaluate(self, raw_traces: list[Any]) -> OPEGateReport:
        total = len(raw_traces)
        comparable = 0
        divergences = 0
        points: list[DivergenceOutcomePoint] = []
        type_counts: Counter[str] = Counter()

        for raw in raw_traces:
            trace = _loads(raw)
            if trace is None:
                continue
            actual = _actual_mode(trace)
            shadow = _shadow_mode(trace)
            if not actual or not shadow:
                continue
            comparable += 1
            if actual == shadow:
                continue
            divergences += 1
            type_counts[self._disagreement_type(actual, shadow)] += 1
            point = self._labeled_point(trace, actual, shadow)
            if point is not None:
                points.append(point)

        shadow_wins = sum(1 for point in points if point.winner == "shadow")
        production_wins = sum(1 for point in points if point.winner == "production")
        ties = sum(1 for point in points if point.winner == "tie")
        decisive = shadow_wins + production_wins
        shadow_rate = shadow_wins / decisive if decisive else 0.0
        shadow_p = _one_sided_binomial_p_value(successes=shadow_wins, trials=decisive)
        production_p = _one_sided_binomial_p_value(successes=production_wins, trials=decisive)
        blockers: list[str] = []
        if comparable == 0:
            blockers.append("no_actual_shadow_comparable_traces")
        if divergences == 0:
            blockers.append("no_disagreement_points")
        if decisive < self.min_labeled_divergence:
            blockers.append("insufficient_labeled_divergence_points")

        if blockers:
            recommendation = "continue_shadow_collection"
        elif shadow_rate > 0.5 and shadow_p < self.alpha:
            recommendation = "enable_belief_router_candidate"
        elif production_wins / decisive > 0.5 and production_p < self.alpha:
            recommendation = "keep_current_router_and_debug_belief_signals"
        elif decisive >= 200 and abs(shadow_rate - 0.5) <= 0.03:
            recommendation = "functionally_equivalent_cutover_optional_for_observability"
        else:
            recommendation = "continue_shadow_collection"

        return OPEGateReport(
            total_traces=total,
            comparable_traces=comparable,
            divergence_points=divergences,
            labeled_divergence_points=len(points),
            shadow_wins=shadow_wins,
            production_wins=production_wins,
            ties=ties,
            shadow_win_rate=round(shadow_rate, 4),
            shadow_p_value=round(shadow_p, 6),
            production_p_value=round(production_p, 6),
            recommendation=recommendation,
            blockers=blockers,
            disagreement_type_counts=dict(type_counts),
            examples=[point.to_dict() for point in points[:10]],
        )

    def _labeled_point(self, trace: dict[str, Any], actual: str, shadow: str) -> DivergenceOutcomePoint | None:
        reward = trace.get("reward")
        if not isinstance(reward, dict):
            return None
        signal_type = str(reward.get("signal_type") or "unknown")
        if signal_type in EXCLUDED_SIGNAL_TYPES or bool(reward.get("is_censored")):
            return None
        try:
            total_reward = float(reward.get("total_reward"))
        except (TypeError, ValueError):
            return None
        if signal_type in POSITIVE_SIGNAL_TYPES or total_reward > 0:
            winner = "production"
            basis = "actual_action_led_to_positive_observed_outcome"
        elif signal_type in NEGATIVE_SIGNAL_TYPES or total_reward < 0:
            winner = "shadow"
            basis = "actual_action_led_to_negative_observed_outcome"
        else:
            winner = "tie"
            basis = "neutral_or_unclassifiable_observed_outcome"

        # If both modes are on the same side of balanced, the proxy is weaker.
        if abs(_mode_rank(actual) - _mode_rank(shadow)) == 1 and abs(total_reward) < 0.15:
            winner = "tie"
            basis = "small_reward_adjacent_mode_difference"

        return DivergenceOutcomePoint(
            trace_id=str(trace.get("trace_id")) if trace.get("trace_id") is not None else None,
            actual_mode=actual,
            shadow_mode=shadow,
            winner=winner,
            signal_type=signal_type,
            reward=round(total_reward, 4),
            basis=basis,
        )

    @staticmethod
    def _disagreement_type(actual: str, shadow: str) -> str:
        if actual == "execution_first" and shadow == "cognitive_first":
            return "type_1_over_hard"
        if actual == "cognitive_first" and shadow == "execution_first":
            return "type_2_over_support"
        if shadow == "balanced":
            return "shadow_balanced"
        if actual == "balanced":
            return "actual_balanced"
        return "other"
