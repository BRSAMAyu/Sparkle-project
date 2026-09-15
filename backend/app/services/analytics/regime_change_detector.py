from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.services.evidence.belief_state import BeliefState
from app.services.evidence.unified_evidence import EvidenceTarget


@dataclass(frozen=True)
class RegimeChangeSignal:
    target: str
    direction: str
    value: float
    baseline: float
    statistic: float
    threshold: float
    triggered: bool
    steps_observed: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["value"] = round(float(self.value), 6)
        payload["baseline"] = round(float(self.baseline), 6)
        payload["statistic"] = round(float(self.statistic), 6)
        payload["threshold"] = round(float(self.threshold), 6)
        return payload


class CUSUMRegimeDetector:
    """One-sided CUSUM detector for belief-state regime shifts."""

    def __init__(
        self,
        *,
        target: EvidenceTarget,
        baseline: float = 0.5,
        direction: str = "increase",
        drift: float = 0.03,
        threshold: float = 0.35,
    ) -> None:
        if direction not in {"increase", "decrease"}:
            raise ValueError("direction must be increase or decrease")
        self.target = target
        self.baseline = float(baseline)
        self.direction = direction
        self.drift = float(drift)
        self.threshold = float(threshold)
        self.statistic = 0.0
        self.steps_observed = 0

    def update(self, value: float) -> RegimeChangeSignal:
        self.steps_observed += 1
        centered = float(value) - self.baseline
        increment = centered if self.direction == "increase" else -centered
        self.statistic = max(0.0, self.statistic + increment - self.drift)
        return RegimeChangeSignal(
            target=self.target.value,
            direction=self.direction,
            value=float(value),
            baseline=self.baseline,
            statistic=self.statistic,
            threshold=self.threshold,
            triggered=self.statistic >= self.threshold,
            steps_observed=self.steps_observed,
        )

    def update_from_belief(self, belief_state: BeliefState) -> RegimeChangeSignal:
        variable = belief_state.peek_variable(self.target)
        value = float(variable.mean) if variable is not None else self.baseline
        return self.update(value)

    def reset(self) -> None:
        self.statistic = 0.0
        self.steps_observed = 0


class AuroraRegimeDetector:
    """Small ensemble of CUSUM detectors for Aurora state shifts."""

    def __init__(self) -> None:
        self.detectors = [
            CUSUMRegimeDetector(
                target=EvidenceTarget.EMOTIONAL_BLOCK,
                baseline=0.52,
                direction="increase",
                threshold=0.38,
            ),
            CUSUMRegimeDetector(
                target=EvidenceTarget.COGNITIVE_LOAD,
                baseline=0.55,
                direction="increase",
                threshold=0.38,
            ),
            CUSUMRegimeDetector(
                target=EvidenceTarget.TASK_AVERSION,
                baseline=0.52,
                direction="increase",
                threshold=0.38,
            ),
            CUSUMRegimeDetector(
                target=EvidenceTarget.EXECUTION_CAPACITY,
                baseline=0.50,
                direction="decrease",
                threshold=0.34,
            ),
        ]

    def update(self, belief_state: BeliefState) -> dict[str, Any]:
        signals = [detector.update_from_belief(belief_state) for detector in self.detectors]
        triggered = [signal for signal in signals if signal.triggered]
        return {
            "schema_version": "aurora_regime_detection.v1",
            "triggered": bool(triggered),
            "triggered_targets": [signal.target for signal in triggered],
            "signals": [signal.to_dict() for signal in signals],
        }

    def reset(self) -> None:
        for detector in self.detectors:
            detector.reset()
