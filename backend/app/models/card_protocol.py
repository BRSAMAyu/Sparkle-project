"""
Card Protocol Models — Phase 1 Core Primitives

Six persistent primitives for the Sparkle Growth Loop System.
Aligned with: docs/product/SPARKLE_CARD_PROTOCOL_TAXONOMY_2026-04-02.md
ADR: docs/adr/0004-card-protocol-architecture.md
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    event as sa_event,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


def _string_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda members: [member.value for member in members],
    )


# ---------------------------------------------------------------------------
# Enums — must match frozen taxonomy exactly
# ---------------------------------------------------------------------------


class CardType(str, enum.Enum):
    PLAN = "PLAN"
    PHASE = "PHASE"
    TASK = "TASK"
    KNOWLEDGE = "KNOWLEDGE"
    ACHIEVEMENT = "ACHIEVEMENT"
    CUSTOM = "CUSTOM"


class CardLifecycleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"
    CANCELLED = "CANCELLED"


class CardVisibility(str, enum.Enum):
    PRIVATE = "PRIVATE"
    FRIENDS = "FRIENDS"
    COMMUNITY = "COMMUNITY"
    PUBLIC = "PUBLIC"


class CardSourceType(str, enum.Enum):
    ORIGINAL = "ORIGINAL"
    ADOPTED = "ADOPTED"
    FORKED = "FORKED"
    IMPORTED = "IMPORTED"
    GENERATED = "GENERATED"


class CardCreatedBy(str, enum.Enum):
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"


class EdgeType(str, enum.Enum):
    CONTAINS = "CONTAINS"
    REFERENCES = "REFERENCES"
    DEPENDS_ON = "DEPENDS_ON"
    BLOCKS = "BLOCKS"
    GENERATED_FROM = "GENERATED_FROM"
    EVIDENCE_FOR = "EVIDENCE_FOR"
    ENABLES = "ENABLES"
    REWARDS = "REWARDS"
    ADOPTED_FROM = "ADOPTED_FROM"
    FORKED_FROM = "FORKED_FROM"


class BindingMode(str, enum.Enum):
    OWNED = "OWNED"
    REFERENCE = "REFERENCE"
    MIRROR = "MIRROR"
    SNAPSHOT = "SNAPSHOT"


class OccurrenceStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    MISSED = "MISSED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"


class ArtifactType(str, enum.Enum):
    DISCOVERY_DOSSIER = "DISCOVERY_DOSSIER"
    GLOBAL_COMPASS = "GLOBAL_COMPASS"
    STRATEGY_MAP = "STRATEGY_MAP"
    PHASE_BLUEPRINT = "PHASE_BLUEPRINT"
    ACTIVE_PHASE_PACK = "ACTIVE_PHASE_PACK"
    REFLECTION_REPORT = "REFLECTION_REPORT"
    DECISION_LOG = "DECISION_LOG"
    RISK_REGISTER = "RISK_REGISTER"


class ArtifactStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class InterventionTriggerType(str, enum.Enum):
    CONCEPT_GAP = "CONCEPT_GAP"
    PLAN_RISK = "PLAN_RISK"
    STALL_PATTERN = "STALL_PATTERN"
    OVERLOAD = "OVERLOAD"
    MISALIGNMENT = "MISALIGNMENT"


class DeliveryStrategy(str, enum.Enum):
    CURIOUS = "CURIOUS"
    SUPPORTIVE = "SUPPORTIVE"
    DIRECT = "DIRECT"
    MICRO_RESTART = "MICRO_RESTART"


class DeliveryChannel(str, enum.Enum):
    CHAT = "CHAT"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    FOCUS_MODE = "FOCUS_MODE"


class InterventionAcceptanceStatus(str, enum.Enum):
    CREATED = "CREATED"
    DELIVERED = "DELIVERED"
    SEEN = "SEEN"
    DISMISSED = "DISMISSED"
    SNOOZED = "SNOOZED"
    ACCEPTED = "ACCEPTED"
    ACTED = "ACTED"


class InterventionOutcomeStatus(str, enum.Enum):
    PENDING = "PENDING"
    EFFECTIVE = "EFFECTIVE"
    INEFFECTIVE = "INEFFECTIVE"
    UNKNOWN = "UNKNOWN"


class ShareScope(str, enum.Enum):
    USER = "USER"
    GROUP = "GROUP"
    COMMUNITY = "COMMUNITY"
    PUBLIC = "PUBLIC"


class SharePermission(str, enum.Enum):
    VIEW = "VIEW"
    ADOPT = "ADOPT"
    FORK = "FORK"
    COMMENT = "COMMENT"
    EDIT = "EDIT"


class ImportMode(str, enum.Enum):
    ADOPT = "ADOPT"
    FORK = "FORK"


# ---------------------------------------------------------------------------
# Card — canonical semantic entity
# ---------------------------------------------------------------------------


class Card(BaseModel):
    __tablename__ = "cards"

    card_type = Column(Enum(CardType, name="card_type_enum"), nullable=False, index=True)
    owner_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    holder_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    schema_version = Column(String(16), nullable=False, default="3.0")
    lifecycle_status = Column(
        Enum(CardLifecycleStatus, name="card_lifecycle_enum"),
        nullable=False,
        default=CardLifecycleStatus.DRAFT,
        index=True,
    )
    visibility = Column(
        Enum(CardVisibility, name="card_visibility_enum"),
        nullable=False,
        default=CardVisibility.PRIVATE,
    )
    tags = Column(JSONBCompat, nullable=False, server_default="[]")
    metadata_ = Column("metadata", JSONBCompat, nullable=False, server_default="{}")
    source_type = Column(
        Enum(CardSourceType, name="card_source_type_enum"),
        nullable=False,
        default=CardSourceType.ORIGINAL,
    )
    origin_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    origin_snapshot_id = Column(GUID(), nullable=True)
    created_by = Column(
        Enum(CardCreatedBy, name="card_created_by_enum"),
        nullable=False,
        default=CardCreatedBy.AI,
    )
    updated_by = Column(
        Enum(CardCreatedBy, name="card_updated_by_enum"),
        nullable=False,
        default=CardCreatedBy.AI,
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    holder = relationship("User", foreign_keys=[holder_id])
    origin_card = relationship("Card", remote_side="Card.id", foreign_keys=[origin_card_id])

    # Type-specific payload is stored in metadata_ JSONB
    # PLAN metadata keys: name, description, plan_kind, horizon_start, horizon_end,
    #   global_compass_artifact_id, strategy_map_artifact_id, current_phase_card_id,
    #   execution_policy, progress_policy
    # PHASE metadata keys: phase_index, objective, estimated_start, estimated_end,
    #   entry_criteria, exit_criteria, adaptation_policy, feedback_gate_policy, phase_weight
    # TASK metadata keys: title, description, task_kind, effort_minutes_default, difficulty,
    #   energy_cost, execution_mode, completion_definition, recurrence_rule, scheduling_policy,
    #   context_triggers, deferral_policy
    # KNOWLEDGE metadata keys: name, description, keywords, mastery_state, relations,
    #   embedding_ref, learning_stats

    __table_args__ = (
        Index("ix_cards_owner_type", "owner_id", "card_type"),
        Index("ix_cards_holder_status", "holder_id", "lifecycle_status"),
        Index("ix_cards_type_status", "card_type", "lifecycle_status"),
    )

    def __repr__(self):
        return f"<Card(id={self.id}, type={self.card_type}, status={self.lifecycle_status})>"


# ---------------------------------------------------------------------------
# CardEdge — graph relationship layer (card-to-card only)
# ---------------------------------------------------------------------------


class CardEdge(BaseModel):
    __tablename__ = "card_edges"

    from_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    to_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_type = Column(Enum(EdgeType, name="edge_type_enum"), nullable=False, index=True)
    binding_mode = Column(Enum(BindingMode, name="binding_mode_enum"), nullable=False, default=BindingMode.OWNED)
    order_index = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    temporal_window = Column(JSONBCompat, nullable=True)
    metadata_ = Column("metadata", JSONBCompat, nullable=False, server_default="{}")
    active = Column(Boolean, nullable=False, default=True)
    removed_at = Column(DateTime, nullable=True)

    # Relationships
    from_card = relationship("Card", foreign_keys=[from_card_id])
    to_card = relationship("Card", foreign_keys=[to_card_id])

    __table_args__ = (
        Index("ix_card_edges_from_type", "from_card_id", "edge_type"),
        Index("ix_card_edges_to_type", "to_card_id", "edge_type"),
        Index("ix_card_edges_active", "active", "edge_type"),
        UniqueConstraint("from_card_id", "to_card_id", "edge_type", name="uq_card_edge_unique"),
    )

    def __repr__(self):
        return f"<CardEdge(from={self.from_card_id}, to={self.to_card_id}, type={self.edge_type})>"


# ---------------------------------------------------------------------------
# TaskOccurrence — concrete execution instance (NOT a card)
# Provenance lives on the occurrence record itself, not in card_edges.
# ---------------------------------------------------------------------------


class TaskOccurrence(BaseModel):
    __tablename__ = "task_occurrences"

    series_card_id = Column(
        GUID(), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True)
    scheduled_for = Column(Date, nullable=True, index=True)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    occurrence_status = Column(
        Enum(OccurrenceStatus, name="occurrence_status_enum"),
        nullable=False,
        default=OccurrenceStatus.PLANNED,
        index=True,
    )
    actual_minutes = Column(Integer, nullable=True)
    completion_quality = Column(Integer, nullable=True)
    deferral_count = Column(Integer, nullable=False, default=0)
    generated_by_rule_hash = Column(String(128), nullable=False, server_default="")
    feedback_payload = Column(JSONBCompat, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    series_card = relationship("Card", foreign_keys=[series_card_id])
    plan_card = relationship("Card", foreign_keys=[plan_card_id])
    phase_card = relationship("Card", foreign_keys=[phase_card_id])

    __table_args__ = (
        Index("ix_occurrences_series_status", "series_card_id", "occurrence_status"),
        Index("ix_occurrences_scheduled_date", "scheduled_for", "occurrence_status"),
        Index("ix_occurrences_plan_date", "plan_card_id", "scheduled_for"),
    )

    def __repr__(self):
        return f"<TaskOccurrence(id={self.id}, series={self.series_card_id}, status={self.occurrence_status})>"


# ---------------------------------------------------------------------------
# PlanningArtifact — versioned AI governance records
# ---------------------------------------------------------------------------


class PlanningArtifact(BaseModel):
    __tablename__ = "planning_artifacts"

    plan_card_id = Column(
        GUID(), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_type = Column(
        _string_enum(ArtifactType, "artifact_type_enum"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False, default=1)
    status = Column(
        _string_enum(ArtifactStatus, "artifact_status_enum"),
        nullable=False,
        default=ArtifactStatus.DRAFT,
        index=True,
    )
    payload = Column(JSONBCompat, nullable=False, server_default="{}")
    based_on_versions = Column(JSONBCompat, nullable=False, server_default="{}")
    created_by_agent = Column(String(64), nullable=True)
    approved_by_user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    superseded_at = Column(DateTime, nullable=True)

    # Relationships
    plan_card = relationship("Card", foreign_keys=[plan_card_id])
    approved_by_user = relationship("User", foreign_keys=[approved_by_user_id])

    __table_args__ = (
        Index("ix_artifacts_plan_type", "plan_card_id", "artifact_type"),
        Index("ix_artifacts_type_status", "artifact_type", "status"),
        UniqueConstraint("plan_card_id", "artifact_type", "version", name="uq_artifact_version"),
    )

    def __repr__(self):
        return f"<PlanningArtifact(id={self.id}, type={self.artifact_type}, v{self.version})>"


# ---------------------------------------------------------------------------
# InterventionRecord — tracked intervention lifecycle
# ---------------------------------------------------------------------------


class InterventionRecord(BaseModel):
    __tablename__ = "intervention_records"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    task_occurrence_id = Column(
        GUID(), ForeignKey("task_occurrences.id", ondelete="SET NULL"), nullable=True
    )
    knowledge_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    trigger_type = Column(
        _string_enum(InterventionTriggerType, "intervention_trigger_enum"),
        nullable=False,
        index=True,
    )
    trigger_source_ref = Column(String(128), nullable=True)
    diagnosis_payload = Column(JSONBCompat, nullable=False, server_default="{}")
    delivery_strategy = Column(
        _string_enum(DeliveryStrategy, "delivery_strategy_enum"), nullable=False
    )
    delivery_channel = Column(
        _string_enum(DeliveryChannel, "delivery_channel_enum"), nullable=False
    )
    content_version = Column(String(64), nullable=False, server_default="1")
    acceptance_status = Column(
        _string_enum(InterventionAcceptanceStatus, "intervention_acceptance_enum"),
        nullable=False,
        default=InterventionAcceptanceStatus.CREATED,
        index=True,
    )
    action_payload = Column(JSONBCompat, nullable=True)
    outcome_window_days = Column(Integer, nullable=False, default=7)
    outcome_status = Column(
        _string_enum(InterventionOutcomeStatus, "intervention_outcome_enum"),
        nullable=False,
        default=InterventionOutcomeStatus.PENDING,
    )
    evidence_payload = Column(JSONBCompat, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    plan_card = relationship("Card", foreign_keys=[plan_card_id])
    phase_card = relationship("Card", foreign_keys=[phase_card_id])
    task_occurrence = relationship("TaskOccurrence", foreign_keys=[task_occurrence_id])
    knowledge_card = relationship("Card", foreign_keys=[knowledge_card_id])

    __table_args__ = (
        Index("ix_intervention_user_status", "user_id", "acceptance_status"),
        Index("ix_intervention_trigger_channel", "trigger_type", "delivery_channel"),
        Index("ix_intervention_outcome", "outcome_status", "outcome_window_days"),
    )

    def __repr__(self):
        return f"<InterventionRecord(id={self.id}, trigger={self.trigger_type}, status={self.acceptance_status})>"


# ---------------------------------------------------------------------------
# CardSnapshot — portable card tree serialization for sharing/adoption
# ---------------------------------------------------------------------------


class CardSnapshot(BaseModel):
    __tablename__ = "card_snapshots"

    root_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True)
    source_owner_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source_card_type = Column(Enum(CardType, name="snapshot_card_type_enum"), nullable=False, index=True)
    schema_version = Column(String(16), nullable=False, server_default="1.0")
    payload = Column(JSONBCompat, nullable=False, server_default="{}")
    metadata_ = Column("metadata", JSONBCompat, nullable=False, server_default="{}")

    root_card = relationship("Card", foreign_keys=[root_card_id])
    source_owner = relationship("User", foreign_keys=[source_owner_id])

    __table_args__ = (
        Index("ix_card_snapshots_root_type", "root_card_id", "source_card_type"),
        Index("ix_card_snapshots_owner_type", "source_owner_id", "source_card_type"),
    )

    def __repr__(self):
        return f"<CardSnapshot(id={self.id}, root={self.root_card_id}, type={self.source_card_type})>"


# ---------------------------------------------------------------------------
# CardShareRecord — a frozen share offer built from a snapshot
# ---------------------------------------------------------------------------


class CardShareRecord(BaseModel):
    __tablename__ = "card_share_records"

    snapshot_id = Column(
        GUID(), ForeignKey("card_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    root_card_id = Column(GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True)
    shared_by_user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    scope = Column(Enum(ShareScope, name="share_scope_enum"), nullable=False, index=True)
    permission = Column(
        Enum(SharePermission, name="share_permission_enum"),
        nullable=False,
        default=SharePermission.ADOPT,
    )
    message = Column(String(500), nullable=True)
    adoption_count = Column(Integer, nullable=False, default=0)
    view_count = Column(Integer, nullable=False, default=0)
    revoked_at = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", JSONBCompat, nullable=False, server_default="{}")

    snapshot = relationship("CardSnapshot", foreign_keys=[snapshot_id])
    root_card = relationship("Card", foreign_keys=[root_card_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])

    __table_args__ = (
        Index("ix_card_share_scope_group", "scope", "group_id"),
        Index("ix_card_share_scope_target", "scope", "target_user_id"),
        Index("ix_card_share_owner_scope", "shared_by_user_id", "scope"),
    )

    def __repr__(self):
        return f"<CardShareRecord(id={self.id}, scope={self.scope}, permission={self.permission})>"


# ---------------------------------------------------------------------------
# CardAdoptionRecord — adoption / fork lineage tracking
# ---------------------------------------------------------------------------


class CardAdoptionRecord(BaseModel):
    __tablename__ = "card_adoption_records"

    share_record_id = Column(
        GUID(), ForeignKey("card_share_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adopter_user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    adopted_root_card_id = Column(
        GUID(), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True
    )
    import_mode = Column(Enum(ImportMode, name="import_mode_enum"), nullable=False, index=True)
    attribution_payload = Column(JSONBCompat, nullable=False, server_default="{}")

    share_record = relationship("CardShareRecord", foreign_keys=[share_record_id])
    adopter_user = relationship("User", foreign_keys=[adopter_user_id])
    adopted_root_card = relationship("Card", foreign_keys=[adopted_root_card_id])

    __table_args__ = (
        Index("ix_card_adoption_user_mode", "adopter_user_id", "import_mode"),
    )

    def __repr__(self):
        return f"<CardAdoptionRecord(id={self.id}, mode={self.import_mode}, adopter={self.adopter_user_id})>"
