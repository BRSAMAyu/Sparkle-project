from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any


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


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _reward_value(trace: dict[str, Any]) -> float | None:
    reward = trace.get("reward")
    if not isinstance(reward, dict):
        return None
    if reward.get("is_censored"):
        return None
    signal_type = str(reward.get("signal_type") or "unknown")
    if signal_type in {"unknown", "no_negative_followup_signal"}:
        return None
    try:
        return float(reward.get("total_reward") or 0.0)
    except (TypeError, ValueError):
        return None


def _belief_means_vector(trace: dict[str, Any]) -> tuple[float, ...] | None:
    bsv = trace.get("belief_state_vector")
    if not isinstance(bsv, dict):
        return None
    targets = [
        "emotional_block", "task_aversion", "cognitive_load",
        "goal_clarity", "execution_capacity", "metacognition_accuracy",
        "system_dissatisfaction",
    ]
    values: list[float] = []
    for target in targets:
        if f"{target}_mean" in bsv:
            values.append(round(_as_float(bsv.get(f"{target}_mean"), default=0.5), 4))
            continue
        entry = bsv.get(target)
        values.append(round(_as_float(entry.get("mean"), default=0.5), 4) if isinstance(entry, dict) else 0.5)
    return tuple(values)


def _belief_bucket(vector: tuple[float, ...]) -> str:
    support_pressure = vector[0] + vector[1] + vector[2] + vector[6]
    execution_readiness = vector[3] + vector[4] - vector[0] - vector[1]
    if support_pressure > 2.4:
        return "high_support_need"
    if execution_readiness > 1.2:
        return "high_execution_ready"
    if support_pressure >= 2.0:
        return "mixed_lean_support"
    if execution_readiness >= 0.6:
        return "mixed_lean_execution"
    return "neutral"


def _wilson_interval(successes: int, total: int, *, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial positive-rate estimate."""
    if total <= 0:
        return 0.0, 0.0
    p_hat = successes / total
    denominator = 1.0 + z * z / total
    center = (p_hat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p_hat * (1.0 - p_hat) + z * z / (4 * total)) / total) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


@dataclass(frozen=True)
class BucketOutcomeCell:
    bucket: str
    mode: str
    count: int
    mean_reward: float
    positive_rate: float
    positive_rate_ci_low: float
    positive_rate_ci_high: float
    std_reward: float
    min_effective_n: int = 10
    interval_method: str = "wilson_95"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModeQualityByBucket:
    bucket: str
    mode_results: dict[str, BucketOutcomeCell]
    detectable_difference: bool
    best_mode: str
    worst_mode: str
    effect_size: float
    sufficient_data: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "bucket": self.bucket,
            "mode_results": {key: value.to_dict() for key, value in self.mode_results.items()},
            "detectable_difference": self.detectable_difference,
            "best_mode": self.best_mode,
            "worst_mode": self.worst_mode,
            "effect_size": round(self.effect_size, 6),
            "sufficient_data": self.sufficient_data,
        }


@dataclass(frozen=True)
class AbsoluteQualityReport:
    total_labeled_traces: int
    bucket_count: int
    buckets: list[ModeQualityByBucket]
    overall_detectable: bool
    overall_effect_size: float
    router_leverage_assessment: str
    recommendation: str
    blockers: list[str] = field(default_factory=list)
    methodology: str = (
        "Stratify traces by discretized belief-state region; within each region, "
        "compare observed outcome rewards across the three routing modes. "
        "If no mode-detected outcome difference exists across most regions, "
        "the router decision itself may have limited leverage over user outcomes."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "router_absolute_quality.v1",
            "total_labeled_traces": self.total_labeled_traces,
            "bucket_count": self.bucket_count,
            "buckets": [bucket.to_dict() for bucket in self.buckets],
            "overall_detectable": self.overall_detectable,
            "overall_effect_size": round(self.overall_effect_size, 6),
            "router_leverage_assessment": self.router_leverage_assessment,
            "recommendation": self.recommendation,
            "blockers": self.blockers,
            "methodology": self.methodology,
        }


class RouterAbsoluteQualityAnalyzer:
    """Measure whether routing mode choice has ANY effect on outcomes.

    This is orthogonal to OPE. OPE compares new Router vs old Router.
    This asks: within a fixed belief-state region, does the Router's mode
    choice produce measurably different user outcomes?

    If the answer is NO across most regions, the entire routing architecture
    may have lower leverage than expected — regardless of which Router wins.
    """

    def __init__(
        self,
        *,
        min_labeled_per_cell: int = 8,
        min_mode_samples: int = 3,
        detectable_effect_min: float = 0.12,
    ) -> None:
        self.min_labeled_per_cell = min_labeled_per_cell
        self.min_mode_samples = min_mode_samples
        self.detectable_effect_min = detectable_effect_min

    def evaluate(self, raw_traces: list[Any]) -> AbsoluteQualityReport:
        cells: dict[tuple[str, str], list[float]] = defaultdict(list)
        for raw in raw_traces:
            trace = _loads(raw)
            if trace is None:
                continue
            mode = _actual_mode(trace)
            if mode is None:
                continue
            reward = _reward_value(trace)
            if reward is None:
                continue
            vector = _belief_means_vector(trace)
            if vector is None:
                continue
            bucket = _belief_bucket(vector)
            cells[(bucket, mode)].append(reward)

        buckets: list[ModeQualityByBucket] = []
        bucket_order = [
            "high_support_need", "mixed_lean_support", "neutral",
            "mixed_lean_execution", "high_execution_ready",
        ]
        detectable_count = 0
        total_effect = 0.0
        for bucket in bucket_order:
            mode_results: dict[str, BucketOutcomeCell] = {}
            for mode in ("execution_first", "balanced", "cognitive_first"):
                rewards = cells.get((bucket, mode), [])
                n = len(rewards)
                mean_reward = sum(rewards) / n if n else 0.0
                positive = sum(1 for r in rewards if r > 0)
                ci_low, ci_high = _wilson_interval(positive, n)
                std = math.sqrt(
                    sum((r - mean_reward) ** 2 for r in rewards) / n
                ) if n > 1 else 0.0
                mode_results[mode] = BucketOutcomeCell(
                    bucket=bucket,
                    mode=mode,
                    count=n,
                    mean_reward=round(mean_reward, 4),
                    positive_rate=round(positive / n, 4) if n else 0.0,
                    positive_rate_ci_low=round(ci_low, 4),
                    positive_rate_ci_high=round(ci_high, 4),
                    std_reward=round(std, 4),
                )

            sufficient = (
                sum(1 for c in mode_results.values() if c.count >= self.min_mode_samples) >= 2
                and sum(c.count for c in mode_results.values()) >= self.min_labeled_per_cell
            )

            means = [c.mean_reward for c in mode_results.values()]
            max_mean = max(means)
            min_mean = min(means)
            effect = max_mean - min_mean

            best = max(mode_results, key=lambda m: mode_results[m].mean_reward)
            worst = min(mode_results, key=lambda m: mode_results[m].mean_reward)

            detectable = effect >= self.detectable_effect_min and sufficient
            if detectable:
                detectable_count += 1
            total_effect += effect

            buckets.append(ModeQualityByBucket(
                bucket=bucket,
                mode_results=mode_results,
                detectable_difference=detectable,
                best_mode=best,
                worst_mode=worst,
                effect_size=effect,
                sufficient_data=sufficient,
            ))

        avg_effect = total_effect / len(buckets) if buckets else 0.0
        overall_detectable = detectable_count >= 3
        blockers: list[str] = []

        if not buckets or sum(sum(c.count for c in b.mode_results.values()) for b in buckets) == 0:
            blockers.append("no_labeled_traces_with_belief_vectors")
        if sum(1 for b in buckets if b.sufficient_data) < 2:
            blockers.append("insufficient_data_across_buckets")

        if overall_detectable:
            leverage = "high"
            recommendation = "router_mode_has_measurable_impact_on_outcomes"
        elif detectable_count >= 1:
            leverage = "moderate"
            recommendation = "router_impact_present_in_limited_regions_expand_or_redesign"
        elif [b for b in buckets if b.sufficient_data]:
            leverage = "low"
            recommendation = "router_mode_shows_low_leverage_consider_redesign_or_wider_strategy_space"
        else:
            leverage = "indeterminate"
            recommendation = "collect_more_labeled_traces"

        return AbsoluteQualityReport(
            total_labeled_traces=sum(sum(c.count for c in b.mode_results.values()) for b in buckets),
            bucket_count=len(buckets),
            buckets=buckets,
            overall_detectable=overall_detectable,
            overall_effect_size=avg_effect,
            router_leverage_assessment=leverage,
            recommendation=recommendation,
            blockers=blockers,
        )
