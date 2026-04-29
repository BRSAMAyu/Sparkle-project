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


class _MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.lists.get(key, [])
        self.lists[key] = values[start : end + 1]

    async def expire(self, key: str, seconds: int) -> None:
        return None

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.get(key, [])
        if end == -1:
            return values[start:]
        return values[start : end + 1]


# ── OutcomeTracker tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_expected_stores_pending() -> None:
    redis = MagicMock()
    redis.set = AsyncMock()
    redis.pipeline.return_value = pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, 1, 1])

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
    pipe.set.assert_called_once()
    pipe.lpush.assert_called_once_with("spine:pending_outcomes:user:u1", outcome_id)
    pipe.ltrim.assert_called_once_with("spine:pending_outcomes:user:u1", 0, 49)
    pipe.expire.assert_called_once_with("spine:pending_outcomes:user:u1", 24 * 3600)
    pipe.execute.assert_awaited_once()


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


@pytest.mark.asyncio
async def test_verify_pending_marks_unresolved_as_timeout() -> None:
    from app.signals.outcome_tracker import OutcomeTracker

    pending = {
        "outcome_id": "po_timeout",
        "user_id": "u1",
        "directive_type": "push_nudge",
        "trace_id": "trace_test_001",
        "expected_outcome": "user_response",
        "context": {"reason": "task_not_started"},
        "registered_at": "2020-01-01T00:00:00Z",
        "verification_window_hours": 48,
        "resolved": False,
    }
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"po_timeout"])
    redis.get = AsyncMock(return_value=json.dumps(pending))

    tracker = OutcomeTracker(redis)
    with patch.object(tracker, "record_actual", new_callable=AsyncMock) as mock_record:
        mock_record.return_value = _make_record(attribution="inconclusive", attribution_confidence=0.3)
        resolved = await tracker.verify_pending("u1")

    assert resolved == [mock_record.return_value]
    mock_record.assert_awaited_once_with(
        pending_outcome_id="po_timeout",
        actual_outcome={"timeout": True, "no_observable_change": True},
    )


@pytest.mark.asyncio
async def test_verify_pending_skips_active_verification_window() -> None:
    from datetime import UTC, datetime

    from app.signals.outcome_tracker import OutcomeTracker

    pending = {
        "outcome_id": "po_active",
        "user_id": "u1",
        "directive_type": "push_nudge",
        "trace_id": "trace_test_001",
        "expected_outcome": "user_response",
        "context": {"reason": "task_not_started"},
        "registered_at": datetime.now(UTC).isoformat(),
        "verification_window_hours": 48,
        "resolved": False,
    }
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"po_active"])
    redis.get = AsyncMock(return_value=json.dumps(pending))

    tracker = OutcomeTracker(redis)
    with patch.object(tracker, "record_actual", new_callable=AsyncMock) as mock_record:
        resolved = await tracker.verify_pending("u1")

    assert resolved == []
    mock_record.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_pending_count_counts_only_unresolved() -> None:
    from app.signals.outcome_tracker import OutcomeTracker

    unresolved = {"resolved": False}
    resolved = {"resolved": True}
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=["po_open", "po_done", "po_missing"])
    redis.get = AsyncMock(side_effect=[
        json.dumps(unresolved),
        json.dumps(resolved),
        None,
    ])

    tracker = OutcomeTracker(redis)
    assert await tracker.get_pending_count("u1") == 1


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


@pytest.mark.asyncio
async def test_check_insufficient_streak_true_at_limit() -> None:
    from app.signals.learning_guard import LearningGuard

    guard = LearningGuard(AsyncMock())
    with patch(
        "app.signals.learning_guard.OutcomeRecorder.get_insufficient_count_for_policy",
        new_callable=AsyncMock,
    ) as mock_count:
        mock_count.return_value = 3
        assert await guard.check_insufficient_streak("u1", "task_policy") is True

    mock_count.assert_awaited_once_with("u1", "task_policy")


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


@pytest.mark.asyncio
async def test_policy_effect_helpers_round_trip_insufficient_entries() -> None:
    from app.signals.outcome_recorder import OutcomeRecorder

    redis = _MemoryRedis()
    redis.values["spine:trace:trace_test_001"] = json.dumps({"trace_id": "trace_test_001"})
    redis.lists["spine:user_traces:u1"] = ["trace_test_001"]
    recorder = OutcomeRecorder(redis)

    await recorder._write_policy_effect(
        _make_record(
            attribution="insufficient",
            attribution_confidence=0.6,
            actual_outcome={"user_feedback": "太难了"},
            new_hypothesis="task_completed_but_intervention_may_be_insufficient",
        )
    )

    effects = await recorder.get_recent_policy_effects("u1")
    assert len(effects) == 1
    assert effects[0].policy_key == "task_not_started"
    assert effects[0].attribution == "insufficient"
    assert effects[0].user_feedback_signal == "too_hard"
    assert await recorder.get_insufficient_count_for_policy("u1", "task_not_started") == 1


def test_build_self_correction_receipt_for_insufficient_outcome() -> None:
    from app.signals.outcome_recorder import OutcomeRecorder

    receipt = OutcomeRecorder.build_self_correction_receipt(
        _make_record(
            attribution="insufficient",
            actual_outcome={"user_feedback": "太难了"},
            new_hypothesis="task_completed_but_intervention_may_be_insufficient",
        )
    )

    assert receipt is not None
    assert receipt["type"] == "divine_moment_self_correction"
    assert receipt["new_action"] == "diagnostic_check"
