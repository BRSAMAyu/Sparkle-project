from __future__ import annotations

from math import isfinite

from app.config import settings
from app.core.metrics import get_or_create_metric
from app.schemas.foresight import AttractorState, Deviation
from prometheus_client import Counter as PrometheusCounter


FORESIGHT_DEVIATION_DETECTED_TOTAL = get_or_create_metric(
    PrometheusCounter,
    "sparkle_foresight_deviation_detected_total",
    "Total foresight deviations detected",
    ["dim", "direction"],
)


class DeviationDetector:
    MIN_VARIABILITY = 0.05

    def __init__(self, *, z_threshold: float | None = None) -> None:
        self.z_threshold = float(z_threshold if z_threshold is not None else settings.AURORA_FORESIGHT_DEVIATION_Z_THRESHOLD)

    def detect(
        self,
        *,
        attractors: dict[str, AttractorState],
        current_observations: dict[str, float],
    ) -> tuple[Deviation, ...]:
        deviations: list[Deviation] = []
        for dim, state in attractors.items():
            if state.confidence < float(settings.AURORA_FORESIGHT_ATTRACTOR_MIN_CONFIDENCE):
                continue
            if dim not in current_observations:
                continue
            current_value = float(current_observations[dim])
            baseline = float(state.baseline)
            denominator = max(self.MIN_VARIABILITY, abs(float(state.variability)))
            z_score = (current_value - baseline) / denominator
            if not isfinite(z_score) or abs(z_score) < self.z_threshold:
                continue
            direction = "above" if z_score > 0 else "below"
            projected_3d = self._project_trajectory(
                current_value=current_value,
                baseline=baseline,
                recovery_rate=float(state.recovery_rate),
            )
            deviation = Deviation(
                dim=dim,
                current_value=round(current_value, 4),
                baseline=round(baseline, 4),
                z_score=round(z_score, 4),
                direction=direction,
                projected_3d=round(projected_3d, 4),
                confidence=round(max(0.0, min(0.99, float(state.confidence))), 4),
            )
            FORESIGHT_DEVIATION_DETECTED_TOTAL.labels(dim=dim, direction=direction).inc()
            deviations.append(deviation)
        deviations.sort(key=lambda item: (-abs(item.z_score), item.dim))
        return tuple(deviations)

    @staticmethod
    def _project_trajectory(
        *,
        current_value: float,
        baseline: float,
        recovery_rate: float,
    ) -> float:
        step = max(0.0, float(recovery_rate)) * 3.0
        if current_value > baseline:
            return max(baseline, current_value - step)
        if current_value < baseline:
            return min(baseline, current_value + step)
        return baseline
