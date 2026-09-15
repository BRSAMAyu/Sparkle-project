from __future__ import annotations

from app.services.analytics.probe_validation import (
    InnovationResidualCalibrator,
    ProbeConsistencyEvent,
    ProbeValidationAnalyzer,
)
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)


def test_probe_validation_reports_reliability_and_retention() -> None:
    events = [
        ProbeConsistencyEvent(
            target="task_aversion",
            probe_response_direction=1,
            belief_before=0.3,
            belief_after=0.5,
            retained_next_turn=True,
        ),
        ProbeConsistencyEvent(
            target="task_aversion",
            probe_response_direction=-1,
            belief_before=0.5,
            belief_after=0.4,
            retained_next_turn=False,
        ),
    ]

    report = ProbeValidationAnalyzer().evaluate(events).to_dict()

    assert report["total_probes"] == 2
    assert report["consistent_probes"] == 2
    assert report["reliability"] == 1.0
    assert report["next_turn_retention_rate"] == 0.5
    assert "insufficient_probe_events" in report["blockers"]


def test_innovation_residual_calibrator_penalizes_text_behavior_conflict() -> None:
    calibrator = InnovationResidualCalibrator(window=3, residual_threshold=0.25)
    subjective = UnifiedEvidence(
        source_type=EvidenceSourceType.PROBE_EXPLICIT,
        target_latent_variable=EvidenceTarget.TASK_AVERSION,
        direction=EvidenceDirection.OBSERVE,
        strength=0.1,
        confidence=0.9,
        evidence_text="不难",
    )
    behavior = UnifiedEvidence(
        source_type=EvidenceSourceType.BEHAVIORAL_IMPLICIT,
        target_latent_variable=EvidenceTarget.TASK_AVERSION,
        direction=EvidenceDirection.OBSERVE,
        strength=0.85,
        confidence=0.7,
        evidence_text="repeated retries",
    )

    report = calibrator.compare(
        subjective_evidence=subjective,
        behavioral_evidence=behavior,
    )

    assert report.residual > 0.7
    assert report.variance_multiplier > 1.0
    assert report.adjusted_confidence < subjective.confidence
    assert "rolling_residual_high" in report.reasons
