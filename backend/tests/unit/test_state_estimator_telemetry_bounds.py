"""V3-FIX-11 T1 red/green: telemetry must not saturate cognitive_load nor
re-arm the state estimator on every request.

D-01 R2 evidence (F4, "request-arms-the-estimator"): the ingest endpoint and
the cognitive stream worker both call ``StateEstimatorService.update_state``
synchronously, and ``cognitive_load = min(1, wrong*0.15 + total*0.02)`` — the
pure event-volume term saturates at ~50 events/24h, so a misbehaving client
can push a user's cognitive-load estimate to 1.0 (interruptibility 0) with
semantically empty noise (heartbeat / screen_view).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.telemetry_boundary import (
    STATE_ESTIMATOR_MIN_INTERVAL_SECONDS,
    TELEMETRY_DERIVED_LOAD_CAP,
)
from app.models.event import TrackingEvent
from app.models.user_state import UserStateSnapshot
from app.services.state_estimator_service import StateEstimatorService, StateWindow


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _event(event_type: str, payload: dict | None = None, received_at: datetime | None = None):
    return TrackingEvent(
        event_id=uuid4().hex,
        user_id=uuid4(),
        event_type=event_type,
        schema_version="event.v1",
        source="client",
        ts_ms=int(_utcnow().timestamp() * 1000),
        entities=None,
        payload=payload or {},
        received_at=received_at or _utcnow(),
    )


def test_volume_noise_cannot_saturate_cognitive_load():
    """50 semantically-empty events in 24h must not saturate cognitive_load.

    RED against the pre-fix formula: min(1, 0 + 50*0.02) == 1.0.
    """
    now = _utcnow()
    events = [_event("screen_view") for _ in range(50)]
    service = StateEstimatorService(db=None)
    window = StateWindow(start=now - timedelta(hours=24), end=now)
    snapshot = service._compute_state(uuid4(), events, window, "UTC")

    assert snapshot.cognitive_load <= TELEMETRY_DERIVED_LOAD_CAP, (
        f"telemetry volume noise pushed cognitive_load to {snapshot.cognitive_load}; "
        "client telemetry must be capped below decision-saturation "
        f"(TELEMETRY_DERIVED_LOAD_CAP={TELEMETRY_DERIVED_LOAD_CAP})"
    )


def test_forged_wrong_events_cannot_saturate_cognitive_load():
    """Forged quiz_wrong events must not saturate cognitive_load either.

    RED against the pre-fix formula: min(1, 7*0.15 + 0) == 1.05 -> 1.0.
    Both terms of the load are client telemetry, so the combined
    telemetry-derived contribution is capped.
    """
    now = _utcnow()
    events = [_event("quiz_wrong") for _ in range(7)]
    service = StateEstimatorService(db=None)
    window = StateWindow(start=now - timedelta(hours=24), end=now)
    snapshot = service._compute_state(uuid4(), events, window, "UTC")

    assert snapshot.cognitive_load <= TELEMETRY_DERIVED_LOAD_CAP


def test_legitimate_struggle_signal_survives_below_cap():
    """A genuine wrong-answer cluster still raises load (direction preserved),
    just bounded: 3 wrongs -> 0.45 uncapped -> 0.3 capped, still > idle 0.02."""
    now = _utcnow()
    events = [_event("quiz_wrong") for _ in range(3)] + [_event("screen_view")]
    service = StateEstimatorService(db=None)
    window = StateWindow(start=now - timedelta(hours=24), end=now)
    snapshot = service._compute_state(uuid4(), events, window, "UTC")

    assert 0 < snapshot.cognitive_load <= TELEMETRY_DERIVED_LOAD_CAP


class _ScalarOneOrNone:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsAll:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    """Minimal async-session stand-in for update_state's query paths."""

    def __init__(self, existing_snapshots=None, events=None):
        self.snapshots = list(existing_snapshots or [])
        self.events = list(events or [])
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        # Distinguish the two selects by column descriptions.
        desc = {d["name"] for d in stmt.column_descriptions}
        if any(name in desc for name in ("UserStateSnapshot", "user_id", "id")) and "TrackingEvent" not in str(stmt):
            # latest-snapshot lookup: newest first, limit 1
            ordered = sorted(self.snapshots, key=lambda s: s.snapshot_at, reverse=True)
            return _ScalarOneOrNone(ordered[0] if ordered else None)
        return _ScalarsAll(self.events)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None


def _snapshot(user_id, snapshot_at):
    return UserStateSnapshot(
        user_id=user_id,
        snapshot_at=snapshot_at,
        window_start=snapshot_at - timedelta(hours=24),
        window_end=snapshot_at,
        cognitive_load=0.1,
        interruptibility=0.9,
        strain_index=0.1,
        focus_mode=False,
        sprint_mode=False,
        time_context={"hour": 12, "weekday": 0},
        derived_event_ids=[],
    )


async def test_update_state_debounces_rapid_telemetry_bursts():
    """A second telemetry-triggered update_state inside the debounce window
    must NOT mint a fresh snapshot (RED: pre-fix code recomputes every call).

    This is the "single request cannot synchronously move state" bound: the
    ingest endpoint / stream worker still call update_state, but the service
    itself rate-limits recompute frequency per user.
    """
    user_id = uuid4()
    now = _utcnow()
    fresh = _snapshot(user_id, now - timedelta(seconds=10))
    db = _FakeSession(existing_snapshots=[fresh])
    service = StateEstimatorService(db)

    returned = await service.update_state(user_id, timezone_name=None)

    assert returned is fresh, "must return the existing fresh snapshot"
    assert db.added == [], "no new snapshot may be created inside the debounce window"
    assert db.commits == 0


async def test_update_state_recomputes_when_snapshot_is_stale():
    """Outside the debounce window the estimator still refreshes (telemetry
    remains a bounded signal, not a banned one)."""
    user_id = uuid4()
    now = _utcnow()
    stale = _snapshot(user_id, now - timedelta(seconds=STATE_ESTIMATOR_MIN_INTERVAL_SECONDS + 60))
    db = _FakeSession(existing_snapshots=[stale])
    service = StateEstimatorService(db)

    returned = await service.update_state(user_id, timezone_name=None)

    assert returned is not stale
    assert len(db.added) == 1
    assert db.commits >= 1


async def test_update_state_first_ever_call_recomputes():
    """No prior snapshot -> compute (bootstrap path unaffected)."""
    user_id = uuid4()
    db = _FakeSession()
    service = StateEstimatorService(db)

    returned = await service.update_state(user_id, timezone_name=None)

    assert returned is not None
    assert len(db.added) == 1
