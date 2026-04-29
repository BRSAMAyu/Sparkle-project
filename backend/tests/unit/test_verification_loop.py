from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.signals.types import CausalTrace, OutcomeRecord


def _make_trace() -> CausalTrace:
    return CausalTrace(
        trace_id="trace_test_001",
        raw_event_ids=[],
        signal_ids=[],
        directive_ids=[],
    )


def _make_record(**overrides) -> OutcomeRecord:
    defaults = {
        "outcome_id": "or_test_001",
        "causal_trace_id": "trace_test_001",
        "intervention": "push_nudge",
        "reason": "task_not_started",
        "expected_outcome": "task_started_and_completed",
        "actual_outcome": {"completed": True},
        "attribution": "effective",
        "attribution_confidence": 0.8,
        "new_hypothesis": None,
        "next_policy_suggestion": None,
    }
    defaults.update(overrides)
    return OutcomeRecord(**defaults)


# ── OutcomeTracker tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_expected_stores_pending() -> None:
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.lpush = AsyncMock()
    redis.ltrim = AsyncMock()
    redis.expire = AsyncMock()

    from app.signals.outcome_tracker import OutcomeTracker
    tracker = OutcomeTracker(redis)

    trace = _make_trace()
    outcome_id = await tracker.register_expected(
        user_id="u1",
        directive_type="notification",
        trace=trace,
        expected_outcome="user_response",
        verification_window_hours=24,
    )
    assert outcome_id.startswith("po")
    redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_record_actual_resolves_pending() -> None:
    from app.signals.outcome_tracker import OutcomeTracker

    pending = {
        "outcome_id": "po_test",
        "user_id": "u1",
        "directive_type": "push_nudge",
        "trace_id": "trace_test_001",
        "expected_outcome": "task_started_and_completed",
        "context": {"reason": "task_not_started"},
        "registered_at": "2026-01-01T00:00:00Z",
        "verification_window_hours": 48,
        "resolved": False,
    }

    redis = AsyncMock()
    # First call: get pending outcome → return pending data
    # Subsequent calls: OutcomeRecorder.record_outcome → store trace/outcome
    redis.get = AsyncMock(return_value=json.dumps(pending))
    redis.set = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])

    tracker = OutcomeTracker(redis)

    with patch.object(
        tracker.recorder, "record_outcome", new_callable=AsyncMock
    ) as mock_record:
        mock_record.return_value = _make_record()
        result = await tracker.record_actual(
            pending_outcome_id="po_test",
            actual_outcome={"completed": True},
        )

    assert result is not None
    assert result.attribution == "effective"
    mock_record.assert_called_once()


@pytest.mark.asyncio
async def test_record_actual_returns_none_if_not_found() -> None:
    from app.signals.outcome_tracker import OutcomeTracker

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)

    tracker = OutcomeTracker(redis)
    result = await tracker.record_actual(
        pending_outcome_id="po_nonexistent",
        actual_outcome={"completed": True},
    )
    assert result is None


# ── LearningGuard tests ──────────────────────────────────────────


def test_should_learn_effective_high_confidence() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="effective", attribution_confidence=0.8)
    assert guard.should_learn(record) is True


def test_should_not_learn_effective_low_confidence() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="effective", attribution_confidence=0.5)
    assert guard.should_learn(record) is False


def test_should_not_learn_harmful() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="harmful", attribution_confidence=0.9)
    assert guard.should_learn(record) is False


def test_should_not_learn_inconclusive() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="inconclusive", attribution_confidence=0.3)
    assert guard.should_learn(record) is False


def test_should_retract_harmful() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="harmful", attribution_confidence=0.9)
    assert guard.should_retract(record) is True


def test_should_not_retract_effective() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="effective", attribution_confidence=0.8)
    assert guard.should_retract(record) is False


def test_guard_verdict_effective() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="effective", attribution_confidence=0.8)
    verdict = guard.get_guard_verdict(record)
    assert verdict["should_learn"] is True
    assert verdict["should_retract"] is False
    assert verdict["action"] == "write_to_policy"


def test_guard_verdict_harmful_triggers_retraction() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="harmful", attribution_confidence=0.9)
    verdict = guard.get_guard_verdict(record)
    assert verdict["should_learn"] is False
    assert verdict["should_retract"] is True
    assert verdict["action"] == "retract_and_apologize"
    assert verdict["self_correction_receipt"] is not None


def test_guard_verdict_inconclusive_skips() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    record = _make_record(attribution="inconclusive", attribution_confidence=0.3)
    verdict = guard.get_guard_verdict(record)
    assert verdict["should_learn"] is False
    assert verdict["should_retract"] is False
    assert verdict["action"] == "skip"


# ── OutcomeRecorder attribution tests ─────────────────────────────


def test_attribution_effective_task_completed() -> None:
    from app.signals.outcome_recorder import OutcomeRecorder

    recorder = OutcomeRecorder(AsyncMock())
    attr, conf, hyp, policy = recorder._attribute(
        "task_started_and_completed",
        {"completed": True},
    )
    assert attr == "effective"
    assert conf == 0.8


def test_attribution_insufficient_task_started_but_not_completed() -> None:
    from app.signals.outcome_recorder import OutcomeRecorder

    recorder = OutcomeRecorder(AsyncMock())
    attr, conf, hyp, policy = recorder._attribute(
        "task_started_and_completed",
        {"completed": False, "started": True},
    )
    assert attr == "insufficient"
    assert hyp is not None


def test_attribution_harmful_user_reported_negative() -> None:
    from app.signals.outcome_recorder import OutcomeRecorder

    recorder = OutcomeRecorder(AsyncMock())
    attr, conf, hyp, policy = recorder._attribute(
        "user_wellbeing",
        {"user_reported_negative": True},
    )
    assert attr == "harmful"


def test_attribution_inconclusive_unknown_outcome_type() -> None:
    from app.signals.outcome_recorder import OutcomeRecorder

    recorder = OutcomeRecorder(AsyncMock())
    attr, conf, hyp, policy = recorder._attribute(
        "unknown_outcome_type",
        {"some_data": True},
    )
    assert attr == "inconclusive"
