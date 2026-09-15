"""Reference-flow harness skeleton for Aurora Wave 1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.aurora.schemas import (
    AuroraPolicyVersion,
    AuditInvariants,
    Commitment,
    CommitmentStatus,
    ContinuousLearningPolicy,
    FocusContract,
    ImpactClass,
    InitiationType,
    InteractionModelConfig,
    InteractionModelVariant,
    InsightClaim,
    ParameterWriteAuthority,
    ParameterWriteAuthLevel,
    PersonaInvariants,
    ProactivePolicy,
    ProjectionPolicy,
    ReconciliationPolicy,
    RetentionTier,
    SignalSnapshot,
    UXIntent,
    UserScenarioState,
    WindowMode,
    WindowState,
    WritePath,
    DecisionBasis,
    DecisionMechanism,
    TransitionDecisionRecord,
    ClaimSource,
    ClaimLifecycle,
    AuroraPresenceLevel,
    DistilledStrategyLifecycle,
    Shareability,
)


@dataclass(frozen=True)
class AuroraReferenceFlowCase:
    """Frozen input bundle for one reference flow."""

    name: str
    trigger_point: str
    snapshot: SignalSnapshot
    focus_contract: FocusContract
    commitment: Commitment
    window_state: WindowState
    user_scenario_state: UserScenarioState
    policy_version: AuroraPolicyVersion
    expected_object_sequence: tuple[str, ...]
    expected_output_classes: tuple[str, ...]


class AuroraReferenceFlowHarness:
    """Builds Gate 0 reference-flow fixtures for later Wave 1 execution tests."""

    def __init__(self) -> None:
        self._policy_version = self._build_policy_version()

    def build_day3_study_resistance_case(self) -> AuroraReferenceFlowCase:
        focus_contract = FocusContract(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            user_id=UUID("22222222-2222-2222-2222-222222222222"),
            version=3,
            scenario_pack_id="exam_prep_14d@v1.0",
            active_node="day3_execution",
            focus_description="继续推进热力学备考",
            desire_hypothesis="想要稳住节奏但今天状态偏低",
            commitment_ids=[UUID("33333333-3333-3333-3333-333333333333")],
            created_at=datetime(2026, 4, 17, 9, 0, 0),
            created_by="aurora",
            evidence_refs=["user_msg_t0", "task_completion_60%"],
        )
        commitment = Commitment(
            id=UUID("33333333-3333-3333-3333-333333333333"),
            user_id=focus_contract.user_id,
            description="完成热力学前5章",
            node_id="day3_execution",
            success_criteria="能够完成前5章的核心题目并复盘错因",
            status=CommitmentStatus.ACTIVE,
            created_at=datetime(2026, 4, 16, 20, 0, 0),
            activated_at=datetime(2026, 4, 16, 20, 30, 0),
            deadline=datetime(2026, 4, 28, 23, 59, 0),
            witness_ids=[],
            evidence_refs=["commitment_C1"],
        )
        window_state = WindowState(
            id=UUID("44444444-4444-4444-4444-444444444444"),
            user_id=focus_contract.user_id,
            created_at=datetime(2026, 4, 17, 8, 30, 0),
            global_mode=WindowMode.COMMITMENT,
            set_by="aurora",
            evidence_refs=["window_commitment"],
        )
        user_scenario_state = UserScenarioState(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            user_id=focus_contract.user_id,
            created_at=datetime(2026, 4, 16, 20, 0, 0),
            updated_at=datetime(2026, 4, 17, 9, 0, 0),
            pack_id=focus_contract.scenario_pack_id,
            current_node=focus_contract.active_node,
            current_focus_contract_id=focus_contract.id,
            current_focus_contract_version=focus_contract.version,
            is_on_backbone=True,
        )
        snapshot = SignalSnapshot(
            snapshot_hash="ss_day3_reference",
            user_id=focus_contract.user_id,
            collected_at=datetime(2026, 4, 17, 9, 0, 0),
            scenario_pack_id=focus_contract.scenario_pack_id,
            policy_version=self._policy_version.id,
            core_signals={"user_message": "我今天不想做"},
            enhanced_signals={"task_completion_7d": 0.6},
            optional_signals={"partner_report": {"status": "stale"}},
            total_tokens=2800,
            budget_limit=4000,
            retention_tier=RetentionTier.HOT,
        )
        return AuroraReferenceFlowCase(
            name="day3_study_resistance",
            trigger_point="pre-node-routing",
            snapshot=snapshot,
            focus_contract=focus_contract,
            commitment=commitment,
            window_state=window_state,
            user_scenario_state=user_scenario_state,
            policy_version=self._policy_version,
            expected_object_sequence=(
                "SignalSnapshot",
                "InsightClaim",
                "TransitionDecisionRecord",
                "ProbeOutcome",
            ),
            expected_output_classes=(
                "impact_class",
                "transition_decision_record",
                "inference_knobs",
                "capability_gate",
                "ux_intent",
                "aurora_presence",
            ),
        )

    def build_crisis_recovery_case(self) -> AuroraReferenceFlowCase:
        case = self.build_day3_study_resistance_case()
        snapshot = SignalSnapshot(
            snapshot_hash="ss_crisis_reference",
            user_id=case.snapshot.user_id,
            collected_at=datetime(2026, 4, 18, 9, 0, 0),
            scenario_pack_id=case.snapshot.scenario_pack_id,
            policy_version=self._policy_version.id,
            core_signals={"user_message": "我家里出事了，最近可能没法继续"},
            enhanced_signals={"energy_state": "sharp_drop"},
            optional_signals={},
            total_tokens=1600,
            budget_limit=4000,
        )
        return AuroraReferenceFlowCase(
            name="crisis_recovery",
            trigger_point="pre-tool-selection",
            snapshot=snapshot,
            focus_contract=case.focus_contract,
            commitment=case.commitment,
            window_state=case.window_state,
            user_scenario_state=case.user_scenario_state,
            policy_version=self._policy_version,
            expected_object_sequence=(
                "SignalSnapshot",
                "InsightClaim",
                "TransitionDecisionRecord",
                "WindowState",
                "FocusContract",
            ),
            expected_output_classes=(
                "impact_class",
                "transition_decision_record",
                "inference_knobs",
                "capability_gate",
                "ux_intent",
                "aurora_presence",
            ),
        )

    def build_partner_concern_case(self) -> AuroraReferenceFlowCase:
        case = self.build_day3_study_resistance_case()
        snapshot = SignalSnapshot(
            snapshot_hash="ss_partner_reference",
            user_id=case.snapshot.user_id,
            collected_at=datetime(2026, 4, 19, 9, 0, 0),
            scenario_pack_id=case.snapshot.scenario_pack_id,
            policy_version=self._policy_version.id,
            core_signals={"partner_report": {"severity": "medium"}},
            enhanced_signals={"task_completion_4d": 0.0, "behavioral_signal": "gaming_detected"},
            optional_signals={},
            total_tokens=2000,
            budget_limit=4000,
        )
        return AuroraReferenceFlowCase(
            name="partner_concern",
            trigger_point="pre-node-routing",
            snapshot=snapshot,
            focus_contract=case.focus_contract,
            commitment=case.commitment,
            window_state=case.window_state,
            user_scenario_state=case.user_scenario_state,
            policy_version=self._policy_version,
            expected_object_sequence=(
                "SignalSnapshot",
                "InsightClaim",
                "ProbeOutcome",
                "TransitionDecisionRecord",
            ),
            expected_output_classes=(
                "inference_knobs",
                "capability_gate",
                "ux_intent",
                "aurora_presence",
                "transition_decision_record",
                "impact_class",
            ),
        )

    def build_decision_stub(self, case: AuroraReferenceFlowCase) -> TransitionDecisionRecord:
        """Placeholder decision payload for later Wave 1 execution wiring."""

        return TransitionDecisionRecord(
            id=UUID("66666666-6666-6666-6666-666666666666"),
            user_id=case.snapshot.user_id,
            created_at=case.snapshot.collected_at,
            decision_type="stay",
            initiation_type=InitiationType.REACTIVE,
            decision_mechanism=DecisionMechanism.DETERMINISTIC,
            decision_basis=DecisionBasis.COMMITMENT_CONFLICT,
            input_snapshot_ref=case.snapshot.snapshot_hash,
            rollback_anchor={
                "prev_focus_contract_version": case.focus_contract.version,
                "prev_active_commitment_ids": [str(case.commitment.id)],
                "prev_claim_statuses": {},
                "policy_version_at_decision": case.policy_version.id,
            },
            policy_version=case.policy_version.id,
            evidence_refs=["reference_flow_stub"],
        )

    def build_claim_stub(self, case: AuroraReferenceFlowCase) -> InsightClaim:
        """Placeholder claim payload for later Wave 1 execution wiring."""

        return InsightClaim(
            id=UUID("77777777-7777-7777-7777-777777777777"),
            user_id=case.snapshot.user_id,
            created_at=case.snapshot.collected_at,
            updated_at=case.snapshot.collected_at,
            claim_type="avoidance_or_fatigue",
            content="用户可能在回避任务，也可能确实疲劳，需探测",
            source=ClaimSource.AURORA_INFERENCE,
            confidence=0.6,
            status=ClaimLifecycle.OPEN,
            projection_policy=ProjectionPolicy.OPEN_DISCUSSABLE,
        )

    def _build_policy_version(self) -> AuroraPolicyVersion:
        variant_registry = [
            InteractionModelConfig(
                variant=InteractionModelVariant.DEFAULT_CONVERSATION,
                context_budget=1200,
                allowed_tools_base=["probe_question", "minimal_session_offer"],
                default_tone="warm_conversational",
                default_proactivity=0.2,
                writable_policy_scope=["ux_intent", "aurora_presence"],
            ),
            InteractionModelConfig(
                variant=InteractionModelVariant.TASK_EXECUTION,
                context_budget=1000,
                allowed_tools_base=["task_breakdown", "checklist_offer"],
                default_tone="structured_precise",
                default_proactivity=0.35,
                writable_policy_scope=["ux_intent", "capability_gate"],
            ),
            InteractionModelConfig(
                variant=InteractionModelVariant.META_REFLECTION,
                context_budget=1500,
                allowed_tools_base=["direct_question", "reconciliation_probe"],
                default_tone="reflective",
                default_proactivity=0.5,
                writable_policy_scope=["ux_intent", "aurora_presence", "capability_gate"],
            ),
            InteractionModelConfig(
                variant=InteractionModelVariant.HOLDING_MODE,
                context_budget=900,
                allowed_tools_base=["emotional_support", "commitment_pause"],
                default_tone="gentle_supportive",
                default_proactivity=0.15,
                writable_policy_scope=["ux_intent", "aurora_presence"],
            ),
        ]
        return AuroraPolicyVersion(
            id="aurora_policy@v1.0",
            version="v1.0",
            created_at=datetime(2026, 4, 17, 0, 0, 0),
            author="human",
            changelog=["Frozen Gate 0 policy stub for wave 0 test fixtures."],
            persona_invariants=PersonaInvariants(),
            audit_invariants=AuditInvariants(),
            proactive_policy=ProactivePolicy(),
            reconciliation_policy=ReconciliationPolicy(),
            continuous_learning_policy=ContinuousLearningPolicy(),
            parameter_write_authority=[
                ParameterWriteAuthority(
                    parameter_name="ux_intent",
                    authority_level=ParameterWriteAuthLevel.AUTO_WRITE,
                )
            ],
            interaction_model_registry=variant_registry,
            materiality_threshold=0.5,
            default_rollback_anchor_schema={
                "prev_focus_contract_version": 0,
                "prev_active_commitment_ids": [],
                "prev_claim_statuses": {},
                "policy_version_at_decision": "aurora_policy@v1.0",
            },
        )


__all__ = ["AuroraReferenceFlowCase", "AuroraReferenceFlowHarness"]
