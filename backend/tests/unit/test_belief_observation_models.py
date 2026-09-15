from __future__ import annotations

from app.services.analytics.belief_observation_models import BlockDiagonalBeliefFusionEngine
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)


def test_block_diagonal_fusion_propagates_stress_cluster_signal() -> None:
    engine = BlockDiagonalBeliefFusionEngine()
    state = engine.initial_state("u1")
    evidence = UnifiedEvidence(
        source_type=EvidenceSourceType.HEURISTIC_FALLBACK,
        target_latent_variable=EvidenceTarget.EMOTIONAL_BLOCK,
        direction=EvidenceDirection.OBSERVE,
        strength=0.9,
        confidence=0.9,
        evidence_text="simulated emotional block observation",
    )

    updated = engine.fuse_evidence(state, evidence)

    emotional = updated.belief_state.get_variable(EvidenceTarget.EMOTIONAL_BLOCK)
    aversion = updated.belief_state.get_variable(EvidenceTarget.TASK_AVERSION)
    load = updated.belief_state.get_variable(EvidenceTarget.COGNITIVE_LOAD)
    assert emotional.mean > 0.85
    assert aversion.mean > 0.55
    assert load.mean > 0.55
    assert emotional.variance < 0.05
    assert updated.to_debug_payload()["stress_cluster"] == [
        "emotional_block",
        "task_aversion",
        "cognitive_load",
    ]
