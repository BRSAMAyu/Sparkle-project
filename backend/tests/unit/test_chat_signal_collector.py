from datetime import timezone, datetime, timedelta

from app.services.chat_signal_collector import ChatSignalCollector


def test_chat_signal_collector_satisfaction_defaults_to_neutral_not_positive() -> None:
    collector = ChatSignalCollector(redis=None)
    entries = [
        {"gratitude": False, "dissatisfaction": False, "follow_up": False},
        {"gratitude": False, "dissatisfaction": False, "follow_up": False},
        {"gratitude": True, "dissatisfaction": False, "follow_up": False},
        {"gratitude": False, "dissatisfaction": True, "follow_up": False},
    ]

    rate = collector._satisfaction_rate(entries)

    assert rate == 0.5


def test_chat_signal_collector_detects_explicit_dissatisfaction() -> None:
    assert ChatSignalCollector._detect_dissatisfaction("这个答案不太对，我还是不懂")
    assert ChatSignalCollector._detect_dissatisfaction("This is wrong and still confused")
    assert not ChatSignalCollector._detect_dissatisfaction("谢谢，我明白了")


def test_chat_signal_collector_weights_recent_sentiment_more_heavily() -> None:
    collector = ChatSignalCollector(redis=None)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entries = [
        {
            "ts": (now - timedelta(days=6)).isoformat(),
            "gratitude": True,
            "dissatisfaction": False,
            "follow_up": False,
        },
        {
            "ts": now.isoformat(),
            "gratitude": False,
            "dissatisfaction": True,
            "follow_up": False,
        },
    ]

    rate = collector._satisfaction_rate(entries)

    assert rate < 0.35


def test_chat_signal_collector_prefers_recent_active_hours() -> None:
    collector = ChatSignalCollector(redis=None)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entries = [
        {"ts": (now - timedelta(days=6)).isoformat(), "hour": 3},
        {"ts": now.isoformat(), "hour": 14},
        {"ts": now.isoformat(), "hour": 14},
    ]

    active_hours = collector._active_hours(entries)

    assert active_hours[0] == 14
