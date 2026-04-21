"""Changepoint detection: CUSUM and sliding-window variance for metric shifts.

Detects when SGW metrics shift significantly within or across runs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Changepoint:
    """A detected changepoint in metric trajectory."""
    index: int                  # position in the sequence
    metric: str                 # which metric shifted
    direction: str              # "up" | "down"
    magnitude: float            # size of shift
    confidence: float           # 0-1, detection confidence
    context: dict[str, Any] = field(default_factory=dict)


class CUSUMDetector:
    """CUSUM (Cumulative Sum) changepoint detector.

    Detects upward and downward shifts in a metric sequence.
    Non-parametric: only requires the sequence and a target mean.
    """

    def __init__(self, *, threshold: float = 5.0, drift: float = 0.5, min_window: int = 5):
        self.threshold = threshold    # alarm threshold
        self.drift = drift            # allowable drift before accumulating
        self.min_window = min_window  # minimum observations before detection

    def detect(
        self,
        sequence: list[float],
        metric: str = "",
        baseline_mean: float | None = None,
    ) -> list[Changepoint]:
        """Run CUSUM on a sequence of metric values.

        If baseline_mean is None, uses the first min_window values as baseline.
        """
        if len(sequence) < self.min_window * 2:
            return []

        if baseline_mean is None:
            baseline_mean = sum(sequence[:self.min_window]) / self.min_window

        if baseline_mean == 0:
            baseline_mean = 1e-6  # avoid div-by-zero

        # Normalize by baseline to make threshold scale-independent
        normalized = [(v - baseline_mean) / abs(baseline_mean) for v in sequence]

        cusum_pos = 0.0
        cusum_neg = 0.0
        changepoints: list[Changepoint] = []

        for i, val in enumerate(normalized):
            cusum_pos = max(0, cusum_pos + val - self.drift)
            cusum_neg = max(0, cusum_neg - val - self.drift)

            if i < self.min_window:
                continue

            if cusum_pos > self.threshold:
                magnitude = sequence[i] - baseline_mean
                changepoints.append(Changepoint(
                    index=i,
                    metric=metric,
                    direction="up",
                    magnitude=abs(magnitude),
                    confidence=min(1.0, cusum_pos / (self.threshold * 2)),
                    context={"cusum_value": cusum_pos, "baseline": baseline_mean},
                ))
                cusum_pos = 0  # reset after detection

            elif cusum_neg > self.threshold:
                magnitude = baseline_mean - sequence[i]
                changepoints.append(Changepoint(
                    index=i,
                    metric=metric,
                    direction="down",
                    magnitude=abs(magnitude),
                    confidence=min(1.0, cusum_neg / (self.threshold * 2)),
                    context={"cusum_value": cusum_neg, "baseline": baseline_mean},
                ))
                cusum_neg = 0

        return changepoints


class VarianceShiftDetector:
    """Detect variance changes (not just mean shifts) using sliding windows.

    Useful for detecting when a metric becomes unstable, not just when
    it shifts in one direction.
    """

    def __init__(self, *, window_size: int = 10, ratio_threshold: float = 3.0):
        self.window_size = window_size
        self.ratio_threshold = ratio_threshold

    def detect(
        self,
        sequence: list[float],
        metric: str = "",
    ) -> list[Changepoint]:
        """Detect variance regime changes."""
        if len(sequence) < self.window_size * 3:
            return []

        changepoints: list[Changepoint] = []

        for i in range(self.window_size * 2, len(sequence)):
            # Before window
            before = sequence[i - self.window_size * 2:i - self.window_size]
            # After window
            after = sequence[i - self.window_size:i]

            var_before = _variance(before)
            var_after = _variance(after)

            if var_before < 1e-10:
                continue

            ratio = var_after / var_before

            if ratio > self.ratio_threshold:
                changepoints.append(Changepoint(
                    index=i,
                    metric=metric,
                    direction="variance_up",
                    magnitude=ratio,
                    confidence=min(1.0, (ratio - self.ratio_threshold) / self.ratio_threshold),
                    context={"var_before": var_before, "var_after": var_after},
                ))
            elif ratio < 1.0 / self.ratio_threshold:
                changepoints.append(Changepoint(
                    index=i,
                    metric=metric,
                    direction="variance_down",
                    magnitude=1.0 / ratio,
                    confidence=min(1.0, (1.0 / ratio - self.ratio_threshold) / self.ratio_threshold),
                    context={"var_before": var_before, "var_after": var_after},
                ))

        return changepoints


def _variance(seq: list[float]) -> float:
    """Sample variance."""
    if len(seq) < 2:
        return 0.0
    mean = sum(seq) / len(seq)
    return sum((x - mean) ** 2 for x in seq) / (len(seq) - 1)
