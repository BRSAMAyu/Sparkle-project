"""
Shared helpers for recency-weighted signal aggregation and hysteresis.
"""
from __future__ import annotations

import math
from collections.abc import Hashable, Iterable
from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def recency_weight(
    observed_at: datetime | None,
    *,
    now: datetime | None = None,
    half_life_days: float = 7.0,
    min_weight: float = 0.2,
) -> float:
    ts = _normalize_timestamp(observed_at)
    if ts is None:
        return min_weight

    current = _normalize_timestamp(now) or _utcnow()
    age_seconds = max((current - ts).total_seconds(), 0.0)
    age_days = age_seconds / 86400.0
    effective_half_life = max(half_life_days, 0.1)
    weight = math.pow(0.5, age_days / effective_half_life)
    return max(min_weight, min(1.0, weight))


def weighted_average(values: Iterable[tuple[float, float]]) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for value, weight in values:
        if weight <= 0:
            continue
        numerator += value * weight
        denominator += weight
    if denominator <= 0:
        return None
    return numerator / denominator


def weighted_median(values: Iterable[tuple[float, float]]) -> float | None:
    weighted_values = sorted(
        (float(value), float(weight))
        for value, weight in values
        if weight > 0
    )
    if not weighted_values:
        return None

    total_weight = sum(weight for _, weight in weighted_values)
    threshold = total_weight / 2.0
    cumulative = 0.0
    for value, weight in weighted_values:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return weighted_values[-1][0]


def weighted_counts(
    items: Iterable[tuple[Hashable, float]],
) -> dict[Hashable, float]:
    counts: dict[Hashable, float] = {}
    for key, weight in items:
        if weight <= 0:
            continue
        counts[key] = counts.get(key, 0.0) + weight
    return counts


def normalize_counts(counts: dict[Hashable, float]) -> dict[Hashable, float]:
    total = sum(max(value, 0.0) for value in counts.values())
    if total <= 0:
        return {}
    return {
        key: value / total
        for key, value in counts.items()
        if value > 0
    }


def pick_with_hysteresis(
    scores: dict[Hashable, float],
    previous: Hashable | None,
    *,
    margin: float = 0.08,
) -> Hashable | None:
    if not scores:
        return previous

    ordered = sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))
    winner, winner_score = ordered[0]
    if previous in scores and winner != previous:
        previous_score = float(scores.get(previous) or 0.0)
        if winner_score - previous_score < margin:
            return previous
    return winner


def classify_band_with_hysteresis(
    value: float,
    previous: str | None,
    *,
    low_enter: float,
    high_enter: float,
    low_exit: float | None = None,
    high_exit: float | None = None,
    low_label: str,
    mid_label: str,
    high_label: str,
) -> str:
    if previous == high_label and high_exit is not None and value >= high_exit:
        return high_label
    if previous == low_label and low_exit is not None and value <= low_exit:
        return low_label
    if value >= high_enter:
        return high_label
    if value <= low_enter:
        return low_label
    return mid_label
