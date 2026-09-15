from datetime import timezone, datetime, timedelta
from types import SimpleNamespace

from app.services.behavior_signal_collector import BehaviorSignalCollector
from app.services.galaxy_feedback_signal_processor import GalaxyFeedbackSignalProcessor


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_behavior_signal_collector_weights_recent_feedback_ratios() -> None:
    now = _utcnow()
    feedbacks = [
        SimpleNamespace(category="too_difficult", created_at=now - timedelta(days=10)),
        SimpleNamespace(category="just_right", created_at=now),
        SimpleNamespace(category="just_right", created_at=now),
    ]

    ratios = BehaviorSignalCollector._difficulty_feedback_ratio(feedbacks)

    assert ratios["just_right"] > ratios["too_hard"]


def test_galaxy_feedback_hysteresis_keeps_previous_depth_when_scores_are_close() -> None:
    now = _utcnow()
    feedbacks = [
        SimpleNamespace(rating=4, created_at=now - timedelta(days=1)),
        SimpleNamespace(rating=3, created_at=now),
        SimpleNamespace(rating=3, created_at=now),
    ]

    depth = GalaxyFeedbackSignalProcessor._preferred_depth(
        feedbacks,
        satisfaction=0.62,
        previous="moderate",
    )

    assert depth == "moderate"
