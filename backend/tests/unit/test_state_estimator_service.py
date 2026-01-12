from datetime import datetime, timedelta
from uuid import uuid4

from app.models.event import TrackingEvent
from app.services.state_estimator_service import StateEstimatorService, StateWindow


def _event(event_type, payload=None, received_at=None):
    return TrackingEvent(
        event_id=uuid4().hex,
        user_id=uuid4(),
        event_type=event_type,
        schema_version="event.v1",
        source="test",
        ts_ms=int(datetime.utcnow().timestamp() * 1000),
        entities=None,
        payload=payload or {},
        received_at=received_at or datetime.utcnow(),
    )


def test_compute_state_focus_and_wrong_events():
    now = datetime.utcnow()
    events = [
        _event("focus_start", received_at=now - timedelta(minutes=10)),
        _event("question_submit", payload={"correct": False}, received_at=now - timedelta(minutes=5)),
        _event("quiz_wrong", received_at=now - timedelta(minutes=2)),
    ]
    service = StateEstimatorService(db=None)
    window = StateWindow(start=now - timedelta(hours=24), end=now)
    snapshot = service._compute_state(uuid4(), events, window, "UTC")

    assert snapshot.focus_mode is True
    assert snapshot.cognitive_load > 0
    assert snapshot.interruptibility < 1
