"""D-01 contract guards: V3 Event Name Registry + shared fields + telemetry boundary.

Pins (red->green against app/core/event_registry.py):
- closed event-name vocabulary (exact frozen set, double-frozen via sha256);
- shared-field envelope rules (event_id/user_id/schema_version/source/
  occurred_at naive-UTC/correlation UUID canonicalization);
- deterministic idempotency key derivation (same-ROW redelivery scope only);
- backward-compatible metadata parsing (legacy {"service": ...} rows) and
  defensive rejection of malformed/oversized/deeply-nested rows;
- telemetry boundary: client telemetry / probe sources can never be business
  truth, and the authoritative truth modules never read tracking_events
  DIRECTLY (see TRUTH_PATH_MODULES note: derived-table second hops are out of
  this guard's sight and are tracked as report findings T1/T2/T3 instead);
- every event name observed in the live dev DB event_outbox is registered.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.event_registry import (
    CORRELATION_KEYS,
    EVENT_REGISTRY,
    EVENT_SCHEMA_VERSION,
    CorrelationIds,
    EventContractError,
    EventNameError,
    EventSource,
    EventStage,
    build_event_metadata,
    classify_stage,
    derive_event_id,
    is_business_truth_eligible,
    is_registered_event_name,
    is_telemetry_source,
    read_event_metadata,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]

# sha256 of "|".join(sorted(EVENT_REGISTRY)) captured at D-01 freeze
# (33 names). See test_event_name_vocabulary_is_frozen.
# X-02 deliberate vocabulary extension (2026-09-19): +1 name
# "allocation.decision_recorded" (stage=DECISION, Human/Agent/Hybrid
# allocation rubric, producer app/services/action_allocation_policy.py) →
# 34 names; hash bumped per the documented extension process (D-01
# EVENT_REGISTRY.md §扩展流程: contract change must be explicit).
_FROZEN_VOCABULARY_SHA256 = "a9f0186796cf1e2db9298e544b6f8d84fb0c22870e051718b407d98eb000a53c"

# Observed distinct event_type values in the live dev DB event_outbox
# (sparkle_readonly, 2026-09-19; 106 rows). run.* / task.status_changed are
# probe-origin rows whose producers do not exist in the repo — they are
# registered with status="observed_unregistered" so the vocabulary stays
# closed without pretending those names have a maintainer.
LIVE_OUTBOX_EVENT_NAMES = (
    "galaxy.node.mastery_updated",
    "run.created",
    "run.step_completed",
    "run.awaiting_user",
    "run.user_resumed",
    "task.status_changed",
)


# --- 1. Closed vocabulary ----------------------------------------------------


def test_registry_covers_all_flywheel_stages():
    stages = {e.stage for e in EVENT_REGISTRY.values()}
    assert stages == set(EventStage)


def test_every_live_outbox_event_name_is_registered():
    for name in LIVE_OUTBOX_EVENT_NAMES:
        assert is_registered_event_name(name), name


def test_event_name_vocabulary_is_frozen():
    # Double freeze: exact name set against a literal hash captured at D-01
    # contract time. Adding/removing/renaming an event name must bump this
    # literal deliberately (contract change, not an accident).
    names = sorted(EVENT_REGISTRY)
    digest = hashlib.sha256("|".join(names).encode()).hexdigest()
    assert len(names) == len(set(names))
    assert digest == _FROZEN_VOCABULARY_SHA256, (
        f"event-name vocabulary changed ({len(names)} names); if intentional, "
        f"update _FROZEN_VOCABULARY_SHA256 deliberately"
    )


def test_unregistered_name_is_rejected_everywhere():
    bogus = "galaxy.node.mastery_deleted"
    assert not is_registered_event_name(bogus)
    with pytest.raises(EventNameError):
        classify_stage(bogus)
    with pytest.raises(EventNameError):
        derive_event_id(
            event_name=bogus,
            aggregate_type="galaxy_node_mastery",
            aggregate_id=uuid4(),
        )
    with pytest.raises(EventNameError):
        build_event_metadata(
            user_id=uuid4(),
            source="server_service",
            service="test",
            event_name=bogus,
            aggregate_type="galaxy_node_mastery",
            aggregate_id=uuid4(),
        )


def test_probe_origin_names_are_flagged_not_live():
    assert EVENT_REGISTRY["run.created"].status == "observed_unregistered"
    assert EVENT_REGISTRY["task.status_changed"].status == "observed_unregistered"
    assert EVENT_REGISTRY["galaxy.node.mastery_updated"].status == "live"


def test_gj03_chain_stages_are_classified():
    # interaction -> execution -> outcome -> state update (DATA_FLYWHEEL §1)
    assert classify_stage("chat.message.sent") is EventStage.INTERACTION
    assert classify_stage("run.created") is EventStage.EXECUTION
    assert classify_stage("task.completed") is EventStage.OUTCOME
    assert classify_stage("galaxy.node.mastery_updated") is EventStage.STATE_UPDATE
    assert classify_stage("intervention.feedback_recorded") is EventStage.OUTCOME


# --- 2. Shared-field envelope -------------------------------------------------


def _envelope(**overrides):
    user_id = str(uuid4())
    kwargs = {
        "user_id": user_id,
        "source": "server_service",
        "service": "test_service",
        "event_name": "galaxy.node.mastery_updated",
        "aggregate_type": "galaxy_node_mastery",
        "aggregate_id": user_id,
        "sequence_number": 3,
        "correlation": {"task_id": uuid4(), "node_id": uuid4()},
    }
    kwargs.update(overrides)
    return build_event_metadata(**kwargs)


def test_envelope_shared_fields_exact_key_set():
    envelope = _envelope()
    assert set(envelope) == {
        "event_id",
        "user_id",
        "schema_version",
        "source",
        "service",
        "occurred_at",
        "correlation",
    }
    assert envelope["schema_version"] == EVENT_SCHEMA_VERSION == "event.v1"
    assert envelope["source"] == "server_service"


def test_envelope_occurred_at_is_naive_utc():
    aware = datetime.now(UTC) + timedelta(hours=5)
    envelope = _envelope(occurred_at=aware)
    parsed = datetime.fromisoformat(envelope["occurred_at"])
    assert parsed.tzinfo is None
    # naive value equals the UTC instant of the aware input
    assert parsed == aware.astimezone(UTC).replace(tzinfo=None)


def test_envelope_rejects_unknown_source():
    with pytest.raises(EventContractError):
        _envelope(source="mobile_client_trust_me")


def test_envelope_canonicalizes_uuid_correlation():
    raw = uuid4()
    envelope = _envelope(correlation={"task_id": raw, "node_id": str(raw)})
    assert envelope["correlation"]["task_id"] == str(raw)
    assert envelope["correlation"]["node_id"] == str(raw)
    with pytest.raises(EventContractError):
        _envelope(correlation={"task_id": "not-a-uuid"})


def test_envelope_rejects_extra_key_collision():
    with pytest.raises(EventContractError):
        _envelope(extra={"user_id": "evil"})


def test_correlation_ids_keys_match_contract():
    assert set(CorrelationIds.__dataclass_fields__) == set(CORRELATION_KEYS)
    # the four card-named cross-links are present
    assert {"intervention_id", "action_id", "run_id", "outcome_id"} <= set(CORRELATION_KEYS)


# --- 3. Idempotency key -------------------------------------------------------


def test_derive_event_id_is_deterministic_and_sensitive():
    aggregate_id = uuid4()
    corr = {"task_id": uuid4()}
    a = derive_event_id(
        event_name="galaxy.node.mastery_updated",
        aggregate_type="galaxy_node_mastery",
        aggregate_id=aggregate_id,
        sequence_number=7,
        correlation=corr,
    )
    b = derive_event_id(
        event_name="galaxy.node.mastery_updated",
        aggregate_type="galaxy_node_mastery",
        aggregate_id=aggregate_id,
        sequence_number=7,
        correlation=corr,
    )
    assert a == b and a.startswith("evt_")
    # any distinguishing input changes the key
    assert a != derive_event_id(
        event_name="galaxy.node.mastery_updated",
        aggregate_type="galaxy_node_mastery",
        aggregate_id=aggregate_id,
        sequence_number=8,
        correlation=corr,
    )
    assert a != derive_event_id(
        event_name="galaxy.node.mastery_updated",
        aggregate_type="galaxy_node_mastery",
        aggregate_id=uuid4(),
        sequence_number=7,
        correlation=corr,
    )


# --- 4. Legacy metadata compat -------------------------------------------------


def test_read_event_metadata_parses_legacy_rows():
    view = read_event_metadata({"service": "galaxy_service"})
    assert view.service == "galaxy_service"
    assert not view.is_v3_envelope
    assert view.user_id is None
    assert view.event_id is None


def test_read_event_metadata_parses_v3_envelope_from_mapping_and_json():
    envelope = _envelope()
    view = read_event_metadata(envelope)
    assert view.is_v3_envelope
    assert view.user_id == envelope["user_id"]
    assert view.source == "server_service"
    assert not view.is_telemetry

    view2 = read_event_metadata(json.dumps(envelope))
    assert view2.event_id == envelope["event_id"]
    assert dict(view2.correlation) == envelope["correlation"]


def test_read_event_metadata_marks_telemetry_source():
    envelope = _envelope(source="client_telemetry")
    assert read_event_metadata(envelope).is_telemetry


# --- 4b. Defensive parse (R2-CHANGES #4 / F10): malformed rows never raise -------


def test_read_event_metadata_degrades_non_mapping_python_objects():
    # Raw list input used to raise TypeError inside dict(); scalars/tuples too.
    for malformed in ([1, 2], ["a", {"service": "x"}], 42, 3.14, True, (1, 2), set()):
        view = read_event_metadata(malformed)  # must not raise
        assert view.service is None
        assert not view.is_v3_envelope
        assert dict(view.raw) == {}


def test_read_event_metadata_degrades_json_array_and_scalar_strings():
    assert read_event_metadata("[1,2]").service is None
    assert read_event_metadata('"just a string"').service is None
    assert read_event_metadata("null").service is None
    assert read_event_metadata("").service is None
    assert read_event_metadata(b"\xff\xfe not utf8").service is None


def test_read_event_metadata_rejects_oversized_json_string_instead_of_parsing():
    oversized = '{"x":"' + "a" * (70 * 1024) + '"}'
    assert len(oversized.encode("utf-8")) > 64 * 1024
    view = read_event_metadata(oversized)  # must not raise / must not parse
    assert view.service is None
    assert dict(view.raw) == {}


def test_read_event_metadata_rejects_oversized_mapping():
    huge = {"service": "s", "blob": "x" * (2 << 20)}
    view = read_event_metadata(huge)  # ~2 MiB str() form > 1 MiB cap
    assert view.service is None
    assert dict(view.raw) == {}


def test_read_event_metadata_survives_deeply_nested_json():
    deep = "[" * 100_000 + "]" * 100_000  # RecursionError inside json.loads
    view = read_event_metadata(deep)  # must degrade, not crash the caller
    assert view.service is None
    assert dict(view.raw) == {}


def test_read_event_metadata_still_parses_at_just_under_caps():
    # Guards must not reject legitimate envelopes: a ~1 KiB envelope and a
    # moderately sized mapping still parse fully.
    envelope = _envelope()
    assert read_event_metadata(json.dumps(envelope)).is_v3_envelope
    view = read_event_metadata({"service": "galaxy_service", "blob": "y" * 2048})
    assert view.service == "galaxy_service"


# --- 4c. Correlation exemption class (R2-CHANGES #3) -----------------------------


def test_correlation_exempt_names_are_frozen():
    # The declared exemption from the "EXECUTION/OUTCOME/STATE_UPDATE events
    # carry >=1 correlation id" rule. Frozen deliberately; adding an exemption
    # is a contract change requiring justification in the constant's comment.
    from app.core.event_registry import CORRELATION_EXEMPT_EVENT_NAMES

    assert set(CORRELATION_EXEMPT_EVENT_NAMES) == {"asset_created", "asset_status_changed"}
    # every exempt name must itself be a registered, live event
    for name in CORRELATION_EXEMPT_EVENT_NAMES:
        entry = EVENT_REGISTRY[name]
        assert entry.status == "live"
    # non-exempt live producers of EXECUTION/OUTCOME/STATE_UPDATE events must
    # be able to correlate: every galaxy/task writer has an upstream causal id.
    exempt_stages = {EventStage.EXECUTION, EventStage.OUTCOME, EventStage.STATE_UPDATE}
    non_exempt = [e for e in EVENT_REGISTRY.values() if e.stage in exempt_stages and e.status == "live"]
    assert non_exempt  # sanity: the rule has someone to bind
    assert {"galaxy.node.mastery_updated", "task.started", "task.completed"} <= {e.name for e in non_exempt}
    assert not ({"galaxy.node.mastery_updated", "task.started"} & CORRELATION_EXEMPT_EVENT_NAMES)


# --- 5. Telemetry boundary -----------------------------------------------------


def test_telemetry_sources_are_never_business_truth():
    assert not is_business_truth_eligible(EventSource.CLIENT_TELEMETRY)
    assert not is_business_truth_eligible(EventSource.PROBE)
    assert not is_business_truth_eligible("client_telemetry")
    assert is_business_truth_eligible(EventSource.SERVER_SERVICE)
    assert is_business_truth_eligible(EventSource.GATEWAY)
    assert is_telemetry_source("probe")
    assert not is_telemetry_source("server_service")
    assert not is_telemetry_source(None)


# Authoritative truth-path modules. If one of these ever starts importing or
# querying tracking_events (client telemetry), this guard fails: telemetry must
# not become business truth (D-01 work item 2).
#
# GUARD SCOPE (honest, F12/R2): direct-reference level ONLY — it greps module
# sources for `tracking_events`/`TrackingEvent`. Derived-table SECOND HOPS
# (telemetry -> cognitive_fragments/user_state_snapshots -> truth module) are
# invisible to a source scan; those chains are documented as findings T1/T2/T3
# in the D-01 report and owned by the remediation card, not by this guard.
# Static list, not directory-level: new files under state_aggregator/ or
# services/evidence/ must be added here deliberately.
TRUTH_PATH_MODULES = (
    "app/state_aggregator/service.py",  # UserStateV1 world state
    "app/state_aggregator/schema.py",
    "app/core/context_pack.py",  # decision context
    "app/services/evidence/fusion_engine.py",  # bayesian evidence fusion
    "app/services/evidence/unified_evidence.py",
    "app/services/evidence/outcome_evidence_adapter.py",
    "app/services/galaxy/stats_service.py",  # galaxy state writer
)


@pytest.mark.parametrize("rel_path", TRUTH_PATH_MODULES)
def test_truth_path_modules_never_read_client_telemetry(rel_path):
    source_path = BACKEND_DIR / rel_path
    assert source_path.exists(), f"truth-path module moved: {rel_path}"
    source = source_path.read_text(encoding="utf-8")
    assert "tracking_events" not in source, f"{rel_path} references tracking_events"
    assert "TrackingEvent" not in source, f"{rel_path} references TrackingEvent"


def test_telemetry_ingest_path_stays_isolated_from_outbox_writers():
    # The client-telemetry ingest service must not write into event_outbox:
    # telemetry and authoritative outbox events are different domains.
    source = (BACKEND_DIR / "app" / "services" / "event_service.py").read_text(encoding="utf-8")
    assert "event_outbox" not in source
    assert "EventBus" in source  # telemetry still flows through the ephemeral bus
