from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

PHASE_E_CONTRACT_VERSION = "2026-04-05.phase_e.v1"
ACTIVE_LEARNING_STATUS = "active"
INACTIVE_LEARNING_STATUSES: tuple[str, ...] = ("blocked", "demoted", "review_due", "stale")
ALL_LEARNING_STATUSES: tuple[str, ...] = (ACTIVE_LEARNING_STATUS, *INACTIVE_LEARNING_STATUSES)

REASON_TAXONOMY: tuple[str, ...] = (
    "repeated_effective_evidence",
    "insufficient_evidence",
    "cross_layer_conflict",
    "stale_without_reinforcement",
    "human_truth_override",
    "constitutional_block",
    "rights_boundary_block",
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _parse_dt(value: Any) -> datetime | None:
    raw = _strip(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed.replace(tzinfo=None)


@dataclass(frozen=True)
class PromotionThreshold:
    min_confidence: float = 0.0
    min_matching_revisions: int = 0
    min_distinct_sessions: int = 0
    requires_measurable_effect: bool = False
    sample_count_threshold: int = 0
    unique_sessions_threshold: int = 0
    requires_freshness: bool = False
    block_on_conflict: bool = False
    review_window_days: int | None = None
    expiry_days: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LayerPolicy:
    layer_id: str
    purpose: str
    read_scope: tuple[str, ...]
    write_scope: tuple[str, ...]
    allowed_signal_types: tuple[str, ...]
    forbidden_writes: tuple[str, ...]
    constitutional_constraints: tuple[str, ...]
    promotion_thresholds: dict[str, PromotionThreshold] = field(default_factory=dict)
    demotion_signals: tuple[str, ...] = field(default_factory=tuple)
    review_window_days: int | None = None
    expiry_days: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "purpose": self.purpose,
            "read_scope": list(self.read_scope),
            "write_scope": list(self.write_scope),
            "allowed_signal_types": list(self.allowed_signal_types),
            "forbidden_writes": list(self.forbidden_writes),
            "constitutional_constraints": list(self.constitutional_constraints),
            "promotion_thresholds": {
                key: value.to_dict() for key, value in self.promotion_thresholds.items()
            },
            "demotion_signals": list(self.demotion_signals),
            "review_window_days": self.review_window_days,
            "expiry_days": self.expiry_days,
        }


@dataclass(frozen=True)
class LayeredLearningContract:
    version: str
    layers: dict[str, LayerPolicy]
    reason_taxonomy: tuple[str, ...]
    effective_runtime_statuses: tuple[str, ...] = (ACTIVE_LEARNING_STATUS,)
    inactive_runtime_statuses: tuple[str, ...] = INACTIVE_LEARNING_STATUSES
    review_due_runtime_policy: str = "exclude_until_revalidated"

    def layer(self, layer_id: str) -> LayerPolicy:
        return self.layers[layer_id]

    def promotion_threshold(self, layer_id: str, threshold_id: str) -> PromotionThreshold:
        layer = self.layer(layer_id)
        return layer.promotion_thresholds[threshold_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "reason_taxonomy": list(self.reason_taxonomy),
            "effective_runtime_statuses": list(self.effective_runtime_statuses),
            "inactive_runtime_statuses": list(self.inactive_runtime_statuses),
            "review_due_runtime_policy": self.review_due_runtime_policy,
            "layers": {key: value.to_dict() for key, value in self.layers.items()},
        }


@dataclass(frozen=True)
class LayerConflictReport:
    conflict_id: str
    learning_key: str
    involved_layers: tuple[str, ...]
    conflict_type: str
    evidence_summary: tuple[str, ...]
    winner: str
    blocked_layers: tuple[str, ...]
    required_action: str
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "learning_key": self.learning_key,
            "involved_layers": list(self.involved_layers),
            "conflict_type": self.conflict_type,
            "evidence_summary": list(self.evidence_summary),
            "winner": self.winner,
            "blocked_layers": list(self.blocked_layers),
            "required_action": self.required_action,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class ConstitutionalSafetyReport:
    allowed: bool
    blocked_reasons: tuple[str, ...]
    manipulation_risk: float
    freedom_risk: float
    goal_hijack_risk: float
    truth_discipline_risk: float
    disposition: str
    allowed_with_constraints: tuple[str, ...] = field(default_factory=tuple)
    escalation_required: bool = False
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked_reasons": list(self.blocked_reasons),
            "manipulation_risk": self.manipulation_risk,
            "freedom_risk": self.freedom_risk,
            "goal_hijack_risk": self.goal_hijack_risk,
            "truth_discipline_risk": self.truth_discipline_risk,
            "disposition": self.disposition,
            "allowed_with_constraints": list(self.allowed_with_constraints),
            "escalation_required": self.escalation_required,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class LayeredGrowthStateSnapshot:
    constitutional_state: dict[str, Any]
    session_state: dict[str, Any]
    episode_state: dict[str, Any]
    profile_state: dict[str, Any]
    system_state: dict[str, Any]
    active_conflicts: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    stale_items: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    pending_promotions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    pending_reviews: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constitutional_state": dict(self.constitutional_state),
            "session_state": dict(self.session_state),
            "episode_state": dict(self.episode_state),
            "profile_state": dict(self.profile_state),
            "system_state": dict(self.system_state),
            "active_conflicts": [dict(item) for item in self.active_conflicts],
            "stale_items": [dict(item) for item in self.stale_items],
            "pending_promotions": [dict(item) for item in self.pending_promotions],
            "pending_reviews": [dict(item) for item in self.pending_reviews],
        }


def classify_profile_claim_kind(
    *,
    confidence: float,
    distinct_sessions: int = 0,
    sample_count: int = 0,
    measurable_effect: bool = False,
) -> str:
    if measurable_effect and confidence >= 0.8 and max(distinct_sessions, sample_count) >= 2:
        return "stable_tendency"
    if measurable_effect or confidence >= 0.65:
        return "recent_state"
    return "one_off_reaction"


def count_distinct_sessions(revisions: list[dict[str, Any]]) -> int:
    session_ids: set[str] = set()
    for item in revisions:
        if not isinstance(item, dict):
            continue
        evidence = _as_dict(item.get("evidence"))
        session_id = _strip(evidence.get("session_id"))
        if session_id:
            session_ids.add(session_id)
    return len(session_ids)


def normalize_evidence_summary(evidence: dict[str, Any] | None) -> str:
    payload = _as_dict(evidence)
    parts = [
        _strip(payload.get("source")),
        _strip(payload.get("snippet")),
    ]
    if payload.get("measurable_effect"):
        parts.append("measurable_effect")
    return " | ".join(part for part in parts if part)[:280]


def learning_status(
    governance: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> str:
    metadata = _as_dict(governance)
    explicit = _strip(metadata.get("status")).lower()
    if explicit in {"blocked", "demoted"}:
        return explicit

    now = now or _utcnow()
    expires_at = _parse_dt(metadata.get("expires_at"))
    if expires_at is not None and expires_at <= now:
        return "stale"

    review_after = _parse_dt(metadata.get("review_after"))
    if review_after is not None and review_after <= now:
        return "review_due"

    if explicit in ALL_LEARNING_STATUSES:
        return explicit
    return ACTIVE_LEARNING_STATUS


def learning_is_active(
    governance: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> bool:
    return learning_status(governance, now=now) == ACTIVE_LEARNING_STATUS


def filter_active_learnings(
    learnings: list[dict[str, Any]] | None,
    governance_by_key: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    now = now or _utcnow()
    active: list[dict[str, Any]] = []
    inactive: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = {}
    for item in learnings or []:
        if not isinstance(item, dict):
            continue
        learning_key = _strip(item.get("learning_key"))
        if not learning_key:
            continue
        metadata = _as_dict(_as_dict(governance_by_key).get(learning_key))
        status = learning_status(metadata, now=now)
        summary[learning_key] = {
            "status": status,
            "active": status == ACTIVE_LEARNING_STATUS,
            "metadata": metadata,
        }
        annotated = {
            **dict(item),
            "governance_status": status,
        }
        if status == ACTIVE_LEARNING_STATUS:
            active.append(annotated)
        else:
            inactive.append(annotated)
    return active, inactive, summary


def build_temporal_metadata(
    *,
    contract: LayeredLearningContract,
    target_layer: str,
    source_layer: str,
    confidence: float,
    evidence: dict[str, Any] | None,
    promotion_reason: str,
    state_kind: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or _utcnow()
    layer_policy = contract.layer(target_layer)
    review_after = None
    expires_at = None
    if layer_policy.review_window_days:
        review_after = now + timedelta(days=layer_policy.review_window_days)
    if layer_policy.expiry_days:
        expires_at = now + timedelta(days=layer_policy.expiry_days)
    return {
        "source_layer": source_layer,
        "evidence_summary": normalize_evidence_summary(evidence),
        "confidence": round(max(0.0, min(1.0, float(confidence))), 4),
        "promoted_at": now.isoformat(),
        "review_after": _iso_or_none(review_after),
        "expires_at": _iso_or_none(expires_at),
        "promotion_reason": promotion_reason,
        "state_kind": _strip(state_kind),
        "contract_version": contract.version,
    }


def build_five_layer_contract() -> LayeredLearningContract:
    layers = {
        "constitutional": LayerPolicy(
            layer_id="constitutional",
            purpose="Hold Sparkle's bounded constitution and anti-drift commitments.",
            read_scope=("all_layers",),
            write_scope=(),
            allowed_signal_types=("constitution_artifact", "identity_kernel"),
            forbidden_writes=("session_adaptation", "profile_self_escalation", "system_scope_expansion"),
            constitutional_constraints=(
                "truth_discipline",
                "non_manipulation",
                "freedom_preservation",
                "user_centered_telos",
            ),
            demotion_signals=(),
        ),
        "session": LayerPolicy(
            layer_id="session",
            purpose="Cheap, reversible adaptation for the current conversation or short horizon.",
            read_scope=("constitutional", "session", "episode", "profile"),
            write_scope=("redis_session_state",),
            allowed_signal_types=("conversation_signal", "turn_feedback", "single_session_effect"),
            forbidden_writes=("profile_replacement", "system_rights_change"),
            constitutional_constraints=("reversible", "bounded", "non_manipulation"),
            review_window_days=1,
            expiry_days=7,
            demotion_signals=("session_end", "expiry", "contradictory_repeated_evidence"),
        ),
        "episode": LayerPolicy(
            layer_id="episode",
            purpose="Journey-bounded learning that should survive across a real plan episode and then decay.",
            read_scope=("constitutional", "session", "episode", "profile"),
            write_scope=("plan_state.facts",),
            allowed_signal_types=("repeated_effective_session_signal", "validated_outcome_learning", "journey_state"),
            forbidden_writes=("constitution_change", "silent_profile_claim"),
            constitutional_constraints=("evidence_gated", "reviewable", "reversible"),
            promotion_thresholds={
                "companion_session_to_episode": PromotionThreshold(
                    min_confidence=0.7,
                    min_matching_revisions=2,
                    min_distinct_sessions=1,
                    requires_measurable_effect=True,
                    review_window_days=14,
                    expiry_days=14,
                ),
                "outcome_learning_to_episode": PromotionThreshold(
                    min_confidence=0.55,
                    sample_count_threshold=2,
                    unique_sessions_threshold=1,
                    requires_freshness=True,
                    block_on_conflict=True,
                    review_window_days=14,
                    expiry_days=14,
                ),
            },
            review_window_days=14,
            expiry_days=14,
            demotion_signals=("plan_completed", "expiry", "stronger_contradictory_evidence", "stale_without_reinforcement"),
        ),
        "profile": LayerPolicy(
            layer_id="profile",
            purpose="Small, durable cross-session truths that remain auditable and contradiction-sensitive.",
            read_scope=("constitutional", "episode", "profile"),
            write_scope=("user_preferences_center.inferred",),
            allowed_signal_types=("multi_session_pattern", "validated_profile_learning", "relationship_boundary"),
            forbidden_writes=("one_off_emotion_as_identity", "silent_intent_replacement", "attachment_optimization"),
            constitutional_constraints=("small_high_confidence", "auditable", "user_benefit"),
            promotion_thresholds={
                "companion_session_to_profile": PromotionThreshold(
                    min_confidence=0.8,
                    min_matching_revisions=3,
                    min_distinct_sessions=2,
                    requires_measurable_effect=True,
                ),
                "companion_conflict_overwrite": PromotionThreshold(
                    min_confidence=0.9,
                    min_matching_revisions=4,
                    min_distinct_sessions=3,
                    requires_measurable_effect=True,
                    block_on_conflict=True,
                ),
                "relationship_note_to_profile": PromotionThreshold(
                    min_confidence=0.8,
                    min_matching_revisions=3,
                    min_distinct_sessions=2,
                    requires_measurable_effect=True,
                ),
                "outcome_learning_to_profile": PromotionThreshold(
                    min_confidence=0.55,
                    sample_count_threshold=3,
                    unique_sessions_threshold=2,
                    requires_freshness=True,
                    block_on_conflict=True,
                ),
            },
            review_window_days=30,
            demotion_signals=("stronger_contradictory_evidence", "human_truth_override", "stale_without_reinforcement"),
        ),
        "system": LayerPolicy(
            layer_id="system",
            purpose="Explicitly bounded registry-governed rights for deeper runtime knobs.",
            read_scope=("constitutional", "system", "profile", "episode"),
            write_scope=("capability_registry_metadata",),
            allowed_signal_types=("rights_contract", "bounded_registry_decision", "human_approved_governance"),
            forbidden_writes=("silent_write_scope_expansion", "unreviewed_non_reversible_change"),
            constitutional_constraints=("approval_bounded", "rights_gated", "constitutional_review"),
            promotion_thresholds={
                "system_rights_completion": PromotionThreshold(
                    min_confidence=0.7,
                    min_matching_revisions=0,
                    min_distinct_sessions=0,
                    requires_measurable_effect=False,
                    block_on_conflict=True,
                )
            },
            review_window_days=30,
            demotion_signals=("rights_boundary_block", "constitutional_block"),
        ),
    }
    return LayeredLearningContract(
        version=PHASE_E_CONTRACT_VERSION,
        layers=layers,
        reason_taxonomy=REASON_TAXONOMY,
    )


DEFAULT_FIVE_LAYER_CONTRACT = build_five_layer_contract()
