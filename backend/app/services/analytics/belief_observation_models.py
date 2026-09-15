from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.evidence.belief_state import (
    DEFAULT_MEAN,
    DEFAULT_VARIANCE,
    MAX_VARIANCE,
    MIN_VARIANCE,
    BeliefState,
)
from app.services.evidence.unified_evidence import EvidenceDirection, EvidenceTarget, UnifiedEvidence

STRESS_CLUSTER: tuple[EvidenceTarget, ...] = (
    EvidenceTarget.EMOTIONAL_BLOCK,
    EvidenceTarget.TASK_AVERSION,
    EvidenceTarget.COGNITIVE_LOAD,
)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def _evidence_observed_mean(evidence: UnifiedEvidence) -> float:
    if evidence.direction == EvidenceDirection.INCREASE:
        return evidence.strength
    if evidence.direction == EvidenceDirection.DECREASE:
        return 1.0 - evidence.strength
    return evidence.strength


def _observation_variance(confidence: float) -> float:
    clamped_conf = max(0.01, min(0.99, float(confidence)))
    return max(MIN_VARIANCE, min(MAX_VARIANCE, (1.0 - clamped_conf) ** 2))


@dataclass
class BlockDiagonalFusionState:
    """BeliefState plus a stress-cluster covariance matrix.

    The production BeliefState remains the public interface. The covariance is
    a shadow-side observation-model detail used to test whether correlated
    updates improve recovery of simulator ground truth.
    """

    belief_state: BeliefState
    stress_covariance: list[list[float]]
    update_count: int = 0

    def to_debug_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "block_diagonal_fusion_state.v1",
            "belief_state_id": self.belief_state.state_id,
            "update_count": self.update_count,
            "stress_cluster": [target.value for target in STRESS_CLUSTER],
            "stress_covariance": [
                [round(float(value), 6) for value in row]
                for row in self.stress_covariance
            ],
        }


@dataclass(frozen=True)
class BlockDiagonalFusionConfig:
    stress_correlation: float = 0.42
    min_variance: float = MIN_VARIANCE
    max_variance: float = MAX_VARIANCE


class BlockDiagonalBeliefFusionEngine:
    """Kalman-like observation model with one correlated stress block.

    V1 models the strongest expected correlation block:
    emotional_block <-> task_aversion <-> cognitive_load.
    Other targets keep the existing independent 1D update through BeliefState.
    """

    def __init__(self, config: BlockDiagonalFusionConfig | None = None) -> None:
        self.config = config or BlockDiagonalFusionConfig()

    def initial_state(self, user_id: str) -> BlockDiagonalFusionState:
        state = BeliefState(user_id=user_id)
        for target in STRESS_CLUSTER:
            state.get_variable(target)
        covariance = self._initial_covariance()
        return BlockDiagonalFusionState(belief_state=state, stress_covariance=covariance)

    def fuse_many(
        self,
        current: BlockDiagonalFusionState,
        evidence_items: list[UnifiedEvidence],
    ) -> BlockDiagonalFusionState:
        for evidence in sorted(evidence_items, key=lambda item: item.timestamp):
            current = self.fuse_evidence(current, evidence)
        return current

    def fuse_evidence(
        self,
        current: BlockDiagonalFusionState,
        evidence: UnifiedEvidence,
    ) -> BlockDiagonalFusionState:
        target = evidence.target_latent_variable
        if target in STRESS_CLUSTER:
            self._fuse_stress_cluster(current, evidence)
        else:
            variable = current.belief_state.get_variable(target)
            variable.update_from_evidence(
                observed_mean=_evidence_observed_mean(evidence),
                confidence=evidence.confidence,
                observed_at=evidence.timestamp,
                evidence_id=evidence.evidence_id,
                source_type=evidence.source_type.value,
            )
        current.belief_state.last_fused_at = evidence.timestamp
        current.update_count += 1
        return current

    def _fuse_stress_cluster(
        self,
        current: BlockDiagonalFusionState,
        evidence: UnifiedEvidence,
    ) -> None:
        target_index = STRESS_CLUSTER.index(evidence.target_latent_variable)
        means = [
            current.belief_state.get_variable(target).mean
            for target in STRESS_CLUSTER
        ]
        covariance = current.stress_covariance
        observed_mean = _clamp(_evidence_observed_mean(evidence))
        obs_variance = _observation_variance(evidence.confidence)
        innovation_variance = max(self.config.min_variance, covariance[target_index][target_index] + obs_variance)
        gains = [covariance[row][target_index] / innovation_variance for row in range(len(STRESS_CLUSTER))]
        residual = observed_mean - means[target_index]
        updated_means = [_clamp(mean + gains[index] * residual) for index, mean in enumerate(means)]

        observed_row = list(covariance[target_index])
        next_covariance: list[list[float]] = []
        for row in range(len(STRESS_CLUSTER)):
            next_row: list[float] = []
            for col in range(len(STRESS_CLUSTER)):
                value = covariance[row][col] - gains[row] * observed_row[col]
                next_row.append(value)
            next_covariance.append(next_row)

        self._symmetrize_and_bound(next_covariance)
        current.stress_covariance = next_covariance
        for index, target in enumerate(STRESS_CLUSTER):
            variable = current.belief_state.get_variable(target)
            variable.mean = updated_means[index]
            variable.unbounded_mean = updated_means[index]
            variable.variance = _clamp(next_covariance[index][index], self.config.min_variance, self.config.max_variance)
            if target == evidence.target_latent_variable:
                variable.evidence_count += 1
                variable.source_breakdown[evidence.source_type.value] = (
                    variable.source_breakdown.get(evidence.source_type.value, 0) + 1
                )
                variable.last_evidence_ids = [evidence.evidence_id, *variable.last_evidence_ids[:9]]
                variable.last_updated = evidence.timestamp

    def _initial_covariance(self) -> list[list[float]]:
        corr = max(-0.75, min(0.75, float(self.config.stress_correlation)))
        covariance: list[list[float]] = []
        for row in range(len(STRESS_CLUSTER)):
            next_row: list[float] = []
            for col in range(len(STRESS_CLUSTER)):
                if row == col:
                    next_row.append(DEFAULT_VARIANCE)
                else:
                    next_row.append(corr * DEFAULT_VARIANCE)
            covariance.append(next_row)
        return covariance

    def _symmetrize_and_bound(self, covariance: list[list[float]]) -> None:
        size = len(covariance)
        for row in range(size):
            for col in range(row + 1, size):
                value = (covariance[row][col] + covariance[col][row]) / 2.0
                covariance[row][col] = value
                covariance[col][row] = value
        for index in range(size):
            covariance[index][index] = _clamp(
                covariance[index][index],
                self.config.min_variance,
                self.config.max_variance,
            )
        for row in range(size):
            for col in range(size):
                if row == col:
                    continue
                max_abs = (covariance[row][row] * covariance[col][col]) ** 0.5
                covariance[row][col] = max(-max_abs, min(max_abs, covariance[row][col]))


def neutral_belief_state(user_id: str, targets: list[EvidenceTarget] | None = None) -> BeliefState:
    state = BeliefState(user_id=user_id)
    for target in targets or list(EvidenceTarget):
        variable = state.get_variable(target)
        variable.mean = DEFAULT_MEAN
        variable.unbounded_mean = DEFAULT_MEAN
        variable.variance = DEFAULT_VARIANCE
    return state
