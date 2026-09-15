from datetime import timezone, datetime, timedelta

from app.services.signal_adaptation import (
    classify_band_with_hysteresis,
    pick_with_hysteresis,
    recency_weight,
)


def test_recency_weight_prefers_recent_events() -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    recent = recency_weight(now - timedelta(hours=1), now=now)
    older = recency_weight(now - timedelta(days=10), now=now)

    assert recent > older


def test_classify_band_with_hysteresis_keeps_previous_state_inside_band() -> None:
    result = classify_band_with_hysteresis(
        6.2,
        "streak_driven",
        low_enter=3.0,
        high_enter=7.0,
        low_exit=4.0,
        high_exit=6.0,
        low_label="task_driven",
        mid_label="balanced",
        high_label="streak_driven",
    )

    assert result == "streak_driven"


def test_pick_with_hysteresis_keeps_previous_when_margin_is_small() -> None:
    winner = pick_with_hysteresis(
        {"moderate": 0.42, "deep": 0.48, "shallow": 0.10},
        "moderate",
        margin=0.08,
    )

    assert winner == "moderate"
