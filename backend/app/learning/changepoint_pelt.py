from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Sequence


@dataclass(frozen=True)
class ChangePointResult:
    index: int
    confidence: float


def _segment_cost(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean_value = sum(values) / len(values)
    return sum((value - mean_value) ** 2 for value in values)


def detect_change_points(
    values: Sequence[float],
    *,
    min_segment_size: int = 7,
    penalty: float = 0.8,
) -> list[ChangePointResult]:
    length = len(values)
    if length < min_segment_size * 2:
        return []

    dp = [math.inf] * (length + 1)
    back = [-1] * (length + 1)
    dp[0] = -penalty

    for end in range(min_segment_size, length + 1):
        for start in range(0, end - min_segment_size + 1):
            segment = values[start:end]
            if len(segment) < min_segment_size:
                continue
            if start and (end - start) < min_segment_size:
                continue
            candidate = dp[start] + _segment_cost(segment) + penalty
            if candidate < dp[end]:
                dp[end] = candidate
                back[end] = start

    indices: list[int] = []
    cursor = length
    while cursor > 0 and back[cursor] >= 0:
        start = back[cursor]
        if start == 0:
            break
        indices.append(start)
        cursor = start
    indices.sort()

    results: list[ChangePointResult] = []
    for index in indices:
        before = values[max(0, index - min_segment_size) : index]
        after = values[index : min(length, index + min_segment_size)]
        if len(before) < min_segment_size or len(after) < min_segment_size:
            continue
        mean_shift = abs((sum(after) / len(after)) - (sum(before) / len(before)))
        pooled = math.sqrt((_segment_cost(before) + _segment_cost(after)) / max(1, len(before) + len(after)))
        normalized = mean_shift / max(0.05, pooled)
        confidence = min(0.8, round(0.3 + (normalized * 0.2), 4))
        if confidence < 0.35:
            continue
        results.append(ChangePointResult(index=index, confidence=confidence))
    return results
