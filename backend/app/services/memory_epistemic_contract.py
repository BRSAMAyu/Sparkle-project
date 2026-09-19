"""Memory V3 epistemic contract (task M-01).

Authority for the five V3 memory record types (FACT / CONFIRMED_PREFERENCE /
OBSERVATION / HYPOTHESIS / EXPERIENCE) over the EXISTING storage —— no second
store is introduced. This module is the single place that defines:

1. Epistemic class derivation from existing columns (``source_lane`` etc.);
2. Record status derivation (active / superseded / revoked / retracted /
   archived / expired / resolved) from the existing lifecycle columns
   (``revoked_at`` / ``retracted_at`` / ``replaced_by_id`` / ``superseded_by_id``
   / ``archived_at`` / ``expires_at`` / ``resolved_at``);
3. Provenance classification for preference writes (explicit vs inferred) and
   the "inference must not overwrite fact" guard predicate;
4. Lane registry semantics: which ``source_lane`` maps to which epistemic
   class, delegating lane *priority* arbitration to
   ``ConflictResolverService.KNOWN_SOURCE_LANES`` (single source of truth for
   lane tiers; registering new lanes there is a product decision —— see
   RESERVED_UNREGISTERED_LANES);
5. The ``memory_epoch`` contract (bump triggers, audit trail) consumed by
   M-07 (context compiler cache invalidation) and C-07 (user-facing control).

Design rules inherited from USER_WORLD_MODEL / MEMORY_V3:
- inference/shadow never writes back over raw fact (enforced by guard
  predicates here and by write-path checks in ``MemoryService`` /
  ``ConflictResolverService``);
- correction produces supersede/revoke, never destructive overwrite;
- transient state stays in working memory (Redis), never pollutes the
  long-term tables.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

MEMORY_EPISTEMIC_CONTRACT_VERSION = "memory-v3.m01.v1"

# ---------------------------------------------------------------------------
# 1. Epistemic classes (V3 memory record types)
# ---------------------------------------------------------------------------


class EpistemicClass(StrEnum):
    """V3 memory record types (MEMORY_V3.md §1 / USER_WORLD_MODEL.md §2)."""

    FACT = "FACT"
    CONFIRMED_PREFERENCE = "CONFIRMED_PREFERENCE"
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    EXPERIENCE = "EXPERIENCE"


# Classes that live on ``episodic_memories``. CONFIRMED_PREFERENCE is carried
# by table membership (``memory_preferences`` / ``memory_goals``) and is not a
# valid ``episodic_memories.epistemic_class`` value.
EPISODIC_EPISTEMIC_CLASSES: frozenset[str] = frozenset(
    {
        EpistemicClass.FACT.value,
        EpistemicClass.OBSERVATION.value,
        EpistemicClass.HYPOTHESIS.value,
        EpistemicClass.EXPERIENCE.value,
    }
)

# ---------------------------------------------------------------------------
# 2. Record status machine
# ---------------------------------------------------------------------------


class MemoryRecordStatus(StrEnum):
    """Storage-derived lifecycle status (MEMORY_V3.md §1/§6).

    ``candidate`` / ``confirmed`` are *view-level* epistemic qualifiers for
    HYPOTHESIS-class records (does the user-facing partition show it under
    "我还不确定的" or as confirmed) and are derived from
    ``MemoryCorrection(action="confirm")`` / lane, not stored per row.
    """

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    RETRACTED = "retracted"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    RESOLVED = "resolved"  # commitment lifecycle closure (episodic only)


# Status precedence: earlier entries win when several lifecycle columns are
# set. revoked (hard user delete) dominates; supersede dominates retraction
# because it points at a replacement record (the fact chain continues).
_STATUS_PRECEDENCE: tuple[str, ...] = (
    MemoryRecordStatus.REVOKED.value,
    MemoryRecordStatus.SUPERSEDED.value,
    MemoryRecordStatus.RETRACTED.value,
    MemoryRecordStatus.ARCHIVED.value,
    MemoryRecordStatus.EXPIRED.value,
    MemoryRecordStatus.RESOLVED.value,
    MemoryRecordStatus.ACTIVE.value,
)


def _get(record: Any, name: str) -> Any:
    return getattr(record, name, None)


def derive_status(record: Any, *, now: datetime | None = None) -> str:
    """Derive the V3 status of an existing memory row from its columns.

    Works for MemoryPreference / MemoryGoal / EpisodicMemory alike; absent
    columns simply do not contribute. ``now`` gates the EXPIRED check
    (``memory_goals.expires_at``); naive-UTC datetimes expected (DB canonical).
    """
    if _get(record, "revoked_at") is not None:
        return MemoryRecordStatus.REVOKED.value
    if _get(record, "replaced_by_id") is not None or _get(record, "superseded_by_id") is not None:
        return MemoryRecordStatus.SUPERSEDED.value
    if _get(record, "retracted_at") is not None:
        return MemoryRecordStatus.RETRACTED.value
    if _get(record, "archived_at") is not None:
        return MemoryRecordStatus.ARCHIVED.value
    expires_at = _get(record, "expires_at")
    if expires_at is not None and now is not None and expires_at <= now:
        return MemoryRecordStatus.EXPIRED.value
    if _get(record, "resolved_at") is not None:
        return MemoryRecordStatus.RESOLVED.value
    return MemoryRecordStatus.ACTIVE.value


STATUS_PRECEDENCE: tuple[str, ...] = _STATUS_PRECEDENCE

# ---------------------------------------------------------------------------
# 3. Lane registry: source_lane -> epistemic semantics
# ---------------------------------------------------------------------------

# Lanes whose records are user-stated (explicit tier). Lane *priority*
# arbitration stays owned by ConflictResolverService.KNOWN_SOURCE_LANES /
# PRIORITY_BY_TIER; this registry only carries epistemic-class semantics.
EXPLICIT_SOURCE_LANES: frozenset[str] = frozenset({"direct_capture", "user_confirmed"})

# source_type values that represent a USER-STATED record on an explicit lane
# (R2-F1). Dev-DB evidence (2026-09-19, read-only): of 184 direct_capture rows
# only user_registered (1 row, user_memory_seed_consumer.py:25) is genuinely
# user-stated; chat_turn(164)/analysis(9)/reflection(6)/error_analysis(2)/
# practice_outcome(2) are machine-written event records —— per this contract
# they are OBSERVATION, not FACT. Extending this set is a product decision
# (writer governance lands with M-04); the m01a backfill SQL mirrors it and
# must be kept in sync.
USER_STATEMENT_SOURCE_TYPES: frozenset[str] = frozenset({"user_registered"})

# Lanes deliberately NOT registered in ConflictResolverService.KNOWN_SOURCE_LANES.
# ``aurora_calibration_receipt`` is a live red-line case (see V3-FIX-06):
# correction_feedback.py writes it to working memory; whether it should
# arbitrate above direct_capture is a product decision this card must NOT
# make. It is documented here so the epistemic contract has a reserved slot
# while conflict arbitration continues to treat it as lowest tier ("unknown").
RESERVED_UNREGISTERED_LANES: dict[str, str] = {
    "aurora_calibration_receipt": (
        "correction receipt lane (working-memory scoped, V3-FIX-06 pending); "
        "deliberately NOT registered in ConflictResolverService.KNOWN_SOURCE_LANES"
    ),
}


def classify_episodic_class(
    source_lane: str | None,
    *,
    explicit_class: str | None = None,
    source_type: str | None = None,
) -> str:
    """Epistemic class of an episodic row.

    ``explicit_class`` is the ``epistemic_class`` column value when present
    (future writers: OBSERVATION for behavioral/system observations,
    EXPERIENCE for situation->intervention->outcome records, M-06). When the
    column is NULL the class derives conservatively (R2-F1 tightened):

    - ``user_confirmed`` lane -> FACT（确认动作本身就是用户陈述）;
    - ``direct_capture`` lane + ``source_type`` in
      ``USER_STATEMENT_SOURCE_TYPES`` -> FACT;
    - other ``direct_capture`` rows (machine-written event records:
      chat_turn / analysis / reflection / ...) -> OBSERVATION;
    - anything else (rule/llm/unknown lanes) -> HYPOTHESIS.
    """
    if explicit_class:
        normalized = str(explicit_class).strip().upper()
        if normalized in EPISODIC_EPISTEMIC_CLASSES:
            return normalized
    lane = str(source_lane or "").strip().lower()
    if lane == "user_confirmed":
        return EpistemicClass.FACT.value
    if lane == "direct_capture":
        if source_type and str(source_type).strip().lower() in USER_STATEMENT_SOURCE_TYPES:
            return EpistemicClass.FACT.value
        return EpistemicClass.OBSERVATION.value
    return EpistemicClass.HYPOTHESIS.value


def lane_priority(source_lane: str | None) -> int:
    """Lane priority rank, delegated to the conflict resolver registry.

    The registry constants (``KNOWN_SOURCE_LANES`` / ``PRIORITY_BY_TIER``)
    stay the single source of truth for lane tiers; unregistered lanes
    conservatively rank lowest ("unknown"), matching resolver behaviour.
    Import is deferred to avoid a circular import at module load.
    """
    from app.services.conflict_resolver_service import ConflictResolverService

    lane = str(source_lane or "").strip().lower()
    tier = ConflictResolverService.KNOWN_SOURCE_LANES.get(lane)
    if tier is not None:
        return ConflictResolverService.PRIORITY_BY_TIER[tier]
    return ConflictResolverService.PRIORITY_BY_TIER["unknown"]


# ---------------------------------------------------------------------------
# 4. Preference provenance + "inference never overwrites fact" guard
# ---------------------------------------------------------------------------

INFERRED_EVIDENCE_TYPES: frozenset[str] = frozenset({"ai_inferred"})
INFERRED_SOURCE_TYPES: frozenset[str] = frozenset({"ai_inferred"})


class Provenance(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


def _refs_iter(evidence_refs: Any):
    refs = evidence_refs or []
    if isinstance(refs, dict):
        refs = refs.get("refs") or []
    for ref in refs:
        if isinstance(ref, dict):
            yield ref


def preference_write_provenance(
    *,
    source_type: str | None,
    evidence_refs: Any,
) -> str:
    """Classify a memory_preferences write as explicit or inferred.

    Mirrors ``app.api.v1.memory._resolve_preference_source``: a record whose
    evidence contains ``ai_inferred`` (or whose source_type says so) is
    inference-layer; everything else (user_state, batch_edit, ...) is the
    explicit fact layer.
    """
    if source_type and str(source_type).strip().lower() in INFERRED_SOURCE_TYPES:
        return Provenance.INFERRED.value
    for ref in _refs_iter(evidence_refs):
        if str(ref.get("type") or "").strip().lower() in INFERRED_EVIDENCE_TYPES:
            return Provenance.INFERRED.value
    return Provenance.EXPLICIT.value


def inferred_may_supersede(head_provenance: str, incoming_provenance: str) -> bool:
    """Guard predicate for the memory_preferences version chain.

    The fact domain must keep user-stated truth as chain head: an inferred
    write may replace another inferred head, but never an explicit head.
    Explicit writes (user correction) may supersede anything.
    """
    if incoming_provenance == Provenance.INFERRED.value and head_provenance == Provenance.EXPLICIT.value:
        return False
    return True


def inferred_lane_may_supersede_lane(winner_lane: str | None, loser_lane: str | None) -> bool:
    """Guard predicate for episodic conflict application.

    An inferred-tier winner may not retract/supersede an explicit-tier loser
    through the automated conflict path. User arbitration
    (``arbitrate_unresolved_conflict``) is an explicit human action and does
    NOT go through this predicate.
    """
    winner_rank = lane_priority(winner_lane)
    loser_rank = lane_priority(loser_lane)
    if winner_rank < loser_rank:
        return False
    if winner_rank == loser_rank:
        # Same-tier: conflict resolver tie-breaks by confidence/recency; the
        # automated path may still not silently replace equal-rank records ——
        # that decision is reserved for the resolver's own arithmetic only
        # when ranks differ, so equal-rank automated supersede is allowed via
        # apply_live_decision only when the resolver explicitly emitted
        # "candidate_overrides_lower_priority" (checked by caller).
        return True
    return True


# ---------------------------------------------------------------------------
# 5. Scope derivation (V3 record field "scope" from existing columns)
# ---------------------------------------------------------------------------


def derive_scope(record: Any) -> dict[str, Any]:
    """Derive the V3 ``scope`` of an existing memory row from its columns.

    No new storage: scope is a projection of columns that already exist
    (subject_type / semantic_key / decay_policy / due_at / expires_at /
    linked_task_id / linked_plan_id / mentioned_entity_hash / session_id).
    """
    scope: dict[str, Any] = {"level": "global"}

    table = getattr(type(record), "__tablename__", "")
    if table == "memory_goals":
        scope["level"] = "goal"
        if _get(record, "linked_task_id") is not None:
            scope["task_id"] = str(_get(record, "linked_task_id"))
        if _get(record, "linked_plan_id") is not None:
            scope["plan_id"] = str(_get(record, "linked_plan_id"))
    elif table == "episodic_memories":
        scope["level"] = "domain"
        if _get(record, "subject_type"):
            scope["domain_key"] = str(_get(record, "subject_type"))
        if _get(record, "mentioned_entity_hash"):
            scope["entity_hash"] = str(_get(record, "mentioned_entity_hash"))
    elif table == "working_memory":
        scope["level"] = "session"
        if _get(record, "session_id") is not None:
            scope["session_id"] = str(_get(record, "session_id"))

    time_window: dict[str, str] = {}
    for key in ("due_at", "expires_at", "occurred_at"):
        value = _get(record, key)
        if value is not None:
            time_window[key] = value.isoformat() if hasattr(value, "isoformat") else str(value)
    if time_window:
        scope["time_window"] = time_window
    if _get(record, "decay_policy"):
        scope["decay_policy"] = str(_get(record, "decay_policy"))
    return scope


# ---------------------------------------------------------------------------
# 6. memory_epoch contract
# ---------------------------------------------------------------------------

# Correction actions that constitute a destructive-enough memory change to
# require epoch bump (MEMORY_V3.md §6: delete -> bump memory_epoch,
# invalidate semantic/context caches). M-07/C-07 consume the epoch value.
EPOCH_BUMP_CORRECTION_ACTIONS: frozenset[str] = frozenset(
    {
        "delete",
        "reject",
        "no_longer_applicable",
    }
)

# Actions that never bump the epoch (confidence nudges, consumption traces).
NON_EPOCH_CORRECTION_ACTIONS: frozenset[str] = frozenset(
    {
        "lower_confidence",
        "confirm",
        "memory_reference_accepted",
        "memory_reference_corrected",
        "memory_reference_ignored",
        "memory_reference_denied",
    }
)
