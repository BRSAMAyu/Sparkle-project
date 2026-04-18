# SPARKLE AURORA GATE 0 — Schema & Contract Specification

> **Version**: 1.0-frozen
> **Date**: 2026-04-17
> **Status**: FROZEN — Gate 0 complete
> **Principle**: "可治理优于更聪明" (Governability over cleverness)
> **Timebox**: 5 working days from first draft

---

## 0. Constitutional Rules

1. **Append-only invariant**: Every primitive marked append-only never mutates existing records. Corrections, status changes, and reversals are new records.
2. **Materiality threshold**: Defined in `AuroraPolicyVersion`, not as code constants.
3. **Rollback anchor**: Composite snapshot `{prev_focus_contract_version, prev_active_commitment_ids, prev_claim_statuses, policy_version_at_decision}`.
4. **Field disputes >30min**: Tag as `provisional` with 1-line comment, defer to Gate 1.
5. **No new concepts after Gate 0 freeze**: New ideas go to Gate 1 backlog.
6. **Reference flow rule**: Any field that cannot be placed in a real reference flow is deleted immediately.

---

## 1. Common Enums

```python
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

# === Decision ===
class DecisionMechanism(str, Enum):
    DETERMINISTIC = "deterministic"
    BAYESIAN = "bayesian"
    LLM = "llm"
    HYBRID = "hybrid"

class DecisionBasis(str, Enum):
    USER_REPORT = "user_report"
    BEHAVIORAL_SIGNAL = "behavioral_signal"
    COMMITMENT_CONFLICT = "commitment_conflict"
    SCHEDULE_CONSTRAINT = "schedule_constraint"
    ENERGY_DROP = "energy_drop"
    PARTNER_SIGNAL = "partner_signal"
    KNOWLEDGE_GAP = "knowledge_gap"
    MIXED = "mixed"

class ImpactClass(str, Enum):
    LOW = "low"                    # simple Q&A, no system state change
    MEDIUM = "medium"              # moderate relevance, routine adjustment
    HIGH = "high"                  # significant, triggers Aurora deliberation
    CRITICAL = "critical"          # crisis / major deviation / safety concern

class InitiationType(str, Enum):
    REACTIVE = "reactive"          # strong signal event
    SCHEDULED = "scheduled"        # session rhythm point
    ON_DEMAND = "on_demand"        # user explicitly asks
    PROACTIVE = "proactive"        # Aurora-initiated

# === Claims ===
class ClaimSource(str, Enum):
    AURORA_INFERENCE = "aurora_inference"
    USER_REPORT = "user_report"
    USER_CORRECTION = "user_correction"
    BEHAVIORAL_SIGNAL = "behavioral_signal"
    SYSTEM_SENSOR = "system_sensor"
    PARTNER_REPORT = "partner_report"

class ClaimLifecycle(str, Enum):
    OPEN = "open"
    PROBED = "probed"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    EXPIRED = "expired"
    CONTEXTUALIZED = "contextualized"   # re-interpreted after reconciliation

# === Window ===
class WindowMode(str, Enum):
    COMMITMENT = "commitment"      # heads-down execution, no goal revision
    ITERATION = "iteration"        # sampling, reflection, model update

# === Commitment ===
class CommitmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    VIOLATED = "violated"
    RENEGOTIATED = "renegotiated"

# === Governance ===
class ProjectionPolicy(str, Enum):
    OPEN_EDITABLE = "open_editable"                  # user can see and directly edit
    OPEN_DISCUSSABLE = "open_discussable"             # visible, changeable only via dialogue/evidence
    SENSITIVE_MEDIATED = "sensitive_mediated"         # shown contextually by Sparkle, not raw params
    INTERNAL = "internal"                             # never shown to user

class WritePath(str, Enum):
    UI_ONLY = "ui_only"                               # only via settings UI
    DIALOGUE_MEDIATED = "dialogue_mediated"           # via conversation + structured confirmation
    POLICY_ONLY = "policy_only"                       # only via AuroraPolicyVersion upgrade
    SYSTEM_INTERNAL = "system_internal"                # system-managed, not user-facing

class Shareability(str, Enum):
    PRIVATE_ONLY = "private_only"
    USER_APPROVED_ABSTRACTABLE = "user_approved_abstractable"
    SYSTEM_ABSTRACTABLE = "system_abstractable"
    PUBLIC_SEED_CANDIDATE = "public_seed_candidate"

# === Parameter Write ===
class ParameterWriteAuthLevel(str, Enum):
    AUTO_WRITE = "auto_write"                          # Aurora can write directly
    SUGGEST_CONFIRM = "suggest_confirm"                # Aurora suggests, user confirms
    EXPLICIT_CONFIRM_ONLY = "explicit_confirm_only"    # user must explicitly request

# === Learning ===
class DistilledStrategyLifecycle(str, Enum):
    DISTILLED = "distilled"                            # draft, pending review
    USER_REVIEWED = "user_reviewed"                    # user confirmed content
    USER_PRIVATE = "user_private"                      # private to source user
    COMMUNITY_SHARED = "community_shared"              # shared across users (after gate)
    RETIRED = "retired"                                # deprecated / quality issue

# === Signal ===
class SignalTier(str, Enum):
    CORE = "core"                  # must exist for Aurora to run
    ENHANCED = "enhanced"          # improves decision quality
    OPTIONAL = "optional"          # nice to have

class RetentionTier(str, Enum):
    HOT = "hot"                                      # 30 days, full access
    COLD_ARCHIVE = "cold_archive"                    # 2 years, material decisions only
    RECONSTRUCTABLE = "reconstructable"              # hash + summary only, data purged

# === Interaction Layer ===
class InteractionModelVariant(str, Enum):
    DEFAULT_CONVERSATION = "default_conversation"    # daily low-weight dialogue
    TASK_EXECUTION = "task_execution"                # structured task interaction
    META_REFLECTION = "meta_reflection"              # reconciliation/identity/deep calibration (Aurora frame)
    HOLDING_MODE = "holding_mode"                    # crisis/energy collapse companionship

class UXIntent(str, Enum):
    ROUTINE = "routine"                              # normal conversation
    ACTIVE_ADJUSTMENT = "active_adjustment"          # Aurora made visible update
    META_SURFACE = "meta_surface"                    # deep dialogue frame
    RECONCILIATION = "reconciliation"                # reconciliation moment
    IDENTITY_MOMENT = "identity_moment"              # identity-layer dialogue
    HOLDING = "holding"                              # crisis/holding frame

class AuroraPresenceLevel(str, Enum):
    AMBIENT = "ambient"                              # always-on, mirror bar subtle pulse
    ACTIVE = "active"                                # actual update happened, shallow visibility
    META_SURFACE = "meta_surface"                    # deep dialogue frame activated
```

---

## 2. Eleven Primitives

### 2.1 FocusContract

```
Current focus anchor. Live object with version chain.
Current version reference stored in UserScenarioState for O(1) lookup.
This object type is append-only. Corrections are new records, never mutations.
```

```python
class FocusContract(BaseModel):
    id: UUID
    user_id: UUID
    version: int                                       # incrementing
    scenario_pack_id: str
    active_node: str                                   # current graph node identifier

    focus_description: str                             # human-readable
    desire_hypothesis: Optional[str] = None            # what user wants, updated over time

    commitment_ids: List[UUID] = []                    # active commitments under this focus

    created_at: datetime
    created_by: str                                    # "aurora" | "user" | "system"
    trigger_decision_ref: Optional[UUID] = None        # TransitionDecisionRecord.id
    evidence_refs: List[str] = []

    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_DISCUSSABLE
    write_path: WritePath = WritePath.SYSTEM_INTERNAL  # emitted by Aurora decisions, not user-writable
```

**Relationships**: Referenced by `UserScenarioState.current_focus_contract_version`. Version chain is linked list of same `id` with incrementing `version`.

---

### 2.2 Commitment

```
Commitment object with lifecycle and witnesses.
Persists across multiple FocusContracts — it is NOT a field of FocusContract.
This object type is append-only. Status transitions are new records, never mutations.
```

```python
class Commitment(BaseModel):
    id: UUID
    user_id: UUID

    description: str                                   # what the user committed to
    node_id: str                                       # graph node this binds to
    success_criteria: str                              # how to verify fulfillment

    status: CommitmentStatus = CommitmentStatus.PENDING
    created_at: datetime
    activated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None

    deadline: datetime
    milestone_ids: List[UUID] = []

    witness_ids: List[UUID] = []                       # accountability partners
    window_override: Optional[WindowMode] = None       # per-commitment window

    evidence_refs: List[str] = []

    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_EDITABLE
    write_path: WritePath = WritePath.DIALOGUE_MEDIATED
    shareability: Shareability = Shareability.USER_APPROVED_ABSTRACTABLE
```

**Relationships**: Referenced by `FocusContract.commitment_ids`, `WindowState.commitment_overrides`, `TransitionDecisionRecord.rollback_anchor`.

---

### 2.3 TransitionDecisionRecord

```
Aurora's decision record. Append-only audit trail.
Every material Aurora decision produces one record.
This object type is append-only. Reversals are new records, never mutations.
```

```python
class TransitionDecisionRecord(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime

    decision_type: str                                 # "transition" | "stay" | "proactive_initiation"
    proposed_transition: Optional[str] = None          # target node; None = stay
    initiation_type: InitiationType

    # MANDATORY: how and why
    decision_mechanism: DecisionMechanism
    decision_basis: DecisionBasis

    # Input traceability
    input_snapshot_ref: str                            # SignalSnapshot.snapshot_hash

    # Aurora 6-class outputs (split into InferenceKnobs + CapabilityGate)
    impact_class: ImpactClass = ImpactClass.MEDIUM
    inference_knobs: Optional[Dict[str, Any]] = None
    #   Expected keys: temperature, retrieval_k, prompt_template, recall_strategy, tone
    capability_gate: Optional[Dict[str, Any]] = None
    #   Expected keys: allowed_tools, disabled_tools, writable_cards, triggerable_events

    # Interaction model selection (explicit, not buried in capability_gate)
    interaction_model_variant: InteractionModelVariant = InteractionModelVariant.DEFAULT_CONVERSATION

    # Rollback
    rollback_anchor: Dict[str, Any]
    #   {prev_focus_contract_version, prev_active_commitment_ids,
    #    prev_claim_statuses, policy_version_at_decision}

    evidence_refs: List[str] = []
    policy_version: str

    # User confirmation (for material decisions)
    confirmed_by_user: Optional[bool] = None
    user_feedback: Optional[str] = None

    # UX projection (how this decision manifests to the user)
    ux_intent: UXIntent = UXIntent.ROUTINE
    aurora_presence: AuroraPresenceLevel = AuroraPresenceLevel.AMBIENT

    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_DISCUSSABLE
```

**Relationships**: References `SignalSnapshot` via `input_snapshot_ref`. References `AuroraPolicyVersion` via `policy_version`. Referenced by `FocusContract.trigger_decision_ref`.

---

### 2.4 InsightClaim

```
Testable hypothesis about the user. Six sources unified.
Claims are the unit of knowledge about the user — not raw data, not conclusions.
This object type is append-only. Status transitions are new records, never mutations.
```

```python
class InsightClaim(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    claim_type: str           # e.g., "avoidance_pattern", "energy_state", "knowledge_gap"
    content: str              # the hypothesis statement
    source: ClaimSource
    confidence: float         # 0.0–1.0

    status: ClaimLifecycle = ClaimLifecycle.OPEN
    probed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    evidence_refs: List[str] = []
    probe_outcome_ids: List[UUID] = []

    projection_policy: ProjectionPolicy
    write_path: WritePath = WritePath.SYSTEM_INTERNAL
    shareability: Shareability = Shareability.PRIVATE_ONLY
```

**Relationships**: Referenced by `ProbeOutcome.claim_id`. Referenced in `TransitionDecisionRecord.rollback_anchor.prev_claim_statuses`.

---

### 2.5 ProbeOutcome

```
Result of a directed verification action against an InsightClaim.
This object type is append-only.
```

```python
class ProbeOutcome(BaseModel):
    id: UUID
    claim_id: UUID                                     # ref to InsightClaim
    created_at: datetime

    probe_type: str       # "direct_question" | "behavioral_observation" | "partner_check"
    probe_content: str    # what was asked or observed

    result: str           # "confirmed" | "partially_confirmed" | "refuted" | "inconclusive"
    evidence: str         # what was learned
    confidence_adjustment: float  # delta applied to source claim confidence

    evidence_refs: List[str] = []
```

**Relationships**: References `InsightClaim.id`. Listed in `InsightClaim.probe_outcome_ids`.

---

### 2.6 IdentityEvidence

```
Evidence structure for identity tracking. Not labels — accumulated proof.
Behavior → evidence → identity hypothesis update.
This object type is append-only. Identity is accumulated evidence, not labels.
```

```python
class IdentityEvidence(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime

    dimension: str          # "resilience" | "consistency" | "initiative" | "adaptability" | ...
    evidence_type: str      # "behavioral" | "verbal" | "outcome" | "partner_observation"
    description: str        # what happened

    strength: float         # 0.0–1.0, how strongly this supports the dimension
    valence: str            # "supporting" | "contradicting" | "nuancing"

    source: ClaimSource
    evidence_refs: List[str] = []

    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_DISCUSSABLE
    shareability: Shareability = Shareability.USER_APPROVED_ABSTRACTABLE
```

**Relationships**: Consumed by Aurora when updating user model. Contributes to long-term identity hypothesis.

---

### 2.7 WindowState

```
Commitment/iteration window state. Global default + per-commitment overrides.
This object type is append-only. Window changes are new records, never mutations.
```

```python
class WindowState(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime

    global_mode: WindowMode
    commitment_overrides: Dict[str, WindowMode] = {}  # commitment_id → window_mode

    set_by: str                                        # "aurora" | "user" | "policy"
    trigger_decision_ref: Optional[UUID] = None
    evidence_refs: List[str] = []

    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_EDITABLE
    write_path: WritePath = WritePath.DIALOGUE_MEDIATED
```

**Relationships**: `commitment_overrides` keys reference `Commitment.id`.

---

### 2.8 ScenarioPackManifest

```
Read-only scenario template. Users don't modify this.
Former expert system content migrated into node_persona fields.
Not append-only — it is an immutable template with versioned releases.
```

```python
class NodeConfig(BaseModel):
    node_id: str
    node_persona: str                                  # migrated from expert system
    prompt_template: str
    available_tools: List[str]
    exit_conditions: List[str]
    neighbors: List[str]                               # allowed transitions
    transition_triggers: Dict[str, str]                # condition → target_node
    ux_mapping: Dict[str, Any]
    default_interaction_model: InteractionModelVariant = InteractionModelVariant.DEFAULT_CONVERSATION
    default_ux_intent: UXIntent = UXIntent.ROUTINE

class ReadinessCriterion(BaseModel):
    signal_type: str
    minimum_confidence: float
    required: bool

class ScenarioPackManifest(BaseModel):
    id: str                                            # versioned: "exam_prep_14d@v1.2"
    name: str
    version: str
    description: str

    applicability_conditions: List[str]
    target_user_profile: Dict[str, Any]

    backbone_nodes: List[NodeConfig]
    readiness_criteria: Dict[str, ReadinessCriterion]

    default_strategies: Dict[str, str]
    ux_mappings: Dict[str, Any]

    created_at: datetime
    author: str                                        # "human" | "system" | "hybrid"
    changelog: List[str] = []
```

**Relationships**: Referenced by `UserScenarioState.pack_id`. `readiness_criteria` drives Aurora's sufficiency check before planning begins.

---

### 2.9 UserScenarioState

```
User's mutable state on current scenario pack.
This is a mutable live object. Changes are mediated by TransitionDecisions.
Current FocusContract version stored here for O(1) lookup — no chain traversal.
NOT append-only — it IS the current state view. History is in FocusContract versions and TransitionDecisions.
```

```python
class UserScenarioState(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    pack_id: str                                       # active ScenarioPackManifest.id
    current_node: str                                  # current backbone node
    current_focus_contract_id: UUID
    current_focus_contract_version: int                # O(1) lookup

    drift_from_backbone: Optional[str] = None
    is_on_backbone: bool = True

    overrides: Dict[str, Any] = {}                     # user-specific deviations from pack defaults

    last_signal: Optional[str] = None
    last_signal_at: Optional[datetime] = None

    projection_policy: ProjectionPolicy = ProjectionPolicy.OPEN_EDITABLE
    write_path: WritePath = WritePath.DIALOGUE_MEDIATED
```

**Relationships**: References `ScenarioPackManifest.id` and `FocusContract`.

---

### 2.10 AuroraPolicyVersion

```
Versioned policy configuration. Immutable once published (new version = new record).
Contains all governance sub-policies and interaction model registry.
This object type is append-only. New policies are new records, never mutations.

NOTE: Per-user relationship state (PersonaState) is NOT stored here.
It is extracted as SparkleRelationshipState — a per-user derived view.
See Section 2.10b.
```

```python
class PersonaInvariants(BaseModel):
    """Hard boundaries for Sparkle personality. Immutable by Aurora itself."""
    anti_flattery: bool = True                         # honest disagreement > false agreement
    directionality: bool = True                        # guide toward user's stated positive direction
    safety: bool = True                                # no self-harm / harmful behavior encouragement
    consistency: bool = True                           # same user sees consistent Sparkle across sessions
    privacy: bool = True                               # no cross-user leakage of individual details

class AuditInvariants(BaseModel):
    """System-level auditability requirements. Parallel to persona_invariants."""
    all_decisions_logged: bool = True
    decision_mechanism_required: bool = True
    decision_basis_required: bool = True
    evidence_refs_required: bool = True
    rollback_anchor_required: bool = True
    input_snapshot_ref_required: bool = True

class ProactivePolicy(BaseModel):
    """Constraints on Aurora's proactive initiation."""
    daily_budget: int = 3
    weekly_budget: int = 10
    allowed_time_windows: List[Dict[str, str]] = []    # [{"start": "09:00", "end": "21:00"}]
    respect_busy_schedule: bool = True
    minimum_relationship_maturity: float = 0.5
    requires_material_state_change: bool = True
    requires_reason_chain_visible: bool = True

class ReconciliationPolicy(BaseModel):
    """How to handle user-system disagreements."""
    default_bias: str = "trust_user_single_turn"
    meta_discussion_threshold: int = 3                 # after N same-type reconciliations
    meta_timing: str = "natural_breakpoint"            # + WindowState allows + conversation break
    requires_window_state_ok: bool = True
    claim_on_reconcile: str = "contextualized"

class ContinuousLearningPolicy(BaseModel):
    """Governance for cross-user learning."""
    requires_abstraction: bool = True
    requires_deidentification: bool = True
    requires_human_review: bool = True
    human_review_threshold: int = 100                  # first N items need human review
    requires_user_authorization: bool = True
    requires_quality_gate: bool = True
    cooldown_monitoring: bool = True
    auto_downgrade_on_negative_signal: bool = True

class ParameterWriteAuthority(BaseModel):
    """Per-parameter write permission declaration."""
    parameter_name: str
    authority_level: ParameterWriteAuthLevel
    requires_confirmation: bool = True
    origin_trail_required: bool = True

class InteractionModelConfig(BaseModel):
    """Configuration for one interaction model variant."""
    variant: InteractionModelVariant
    context_budget: int                                # token budget for this variant
    allowed_tools_base: List[str]                      # baseline tool permissions
    default_tone: str                                  # e.g., "warm_conversational", "structured_precise"
    default_proactivity: float                         # 0.0–1.0
    writable_policy_scope: List[str]                   # which policy fields this variant can write to

class AuroraPolicyVersion(BaseModel):
    id: str                                            # versioned: "aurora_policy@v1.0"
    version: str
    created_at: datetime
    author: str                                        # "human" | "system_upgrade"
    changelog: List[str] = []

    persona_invariants: PersonaInvariants
    audit_invariants: AuditInvariants
    proactive_policy: ProactivePolicy
    reconciliation_policy: ReconciliationPolicy
    continuous_learning_policy: ContinuousLearningPolicy
    parameter_write_authority: List[ParameterWriteAuthority]

    interaction_model_registry: List[InteractionModelConfig]

    materiality_threshold: float = 0.5
    default_rollback_anchor_schema: Dict[str, Any]
```

**Relationships**: Referenced by `TransitionDecisionRecord.policy_version`. `interaction_model_registry` defines the allowed interaction model variants and their configurations.

### 2.10b SparkleRelationshipState (provisional)

```
Per-user, mutable. Sparkle's relationship with a specific user.
Evolution happens within AuroraPolicyVersion.persona_invariants boundaries.
This is a DERIVED VIEW: computed from InsightClaims + IdentityEvidence + interaction metadata.
Persistence form (cached or pure-derived) to be decided in Gate 1 — currently marked provisional.
```

```python
class SparkleRelationshipState(BaseModel):
    """Per-user relationship state. Emerges from interaction, not pre-set."""
    user_id: UUID
    relationship_maturity: float = 0.0                 # 0.0–1.0
    communication_style_emergent: Optional[str] = None # discovered through interaction
    interaction_count: int = 0
    last_interaction_at: Optional[datetime] = None
    shared_history_highlights: List[str] = []
    bound_policy_version: str                          # which AuroraPolicyVersion's invariants apply
```

---

### 2.11 DistilledStrategy

```
Distilled reusable strategy from successful attribution.
Evolution of Seed Library — system-extracted, user-confirmed, quality-gated.
This object type is append-only. Lifecycle transitions are new records, never mutations.
```

```python
class DistilledStrategy(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime

    title: str
    description: str                                   # high-density, actionable
    strategy_type: str                                 # "motivation" | "planning" | "recovery" | "anti_avoidance" | ...

    status: DistilledStrategyLifecycle = DistilledStrategyLifecycle.DISTILLED

    applicability_scope: str                           # when this strategy is relevant
    contraindications: List[str] = []                  # when NOT to use

    evidence_strength: float = 0.0                     # how many successful attributions
    diversity_score: float = 0.0                       # cross-profile replication
    safety_audit: Optional[Dict[str, bool]] = None     # persona_invariants compliance check

    source_trajectory_type: str                        # what kind of journey produced this
    attribution_count: int = 0
    deidentification_verified: bool = False
    user_authorization: Optional[bool] = None

    projection_policy: ProjectionPolicy = ProjectionPolicy.SENSITIVE_MEDIATED
    shareability: Shareability = Shareability.PRIVATE_ONLY

    application_count: int = 0
    satisfaction_after_application: Optional[float] = None
    cooldown_status: str = "active"                    # "active" | "under_review" | "downgraded"
```

**Relationships**: Referenced by `SignalSnapshot.distilled_strategy_refs`. Matures from `DISTILLED` → `COMMUNITY_SHARED` through the continuous learning pipeline. Designers can promote mature strategies into `ScenarioPackManifest` node configs.

---

## 3. Aurora I/O Contract

### 3.0 Aurora Output Discipline (Constitutional)

```
Aurora outputs: frame / knobs / gate / decision / claim / evidence.
Aurora NEVER directly produces user-facing text.

User-facing text is rendered by InteractionModel variants, guided by Aurora's
InferenceKnobs + CapabilityGate + UXIntent + AuroraPresenceLevel.

This principle ensures: audit chain integrity, safety filter interception,
rollback granularity, and Aurora testability.

Any future design that violates this principle (regardless of appeal)
MUST go through formal AuroraPolicyVersion upgrade. No shortcuts.
```

### 3.1 Aurora's Input: SignalSnapshot

```
Aggregated input for Aurora. Produced by SignalAggregator middleware.
Aurora only consumes — it never pulls from individual services.
Not a persistent primitive, but structure is frozen in Gate 0.
Each TransitionDecisionRecord binds to one snapshot via input_snapshot_ref.
```

```python
class SignalSnapshot(BaseModel):
    snapshot_hash: str                                 # deterministic hash for addressing
    user_id: UUID
    collected_at: datetime
    scenario_pack_id: str
    policy_version: str

    core_signals: Dict[str, Any]                       # MUST exist for Aurora to run
    enhanced_signals: Dict[str, Any] = {}              # improves quality
    optional_signals: Dict[str, Any] = {}              # nice to have

    signal_freshness: Dict[str, datetime] = {}         # signal_key → collected_at
    stale_signals: List[str] = []                      # past validity window

    total_tokens: int = 0
    budget_limit: int = 4000

    distilled_strategy_refs: List[UUID] = []           # strategies considered relevant

    retention_tier: RetentionTier = RetentionTier.HOT
    summary_digest: Optional[str] = None               # for cold archive / reconstruction
```

### 3.2 Signal Aggregation Responsibility

| Component | Responsibility |
|-----------|---------------|
| **SignalAggregator** | Pulls from all services, assembles SignalSnapshot, manages budget and freshness |
| **Aurora** | Pure decision function: SignalSnapshot + PolicyVersion → Decision |
| **SignalProcessor** | Consumes Aurora decisions, executes writes to downstream systems |
| **Existing services** | Continue owning their data. Aurora reads via aggregator, writes via processor |

### 3.3 Aurora's 6 Output Classes

| Output | Description | Carrier |
|--------|-------------|---------|
| `ImpactClass` | How important is this situation? Low/medium/high/critical | TransitionDecisionRecord field |
| `FocusContract` | What should the user focus on? | Emits new FocusContract version |
| `WindowState` | Should we be in commitment or iteration mode? | Emits new WindowState record |
| `TransitionDecision` | Should user stay, transition, or is this a proactive initiation? | Emits TransitionDecisionRecord |
| `InferenceKnobs` | How should the interaction model respond? (tone, temperature, retrieval) | TransitionDecisionRecord.inference_knobs |
| `CapabilityGate` | What tools/cards/events are allowed at this node? | TransitionDecisionRecord.capability_gate |

### 3.4 Write Authority Matrix

| Target | Who writes | Via |
|--------|-----------|-----|
| UserProfile signals | SignalProcessor (from Aurora claims) | Claim confirmation → profile update |
| FocusContract | SignalProcessor (from Aurora decision) | New version append |
| Commitment | SignalProcessor (from Aurora/user dialogue) | Status transition record |
| InsightClaim | Aurora (claims) + User (corrections) | New claim record |
| UserScenarioState | SignalProcessor (from Aurora decision) | Mutable update |
| ScenarioPackManifest | Designers only (human authorship) | New versioned pack |
| AuroraPolicyVersion | Designers / system upgrade | New versioned policy |
| DistilledStrategy | Continuous learning pipeline | Lifecycle transition |

---

## 4. Reference Flows

### 4.1 Main Flow: 14-Day Exam Prep, Day 3 — "I don't want to do this today"

```
PREREQUISITES:
  FocusContract#FC1 version=3, active_node="day3_execution"
  Commitment#C1 status=active, deadline=T+11d, description="完成热力学前5章"
  WindowState#WS1 global_mode=commitment
  UserScenarioState current_node="day3_execution", is_on_backbone=True
  ScenarioPackManifest "exam_prep_14d@v1.0"

t=0   user.message: "我今天不想做"

t=1   SignalAggregator → assemble SignalSnapshot#SS_01
      ├─ core: UserProfile(user_id, goals, preferences)
      │         FocusContract#FC1(v3, node=day3_execution)
      │         Commitment#C1(active, deadline=T+11d)
      │         WindowState#WS1(global=commitment)
      ├─ enhanced: TaskCompletion(recent_7d=60%, trend=declining)
      │            BehavioralSignal(late_night_study, 3_consecutive)
      ├─ optional: PartnerReport(last=5d_ago, status=stale)
      ├─ stale_signals: ["partner_report"]
      ├─ distilled_strategy_refs: [DS#motivation_low_energy]
      ├─ total_tokens: 2800, budget_limit: 4000
      └─ snapshot_hash: "ss_a1b2c3d4"

t=2   Aurora.trigger(type=reactive)
      └─ materiality_check(ss=SS_01, threshold=0.5)
         └─ PASSED: user message conflicts with active Commitment#C1
            (signal_conflict + commitment_active + commitment_window)

t=3   Aurora.deliberate(snapshot=SS_01, policy=APV@v1.0)
      │
      ├─ EMIT InsightClaim#IC1
      │  ├─ claim_type: "avoidance_or_fatigue"
      │  ├─ content: "用户可能在回避任务，也可能确实疲劳，需探测"
      │  ├─ source: aurora_inference
      │  ├─ confidence: 0.6
      │  ├─ status: open
      │  ├─ projection_policy: open_discussable
      │  └─ write_path: system_internal
      │
      └─ EMIT TransitionDecisionRecord#TDR1
         ├─ decision_type: "stay"
         ├─ proposed_transition: None (stay on day3_execution)
         ├─ initiation_type: reactive
         ├─ decision_mechanism: deterministic
         │  (rule: commitment_active + user_conflict → stay + probe)
         ├─ decision_basis: commitment_conflict
         ├─ input_snapshot_ref: "ss_a1b2c3d4"
         ├─ InferenceKnobs: {
         │    "tone": "协商",
         │    "temperature": 0.6,
         │    "retrieval_k": 3,
         │    "prompt_template": "commitment_conflict_probe"
         │  }
         ├─ CapabilityGate: {
         │    "allowed_tools": ["minimal_session_offer", "probe_question"],
         │    "disabled_tools": ["reschedule", "new_plan_generation"],
         │    "writable_cards": [],
         │    "triggerable_events": []
         │  }
         ├─ rollback_anchor: {
         │    "prev_focus_contract_version": 3,
         │    "prev_active_commitment_ids": ["C1"],
         │    "prev_claim_statuses": {},
         │    "policy_version_at_decision": "aurora_policy@v1.0"
         │  }
         ├─ evidence_refs: ["user_msg_t0", "commitment_C1", "task_completion_60%"]
         ├─ policy_version: "aurora_policy@v1.0"
         ├─ ux_intent: active_adjustment
         ├─ aurora_presence: active
         └─ confirmed_by_user: None (not required for "stay" decision)

      ux_projection:
        ├─ aurora_presence: active              # Aurora made a real decision
        ├─ interaction_model_variant: default_conversation
        ├─ ux_intent: active_adjustment
        ├─ mirror_bar_pulse: subtle             # gentle pulse showing system is aware
        └─ conversation_frame: unchanged

t=4   Interaction Layer renders response (guided by InferenceKnobs + CapabilityGate)
      └─ "嗯，我记得你最近几天都在坚持。我想和你确认——是真的需要休息，
          还是有点想回避了？我们不一定要今天做满，但不如做一个最小版本？
          花20分钟看一章？这样既尊重你的状态，也不打断节奏。"

t=5   user.message: "好吧，就是有点累，不是因为不想做"

t=6   SignalAggregator → assemble SignalSnapshot#SS_02
      └─ updated with user clarification

t=7   Aurora.trigger(type=reactive)
      │
      ├─ UPDATE InsightClaim#IC1
      │  ├─ status: contextualized  (user explained: fatigue, not avoidance)
      │  └─ updated_at: now
      │
      ├─ EMIT ProbeOutcome#PO1
      │  ├─ claim_id: IC1
      │  ├─ probe_type: "direct_question"
      │  ├─ result: "partially_confirmed"
      │  ├─ evidence: "用户自述疲劳，非回避。动机完整，能量不足。"
      │  └─ confidence_adjustment: -0.1
      │
      └─ NO new TransitionDecision (stay on backbone, no state change)

t=8   Interaction Layer renders response
      └─ "谢谢你的坦诚。辛苦了。那我们今天就做一个最轻量的版本——
          20分钟复习昨天看过的，不学新东西。既不打断节奏，也不勉强你。
          早点休息，明天继续。"
```

---

### 4.2 Annex Flow A: Crash Recovery — User reports family emergency mid-prep

```
PREREQUISITES:
  FocusContract#FC2 version=5, active_node="day7_execution"
  Commitment#C1 status=active, deadline=T+7d
  WindowState#WS2 global_mode=commitment
  UserScenarioState current_node="day7_execution", is_on_backbone=True

t=0   user.message: "我家里出事了，最近可能没法继续"

t=1   SignalAggregator → SignalSnapshot#SS_10
      ├─ core: (standard) + user_message_high_severity
      ├─ enhanced: EnergyState(sharp_drop_detected)

t=2   Aurora.trigger(type=reactive)
      └─ materiality_check: PASSED (severity=high, conflicts with commitment)

t=3   Aurora.deliberate(snapshot=SS_10, policy=APV@v1.0)
      │
      ├─ EMIT InsightClaim#IC10
      │  ├─ claim_type: "life_disruption"
      │  ├─ content: "用户遭遇重大生活变故，当前目标可能需要暂停或调整"
      │  ├─ source: user_report
      │  ├─ confidence: 0.9
      │  └─ status: open
      │
      ├─ EMIT TransitionDecisionRecord#TDR10
      │  ├─ decision_type: "transition"
      │  ├─ proposed_transition: "crisis_recovery"
      │  ├─ initiation_type: reactive
      │  ├─ decision_mechanism: deterministic
      │  ├─ decision_basis: user_report
      │  ├─ InferenceKnobs: {"tone": "关怀", "temperature": 0.3, "prompt_template": "crisis_response"}
      │  ├─ CapabilityGate: {
      │  │    "allowed_tools": ["emotional_support", "commitment_pause"],
      │  │    "disabled_tools": ["task_assignment", "schedule_push", "achievement_check"],
      │  │    "triggerable_events": ["partner_notify_if_witnessed"]
      │  │  }
      │  └─ confirmed_by_user: True (required for transition off backbone)
      │
      ux_projection:
        ├─ aurora_presence: meta_surface        # deep intervention activated
        ├─ interaction_model_variant: holding_mode
        ├─ ux_intent: holding
        ├─ mirror_bar_pulse: attentive          # heightened awareness indicator
        └─ conversation_frame: softened (reduced pace, no task card prompts)

      ├─ EMIT WindowState#WS3
      │  ├─ global_mode: iteration (switch from commitment to iteration)
      │  └─ set_by: "aurora"
      │
      └─ EMIT FocusContract#FC2 version=6
         ├─ active_node: "crisis_recovery"
         ├─ desire_hypothesis: (unchanged, desire track continues in parallel)
         └─ is_on_backbone: False (off-backbone transition)

t=4   SignalProcessor executes:
      ├─ Pause Commitment#C1 → status: renegotiated (with timeline TBD)
      ├─ Update UserScenarioState → current_node="crisis_recovery", is_on_backbone=False

t=5   Interaction Layer renders:
      └─ "听到这个消息我很抱歉。你现在最重要的是处理好这件事。
          备考的事情我们先按下不表，不会消失，等你准备好了随时继续。
          如果你需要找人聊聊，我一直在。"

t=6   [Async] Aurora schedules:
      └─ proactive check-in after 48h (within proactive_policy daily_budget)
         with CapabilityGate tuned to emotional support only
```

---

### 4.3 Annex Flow B: Accountability Partner Reports Concern

```
PREREQUISITES:
  Commitment#C1 has witness_ids=[Partner#P1]
  FocusContract#FC3 version=4, active_node="day10_execution"
  User has not completed tasks for 4 consecutive days
  InsightClaim#IC5 exists: status=open, type="avoidance_pattern", confidence=0.4

t=0   partner_report(P1): "他最近好像在逃避，跟我说不想学了，但又在打游戏"

t=1   SignalAggregator → SignalSnapshot#SS_20
      ├─ core: + partner_report(severity=medium)
      ├─ enhanced: TaskCompletion(recent_4d=0%), BehavioralSignal(gaming_detected)

t=2   Aurora.trigger(type=reactive)
      └─ materiality_check: PASSED (partner_signal + task_streak_broken + existing_open_claim)

t=3   Aurora.deliberate(snapshot=SS_20, policy=APV@v1.0)
      │
      ├─ UPDATE InsightClaim#IC5
      │  ├─ confidence: 0.4 → 0.7 (partner corroboration + behavioral signal)
      │  ├─ status: open → probed (new evidence supports, needs direct check)
      │
      ├─ EMIT ProbeOutcome#PO5
      │  ├─ claim_id: IC5
      │  ├─ probe_type: "partner_check"
      │  ├─ result: "confirmed"
      │  ├─ evidence: "伙伴报告回避行为 + 任务4天未完成 + 游戏行为检测"
      │  └─ confidence_adjustment: +0.3
      │
      ├─ EMIT TransitionDecisionRecord#TDR20
      │  ├─ decision_type: "stay"  (no transition off backbone)
      │  ├─ initiation_type: proactive
      │  ├─ decision_mechanism: hybrid (rule: partner_signal, LLM: probe wording)
      │  ├─ decision_basis: partner_signal
      │  ├─ InferenceKnobs: {"tone": "直接但不压迫", "temperature": 0.5}
      │  ├─ CapabilityGate: {
      │  │    "allowed_tools": ["direct_question", "recommitment_offer"],
      │  │    "disabled_tools": ["new_plan_generation", "reschedule"]
      │  │  }
      │  └─ confirmed_by_user: None (proactive, not requiring confirmation)
      │
      ux_projection:
        ├─ aurora_presence: active              # proactive outreach, mid-level visibility
        ├─ interaction_model_variant: meta_reflection
        ├─ ux_intent: reconciliation
        ├─ mirror_bar_pulse: notifying           # system-initiated contact indicator
        └─ conversation_frame: slightly_deepened

      └─ proactive_policy budget check:
         daily_budget=3, today_used=0 → APPROVED

t=4   Interaction Layer renders (proactive initiation):
      └─ "嘿，我知道你最近状态不太好。你的伙伴也有些担心你。
          我们不需要假装一切正常——你愿意和我说说现在是什么情况吗？
          不评判，就是想搞清楚，然后一起看看怎么办。"

t=5   [If user responds with explanation]
      → reconciliation flow activates (single-turn trust user,
         contextualize IC5, schedule meta-review if ≥3 occurrences)
```

---

## 5. Schema Generation Pipeline (Design Placeholder)

**Strategy**: Pydantic as source of truth. Proto and TypeScript generated, never hand-written.

```
Pydantic models (source of truth)
    │
    ├─→ pydantic-to-proto generator (Gate 1 implementation)
    │       │
    │       └─→ Proto files for gRPC contract
    │
    ├─→ proto-to-typescript generator (existing buf pipeline)
    │       │
    │       └─→ TypeScript types for Flutter/Dart (via buf + protoc_plugin)
    │
    └─→ JSON Schema export (Pydantic built-in)
            │
            └─→ API contract validation, test fixtures

Gate 0: Pydantic schemas only. Generation pipeline design accepted, implementation deferred to Gate 1.
Proto/TS files in this phase are auto-generated drafts, not hand-reviewed.
```

---

## 6. Appendix: Migration Notes

### 6.1 Expert System → ScenarioPack

| Legacy | Target | Action |
|--------|--------|--------|
| `agent_profiles.py` (20+ roles) | `ScenarioPackManifest.backbone_nodes[].node_persona` | Migrate prompt templates |
| `public_expert_catalog` | `ScenarioPackManifest` registry | Rebuild as pack registry |
| `expert_auto` routing | `Aurora.impact_class` + node routing | Replace with Aurora decision |
| Flutter expert selector | Deprecated, hidden for new users | Remove from main UI |

### 6.2 Seed Library → DistilledStrategy

| Legacy | Target | Action |
|--------|--------|--------|
| Hand-authored seeds | `DistilledStrategy` with `source_trajectory_type: "human_authored"` | Import existing |
| User-created seeds | `DistilledStrategy` with `status: user_private` | Migrate |
| Seed browsing UI | Unified knowledge seed interface | Redesign (shared retrieval) |

### 6.3 Existing Systems → Aurora Readers

| System | Aurora reads via | Aurora writes via |
|--------|-----------------|-------------------|
| UserInsightState | SignalAggregator → core_signals | SignalProcessor → profile update from confirmed claims |
| BehaviorPattern | SignalAggregator → enhanced_signals | Read-only for Aurora |
| AchievementEngine | SignalAggregator → optional_signals | Read-only for Aurora |
| GalaxyService | SignalAggregator → enhanced_signals | SignalProcessor → mastery update from plan execution |
| CommunityService | SignalAggregator → optional_signals | SignalProcessor → partner notifications |
| ChatHistory | SignalAggregator → core_signals | Read-only for Aurora |
| CalendarService | SignalAggregator → core_signals | SignalProcessor → schedule writes (dialogue-mediated) |
| CognitiveService | SignalAggregator → enhanced_signals | Read-only for Aurora |
| TaskService | SignalAggregator → core_signals | SignalProcessor → task creation from plan decisions |

---

## 7. Consensus Lock List (23 Items)

1. Aurora = control bus, not replacement layer
2. Governance boundary frozen, relationship morphology evolves
3. Proactive contact: 4-layer constraints (hard/policy/state/relationship)
4. projection_policy: 4 tiers (open_editable / open_discussable / sensitive_mediated / internal)
5. decision_mechanism + decision_basis: dual mandatory fields
6. Conversation-mediated parameter updates: NL → structured → confirm → write
7. Transparent profile = LM-mediated, layered projection, discussable
8. Continuous learning: 4 layers (in-session / cross-session / pack / cross-user)
9. System-level learning requires abstraction + deidentification + review + authorization
10. Users cannot directly overwrite all system judgments — update explanations, not values
11. Gate 0 deliverables: Pydantic schema + 3 reference flows + common enums + I/O contract
12. Append-only invariant at end of each applicable primitive
13. Field disputes >30min → provisional tag, defer to Gate 1
14. Rollback anchor = composite snapshot
15. Ledger = union view of append-only objects, not a separate primitive
16. Persona invariants/envelope frozen in AuroraPolicyVersion; per-user relationship state extracted as SparkleRelationshipState (provisional, derived view)
17. Aurora trigger: 3 tiers (reactive / scheduled / on_demand)
18. WindowState: global + per-commitment override
19. FocusContract: live object + version chain, current ref in UserScenarioState
20. InsightClaim: 6 sources unified, with provenance/confidence/lifecycle
21. ScenarioPack = read-only template, user state independent
22. Aurora presence as continuous spectrum (ambient / active / meta-surface), not binary switch
23. Aurora never directly produces user-facing text; all text rendered by InteractionModel variants from Aurora frame
