"""Tests for AbsenceDetector (MAGIC-004)."""

from __future__ import annotations

import pytest
from datetime import datetime, UTC, timedelta

from app.signals.absence_detector import (
    AbsenceDetector,
    AbsenceSnapshot,
    classify,
)


# ── classify() ──────────────────────────────────────────────────────


class TestClassify:
    def test_present_under_15_min(self):
        assert classify(5) == "present"
        assert classify(14.9) == "present"

    def test_idle_15_to_60(self):
        assert classify(15) == "idle"
        assert classify(30) == "idle"
        assert classify(59.9) == "idle"

    def test_short_60_to_360(self):
        assert classify(60) == "short"
        assert classify(120) == "short"
        assert classify(359.9) == "short"

    def test_prolonged_360_to_2880(self):
        assert classify(360) == "prolonged"
        assert classify(1440) == "prolonged"
        assert classify(2879.9) == "prolonged"

    def test_extended_2880_plus(self):
        assert classify(2880) == "extended"
        assert classify(10000) == "extended"


# ── to_actionable_signal() ──────────────────────────────────────────


class TestToActionableSignal:
    def test_short_absence_signal(self):
        detector = AbsenceDetector()
        snap = AbsenceSnapshot(
            user_id="u1",
            absence_level="short",
            elapsed_minutes=90,
            last_interaction_at="2026-05-06T10:00:00+00:00",
            has_active_goal=True,
            has_active_task=True,
        )
        signal = detector.to_actionable_signal(snap)

        assert signal.source_system == "absence_detector"
        assert signal.state_key == "engagement_pattern"
        assert signal.claim == "user_short_absence"
        assert signal.priority == "medium"
        assert "queue_gentle_recall" in signal.possible_effects
        assert signal.confidence >= 0.80

    def test_extended_absence_signal(self):
        detector = AbsenceDetector()
        snap = AbsenceSnapshot(
            user_id="u2",
            absence_level="extended",
            elapsed_minutes=5000,
            last_interaction_at="2026-05-04T10:00:00+00:00",
            has_active_goal=True,
            has_active_task=False,
        )
        signal = detector.to_actionable_signal(snap)

        assert signal.claim == "user_extended_absence"
        assert signal.priority == "high"
        assert "send_reengagement_message" in signal.possible_effects
        assert "pause_plan_gracefully" in signal.possible_effects

    def test_idle_signal(self):
        detector = AbsenceDetector()
        snap = AbsenceSnapshot(
            user_id="u3",
            absence_level="idle",
            elapsed_minutes=20,
            last_interaction_at="2026-05-06T11:40:00+00:00",
            has_active_goal=True,
            has_active_task=False,
        )
        signal = detector.to_actionable_signal(snap)
        assert signal.claim == "user_idle"
        assert signal.priority == "medium"

    def test_prolonged_with_active_task_higher_confidence(self):
        detector = AbsenceDetector()
        snap_with_task = AbsenceSnapshot(
            user_id="u4",
            absence_level="prolonged",
            elapsed_minutes=500,
            last_interaction_at="2026-05-05T10:00:00+00:00",
            has_active_goal=True,
            has_active_task=True,
        )
        snap_without = AbsenceSnapshot(
            user_id="u4b",
            absence_level="prolonged",
            elapsed_minutes=500,
            last_interaction_at="2026-05-05T10:00:00+00:00",
            has_active_goal=True,
            has_active_task=False,
        )
        sig_with = detector.to_actionable_signal(snap_with_task)
        sig_without = detector.to_actionable_signal(snap_without)
        assert sig_with.confidence > sig_without.confidence


# ── check_user() with mock redis ────────────────────────────────────


class _FakeRedis:
    """Minimal async Redis mock for tests."""

    def __init__(self, data: dict[str, str | None] | None = None):
        self._data: dict[str, str | None] = data or {}

    async def get(self, key: str):
        return self._data.get(key)

    async def exists(self, key: str) -> bool:
        return key in self._data and self._data[key] is not None

    async def set(self, key: str, value: str, ex: int | None = None):
        self._data[key] = value


class TestCheckUser:
    @pytest.mark.asyncio
    async def test_present_user_returns_none(self):
        now_iso = datetime.now(UTC).isoformat()
        redis = _FakeRedis({f"spine:last_chat_turn_at:u1": now_iso})
        detector = AbsenceDetector()
        result = await detector.check_user("u1", redis)
        assert result is None

    @pytest.mark.asyncio
    async def test_absent_user_returns_snapshot(self):
        two_hours_ago = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        redis = _FakeRedis({
            f"spine:last_chat_turn_at:u2": two_hours_ago,
            f"spine:session_active:u2": "1",
        })
        detector = AbsenceDetector()
        result = await detector.check_user("u2", redis)
        assert result is not None
        assert result.absence_level == "short"
        assert result.has_active_task is True

    @pytest.mark.asyncio
    async def test_no_heartbeat_returns_none(self):
        redis = _FakeRedis({})
        detector = AbsenceDetector()
        result = await detector.check_user("u99", redis)
        assert result is None

    @pytest.mark.asyncio
    async def test_cooldown_skips_signal(self):
        two_hours_ago = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        redis = _FakeRedis({
            f"spine:last_chat_turn_at:u3": two_hours_ago,
            f"spine:absence_cooldown:u3:short": "1",
        })
        detector = AbsenceDetector()
        result = await detector.check_user("u3", redis)
        assert result is None
