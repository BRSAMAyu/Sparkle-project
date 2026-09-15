from __future__ import annotations

from app.services.analytics.regime_change_detector import AuroraRegimeDetector, CUSUMRegimeDetector
from app.services.evidence.belief_state import BeliefState
from app.services.evidence.unified_evidence import EvidenceTarget


def test_cusum_regime_detector_triggers_after_sustained_shift() -> None:
    detector = CUSUMRegimeDetector(
        target=EvidenceTarget.EMOTIONAL_BLOCK,
        baseline=0.4,
        direction="increase",
        drift=0.02,
        threshold=0.25,
    )

    signals = [detector.update(value) for value in [0.42, 0.56, 0.62, 0.66]]

    assert signals[-1].triggered is True
    assert signals[-1].statistic >= detector.threshold


def test_aurora_regime_detector_reads_belief_state() -> None:
    detector = AuroraRegimeDetector()
    state = BeliefState(user_id="u1")
    emotional = state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    emotional.mean = 0.86
    load = state.get_variable(EvidenceTarget.COGNITIVE_LOAD)
    load.mean = 0.82

    report = detector.update(state)
    report = detector.update(state)

    assert report["schema_version"] == "aurora_regime_detection.v1"
    assert report["triggered"] is True
    assert "emotional_block" in report["triggered_targets"]
