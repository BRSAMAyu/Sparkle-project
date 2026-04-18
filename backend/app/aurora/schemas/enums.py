"""Frozen Gate 0 Aurora enums."""

from __future__ import annotations

from enum import Enum


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
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InitiationType(str, Enum):
    REACTIVE = "reactive"
    SCHEDULED = "scheduled"
    ON_DEMAND = "on_demand"
    PROACTIVE = "proactive"


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
    CONTEXTUALIZED = "contextualized"


class WindowMode(str, Enum):
    COMMITMENT = "commitment"
    ITERATION = "iteration"


class CommitmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    VIOLATED = "violated"
    RENEGOTIATED = "renegotiated"


class ProjectionPolicy(str, Enum):
    OPEN_EDITABLE = "open_editable"
    OPEN_DISCUSSABLE = "open_discussable"
    SENSITIVE_MEDIATED = "sensitive_mediated"
    INTERNAL = "internal"


class WritePath(str, Enum):
    UI_ONLY = "ui_only"
    DIALOGUE_MEDIATED = "dialogue_mediated"
    POLICY_ONLY = "policy_only"
    SYSTEM_INTERNAL = "system_internal"


class Shareability(str, Enum):
    PRIVATE_ONLY = "private_only"
    USER_APPROVED_ABSTRACTABLE = "user_approved_abstractable"
    SYSTEM_ABSTRACTABLE = "system_abstractable"
    PUBLIC_SEED_CANDIDATE = "public_seed_candidate"


class ParameterWriteAuthLevel(str, Enum):
    AUTO_WRITE = "auto_write"
    SUGGEST_CONFIRM = "suggest_confirm"
    EXPLICIT_CONFIRM_ONLY = "explicit_confirm_only"


class DistilledStrategyLifecycle(str, Enum):
    DISTILLED = "distilled"
    USER_REVIEWED = "user_reviewed"
    USER_PRIVATE = "user_private"
    COMMUNITY_SHARED = "community_shared"
    RETIRED = "retired"


class SignalTier(str, Enum):
    CORE = "core"
    ENHANCED = "enhanced"
    OPTIONAL = "optional"


class RetentionTier(str, Enum):
    HOT = "hot"
    COLD_ARCHIVE = "cold_archive"
    RECONSTRUCTABLE = "reconstructable"


class InteractionModelVariant(str, Enum):
    DEFAULT_CONVERSATION = "default_conversation"
    TASK_EXECUTION = "task_execution"
    META_REFLECTION = "meta_reflection"
    HOLDING_MODE = "holding_mode"


class UXIntent(str, Enum):
    ROUTINE = "routine"
    ACTIVE_ADJUSTMENT = "active_adjustment"
    META_SURFACE = "meta_surface"
    RECONCILIATION = "reconciliation"
    IDENTITY_MOMENT = "identity_moment"
    HOLDING = "holding"


class AuroraPresenceLevel(str, Enum):
    AMBIENT = "ambient"
    ACTIVE = "active"
    META_SURFACE = "meta_surface"

