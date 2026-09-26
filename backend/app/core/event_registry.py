"""V3 Event Name Registry & shared-fields contract (D-01).

Single authority (backend/app side) for:

1. **Closed vocabulary of V3 event names** — every event name that may be
   written into the shared event domain (``event_outbox`` / ``event_store`` /
   gateway CQRS bus) is declared here with its flywheel stage, aggregate type,
   producers and lifecycle status. Free-string event names are contract
   violations for new writers.
2. **Shared fields contract** — the envelope every V3 event must carry
   (idempotency ``event_id``, isolation ``user_id``, correlation ids linking
   intervention/action/run/outcome, naive-UTC ``occurred_at``,
   ``schema_version``, closed ``source`` enum). The physical column set of
   ``event_outbox`` is NOT extended: shared fields ride in the ``metadata``
   jsonb (and payload), so existing writers/consumers stay wire-compatible.
   Legacy rows whose metadata is only ``{"service": ...}``` remain readable
   through :func:`read_event_metadata`.
3. **Telemetry boundary** — ``tracking_events`` (client telemetry) is declared
   non-truth: events with source ``client_telemetry`` are ineligible as
   business truth. The authoritative user world state (state_aggregator /
   evidence fusion) must consume only server-authoritative sources.

Aligned with C-01 ``decision_context.v1``: correlation ids are the same
record ids referenced by ``memory://`` / ``plan://`` ref URIs, and
``schema_version`` follows the same ``<contract>.v<n>`` convention.

This module is stdlib-only and performs no I/O; it is importable from any
layer of backend/app (services, workers, api) without cycle risk.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

_LOGGER = logging.getLogger("app.core.event_registry")

__all__ = [
    "EVENT_SCHEMA_VERSION",
    "EventStage",
    "EventSource",
    "RegisteredEvent",
    "EventNameError",
    "EventContractError",
    "CorrelationIds",
    "EVENT_REGISTRY",
    "REGISTERED_EVENT_NAMES",
    "CORRELATION_EXEMPT_EVENT_NAMES",
    "require_registered_event",
    "is_registered_event_name",
    "classify_stage",
    "derive_event_id",
    "build_event_metadata",
    "read_event_metadata",
    "MAX_METADATA_JSON_BYTES",
    "MAX_METADATA_MAPPING_CHARS",
    "normalize_occurred_at",
    "is_telemetry_source",
    "is_business_truth_eligible",
    "TELEMETRY_TABLE",
    "CORRELATION_KEYS",
]

# --- Contract identity -------------------------------------------------------

EVENT_SCHEMA_VERSION = "event.v1"
"""Schema version stamped into every V3 event metadata envelope."""

TELEMETRY_TABLE = "tracking_events"
"""Physical table holding client telemetry. Declared non-truth for business decisions."""


# --- Closed vocabularies -----------------------------------------------------


class EventStage(StrEnum):
    """Flywheel stage (DATA_FLYWHEEL.md §1) an event belongs to."""

    INTERACTION = "interaction"  # user-visible interaction (chat, study, UI action)
    DECISION = "decision"  # routing / aurora / planner decisions
    EXECUTION = "execution"  # intervention / action / agent-run execution steps
    OUTCOME = "outcome"  # outcome observations (feedback, results, effects)
    STATE_UPDATE = "state_update"  # user world / galaxy / memory state mutations


class EventSource(StrEnum):
    """Closed producer-source enum (shared field ``source``)."""

    SERVER_SERVICE = "server_service"  # python engine service (authoritative writer)
    GATEWAY = "gateway"  # go gateway CQRS (authoritative writer)
    WORKER = "worker"  # celery / run worker (authoritative writer)
    CLIENT_TELEMETRY = "client_telemetry"  # mobile-reported telemetry (NON-TRUTH)
    PROBE = "probe"  # dev probes / experiments (NON-TRUTH for cohorts)


TELEMETRY_SOURCES: frozenset[EventSource] = frozenset({EventSource.CLIENT_TELEMETRY, EventSource.PROBE})


class EventNameError(Exception):
    """Raised when an event name is not in the closed registry."""


class EventContractError(Exception):
    """Raised when a shared-field contract rule is violated."""


@dataclass(frozen=True)
class RegisteredEvent:
    """One entry of the closed event-name vocabulary."""

    name: str
    stage: EventStage
    aggregate_type: str
    producers: tuple[str, ...]
    status: str  # "live" (produced in repo) | "observed_unregistered" (in DB, no producer in repo) | "reserved" (V3, not yet produced)

    @property
    def is_live(self) -> bool:
        return self.status == "live"


def _go(*names: str) -> tuple[str, ...]:
    return tuple(f"gateway/internal/cqrs/event/types.go ({n})" for n in names)


# The registry itself. Ordering follows the flywheel loop.
EVENT_REGISTRY: dict[str, RegisteredEvent] = {
    e.name: e
    for e in (
        # --- INTERACTION ----------------------------------------------------
        RegisteredEvent(
            name="chat.message.sent",
            stage=EventStage.INTERACTION,
            aggregate_type="ChatSession",
            producers=_go("EventMessageSent"),
            status="live",
        ),
        RegisteredEvent(
            name="chat.message.received",
            stage=EventStage.INTERACTION,
            aggregate_type="ChatSession",
            producers=_go("EventMessageReceived"),
            status="live",
        ),
        RegisteredEvent(
            name="chat.session.created",
            stage=EventStage.INTERACTION,
            aggregate_type="ChatSession",
            producers=_go("EventSessionCreated"),
            status="live",
        ),
        RegisteredEvent(
            name="chat.session.ended",
            stage=EventStage.INTERACTION,
            aggregate_type="ChatSession",
            producers=_go("EventSessionEnded"),
            status="live",
        ),
        RegisteredEvent(
            name="galaxy.study.recorded",
            stage=EventStage.INTERACTION,
            aggregate_type="KnowledgeNode",
            producers=_go("EventStudyRecordAdded"),
            status="live",
        ),
        RegisteredEvent(
            name="user.preferences.updated",
            stage=EventStage.INTERACTION,
            aggregate_type="User",
            producers=_go("EventPreferencesUpdated"),
            status="live",
        ),
        # --- DECISION -------------------------------------------------------
        RegisteredEvent(
            name="decision.recorded",
            stage=EventStage.DECISION,
            aggregate_type="decision_record",
            producers=("v3: decision_records read projection",),
            status="reserved",
        ),
        RegisteredEvent(
            name="routing.decision_recorded",
            stage=EventStage.DECISION,
            aggregate_type="intervention_request",
            producers=("app/services/routing_outcome_service.py (passive_signals, " "schema routing_outcome.v1)",),
            status="reserved",
        ),
        RegisteredEvent(
            # X-02 · Human/Agent/Hybrid allocation rubric 决策事件（与
            # routing.decision_recorded 同族：决策域的细分事件名）。产出方是
            # app/services/action_allocation_policy.py 的决策记录结构；落
            # event_outbox 由消费方（A-04 Aurora 联合决策 / X-05 Unified Run）执行。
            name="allocation.decision_recorded",
            stage=EventStage.DECISION,
            aggregate_type="allocation_decision",
            producers=("app/services/action_allocation_policy.py",),
            status="reserved",
        ),
        # --- EXECUTION: interventions / actions / runs ----------------------
        RegisteredEvent(
            name="intervention.requested",
            stage=EventStage.EXECUTION,
            aggregate_type="intervention_request",
            producers=("v3: intervention pipeline",),
            status="reserved",
        ),
        RegisteredEvent(
            name="intervention.delivered",
            stage=EventStage.EXECUTION,
            aggregate_type="intervention_request",
            producers=("v3: intervention pipeline",),
            status="reserved",
        ),
        RegisteredEvent(
            name="intervention.feedback_recorded",
            stage=EventStage.OUTCOME,
            aggregate_type="intervention_request",
            producers=("v3: intervention feedback",),
            status="reserved",
        ),
        RegisteredEvent(
            # D-05 (2026-09-19): intervention lifecycle analysis events. The
            # durable analysis truth is intervention_lifecycle_events (D-02
            # read-model family); these outbox names carry the integration
            # notifications only (outbox rows are cleanup-deleted after 7 days
            # and are NOT the analysis store). decision_id (aurora_<32hex>)
            # rides payload/metadata extra — CorrelationIds enforces canonical
            # UUIDs, so it cannot ride correlation.decision_id (D-01/D-02
            # registered follow-up, same as evt_/outc_ prefixes).
            name="intervention.exposed",
            stage=EventStage.EXECUTION,
            aggregate_type="intervention_lifecycle",
            producers=("app/services/intervention_lifecycle_service.py",),
            status="reserved",
        ),
        RegisteredEvent(
            name="intervention.started",
            stage=EventStage.EXECUTION,
            aggregate_type="intervention_lifecycle",
            producers=("app/services/intervention_lifecycle_service.py",),
            status="reserved",
        ),
        RegisteredEvent(
            # Association fact: one whitelisted D-02 outcome linked to one
            # intervention decision within its observation window. outcome facts
            # stay owned by the D-02 five sources; this event records only the
            # (decision_id, outcome_ref) link.
            name="intervention.outcome_associated",
            stage=EventStage.OUTCOME,
            aggregate_type="intervention_lifecycle",
            producers=("app/services/intervention_lifecycle_service.py",),
            status="reserved",
        ),
        RegisteredEvent(
            # X-03 (2026-09-19): Action proposal 统一 command path 落地 producer
            # （app/services/action_command_service.py，proposal/commit/reject 同事务
            # 写 outbox）。词表名不变（D-01 冻结 36 名零新增），reserved→live。
            name="action.proposed",
            stage=EventStage.EXECUTION,
            aggregate_type="action",
            producers=("app/services/action_command_service.py",),
            status="live",
        ),
        RegisteredEvent(
            name="action.accepted",
            stage=EventStage.EXECUTION,
            aggregate_type="action",
            producers=("app/services/action_command_service.py",),
            status="live",
        ),
        RegisteredEvent(
            name="action.rejected",
            stage=EventStage.OUTCOME,
            aggregate_type="action",
            producers=("app/services/action_command_service.py",),
            status="live",
        ),
        RegisteredEvent(
            # X-05 (2026-09-19): unified agent run 持久状态机落地，仓内首个
            # run.* producer（app/services/agent_run_service.py）。原探针行
            # （2026-09-17，run_worker_service）的 4 个名字转为 live。
            name="run.created",
            stage=EventStage.EXECUTION,
            aggregate_type="agent_run",
            producers=("app/services/agent_run_service.py",),
            status="live",
        ),
        RegisteredEvent(
            # X-05: 其余状态迁移的统一事件（语义时刻用专名 run.awaiting_user /
            # run.user_resumed，进度用 run.step_completed；QUEUED→RUNNING、
            # 各终态等一律 run.status_changed）。与 task.status_changed 同族。
            # X-05B: execution 轨道步进里程碑复用本名上 EventBus
            # （execution_run_producer → run 投影消费；零新事件名，schema
            # 扩展字段 milestone/run 块）。
            name="run.status_changed",
            stage=EventStage.EXECUTION,
            aggregate_type="agent_run",
            producers=(
                "app/services/agent_run_service.py",
                "app/services/execution_run_producer.py",
            ),
            status="live",
        ),
        RegisteredEvent(
            name="run.step_completed",
            stage=EventStage.EXECUTION,
            aggregate_type="agent_run",
            producers=("app/services/agent_run_service.py",),
            status="live",
        ),
        RegisteredEvent(
            name="run.awaiting_user",
            stage=EventStage.EXECUTION,
            aggregate_type="agent_run",
            producers=("app/services/agent_run_service.py",),
            status="live",
        ),
        RegisteredEvent(
            name="run.user_resumed",
            stage=EventStage.EXECUTION,
            aggregate_type="agent_run",
            producers=("app/services/agent_run_service.py",),
            status="live",
        ),
        RegisteredEvent(
            name="task.status_changed",
            stage=EventStage.EXECUTION,
            aggregate_type="task_command",
            producers=(),
            status="observed_unregistered",
        ),
        RegisteredEvent(
            name="task.created",
            stage=EventStage.INTERACTION,
            aggregate_type="Task",
            producers=_go("EventTaskCreated"),
            status="live",
        ),
        RegisteredEvent(
            name="task.started",
            stage=EventStage.EXECUTION,
            aggregate_type="Task",
            producers=_go("EventTaskStarted"),
            status="live",
        ),
        RegisteredEvent(
            name="task.completed",
            stage=EventStage.OUTCOME,
            aggregate_type="Task",
            producers=_go("EventTaskCompleted"),
            status="live",
        ),
        RegisteredEvent(
            name="task.abandoned",
            stage=EventStage.OUTCOME,
            aggregate_type="Task",
            producers=_go("EventTaskAbandoned"),
            status="live",
        ),
        RegisteredEvent(
            name="asset_created",
            stage=EventStage.EXECUTION,
            aggregate_type="learning_asset",
            producers=("app/services/learning_asset_service.py",),
            status="live",
        ),
        RegisteredEvent(
            name="asset_status_changed",
            stage=EventStage.EXECUTION,
            aggregate_type="learning_asset",
            producers=("app/services/learning_asset_service.py",),
            status="live",
        ),
        # --- OUTCOME --------------------------------------------------------
        RegisteredEvent(
            name="outcome.recorded",
            stage=EventStage.OUTCOME,
            aggregate_type="outcome",
            producers=(
                "app/services/outcome_capture_service.py (X-08 outcome evidence adapter: "
                "task terminal states COMPLETED/ABANDONED → unified Outcome capture; "
                "partial/failed preserved as NEUTRAL/NEGATIVE polarity, never lit)",
            ),
            status="live",
        ),
        RegisteredEvent(
            # S-04 (2026-09-25): community peer-feedback adoption → structured
            # Goal outcome evidence. The durable truth is the
            # community_outcome_evidence table (S-04; one row per adopted
            # feedback, real FKs to goal/feedback/shared_resource); this outbox
            # name carries the integration notification only — same split as
            # D-05 (outbox rows are cleanup-deleted after 7 days and are NOT
            # the analysis store). Feedback that is NOT explicitly adopted by
            # the resource owner never produces this event (and never touches
            # mastery/progress). Payload is ids + closed verdict vocabulary
            # only (no comments, no peer aliases — audit-without-exposure).
            # feedback_id/goal_id/evidence_id ride payload/metadata extra:
            # feedback_id and goal_id are not in CORRELATION_KEYS (D-01 froze
            # that set), task_id/plan_id correlation rides when the shared
            # artifact carries them.
            name="community.feedback_adopted",
            stage=EventStage.OUTCOME,
            aggregate_type="community_outcome_evidence",
            producers=("app/services/community_feedback_service.py",),
            status="live",
        ),
        # --- STATE UPDATE ---------------------------------------------------
        RegisteredEvent(
            name="galaxy.node.mastery_updated",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="galaxy_node_mastery",
            producers=(
                "app/services/galaxy_service.py::_write_mastery_outbox_event",
                "app/services/galaxy/stats_service.py::_write_spark_outbox_event",
            ),
            status="live",
        ),
        RegisteredEvent(
            name="galaxy.node.created",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="KnowledgeNode",
            producers=_go("EventNodeCreated"),
            status="live",
        ),
        RegisteredEvent(
            name="galaxy.node.unlocked",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="KnowledgeNode",
            producers=_go("EventNodeUnlocked"),
            status="live",
        ),
        RegisteredEvent(
            name="galaxy.mastery.updated",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="KnowledgeNode",
            producers=_go("EventMasteryUpdated"),
            status="live",
        ),
        RegisteredEvent(
            name="user_state.updated",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="user_state",
            producers=("v3: state_aggregator projection",),
            status="reserved",
        ),
        # M-07 (2026-09-19): memory invalidation. Emitted exactly once per
        # effective memory mutation (correction/revoke/supersede/delete) by the
        # unified pipeline, carrying the post-mutation memory_epoch so cache
        # holders and in-flight runs can detect staleness (MEMORY_V3.md §6).
        # Payload is content-free by contract (ids/action/epoch only).
        RegisteredEvent(
            name="memory.invalidated",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="user_memory",
            producers=("app/services/memory_invalidation_pipeline.py",),
            status="live",
        ),
        RegisteredEvent(
            name="user.created",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="User",
            producers=_go("EventUserCreated"),
            status="live",
        ),
        RegisteredEvent(
            name="user.updated",
            stage=EventStage.STATE_UPDATE,
            aggregate_type="User",
            producers=_go("EventUserUpdated"),
            status="live",
        ),
    )
}

REGISTERED_EVENT_NAMES: frozenset[str] = frozenset(EVENT_REGISTRY)

CORRELATION_EXEMPT_EVENT_NAMES: frozenset[str] = frozenset(
    {
        # Aggregate-root lifecycle events with no upstream causal object: the
        # learning-asset flow has no intervention/action/run/outcome/task id to
        # link — the asset itself (aggregate_id) + user_id IS the full lineage.
        # Declared exemption, not an oversight (D-01 R2-CHANGES #3); frozen by
        # test_correlation_exempt_names_are_frozen. Any new exemption must be
        # added deliberately with the same justification.
        "asset_created",
        "asset_status_changed",
    }
)


def is_registered_event_name(name: str) -> bool:
    return name in EVENT_REGISTRY


def require_registered_event(name: str) -> RegisteredEvent:
    """Return the registry entry or raise — the gate new writers must pass."""
    try:
        return EVENT_REGISTRY[name]
    except KeyError:
        raise EventNameError(
            f"Event name {name!r} is not in the V3 event registry. "
            "Register it in app/core/event_registry.py before emitting "
            "(closed vocabulary, D-01 contract)."
        ) from None


def classify_stage(name: str) -> EventStage:
    return require_registered_event(name).stage


# --- Correlation ids ---------------------------------------------------------

CORRELATION_KEYS: tuple[str, ...] = (
    "intervention_id",
    "action_id",
    "run_id",
    "outcome_id",
    # auxiliary causal links (same mechanism, wider than the four card names)
    "task_id",
    "session_id",
    "message_id",
    "decision_id",
    "plan_id",
    "node_id",
    # M-07: memory record id of the mutated memory (memory.invalidated events).
    "memory_id",
)


@dataclass(frozen=True)
class CorrelationIds:
    """Optional cross-links that stitch one event into the lineage graph.

    All values are canonical UUID strings. At least one correlation id is
    expected on EXECUTION/OUTCOME/STATE_UPDATE events so a GJ trace can walk
    interaction → decision → execution → outcome → state update purely by ids.
    """

    intervention_id: str | None = None
    action_id: str | None = None
    run_id: str | None = None
    outcome_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    message_id: str | None = None
    decision_id: str | None = None
    plan_id: str | None = None
    node_id: str | None = None
    memory_id: str | None = None

    def as_dict(self, drop_nones: bool = True) -> dict[str, str | None]:
        raw = {
            "intervention_id": self.intervention_id,
            "action_id": self.action_id,
            "run_id": self.run_id,
            "outcome_id": self.outcome_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "decision_id": self.decision_id,
            "plan_id": self.plan_id,
            "node_id": self.node_id,
            "memory_id": self.memory_id,
        }
        if drop_nones:
            return {k: v for k, v in raw.items() if v is not None}
        return raw

    @classmethod
    def coerce(cls, value: CorrelationIds | Mapping[str, Any] | None) -> CorrelationIds:
        if value is None:
            return cls()
        if isinstance(value, CorrelationIds):
            return value
        known = {f for f in cls.__dataclass_fields__}  # noqa: C416 — clarity
        return cls(**{k: _canonical_uuid(v) for k, v in dict(value).items() if k in known and v is not None})

    def __post_init__(self) -> None:
        for key in CORRELATION_KEYS:
            raw = getattr(self, key)
            if raw is not None:
                object.__setattr__(self, key, _canonical_uuid(raw))


def _canonical_uuid(value: UUID | str) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise EventContractError(f"correlation id {value!r} is not a valid UUID") from exc


# --- Shared-field helpers ----------------------------------------------------


def normalize_occurred_at(value: datetime | None) -> datetime:
    """Return a naive-UTC datetime (DB convention across the event domain)."""
    dt = value or datetime.now(UTC)
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def derive_event_id(
    *,
    event_name: str,
    aggregate_type: str,
    aggregate_id: UUID | str,
    sequence_number: int | str | None = None,
    correlation: CorrelationIds | Mapping[str, Any] | None = None,
) -> str:
    """Deterministic idempotency key for an event.

    Scope of the idempotency semantics (be precise, F1/R2-CHANGES #2):

    - SAME-ROW REDELIVERY: identical inputs (name/aggregate/seq/correlation)
      derive the identical key, so a consumer can dedupe replays of one
      outbox/event row delivered at-least-once.
    - NOT same-cause re-execution: re-running the same causal action burns a
      NEW sequence number (event_sequence_counters), hence a NEW key — that is
      duplicate-causes detection, which this key does not provide.

    CURRENT CONSUMER STATUS: zero consumers. The only active event_outbox
    consumer (gateway ``cqrs/outbox/publisher.go`` → Redis streams) dedupes by
    Redis ``messageID`` / consumer-group position and DECODES metadata through
    Go ``EventMetadata{trace_id, span_id, user_id, correlation_id, causation_id,
    source}`` — ``event_id``/``schema_version``/``occurred_at``/``correlation{}`
    are dropped at that hop. The gateway ``processed_events`` route is NOT
    usable as-is: ``outbox/repository.go IsProcessed`` runs ``uuid.Parse`` on
    the id, which REJECTS the ``evt_`` prefix — wiring a consumer there
    requires resolving the id format first (follow-up card, see D-01 REPORT).
    Callers that already own a globally unique id (e.g. outbox row uuid) may
    pass it as ``event_id`` to :func:`build_event_metadata` instead.
    """
    require_registered_event(event_name)
    corr = CorrelationIds.coerce(correlation).as_dict()
    seed = json.dumps(
        {
            "event_name": event_name,
            "aggregate_type": aggregate_type,
            "aggregate_id": str(aggregate_id),
            "sequence_number": None if sequence_number is None else str(sequence_number),
            "correlation": corr,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "evt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def build_event_metadata(
    *,
    user_id: UUID | str,
    source: EventSource | str,
    service: str,
    event_name: str,
    aggregate_type: str,
    aggregate_id: UUID | str,
    sequence_number: int | None = None,
    occurred_at: datetime | None = None,
    correlation: CorrelationIds | Mapping[str, Any] | None = None,
    event_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical ``event_outbox.metadata`` jsonb for a V3 event.

    Shared fields (contract, order frozen):
      event_id / user_id / schema_version / source / service / occurred_at /
      correlation{...}
    plus any ``extra`` keys (namespaced by caller, must not collide).
    """
    require_registered_event(event_name)
    try:
        source_enum = EventSource(source)
    except ValueError:
        raise EventContractError(f"source {source!r} not in closed enum {[s.value for s in EventSource]}") from None

    user_id = _canonical_uuid(user_id)
    corr = CorrelationIds.coerce(correlation).as_dict()
    metadata: dict[str, Any] = {
        "event_id": event_id
        or derive_event_id(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            sequence_number=sequence_number,
            correlation=corr,
        ),
        "user_id": user_id,
        "schema_version": EVENT_SCHEMA_VERSION,
        "source": source_enum.value,
        "service": service,
        "occurred_at": normalize_occurred_at(occurred_at).isoformat(),
    }
    if corr:
        metadata["correlation"] = corr
    if extra:
        collision = set(extra) & set(metadata)
        if collision:
            raise EventContractError(f"extra keys collide with shared fields: {sorted(collision)}")
        metadata.update(dict(extra))
    return metadata


@dataclass(frozen=True)
class EventMetadataView:
    """Read-side view of one event's shared fields (new or legacy shape)."""

    event_id: str | None
    user_id: str | None
    schema_version: str | None
    source: str | None
    service: str | None
    occurred_at: datetime | None
    correlation: Mapping[str, str] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_v3_envelope(self) -> bool:
        return self.schema_version == EVENT_SCHEMA_VERSION

    @property
    def is_telemetry(self) -> bool:
        return self.source is not None and self.source in {s.value for s in TELEMETRY_SOURCES}


MAX_METADATA_JSON_BYTES = 64 * 1024
"""Cap for str/bytes metadata input before json parsing (R2-CHANGES #4).

Legitimate envelopes are ~0.5 KiB; anything beyond this is a malformed/hostile
row and is rejected (empty view) with a warning log instead of parsed."""

MAX_METADATA_MAPPING_CHARS = 1 << 20
"""Approximate cap for already-decoded Mapping input (len of str() form)."""


def read_event_metadata(metadata: Mapping[str, Any] | str | bytes | None) -> EventMetadataView:
    """Parse an ``event_outbox``/``event_store`` metadata jsonb.

    Backward compatible: legacy rows written as ``{"service": "galaxy_service"}``
    (all 106 live rows at contract time) parse with ``is_v3_envelope == False``
    and ``user_id`` falling back to ``payload.user_id`` when the caller merges
    it via ``payload_hint``-style handling at the query layer.

    Defensive contract (R2-CHANGES #4 / F10): malformed inputs never raise —
    they degrade to an empty view with a warning log. Rejected shapes:
    non-Mapping Python objects (lists/scalars — previously a TypeError crash
    for raw lists), oversized str/bytes input, oversized Mapping input, and
    deeply-nested JSON (RecursionError during parse). Size/nesting guards are
    rejection+log, not truncation: a truncated JSON document is unparseable
    anyway, and logging content would leak row data.
    """
    parsed: dict[str, Any]
    if metadata is None:
        parsed = {}
    elif isinstance(metadata, (str, bytes)):
        raw_len = len(metadata)
        if raw_len > MAX_METADATA_JSON_BYTES:
            _LOGGER.warning(
                "event metadata rejected: oversized input (%d bytes > cap %d)",
                raw_len,
                MAX_METADATA_JSON_BYTES,
            )
            parsed = {}
        else:
            try:
                decoded = json.loads(metadata)
            except (ValueError, TypeError, RecursionError):
                parsed = {}
            else:
                # JSON arrays/scalars degrade to empty view (not an error).
                parsed = decoded if isinstance(decoded, dict) else {}
    elif isinstance(metadata, Mapping):
        if len(str(metadata)) > MAX_METADATA_MAPPING_CHARS:
            _LOGGER.warning(
                "event metadata rejected: oversized mapping (~%d chars > cap %d)",
                len(str(metadata)),
                MAX_METADATA_MAPPING_CHARS,
            )
            parsed = {}
        else:
            parsed = dict(metadata)
    else:
        _LOGGER.warning(
            "event metadata rejected: unsupported input type %s (expected Mapping/str/bytes/None)",
            type(metadata).__name__,
        )
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}

    occurred_raw = parsed.get("occurred_at")
    occurred_at: datetime | None = None
    if isinstance(occurred_raw, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_raw)
        except ValueError:
            occurred_at = None

    correlation = parsed.get("correlation")
    if not isinstance(correlation, dict):
        correlation = {}

    return EventMetadataView(
        event_id=parsed.get("event_id"),
        user_id=parsed.get("user_id"),
        schema_version=parsed.get("schema_version"),
        source=parsed.get("source"),
        service=parsed.get("service"),
        occurred_at=occurred_at,
        correlation={k: str(v) for k, v in correlation.items() if v is not None},
        raw=parsed,
    )


# --- Telemetry boundary ------------------------------------------------------


def is_telemetry_source(source: EventSource | str | None) -> bool:
    """True when the producer is a non-truth source (client telemetry / probe)."""
    if source is None:
        return False
    try:
        return EventSource(source) in TELEMETRY_SOURCES
    except ValueError:
        return False


def is_business_truth_eligible(source: EventSource | str | None) -> bool:
    """Business-truth gate: telemetry and probe events can never be truth.

    ``tracking_events`` (client telemetry) feeds observability and Phase-1
    estimators only. The authoritative user world state (state_aggregator
    UserStateV1, evidence fusion) must read server-authoritative tables
    (chat_messages / tasks / study_records / focus_sessions / …), never
    ``tracking_events``.
    """
    return not is_telemetry_source(source)
