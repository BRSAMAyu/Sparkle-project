from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    UnifiedEvidence,
)


def _directional_value(evidence: UnifiedEvidence) -> float:
    if evidence.direction == EvidenceDirection.INCREASE:
        return float(evidence.strength)
    if evidence.direction == EvidenceDirection.DECREASE:
        return 1.0 - float(evidence.strength)
    return float(evidence.strength)


def _direction_sign(value: float, *, deadband: float = 0.03) -> int:
    if value > deadband:
        return 1
    if value < -deadband:
        return -1
    return 0


@dataclass(frozen=True)
class ProbeConsistencyEvent:
    target: str
    probe_response_direction: int
    belief_before: float
    belief_after: float
    retained_next_turn: bool = True
    outcome_positive: bool | None = None


@dataclass(frozen=True)
class ProbeValidationReport:
    total_probes: int
    consistent_probes: int
    reliability: float
    next_turn_retention_rate: float
    target_reliability: dict[str, float]
    recommendation: str
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProbeValidationAnalyzer:
    """Validate active-probe evidence without using BeliefState as its own judge."""

    def evaluate(self, events: list[ProbeConsistencyEvent]) -> ProbeValidationReport:
        total = len(events)
        consistent = 0
        retained = 0
        by_target: dict[str, list[bool]] = defaultdict(list)
        for event in events:
            drift = _direction_sign(event.belief_after - event.belief_before)
            is_consistent = drift == 0 or drift == event.probe_response_direction
            consistent += int(is_consistent)
            retained += int(event.retained_next_turn)
            by_target[event.target].append(is_consistent)
        reliability = consistent / total if total else 0.0
        target_reliability = {
            target: round(sum(values) / len(values), 4)
            for target, values in sorted(by_target.items())
            if values
        }
        blockers: list[str] = []
        if total < 100:
            blockers.append("insufficient_probe_events")
        if total and reliability < 0.5:
            blockers.append("probe_worse_than_random")
        recommendation = "keep_probe_shadow_only" if blockers else "probe_candidate_for_limited_canary"
        return ProbeValidationReport(
            total_probes=total,
            consistent_probes=consistent,
            reliability=round(reliability, 4),
            next_turn_retention_rate=round(retained / total, 4) if total else 0.0,
            target_reliability=target_reliability,
            recommendation=recommendation,
            blockers=blockers,
        )


@dataclass(frozen=True)
class InnovationResidualReport:
    target: str
    text_value: float
    behavior_value: float
    residual: float
    source: str
    variance_multiplier: float
    adjusted_confidence: float
    reliability: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InnovationResidualCalibrator:
    """Penalize a source when textual/probe evidence conflicts with behavior.

    The independent reference must be behavioral/outcome evidence. This avoids
    the circular mistake of validating probes against the same BeliefState they
    are supposed to improve.
    """

    def __init__(
        self,
        *,
        window: int = 20,
        residual_threshold: float = 0.35,
        max_variance_multiplier: float = 6.0,
    ) -> None:
        self.window = window
        self.residual_threshold = residual_threshold
        self.max_variance_multiplier = max_variance_multiplier
        self._residuals: dict[tuple[str, str], deque[float]] = defaultdict(lambda: deque(maxlen=window))

    def compare(
        self,
        *,
        subjective_evidence: UnifiedEvidence,
        behavioral_evidence: UnifiedEvidence,
    ) -> InnovationResidualReport:
        if behavioral_evidence.source_type not in {EvidenceSourceType.BEHAVIORAL_IMPLICIT, EvidenceSourceType.OUTCOME}:
            raise ValueError("behavioral_evidence must come from behavioral_implicit or outcome source")
        if subjective_evidence.target_latent_variable != behavioral_evidence.target_latent_variable:
            raise ValueError("evidence targets must match")

        target = subjective_evidence.target_latent_variable.value
        source = subjective_evidence.source_type.value
        text_value = _directional_value(subjective_evidence)
        behavior_value = _directional_value(behavioral_evidence)
        residual = abs(text_value - behavior_value)
        key = (source, target)
        self._residuals[key].append(residual)
        rolling = sum(self._residuals[key]) / len(self._residuals[key])
        excess = max(0.0, rolling - self.residual_threshold)
        multiplier = min(self.max_variance_multiplier, 1.0 + excess / max(0.01, self.residual_threshold) * 3.0)
        reliability = max(0.0, min(1.0, 1.0 - rolling))
        adjusted_confidence = max(0.01, min(1.0, subjective_evidence.confidence / multiplier))
        reasons: list[str] = []
        if residual > self.residual_threshold:
            reasons.append("single_residual_high")
        if rolling > self.residual_threshold:
            reasons.append("rolling_residual_high")
        if not reasons:
            reasons.append("residual_within_expected_range")
        return InnovationResidualReport(
            target=target,
            text_value=round(text_value, 4),
            behavior_value=round(behavior_value, 4),
            residual=round(residual, 4),
            source=source,
            variance_multiplier=round(multiplier, 4),
            adjusted_confidence=round(adjusted_confidence, 4),
            reliability=round(reliability, 4),
            reasons=reasons,
        )

    def source_reliability(self) -> dict[str, dict[str, float]]:
        output: dict[str, dict[str, float]] = {}
        for (source, target), residuals in sorted(self._residuals.items()):
            rolling = sum(residuals) / len(residuals) if residuals else 0.0
            output.setdefault(source, {})[target] = round(max(0.0, min(1.0, 1.0 - rolling)), 4)
        return output
