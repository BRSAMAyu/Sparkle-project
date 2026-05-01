from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import NormalDist
from collections.abc import Iterable, Sequence


_NORMAL = NormalDist()


@dataclass(frozen=True)
class CorrelationResult:
    dim_a: str
    dim_b: str
    r_value: float
    p_value_raw: float
    p_value_bh: float
    sample_days: int
    rank_pair_count: int
    density_insufficient: bool


def _materialize_pairs(
    xs: Sequence[float | None] | Iterable[float | None],
    ys: Sequence[float | None] | Iterable[float | None],
) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for left, right in zip(xs, ys, strict=False):
        if left is None or right is None:
            continue
        left_value = float(left)
        right_value = float(right)
        if math.isnan(left_value) or math.isnan(right_value):
            continue
        pairs.append((left_value, right_value))
    return pairs


def _average_ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        start = index
        current = ordered[index][1]
        while index < len(ordered) and ordered[index][1] == current:
            index += 1
        average_rank = (start + 1 + index) / 2.0
        for source_index, _ in ordered[start:index]:
            ranks[source_index] = average_rank
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    centered_x = [value - mean_x for value in xs]
    centered_y = [value - mean_y for value in ys]
    numerator = sum(left * right for left, right in zip(centered_x, centered_y, strict=False))
    denominator = math.sqrt(sum(value * value for value in centered_x) * sum(value * value for value in centered_y))
    if denominator <= 0:
        return 0.0
    return max(-1.0, min(1.0, numerator / denominator))


def spearman_rank_correlation(
    xs: Sequence[float | None] | Iterable[float | None],
    ys: Sequence[float | None] | Iterable[float | None],
) -> tuple[float, float, int]:
    pairs = _materialize_pairs(xs, ys)
    sample_days = len(pairs)
    if sample_days < 3:
        return 0.0, 1.0, sample_days

    left_values = [pair[0] for pair in pairs]
    right_values = [pair[1] for pair in pairs]
    left_ranks = _average_ranks(left_values)
    right_ranks = _average_ranks(right_values)
    r_value = _pearson(left_ranks, right_ranks)
    if abs(r_value) >= 0.999999:
        return round(r_value, 6), 0.0, sample_days
    fisher = 0.5 * math.log((1.0 + r_value) / (1.0 - r_value))
    z_score = abs(fisher) * math.sqrt(max(1.0, float(sample_days - 3)))
    p_value = max(0.0, min(1.0, 2.0 * (1.0 - _NORMAL.cdf(z_score))))
    return round(r_value, 6), round(p_value, 6), sample_days


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    if not p_values:
        return []
    indexed = sorted(enumerate(float(value) for value in p_values), key=lambda item: item[1])
    total = len(indexed)
    adjusted = [1.0] * total
    running = 1.0
    for reverse_index, (original_index, p_value) in enumerate(reversed(indexed), start=1):
        rank = total - reverse_index + 1
        candidate = min(1.0, (p_value * total) / max(1, rank))
        running = min(running, candidate)
        adjusted[original_index] = round(running, 6)
    return adjusted


def correlate_dimensions(
    series_by_dim: dict[str, Sequence[float | None]],
    *,
    density_min_rank_pairs: int = 150,
    density_min_coverage: float = 0.70,
) -> list[CorrelationResult]:
    dims = sorted(series_by_dim)
    pending: list[tuple[str, str, float, float, int, int, bool]] = []
    raw_p_values: list[float] = []
    window_size = max((len(values) for values in series_by_dim.values()), default=0)
    coverage_floor = math.ceil(window_size * density_min_coverage)

    for index, dim_a in enumerate(dims):
        for dim_b in dims[index + 1 :]:
            r_value, p_value, sample_days = spearman_rank_correlation(
                series_by_dim[dim_a],
                series_by_dim[dim_b],
            )
            rank_pair_count = math.comb(sample_days, 2) if sample_days >= 2 else 0
            density_insufficient = (
                rank_pair_count < density_min_rank_pairs
                or sample_days < coverage_floor
            )
            pending.append(
                (
                    dim_a,
                    dim_b,
                    r_value,
                    p_value,
                    sample_days,
                    rank_pair_count,
                    density_insufficient,
                )
            )
            raw_p_values.append(p_value)

    adjusted_p_values = benjamini_hochberg(raw_p_values)
    results: list[CorrelationResult] = []
    for (dim_a, dim_b, r_value, p_value, sample_days, rank_pair_count, density_insufficient), adjusted in zip(
        pending,
        adjusted_p_values,
        strict=False,
    ):
        results.append(
            CorrelationResult(
                dim_a=dim_a,
                dim_b=dim_b,
                r_value=r_value,
                p_value_raw=p_value,
                p_value_bh=adjusted,
                sample_days=sample_days,
                rank_pair_count=rank_pair_count,
                density_insufficient=density_insufficient,
            )
        )
    return results
