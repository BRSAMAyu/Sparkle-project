"""Frozen Gate 0 Aurora primitives."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.aurora.common import AuroraSchemaBase
from app.aurora.schemas.enums import (
    AuroraPresenceLevel,
    ClaimLifecycle,
    ClaimSource,
    CommitmentStatus,
    DecisionBasis,
    DecisionMechanism,
    DistilledStrategyLifecycle,
    ImpactClass,
    InitiationType,
    InteractionModelVariant,
    ParameterWriteAuthLevel,
    ProjectionPolicy,
    RetentionTier,
    Shareability,
    UXIntent,
    WindowMode,
    WritePath,
)


class FocusContract(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    version: int
    scenario_pack_id: str
    active_node: str
    focus_description: str
    desire_hypothesis: str | None = None
    commitment_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    created_by: str
    trigger_decision_ref: UUID | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_DISCUSSABLE
    write_path: WritePath = WritePath.SYSTEM_INTERNAL


class Commitment(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    description: str
    node_id: str
    success_criteria: str
    status: CommitmentStatus = CommitmentStatus.PENDING
    created_at: datetime
    activated_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution: str | None = None
    deadline: datetime
    milestone_ids: list[UUID] = Field(default_factory=list)
    witness_ids: list[UUID] = Field(default_factory=list)
    window_override: WindowMode | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_EDITABLE
    write_path: WritePath = WritePath.DIALOGUE_MEDIATED
    shareability: Shareability = Shareability.USER_APPROVED_ABSTRACTABLE


class TransitionDecisionRecord(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    decision_type: str
    proposed_transition: str | None = None
    initiation_type: InitiationType
    decision_mechanism: DecisionMechanism
    decision_basis: DecisionBasis
    input_snapshot_ref: str
    impact_class: ImpactClass = ImpactClass.MEDIUM
    inference_knobs: dict[str, Any] | None = None
    capability_gate: dict[str, Any] | None = None
    interaction_model_variant: InteractionModelVariant = InteractionModelVariant.DEFAULT_CONVERSATION
    rollback_anchor: dict[str, Any]
    evidence_refs: list[str] = Field(default_factory=list)
    policy_version: str
    confirmed_by_user: bool | None = None
    user_feedback: str | None = None
    ux_intent: UXIntent = UXIntent.ROUTINE
    aurora_presence: AuroraPresenceLevel = AuroraPresenceLevel.AMBIENT
    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_DISCUSSABLE


class InsightClaim(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    claim_type: str
    content: str
    source: ClaimSource
    confidence: float
    status: ClaimLifecycle = ClaimLifecycle.OPEN
    probed_at: datetime | None = None
    resolved_at: datetime | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    probe_outcome_ids: list[UUID] = Field(default_factory=list)
    projection_policy: ProjectionPolicy
    write_path: WritePath = WritePath.SYSTEM_INTERNAL
    shareability: Shareability = Shareability.PRIVATE_ONLY


class ProbeOutcome(AuroraSchemaBase):
    id: UUID
    claim_id: UUID
    created_at: datetime
    probe_type: str
    probe_content: str
    result: str
    evidence: str
    confidence_adjustment: float
    evidence_refs: list[str] = Field(default_factory=list)


class IdentityEvidence(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    dimension: str
    evidence_type: str
    description: str
    strength: float
    valence: str
    source: ClaimSource
    evidence_refs: list[str] = Field(default_factory=list)
    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_DISCUSSABLE
    shareability: Shareability = Shareability.USER_APPROVED_ABSTRACTABLE


class WindowState(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    global_mode: WindowMode
    commitment_overrides: dict[str, WindowMode] = Field(default_factory=dict)
    set_by: str
    trigger_decision_ref: UUID | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_EDITABLE
    write_path: WritePath = WritePath.DIALOGUE_MEDIATED


class NodeConfig(AuroraSchemaBase):
    node_id: str
    node_persona: str
    prompt_template: str
    available_tools: list[str] = Field(default_factory=list)
    exit_conditions: list[str] = Field(default_factory=list)
    neighbors: list[str] = Field(default_factory=list)
    transition_triggers: dict[str, str] = Field(default_factory=dict)
    ux_mapping: dict[str, Any] = Field(default_factory=dict)
    default_interaction_model: InteractionModelVariant = InteractionModelVariant.DEFAULT_CONVERSATION
    default_ux_intent: UXIntent = UXIntent.ROUTINE


class ReadinessCriterion(AuroraSchemaBase):
    signal_type: str
    minimum_confidence: float
    required: bool


class ScenarioPackManifest(AuroraSchemaBase):
    id: str
    name: str
    version: str
    description: str
    applicability_conditions: list[str] = Field(default_factory=list)
    target_user_profile: dict[str, Any] = Field(default_factory=dict)
    backbone_nodes: list[NodeConfig] = Field(default_factory=list)
    readiness_criteria: dict[str, ReadinessCriterion] = Field(default_factory=dict)
    default_strategies: dict[str, str] = Field(default_factory=dict)
    ux_mappings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    author: str
    changelog: list[str] = Field(default_factory=list)


class UserScenarioState(AuroraSchemaBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    pack_id: str
    current_node: str
    current_focus_contract_id: UUID
    current_focus_contract_version: int
    drift_from_backbone: str | None = None
    is_on_backbone: bool = True
    overrides: dict[str, Any] = Field(default_factory=dict)
    last_signal: str | None = None
    last_signal_at: datetime | None = None
    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_EDITABLE
    write_path: WritePath = WritePath.DIALOGUE_MEDIATED


class PersonaInvariants(AuroraSchemaBase):
    anti_flattery: bool = True
    directionality: bool = True
    safety: bool = True
    consistency: bool = True
    privacy: bool = True


class AuditInvariants(AuroraSchemaBase):
    all_decisions_logged: bool = True
    decision_mechanism_required: bool = True
    decision_basis_required: bool = True
    evidence_refs_required: bool = True
    rollback_anchor_required: bool = True
    input_snapshot_ref_required: bool = True


class ProactivePolicy(AuroraSchemaBase):
    daily_budget: int = 3
    weekly_budget: int = 10
    allowed_time_windows: list[dict[str, str]] = Field(default_factory=list)
    respect_busy_schedule: bool = True
    minimum_relationship_maturity: float = 0.5
    requires_material_state_change: bool = True
    requires_reason_chain_visible: bool = True


class ReconciliationPolicy(AuroraSchemaBase):
    default_bias: str = "trust_user_single_turn"
    meta_discussion_threshold: int = 3
    meta_timing: str = "natural_breakpoint"
    requires_window_state_ok: bool = True
    claim_on_reconcile: str = "contextualized"


class ContinuousLearningPolicy(AuroraSchemaBase):
    requires_abstraction: bool = True
    requires_deidentification: bool = True
    requires_human_review: bool = True
    human_review_threshold: int = 100
    requires_user_authorization: bool = True
    requires_quality_gate: bool = True
    cooldown_monitoring: bool = True
    auto_downgrade_on_negative_signal: bool = True


class ParameterWriteAuthority(AuroraSchemaBase):
    parameter_name: str
    authority_level: ParameterWriteAuthLevel
    requires_confirmation: bool = True
    origin_trail_required: bool = True


class InteractionModelConfig(AuroraSchemaBase):
    variant: InteractionModelVariant
    context_budget: int
    allowed_tools_base: list[str] = Field(default_factory=list)
    default_tone: str
    default_proactivity: float
    writable_policy_scope: list[str] = Field(default_factory=list)


class AuroraPolicyVersion(AuroraSchemaBase):
    id: str
    version: str
    created_at: datetime
    author: str
    changelog: list[str] = Field(default_factory=list)
    persona_invariants: PersonaInvariants
    audit_invariants: AuditInvariants
    proactive_policy: ProactivePolicy
    reconciliation_policy: ReconciliationPolicy
    continuous_learning_policy: ContinuousLearningPolicy
    parameter_write_authority: list[ParameterWriteAuthority] = Field(default_factory=list)
    interaction_model_registry: list[InteractionModelConfig] = Field(default_factory=list)
    materiality_threshold: float = 0.5
    default_rollback_anchor_schema: dict[str, Any] = Field(default_factory=dict)


class SparkleRelationshipState(AuroraSchemaBase):
    user_id: UUID
    relationship_maturity: float = 0.0
    communication_style_emergent: str | None = None
    interaction_count: int = 0
    last_interaction_at: datetime | None = None
    shared_history_highlights: list[str] = Field(default_factory=list)
    bound_policy_version: str


class DistilledStrategy(AuroraSchemaBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    title: str
    description: str
    strategy_type: str
    status: DistilledStrategyLifecycle = DistilledStrategyLifecycle.DISTILLED
    applicability_scope: str
    contraindications: list[str] = Field(default_factory=list)
    evidence_strength: float = 0.0
    diversity_score: float = 0.0
    safety_audit: dict[str, bool] | None = None
    source_trajectory_type: str
    attribution_count: int = 0
    deidentification_verified: bool = False
    user_authorization: bool | None = None
    projection_policy: ProjectionPolicy = ProjectionPolicy.SENSITIVE_MEDIATED
    shareability: Shareability = Shareability.PRIVATE_ONLY
    application_count: int = 0
    satisfaction_after_application: float | None = None
    cooldown_status: str = "active"


class SignalSnapshot(AuroraSchemaBase):
    snapshot_hash: str
    user_id: UUID
    collected_at: datetime
    scenario_pack_id: str
    policy_version: str
    core_signals: dict[str, Any]
    enhanced_signals: dict[str, Any] = Field(default_factory=dict)
    optional_signals: dict[str, Any] = Field(default_factory=dict)
    signal_freshness: dict[str, datetime] = Field(default_factory=dict)
    stale_signals: list[str] = Field(default_factory=list)
    total_tokens: int = 0
    budget_limit: int = 4000
    distilled_strategy_refs: list[UUID] = Field(default_factory=list)
    retention_tier: RetentionTier = RetentionTier.HOT
    summary_digest: str | None = None

