from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.aurora.schemas import (
    Commitment,
    CommitmentStatus,
    DecisionBasis,
    DecisionMechanism,
    FocusContract,
    ImpactClass,
    InitiationType,
    NodeConfig,
    ProjectionPolicy,
    ScenarioPackManifest,
    SignalSnapshot,
    TransitionDecisionRecord,
    UXIntent,
    WindowMode,
    WindowState,
    WritePath,
)
from app.graph.backbone import BackbonePathResolver
from app.graph.commitment_engine import CommitmentLifecycleManager
from app.graph.focus_contract_manager import FocusContractLifecycleManager
from app.graph.runtime import GraphRuntime
from app.graph.transitions import TransitionPolicyEngine


def _build_exam_prep_manifest() -> ScenarioPackManifest:
    nodes = []
    for day in range(1, 15):
        node_id = f"day{day}"
        neighbors = [f"day{day + 1}"] if day < 14 else []
        nodes.append(
            NodeConfig(
                node_id=node_id,
                node_persona=f"Exam prep day {day}",
                prompt_template=f"Prompt for {node_id}",
                available_tools=["checklist", "reflection"],
                exit_conditions=["day_complete"],
                neighbors=neighbors,
                transition_triggers={
                    "strong_signal": f"day{min(day + 2, 14)}" if day < 14 else node_id,
                },
            )
        )

    return ScenarioPackManifest(
        id="exam_prep_14d@v1.0",
        name="Exam Prep 14 Day",
        version="v1.0",
        description="Minimal exam prep backbone for graph runtime tests.",
        backbone_nodes=nodes,
        created_at=datetime(2026, 4, 17, 0, 0, 0),
        author="test",
    )


def _build_focus_contract(user_id: UUID, node_id: str, version: int = 3) -> FocusContract:
    return FocusContract(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        user_id=user_id,
        version=version,
        scenario_pack_id="exam_prep_14d@v1.0",
        active_node=node_id,
        focus_description="保持备考节奏",
        desire_hypothesis="稳住执行并减少拖延",
        commitment_ids=[UUID("33333333-3333-3333-3333-333333333333")],
        created_at=datetime(2026, 4, 17, 9, 0, 0),
        created_by="aurora",
        evidence_refs=["reference"],
        projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
        write_path=WritePath.SYSTEM_INTERNAL,
    )


def _build_commitment(user_id: UUID, *, status: CommitmentStatus = CommitmentStatus.ACTIVE, window_override: WindowMode | None = None) -> Commitment:
    return Commitment(
        id=UUID("33333333-3333-3333-3333-333333333333"),
        user_id=user_id,
        description="完成前5章复习",
        node_id="day3",
        success_criteria="完成题目并复盘错因",
        status=status,
        created_at=datetime(2026, 4, 16, 20, 0, 0),
        activated_at=datetime(2026, 4, 16, 20, 30, 0) if status != CommitmentStatus.PENDING else None,
        deadline=datetime(2026, 4, 28, 23, 59, 0),
        witness_ids=[],
        window_override=window_override,
        evidence_refs=["commitment"],
    )


def test_backbone_resolver_traverses_day_to_day_exam_prep_backbone() -> None:
    resolver = BackbonePathResolver(_build_exam_prep_manifest())

    assert resolver.resolve_next_node("day3") == "day4"
    assert resolver.resolve_path("day3", steps=2) == ["day3", "day4", "day5"]
    assert resolver.is_backbone_transition("day3", "day4") is True


def test_transition_policy_allows_strong_signal_off_backbone_transition() -> None:
    resolver = BackbonePathResolver(_build_exam_prep_manifest())
    decision = TransitionDecisionRecord(
        id=uuid4(),
        user_id=uuid4(),
        created_at=datetime(2026, 4, 17, 10, 0, 0),
        decision_type="transition",
        proposed_transition="day5",
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
        input_snapshot_ref="snapshot-1",
        impact_class=ImpactClass.HIGH,
        rollback_anchor={
            "prev_focus_contract_version": 3,
            "prev_active_commitment_ids": [],
            "prev_claim_statuses": {},
            "policy_version_at_decision": "aurora_policy@v1.0",
        },
        policy_version="aurora_policy@v1.0",
        ux_intent=UXIntent.ROUTINE,
    )

    evaluation = TransitionPolicyEngine().evaluate(decision, current_node_id="day3", resolver=resolver)

    assert evaluation.allow is True
    assert evaluation.target_node_id == "day5"
    assert evaluation.is_backbone_transition is False


def test_transitions_rejects_ghost_node() -> None:
    resolver = BackbonePathResolver(_build_exam_prep_manifest())
    decision = TransitionDecisionRecord(
        id=uuid4(),
        user_id=uuid4(),
        created_at=datetime(2026, 4, 17, 10, 5, 0),
        decision_type="transition",
        proposed_transition="ghost_node",
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
        input_snapshot_ref="snapshot-ghost",
        impact_class=ImpactClass.CRITICAL,
        rollback_anchor={
            "prev_focus_contract_version": 3,
            "prev_active_commitment_ids": [],
            "prev_claim_statuses": {},
            "policy_version_at_decision": "aurora_policy@v1.0",
        },
        policy_version="aurora_policy@v1.0",
        ux_intent=UXIntent.ROUTINE,
    )

    evaluation = TransitionPolicyEngine().evaluate(decision, current_node_id="day3", resolver=resolver)

    assert evaluation.allow is False
    assert evaluation.target_node_id == "day3"
    assert evaluation.is_backbone_transition is False
    assert evaluation.reason == "unknown_target_node_rejected"


def test_focus_contract_manager_versions_and_current_lookup() -> None:
    user_id = uuid4()
    manager = FocusContractLifecycleManager()
    initial = _build_focus_contract(user_id, "day3", version=3)

    manager.register(initial)
    versioned = manager.create_version(
        initial,
        active_node="day4",
        focus_description="切到 day4",
        trigger_decision_ref=uuid4(),
        evidence_refs=["decision"],
    )

    assert manager.lookup_current(user_id).version == 4
    assert manager.lookup_current(user_id).active_node == "day4"
    assert manager.lookup_version(initial.id, 3) == initial
    assert manager.lookup_version(initial.id, 4) == versioned
    assert tuple(contract.version for contract in manager.version_chain(initial.id)) == (3, 4)


def test_commitment_lifecycle_and_window_override_management() -> None:
    user_id = uuid4()
    manager = CommitmentLifecycleManager()
    commitment = _build_commitment(user_id, status=CommitmentStatus.PENDING)

    manager.register(commitment)
    activated = manager.activate_commitment(commitment.id)
    fulfilled = manager.fulfill_commitment(commitment.id, resolution="completed")

    window_state = WindowState(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 17, 8, 0, 0),
        global_mode=WindowMode.COMMITMENT,
        set_by="aurora",
    )
    manager.register_window_state(window_state)
    manager.set_commitment_window_override(commitment.id, WindowMode.ITERATION)

    assert activated.status == CommitmentStatus.ACTIVE
    assert fulfilled.status == CommitmentStatus.FULFILLED
    assert manager.resolve_effective_window_mode(user_id, commitment.id) == WindowMode.ITERATION


def test_graph_runtime_consumes_tdr_and_updates_graph_state() -> None:
    user_id = uuid4()
    manifest = _build_exam_prep_manifest()
    runtime = GraphRuntime(manifest)
    focus_contract = _build_focus_contract(user_id, "day3", version=3)
    commitment = _build_commitment(user_id)
    window_state = WindowState(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 17, 8, 30, 0),
        global_mode=WindowMode.COMMITMENT,
        set_by="aurora",
    )
    runtime.bootstrap(
        focus_contract=focus_contract,
        commitments=[commitment],
        window_state=window_state,
    )

    decision = TransitionDecisionRecord(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 17, 9, 15, 0),
        decision_type="transition",
        proposed_transition="day5",
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
        input_snapshot_ref="ss_tdr",
        impact_class=ImpactClass.HIGH,
        rollback_anchor={
            "prev_focus_contract_version": 3,
            "prev_active_commitment_ids": [str(commitment.id)],
            "prev_claim_statuses": {},
            "policy_version_at_decision": "aurora_policy@v1.0",
        },
        policy_version="aurora_policy@v1.0",
        evidence_refs=["signal"],
        ux_intent=UXIntent.ACTIVE_ADJUSTMENT,
    )
    snapshot = SignalSnapshot(
        snapshot_hash="ss_tdr",
        user_id=user_id,
        collected_at=datetime(2026, 4, 17, 9, 15, 0),
        scenario_pack_id="exam_prep_14d@v1.0",
        policy_version="aurora_policy@v1.0",
        core_signals={"user_message": "我今天状态很好，可以跳一下"},
        enhanced_signals={},
        optional_signals={},
        total_tokens=1200,
        budget_limit=4000,
    )

    result = runtime.apply_decision(decision, snapshot=snapshot)

    assert result.transition_evaluation.allow is True
    assert result.current_node_id == "day5"
    assert result.focus_contract.version == 4
    assert runtime.current_focus_contract(user_id).version == 4
    assert runtime.current_focus_contract(user_id).active_node == "day5"


def test_graph_runtime_rejects_invalid_target_without_mutating_focus_contract() -> None:
    user_id = uuid4()
    manifest = _build_exam_prep_manifest()
    runtime = GraphRuntime(manifest)
    focus_contract = _build_focus_contract(user_id, "day3", version=3)
    runtime.bootstrap(focus_contract=focus_contract)

    invalid_decision = TransitionDecisionRecord(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 17, 9, 20, 0),
        decision_type="transition",
        proposed_transition="ghost_node",
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
        input_snapshot_ref="ss_invalid",
        impact_class=ImpactClass.CRITICAL,
        rollback_anchor={
            "prev_focus_contract_version": 3,
            "prev_active_commitment_ids": [],
            "prev_claim_statuses": {},
            "policy_version_at_decision": "aurora_policy@v1.0",
        },
        policy_version="aurora_policy@v1.0",
        evidence_refs=["signal"],
        ux_intent=UXIntent.ROUTINE,
    )

    result = runtime.apply_decision(invalid_decision)

    assert result.transition_evaluation.allow is False
    assert result.current_node_id == "day3"
    assert result.focus_contract.version == 3
    assert result.focus_contract.active_node == "day3"
    assert runtime.current_focus_contract(user_id).version == 3
    assert runtime.current_focus_contract(user_id).active_node == "day3"


def test_graph_runtime_rollback_restores_previous_state_when_enabled() -> None:
    user_id = uuid4()
    manifest = _build_exam_prep_manifest()
    runtime = GraphRuntime(manifest, rollback_enabled=True)
    focus_contract = _build_focus_contract(user_id, "day3", version=3)
    commitment = _build_commitment(user_id)
    runtime.bootstrap(focus_contract=focus_contract, commitments=[commitment])
    runtime.commitments.fulfill_commitment(commitment.id, resolution="temporary change")

    rollback_decision = TransitionDecisionRecord(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime(2026, 4, 17, 11, 0, 0),
        decision_type="rollback",
        proposed_transition=None,
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
        input_snapshot_ref="ss_rollback",
        impact_class=ImpactClass.MEDIUM,
        rollback_anchor={
            "prev_focus_contract_version": 3,
            "prev_active_commitment_ids": [str(commitment.id)],
            "prev_claim_statuses": {},
            "policy_version_at_decision": "aurora_policy@v1.0",
        },
        policy_version="aurora_policy@v1.0",
        evidence_refs=["rollback"],
        ux_intent=UXIntent.RECONCILIATION,
    )

    result = runtime.apply_decision(rollback_decision)

    assert result.rollback_applied is True
    assert result.focus_contract.version == 3
    assert result.focus_contract.active_node == "day3"
    assert runtime.commitments.current(commitment.id).status == CommitmentStatus.ACTIVE
