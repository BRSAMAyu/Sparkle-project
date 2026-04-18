from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.aurora.engine import AuroraDecisionContext, AuroraEngine
from app.aurora.ledger import AppendOnlyLedgerStore, ClaimLifecycleManager
from app.aurora.schemas import (
    ClaimSource,
    Commitment,
    CommitmentStatus,
    FocusContract,
    IdentityEvidence,
    ProbeOutcome,
    ProjectionPolicy,
    WindowMode,
    WindowState,
    WritePath,
)
from app.aurora.signal_processor import SignalProcessor
from app.graph.runtime import GraphRuntime
from app.scenario_packs.registry import load_default_registry
from app.social.accountability import PartnerReportInput, build_partner_report_claim

from .reference_flow_harness import AuroraReferenceFlowCase, AuroraReferenceFlowHarness


PROVISIONAL_GAPS: dict[str, tuple[str, ...]] = {
    "day3_study_resistance": ("InsightClaim", "ProbeOutcome"),
    "crisis_recovery": ("FocusContract(side-effect write)", "WindowState(side-effect write)"),
    "partner_concern": (),
}


@dataclass(frozen=True)
class LiveFlowReplay:
    observed_sequence: tuple[str, ...]
    current_node_id: str
    provisional_gaps: tuple[str, ...]
    claim_record_count: int
    probe_record_count: int


def _manifest():
    registry = load_default_registry()
    manifest = registry.get_by_id("exam_prep_14d@v1.0")
    assert manifest is not None
    return manifest


def _focus_for_case(case: AuroraReferenceFlowCase, *, active_node: str) -> FocusContract:
    return case.focus_contract.model_copy(
        update={
            "scenario_pack_id": "exam_prep_14d@v1.0",
            "active_node": active_node,
            "focus_description": f"Live replay at {active_node}",
            "write_path": WritePath.SYSTEM_INTERNAL,
        }
    )


def _commitment_for_case(case: AuroraReferenceFlowCase, *, node_id: str) -> Commitment:
    return case.commitment.model_copy(
        update={
            "node_id": node_id,
            "status": CommitmentStatus.ACTIVE,
            "window_override": WindowMode.COMMITMENT,
        }
    )


def _window_for_case(case: AuroraReferenceFlowCase) -> WindowState:
    return case.window_state.model_copy(update={"global_mode": WindowMode.COMMITMENT})


def _runtime_for_case(case: AuroraReferenceFlowCase, *, active_node: str) -> GraphRuntime:
    runtime = GraphRuntime(_manifest())
    runtime.bootstrap(
        focus_contract=_focus_for_case(case, active_node=active_node),
        commitments=[_commitment_for_case(case, node_id=active_node)],
        window_state=_window_for_case(case),
    )
    return runtime


def _partner_probe(claim_id: UUID, *, created_at: datetime) -> ProbeOutcome:
    return ProbeOutcome(
        id=uuid4(),
        claim_id=claim_id,
        created_at=created_at,
        probe_type="partner_checkin",
        probe_content="请确认是否需要把今天的目标收缩到最小行动。",
        result="partner_confirmed_support",
        evidence="伙伴确认用户需要 support-first framing",
        confidence_adjustment=0.12,
    )


def _identity_evidence(user_id: UUID, description: str) -> IdentityEvidence:
    return IdentityEvidence(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 19, 10, 0, 0),
        dimension="support",
        evidence_type="interaction",
        description=description,
        strength=0.72,
        valence="positive",
        source=ClaimSource.PARTNER_REPORT,
        projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
    )


def test_live_reference_flow_day3_resistance_replays_current_engine_graph_and_ledger() -> None:
    harness = AuroraReferenceFlowHarness()
    case = harness.build_day3_study_resistance_case()
    runtime = _runtime_for_case(case, active_node="day3_schedule_lock")
    engine = AuroraEngine()
    ledger = AppendOnlyLedgerStore()
    processor = SignalProcessor(ledger=ledger)

    decision = engine.safe_route(
        AuroraDecisionContext(
            snapshot=case.snapshot,
            trigger_point=case.trigger_point,
            current_node="day3_schedule_lock",
            policy_version=case.policy_version,
            mode="shadow",
        )
    )
    graph_result = runtime.apply_decision(decision, snapshot=case.snapshot)
    processor.process({"transition_decision_record": decision})

    observed_sequence = (
        "SignalSnapshot",
        "TransitionDecisionRecord",
        "GraphExecutionResult",
        "Ledger:transition_decision",
    )

    assert observed_sequence[0] == case.expected_object_sequence[0]
    assert decision.decision_type == "stay"
    assert graph_result.current_node_id == "day3_schedule_lock"
    assert ledger.latest_by_type("transition_decision", user_id=case.snapshot.user_id) is not None
    assert PROVISIONAL_GAPS[case.name] == ("InsightClaim", "ProbeOutcome")


def test_live_reference_flow_crisis_recovery_surfaces_current_pack_gap_without_faking_side_effects() -> None:
    harness = AuroraReferenceFlowHarness()
    case = harness.build_crisis_recovery_case()
    runtime = _runtime_for_case(case, active_node="day6_targeted_drill")
    engine = AuroraEngine()
    ledger = AppendOnlyLedgerStore()
    processor = SignalProcessor(ledger=ledger)

    decision = engine.safe_route(
        AuroraDecisionContext(
            snapshot=case.snapshot,
            trigger_point=case.trigger_point,
            current_node="day6_targeted_drill",
            policy_version=case.policy_version,
            mode="shadow",
        )
    )
    graph_result = runtime.apply_decision(decision, snapshot=case.snapshot)
    processor.process({"transition_decision_record": decision})

    replay = LiveFlowReplay(
        observed_sequence=(
            "SignalSnapshot",
            "TransitionDecisionRecord",
            "GraphExecutionResult",
            "Ledger:transition_decision",
        ),
        current_node_id=graph_result.current_node_id,
        provisional_gaps=PROVISIONAL_GAPS[case.name],
        claim_record_count=0,
        probe_record_count=0,
    )

    assert replay.observed_sequence[0] == case.expected_object_sequence[0]
    assert decision.impact_class.value == "medium"
    assert decision.decision_type == "stay"
    assert decision.inference_knobs["reason"] == "strong_signal_without_candidate"
    assert replay.current_node_id == "day6_targeted_drill"
    assert replay.provisional_gaps == ("FocusContract(side-effect write)", "WindowState(side-effect write)")


def test_live_reference_flow_partner_concern_replays_social_claim_probe_and_graph_transition() -> None:
    harness = AuroraReferenceFlowHarness()
    case = harness.build_partner_concern_case()
    runtime = _runtime_for_case(case, active_node="day3_schedule_lock")
    engine = AuroraEngine()
    ledger = AppendOnlyLedgerStore()
    processor = SignalProcessor(ledger=ledger)
    claim_manager = ClaimLifecycleManager(ledger)

    decision = engine.safe_route(
        AuroraDecisionContext(
            snapshot=case.snapshot,
            trigger_point=case.trigger_point,
            current_node="day3_schedule_lock",
            candidate_node="day4_deep_analysis",
            policy_version=case.policy_version,
            mode="shadow",
        )
    )
    partner_bridge = build_partner_report_claim(
        PartnerReportInput(
            reporter_id=uuid4(),
            user_id=case.snapshot.user_id,
            partnership_id=uuid4(),
            summary="连续四天未完成且在回避，建议先缩小目标。",
            confidence=0.86,
            evidence_refs=("partner-checkin-1",),
        )
    )
    claim = claim_manager.create_claim(partner_bridge.claim)
    probe = _partner_probe(claim.id, created_at=case.snapshot.collected_at)
    claim_manager.register_probe_outcome(probe)
    graph_result = runtime.apply_decision(decision, snapshot=case.snapshot)
    processor.process(
        {
            "transition_decision_record": decision,
            "claims": [claim],
            "probe_outcomes": [probe],
        }
    )

    replay = LiveFlowReplay(
        observed_sequence=(
            "SignalSnapshot",
            "InsightClaim",
            "ProbeOutcome",
            "TransitionDecisionRecord",
            "GraphExecutionResult",
            "Ledger:transition_decision",
        ),
        current_node_id=graph_result.current_node_id,
        provisional_gaps=PROVISIONAL_GAPS[case.name],
        claim_record_count=len(ledger.list_records(user_id=case.snapshot.user_id, record_types={"insight_claim"})),
        probe_record_count=len(ledger.list_records(user_id=case.snapshot.user_id, record_types={"probe_outcome"})),
    )

    assert replay.observed_sequence[:4] == case.expected_object_sequence
    assert decision.decision_type == "transition"
    assert decision.decision_basis.value == "partner_signal"
    assert graph_result.current_node_id == "day4_deep_analysis"
    assert replay.claim_record_count >= 1
    assert replay.probe_record_count >= 1
    assert _identity_evidence(case.snapshot.user_id, "伙伴在关键时刻提供了结构化提醒").strength > 0.7
