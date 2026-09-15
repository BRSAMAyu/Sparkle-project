from datetime import timezone, datetime, timedelta
from types import SimpleNamespace

from app.models.focus import FocusStatus
from app.services.focus_signal_processor import FocusSignalProcessor


def test_peak_focus_hours_prioritizes_reliable_high_volume_hours() -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sessions = [
        SimpleNamespace(
            start_time=now - timedelta(hours=1),
            status=FocusStatus.COMPLETED,
        )
    ]
    sessions.extend(
        [
            SimpleNamespace(
                start_time=now - timedelta(days=1, hours=10 - idx),
                status=FocusStatus.COMPLETED if idx < 8 else FocusStatus.INTERRUPTED,
            )
            for idx in range(10)
        ]
    )
    for session in sessions[1:]:
        session.start_time = session.start_time.replace(hour=14)
    sessions[0].start_time = sessions[0].start_time.replace(hour=3)

    peak_hours = FocusSignalProcessor._compute_peak_focus_hours(sessions, now=now)

    assert peak_hours[0] == 14
