from datetime import datetime, timedelta

from app.core.celery_tasks import (
    _spaced_repetition_due_interval_days,
    _spaced_repetition_interval_days_for_mastery,
)


def test_spaced_repetition_window_catches_missed_interval_next_day():
    now = datetime(2026, 4, 26, 9, 0, 0)
    last_reviewed = now - timedelta(days=8, minutes=5)

    assert _spaced_repetition_due_interval_days(last_reviewed, now) == 7


def test_spaced_repetition_window_expires_after_grace_day():
    now = datetime(2026, 4, 26, 9, 0, 0)
    last_reviewed = now - timedelta(days=9)

    assert _spaced_repetition_due_interval_days(last_reviewed, now) is None


def test_spaced_repetition_uses_shorter_interval_for_low_mastery():
    now = datetime(2026, 4, 26, 9, 0, 0)
    last_reviewed = now - timedelta(days=3)

    assert _spaced_repetition_due_interval_days(last_reviewed, now, mastery=0.42) == 3
    assert _spaced_repetition_due_interval_days(last_reviewed, now, mastery=0.72) is None


def test_spaced_repetition_mastery_bands_escalate_intervals():
    assert _spaced_repetition_interval_days_for_mastery(0.31) == (1, 3, 7)
    assert _spaced_repetition_interval_days_for_mastery(0.55) == (3, 7, 14)
    assert _spaced_repetition_interval_days_for_mastery(0.70) == (7, 14, 30)
    assert _spaced_repetition_interval_days_for_mastery(0.80) == (14, 30)
