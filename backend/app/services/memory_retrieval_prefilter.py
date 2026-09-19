"""Memory V3 deterministic retrieval prefilter (task M-03).

Single authority for the L0 hard-cut layer that runs BEFORE any semantic /
ranking stage touches memory candidates. Dimensions and their FIXED evaluation
order (``FILTER_DIMENSIONS`` — the first failing dimension owns the rejection
attribution, so metric attribution is deterministic):

    1. identity / tenant filter          -> dimension ``user``
    2. status filter                     -> dimension ``status`` (M-01 machine)
    3. TTL / freshness                   -> dimension ``ttl`` (incl. today-only)
    4. scope compatibility               -> dimension ``scope`` (lattice below)
    5. purpose & permission              -> dimension ``purpose`` (+ user_memory_settings)
    6. sensitivity ceiling               -> dimension ``sensitivity``

Order note (R2-F2): MEMORY_V3.md §3 documents the pipeline as
identity/status/purpose/scope/TTL; the implementation deliberately evaluates
ttl before scope and purpose after both (cheap column-derived cuts first,
lattice next, settings-snapshot checks last). This implementation order is
the single authority — it is pinned by ``test_filter_dimensions_order_is_pinned``
plus the five adjacent-pair attribution tests; any reorder shifts D-06/O-02
dimension_counts attribution and MUST bump ``MEMORY_PREFILTER_VERSION``.

Step 6 (conflict/supersede resolution) stays with the existing
``MemoryConflictResolver`` / M-01 epistemic contract; steps 7-11 (semantic
retrieval / rerank / Self-ReCheck / budget / receipt) are untouched.

Design rules:

- **Pure core, thin adapter.** ``prefilter_candidates`` performs no I/O so any
  candidate source (SQL pull, vector search, working-memory consolidation)
  can be guarded; ``build_retrieval_context`` is the only async I/O helper
  (loads ``user_memory_settings`` best-effort).
- **No new storage.** Scope / TTL / purpose / sensitivity are derived from
  existing columns via the M-01 projection (``derive_scope`` /
  ``derive_status`` / ``classify_episodic_class``); the typed
  ``MemoryScopeDescriptor`` exists so future writers (M-04/M-06) can declare
  explicit scope without migrations.
- **Conservative-pass on unconstrained dimensions, fail-closed on identity.**
  When the retrieval context does not constrain goal/domain/task_type, a
  scoped record passes (relevance is the semantic stage's job). Identity
  (wrong user), status, TTL and session boundaries are unconditional cuts.
- **Closed vocabularies as single sources of truth** so the lattice cannot be
  re-defined in three places: ``SCOPE_LEVELS`` / ``SCOPE_COMPATIBILITY`` /
  ``LEVEL_ANCHOR_KEYS`` / ``RETRIEVAL_PURPOSES`` / ``SENSITIVITY_RANK`` /
  ``FILTER_DIMENSIONS``. Guards in ``tests/unit/test_memory_retrieval_prefilter.py``
  pin the full-matrix parity, the evaluation order AND the derive_scope <->
  SCOPE_LEVELS vocabulary parity (M-01 adding a scope level turns them red).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Iterable, Mapping
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import MEMORY_PREFILTER_REJECTIONS_TOTAL
from app.core.time_utils import ensure_naive_utc, utcnow
from app.services.memory_epistemic_contract import (
    EpistemicClass,
    MemoryRecordStatus,
    classify_episodic_class,
    derive_scope,
    derive_status,
)

MEMORY_PREFILTER_VERSION = "memory-v3.m03.v1"

# ---------------------------------------------------------------------------
# 1. Closed vocabularies (single source of truth)
# ---------------------------------------------------------------------------


class FilterDimension(StrEnum):
    """Coarse filter dimensions (metrics labels; card: user/status/revoked/
    scope/TTL/purpose/sensitivity —— revoked is a status value under M-01's
    status precedence, so it reports under ``status`` with reason
    ``status:revoked``)."""

    USER = "user"
    STATUS = "status"
    TTL = "ttl"
    SCOPE = "scope"
    PURPOSE = "purpose"
    SENSITIVITY = "sensitivity"


# Fixed evaluation order: the first failing dimension owns the rejection
# reason (deterministic metric attribution).
FILTER_DIMENSIONS: tuple[FilterDimension, ...] = (
    FilterDimension.USER,
    FilterDimension.STATUS,
    FilterDimension.TTL,
    FilterDimension.SCOPE,
    FilterDimension.PURPOSE,
    FilterDimension.SENSITIVITY,
)

# Memory scope levels (compatibility lattice). Aligned with C-01
# ``DECISION_SCOPES``: goal~plan/task anchors, domain~user-subject, global~
# global, session~session; ``task_type`` is the task-shape axis from
# MEMORY_V3.md §1 (no stored record derives it today —— explicit descriptors
# only, future writers).
SCOPE_LEVELS: tuple[str, ...] = ("global", "goal", "domain", "task_type", "session")

# Retrieval-constraint states for the compatibility matrix.
_SCOPE_CTX_STATES: tuple[str, ...] = ("unconstrained", "match", "mismatch")

# The compatibility matrix (closed structure). Semantics:
# - ``unconstrained``: ctx sets no anchor for the record's level, OR the
#   record itself carries no anchor on any constrained key (an unanchored
#   scoped record behaves as user-global).
# - ``match``: at least one record anchor equals a constrained ctx value.
# - ``mismatch``: ctx constrains the level and no anchor matches.
# session is fail-closed: transient/working-memory scope never leaks outside
# its own session (MEMORY_V3 §2 —— transient state must not cross sessions).
SCOPE_COMPATIBILITY: Mapping[tuple[str, str], bool] = MappingProxyType(
    {
        ("global", "unconstrained"): True,
        ("global", "match"): True,
        ("global", "mismatch"): True,
        ("goal", "unconstrained"): True,
        ("goal", "match"): True,
        ("goal", "mismatch"): False,
        ("domain", "unconstrained"): True,
        ("domain", "match"): True,
        ("domain", "mismatch"): False,
        ("task_type", "unconstrained"): True,
        ("task_type", "match"): True,
        ("task_type", "mismatch"): False,
        ("session", "unconstrained"): False,
        ("session", "match"): True,
        ("session", "mismatch"): False,
    }
)

# Which descriptor keys are the anchors for each level (used both to read the
# record's anchors and to find the ctx constraints that apply to it).
LEVEL_ANCHOR_KEYS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "global": (),
        "goal": ("goal_id", "task_id", "plan_id"),
        "domain": ("domain_key",),
        "task_type": ("task_type",),
        "session": ("session_id",),
    }
)

# Closed consumption-purpose vocabulary. ``llm_context`` is the chat/pack
# injection purpose; jobs that legitimately need every row (decay, repair,
# conflict resolution) do not go through retrieval prefiltering.
RETRIEVAL_PURPOSES: frozenset[str] = frozenset({"llm_context", "personalization", "analytics", "export", "governance"})
PURPOSE_LLM_CONTEXT = "llm_context"

# Ordered sensitivity vocabulary: a record is legal only when its sensitivity
# rank <= the retrieval context ceiling. No existing column derives
# ``sensitive`` today (documented limitation —— mechanism is live, policy
# data lands with future writers; see module docstring and M-03 report).
SENSITIVITY_RANK: Mapping[str, int] = MappingProxyType({"normal": 0, "sensitive": 1})
DEFAULT_MAX_SENSITIVITY = "normal"

# TTL rules derived from existing columns (naive-UTC canonical, time_utils):
# - ``due_at+7d`` commitment records (memory_inferred_write_lane) hard-expire
#   7 days after their due_at (D4 ledger: previously NO consumer).
# - ``1d``/``today`` decay policies mark today-only records: valid solely on
#   their capture date (UTC day of ``created_at``).
# Half-life policies (7d/30d/60d/90d) are soft decay, owned by the daily
# decay job (archival -> status dimension); they are NOT hard cuts here.
EPISODIC_HARD_TTL_BY_DECAY_POLICY: Mapping[str, int] = MappingProxyType({"due_at+7d": 7})
TODAY_ONLY_DECAY_POLICIES: frozenset[str] = frozenset({"1d", "today"})

# ---------------------------------------------------------------------------
# 2. Scope descriptor + retrieval context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryScopeDescriptor:
    """Typed scope of one memory candidate.

    ``scope_of_record`` derives it from existing storage via the M-01
    ``derive_scope`` projection; explicit construction is for tests and for
    future writers that declare scope at write time.
    """

    level: str = "global"
    goal_id: str | None = None
    task_id: str | None = None
    plan_id: str | None = None
    domain_key: str | None = None
    task_type: str | None = None
    session_id: str | None = None
    # time window (TTL dimension inputs)
    today_only: bool = False
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    # purpose / sensitivity restrictions (explicit descriptors only today)
    allowed_purposes: frozenset[str] | None = None
    sensitivity: str = "normal"


@dataclass(frozen=True)
class UserMemoryPermissions:
    """Best-effort snapshot of ``user_memory_settings`` (permission layer of
    the purpose dimension). Missing settings row -> everything allowed
    (matches write-side ``_is_user_disabled`` semantics)."""

    enabled: bool = True
    allow_preferences: bool = True
    allow_goals: bool = True
    allow_episodic: bool = True
    allow_inferred_episodic: bool = True
    blocked_pref_keys: frozenset[str] = frozenset()
    blocked_sources: frozenset[str] = frozenset()

    @classmethod
    def from_settings_row(cls, row: Any) -> UserMemoryPermissions:
        if row is None:
            return cls()
        return cls(
            enabled=bool(getattr(row, "enabled", True)),
            allow_preferences=bool(getattr(row, "allow_preferences", True)),
            allow_goals=bool(getattr(row, "allow_goals", True)),
            allow_episodic=bool(getattr(row, "allow_episodic", True)),
            allow_inferred_episodic=bool(getattr(row, "allow_inferred_episodic", True)),
            blocked_pref_keys=frozenset(str(k) for k in (getattr(row, "blocked_pref_keys", None) or [])),
            blocked_sources=frozenset(str(s) for s in (getattr(row, "blocked_sources", None) or [])),
        )


@dataclass(frozen=True)
class RetrievalContext:
    """Everything the deterministic prefilter is allowed to know about the
    consumption act. ``now`` is naive UTC (time_utils canonical)."""

    user_id: str
    purpose: str
    now: datetime
    goal_ids: frozenset[str] = frozenset()
    task_ids: frozenset[str] = frozenset()
    plan_ids: frozenset[str] = frozenset()
    domain_keys: frozenset[str] = frozenset()
    task_type: str | None = None
    session_id: str | None = None
    permissions: UserMemoryPermissions = field(default_factory=UserMemoryPermissions)
    max_sensitivity: str = DEFAULT_MAX_SENSITIVITY

    def __post_init__(self) -> None:
        if self.purpose not in RETRIEVAL_PURPOSES:
            raise ValueError(f"unknown retrieval purpose {self.purpose!r}; vocabulary: {sorted(RETRIEVAL_PURPOSES)}")
        if self.max_sensitivity not in SENSITIVITY_RANK:
            raise ValueError(
                f"unknown max_sensitivity {self.max_sensitivity!r}; vocabulary: {sorted(SENSITIVITY_RANK)}"
            )


# ctx anchor values per descriptor key (single mapping used by both the
# matrix evaluation and the lattice tests —— prevents scattered definitions).
CTX_ANCHOR_VALUES: Mapping[str, Any] = MappingProxyType(
    {
        "goal_id": lambda ctx: ctx.goal_ids,
        "task_id": lambda ctx: ctx.task_ids,
        "plan_id": lambda ctx: ctx.plan_ids,
        "domain_key": lambda ctx: ctx.domain_keys,
        "task_type": lambda ctx: frozenset({ctx.task_type}) if ctx.task_type else frozenset(),
        "session_id": lambda ctx: frozenset({ctx.session_id}) if ctx.session_id else frozenset(),
    }
)


# ---------------------------------------------------------------------------
# 3. Result types (filter reason metrics)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rejection:
    record_id: str
    dimension: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class PrefilterResult:
    allowed: list[Any]
    rejections: list[Rejection]
    input_count: int
    dimension_counts: dict[str, int]
    reason_counts: dict[str, int]

    @property
    def allowed_count(self) -> int:
        return len(self.allowed)

    def to_metric_payload(self) -> dict[str, Any]:
        """Structured filter-reason output for pack metadata / telemetry
        (consumed by D-06/O-02 observability)."""
        return {
            "version": MEMORY_PREFILTER_VERSION,
            "input_count": self.input_count,
            "allowed_count": self.allowed_count,
            "dimension_counts": dict(self.dimension_counts),
            "reason_counts": dict(self.reason_counts),
        }


# ---------------------------------------------------------------------------
# 4. Derivation helpers (delegate to M-01 authorities)
# ---------------------------------------------------------------------------


def record_kind(record: Any) -> str:
    """Which memory family a candidate belongs to (for type-level
    permissions). ORM rows use ``__tablename__``; duck-typed projections fall
    back to attribute sniffing."""
    table = str(getattr(type(record), "__tablename__", "") or "")
    if table == "memory_preferences":
        return "preference"
    if table == "memory_goals":
        return "goal"
    if table == "episodic_memories":
        return "episodic"
    if getattr(record, "pref_key", None) is not None:
        return "preference"
    if getattr(record, "summary", None) is not None and getattr(record, "occurred_at", None) is not None:
        return "episodic"
    if getattr(record, "expires_at", None) is not None or getattr(record, "target_date", None) is not None:
        return "goal"
    return "unknown"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return ensure_naive_utc(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def scope_of_record(record: Any) -> MemoryScopeDescriptor:
    """Lift the M-01 ``derive_scope`` projection into the typed descriptor.

    M-01 stays the derivation authority over existing columns; this module
    only adds TTL/sensitivity/purpose semantics on top.
    """
    projection = derive_scope(record)
    # Unknown levels are PRESERVED, never lifted to "global": scope_compatible
    # fail-closes them (reason scope:unknown_level, metric-observable). Lifting
    # an uninterpretable scope to user-global would be fail-open — exactly the
    # fault class this layer exists to prevent (R2-F1). The derive_scope <->
    # SCOPE_LEVELS vocabulary parity guard in the unit tests turns red the
    # moment M-01 emits a level this module cannot interpret.
    level = str(projection.get("level") or "global")
    time_window = projection.get("time_window") or {}
    decay_policy = str(projection.get("decay_policy") or "").strip().lower()
    today_only = decay_policy in TODAY_ONLY_DECAY_POLICIES
    valid_until = _parse_iso(time_window.get("expires_at"))
    if valid_until is None:
        valid_until = _parse_iso(time_window.get("due_at"))
    return MemoryScopeDescriptor(
        level=level,
        goal_id=str(projection["task_id"]) if level == "goal" and projection.get("task_id") else None,
        task_id=str(projection.get("task_id")) if projection.get("task_id") else None,
        plan_id=str(projection.get("plan_id")) if projection.get("plan_id") else None,
        domain_key=str(projection.get("domain_key")) if projection.get("domain_key") else None,
        task_type=None,
        session_id=str(projection.get("session_id")) if projection.get("session_id") else None,
        today_only=today_only,
        valid_from=None,
        valid_until=valid_until,
    )


def sensitivity_of_record(record: Any, descriptor: MemoryScopeDescriptor) -> str:
    """Record sensitivity. No existing column carries it (default ``normal``);
    explicit descriptors / future columns plug in here without touching the
    enforcement point."""
    value = str(descriptor.sensitivity or DEFAULT_MAX_SENSITIVITY).strip().lower()
    return value if value in SENSITIVITY_RANK else DEFAULT_MAX_SENSITIVITY


def _is_inferred_episodic(record: Any) -> bool:
    """An episodic record written by the inference layer: M-01 classifies
    rule/llm/unknown-lane rows as HYPOTHESIS —— single source of truth."""
    if record_kind(record) != "episodic":
        return False
    epistemic = classify_episodic_class(
        getattr(record, "source_lane", None),
        explicit_class=getattr(record, "epistemic_class", None),
        source_type=getattr(record, "source_type", None),
    )
    return epistemic == EpistemicClass.HYPOTHESIS.value


def _record_id(record: Any) -> str:
    for attr in ("id", "entry_id", "pref_key"):
        value = getattr(record, attr, None)
        if value is not None:
            return str(value)
    return "<unknown>"


def _record_user_id(record: Any) -> str | None:
    value = getattr(record, "user_id", None)
    return None if value is None else str(value)


# ---------------------------------------------------------------------------
# 5. Dimension checks (pure)
# ---------------------------------------------------------------------------


def _reject_user(record: Any, ctx: RetrievalContext) -> Rejection | None:
    record_user = _record_user_id(record)
    if record_user is None or record_user != ctx.user_id:
        return Rejection(
            record_id=_record_id(record),
            dimension=FilterDimension.USER.value,
            reason="user:wrong_user",
            detail=f"record_user={record_user!r} context_user={ctx.user_id!r}",
        )
    return None


def _reject_status(record: Any, ctx: RetrievalContext) -> Rejection | None:
    status = derive_status(record, now=ctx.now)
    if status != MemoryRecordStatus.ACTIVE.value:
        return Rejection(
            record_id=_record_id(record),
            dimension=FilterDimension.STATUS.value,
            reason=f"status:{status}",
            detail="M-01 status machine (revoked>superseded>retracted>archived>expired>resolved)",
        )
    return None


def _reject_ttl(
    record: Any,
    ctx: RetrievalContext,
    descriptor: MemoryScopeDescriptor,
) -> Rejection | None:
    now = ctx.now
    if descriptor.valid_from is not None and now < descriptor.valid_from:
        return Rejection(
            record_id=_record_id(record),
            dimension=FilterDimension.TTL.value,
            reason="ttl:not_yet_valid",
            detail=f"valid_from={descriptor.valid_from.isoformat()}",
        )
    # Column-backed expiry (goals.expires_at) already reported by the status
    # machine as status:expired; here we only add lattice-derived windows.
    due_at = ensure_naive_utc(getattr(record, "due_at", None))
    decay_policy = str(getattr(record, "decay_policy", None) or "").strip().lower()
    hard_days = EPISODIC_HARD_TTL_BY_DECAY_POLICY.get(decay_policy)
    if hard_days is not None and due_at is not None:
        horizon = due_at + timedelta(days=hard_days)
        if now > horizon:
            return Rejection(
                record_id=_record_id(record),
                dimension=FilterDimension.TTL.value,
                reason="ttl:expired",
                detail=f"decay_policy={decay_policy} due_at={due_at.isoformat()} horizon={horizon.isoformat()}",
            )
    if descriptor.today_only:
        anchor_date = ensure_naive_utc(getattr(record, "created_at", None)) or ensure_naive_utc(
            getattr(record, "occurred_at", None)
        )
        anchor_day = anchor_date.date() if anchor_date is not None else None
        if anchor_day is not None and now.date() != anchor_day:
            return Rejection(
                record_id=_record_id(record),
                dimension=FilterDimension.TTL.value,
                reason="ttl:today_only_expired",
                detail=f"valid_on={anchor_day.isoformat()} now={now.date().isoformat()} (naive-UTC days)",
            )
    return None


def _ctx_constraint_state(descriptor: MemoryScopeDescriptor, ctx: RetrievalContext) -> str:
    """Classify the (record, ctx) pair into a SCOPE_COMPATIBILITY column."""
    constrained = False
    matched = False
    for key in LEVEL_ANCHOR_KEYS.get(descriptor.level, ()):  # () for global
        ctx_values = CTX_ANCHOR_VALUES[key](ctx)
        if not ctx_values:
            continue
        constrained = True
        record_anchor = getattr(descriptor, key, None)
        if record_anchor is not None and str(record_anchor) in {str(v) for v in ctx_values}:
            matched = True
    if matched:
        return "match"
    if not constrained:
        return "unconstrained"
    # ctx constrains this level but no record anchor matched. An unanchored
    # record (no anchor values at all on this level's keys) does not
    # restrict itself -> behaves as user-global -> unconstrained column.
    anchors = [getattr(descriptor, key, None) for key in LEVEL_ANCHOR_KEYS.get(descriptor.level, ())]
    if all(anchor is None for anchor in anchors):
        return "unconstrained"
    return "mismatch"


def scope_compatible(descriptor: MemoryScopeDescriptor, ctx: RetrievalContext) -> tuple[bool, str | None]:
    """Evaluate the compatibility matrix for one descriptor. Unknown levels
    fail closed (never inject a record whose scope we cannot interpret)."""
    if descriptor.level not in SCOPE_LEVELS:
        return False, "scope:unknown_level"
    state = _ctx_constraint_state(descriptor, ctx)
    allowed = SCOPE_COMPATIBILITY[(descriptor.level, state)]
    if allowed:
        return True, None
    return False, "scope:mismatch"


def _reject_scope(descriptor: MemoryScopeDescriptor, ctx: RetrievalContext) -> Rejection | None:
    allowed, reason = scope_compatible(descriptor, ctx)
    if allowed:
        return None
    anchors = {
        key: getattr(descriptor, key, None)
        for key in LEVEL_ANCHOR_KEYS.get(descriptor.level, ())
        if getattr(descriptor, key, None) is not None
    }
    return Rejection(
        record_id="",  # filled by caller (needs the record)
        dimension=FilterDimension.SCOPE.value,
        reason=reason or "scope:mismatch",
        detail=f"level={descriptor.level} anchors={anchors}",
    )


def _reject_purpose(
    record: Any,
    ctx: RetrievalContext,
    descriptor: MemoryScopeDescriptor,
) -> Rejection | None:
    permissions = ctx.permissions
    kind = record_kind(record)
    record_id = _record_id(record)

    def _reject(reason: str, detail: str) -> Rejection:
        return Rejection(record_id=record_id, dimension=FilterDimension.PURPOSE.value, reason=reason, detail=detail)

    if not permissions.enabled:
        return _reject("purpose:memory_disabled", "user_memory_settings.enabled=false")
    if kind == "preference":
        if not permissions.allow_preferences:
            return _reject("purpose:type_disabled", "allow_preferences=false")
        pref_key = str(getattr(record, "pref_key", "") or "")
        if pref_key and pref_key in permissions.blocked_pref_keys:
            return _reject("purpose:blocked_pref_key", f"pref_key={pref_key}")
    elif kind == "goal":
        if not permissions.allow_goals:
            return _reject("purpose:type_disabled", "allow_goals=false")
    elif kind == "episodic":
        if not permissions.allow_episodic:
            return _reject("purpose:type_disabled", "allow_episodic=false")
        if not permissions.allow_inferred_episodic and _is_inferred_episodic(record):
            return _reject("purpose:inferred_episodic_disabled", "M-01 class=HYPOTHESIS (inference lane)")
    source_type = str(getattr(record, "source_type", "") or "")
    if source_type and source_type in permissions.blocked_sources:
        return _reject("purpose:blocked_source", f"source_type={source_type}")
    if descriptor.allowed_purposes is not None and ctx.purpose not in descriptor.allowed_purposes:
        return _reject(
            "purpose:not_allowed",
            f"record allows {sorted(descriptor.allowed_purposes)}, consumption purpose={ctx.purpose}",
        )
    return None


def _reject_sensitivity(
    record: Any,
    ctx: RetrievalContext,
    descriptor: MemoryScopeDescriptor,
) -> Rejection | None:
    sensitivity = sensitivity_of_record(record, descriptor)
    if SENSITIVITY_RANK[sensitivity] > SENSITIVITY_RANK[ctx.max_sensitivity]:
        return Rejection(
            record_id=_record_id(record),
            dimension=FilterDimension.SENSITIVITY.value,
            reason="sensitivity:exceeded",
            detail=f"record={sensitivity} ceiling={ctx.max_sensitivity}",
        )
    return None


# ---------------------------------------------------------------------------
# 6. The prefilter (pure core)
# ---------------------------------------------------------------------------


def prefilter_candidates(candidates: Iterable[Any], ctx: RetrievalContext) -> PrefilterResult:
    """Deterministically cut illegal memory candidates before semantic
    retrieval. Returns the legal subset plus per-record rejection reasons and
    per-dimension / per-reason counts (also emitted as logs + metrics)."""
    allowed: list[Any] = []
    rejections: list[Rejection] = []
    dimension_counts: dict[str, int] = {dimension.value: 0 for dimension in FILTER_DIMENSIONS}
    reason_counts: dict[str, int] = {}
    input_count = 0

    for record in candidates:
        input_count += 1
        descriptor = scope_of_record(record)
        rejection: Rejection | None = (
            _reject_user(record, ctx)
            or _reject_status(record, ctx)
            or _reject_ttl(record, ctx, descriptor)
            or _reject_scope(descriptor, ctx)
            or _reject_purpose(record, ctx, descriptor)
            or _reject_sensitivity(record, ctx, descriptor)
        )
        if rejection is None:
            allowed.append(record)
            continue
        if rejection.dimension == FilterDimension.SCOPE.value and not rejection.record_id:
            rejection = Rejection(
                record_id=_record_id(record),
                dimension=rejection.dimension,
                reason=rejection.reason,
                detail=rejection.detail,
            )
        rejections.append(rejection)
        dimension_counts[rejection.dimension] = dimension_counts.get(rejection.dimension, 0) + 1
        reason_counts[rejection.reason] = reason_counts.get(rejection.reason, 0) + 1
        try:
            MEMORY_PREFILTER_REJECTIONS_TOTAL.labels(dimension=rejection.dimension, reason=rejection.reason).inc()
        except Exception:  # pragma: no cover - metrics must never break retrieval
            pass

    result = PrefilterResult(
        allowed=allowed,
        rejections=rejections,
        input_count=input_count,
        dimension_counts=dimension_counts,
        reason_counts=reason_counts,
    )
    if rejections:
        logger.info(
            "M-03 memory prefilter: input={} allowed={} rejected_dims={} rejected_reasons={}",
            input_count,
            result.allowed_count,
            {k: v for k, v in dimension_counts.items() if v},
            reason_counts,
        )
    return result


def apply_memory_prefilter(candidates: Iterable[Any], ctx: RetrievalContext) -> list[Any]:
    """Convenience wrapper returning only the legal subset."""
    return prefilter_candidates(candidates, ctx).allowed


# ---------------------------------------------------------------------------
# 7. Async adapter (only I/O boundary of this module)
# ---------------------------------------------------------------------------


async def build_retrieval_context(
    db: AsyncSession | None,
    *,
    user_id: UUID | str,
    purpose: str,
    plan_id: UUID | str | None = None,
    task_ids: Iterable[UUID | str] = (),
    goal_ids: Iterable[UUID | str] = (),
    domain_keys: Iterable[str] = (),
    task_type: str | None = None,
    session_id: str | None = None,
    max_sensitivity: str = DEFAULT_MAX_SENSITIVITY,
    now: datetime | None = None,
) -> RetrievalContext:
    """Assemble the RetrievalContext for a consumption act.

    Loads ``user_memory_settings`` best-effort (missing row / DB error ->
    defaults, matching write-side semantics); a settings read failure must
    never take down context assembly.
    """
    from app.models.user_memory_settings import UserMemorySettings

    permissions = UserMemoryPermissions()
    if db is not None:
        try:
            result = await db.execute(
                select(UserMemorySettings).where(
                    UserMemorySettings.user_id == UUID(str(user_id)),
                    UserMemorySettings.deleted_at.is_(None),
                )
            )
            permissions = UserMemoryPermissions.from_settings_row(result.scalar_one_or_none())
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("M-03 prefilter: user_memory_settings load failed, using defaults: {}", exc)

    plan_ids = frozenset({str(plan_id)}) if plan_id is not None else frozenset()
    return RetrievalContext(
        user_id=str(user_id),
        purpose=purpose,
        now=ensure_naive_utc(now) or utcnow(),
        goal_ids=frozenset(str(g) for g in goal_ids),
        task_ids=frozenset(str(t) for t in task_ids),
        plan_ids=plan_ids,
        domain_keys=frozenset(str(d) for d in domain_keys),
        task_type=task_type,
        session_id=session_id,
        permissions=permissions,
        max_sensitivity=max_sensitivity,
    )
