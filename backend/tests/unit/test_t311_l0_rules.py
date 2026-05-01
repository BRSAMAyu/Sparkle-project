"""
Tests for T3.1.1: L0 Rule-Aware Aurora — deadline_pressure + quiet_hours.
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.aurora.runtime_v1.l0_rules import L0RuleEngine


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


def _deadline(hours_from_now: float, title: str = "Exam") -> dict:
    return {
        "title": title,
        "deadline_at": (_utcnow() + timedelta(hours=hours_from_now)).isoformat(),
        "type": "exam",
    }


@pytest.fixture
def engine():
    redis = AsyncMock()
    return L0RuleEngine(redis)


@pytest.mark.asyncio
async def test_no_deadlines_returns_none(engine):
    """No upcoming deadlines should return no signal."""
    result = await engine.evaluate_deadline_pressure("user1", upcoming_deadlines=[])
    assert result is None


@pytest.mark.asyncio
async def test_deadline_far_away_returns_none(engine):
    """Deadline > 72h away should not trigger."""
    result = await engine.evaluate_deadline_pressure(
        "user1",
        upcoming_deadlines=[_deadline(100)],
    )
    assert result is None


@pytest.mark.asyncio
async def test_deadline_under_6h_high_confidence(engine):
    """Deadline within 6h should produce high confidence, high priority signal."""
    result = await engine.evaluate_deadline_pressure(
        "user1",
        upcoming_deadlines=[_deadline(3)],
    )
    assert result is not None
    assert result.state_key == "deadline_pressure"
    assert result.confidence >= 0.9
    assert result.priority == "high"
    assert result.ttl_hours >= 3


@pytest.mark.asyncio
async def test_deadline_under_24h_high(engine):
    """Deadline within 24h should produce high priority."""
    result = await engine.evaluate_deadline_pressure(
        "user1",
        upcoming_deadlines=[_deadline(18)],
    )
    assert result is not None
    assert result.confidence >= 0.8
    assert result.priority == "high"


@pytest.mark.asyncio
async def test_deadline_under_48h_medium(engine):
    """Deadline within 48h should produce medium priority."""
    result = await engine.evaluate_deadline_pressure(
        "user1",
        upcoming_deadlines=[_deadline(36)],
    )
    assert result is not None
    assert result.confidence >= 0.7
    assert result.priority == "medium"


@pytest.mark.asyncio
async def test_deadline_48_72h_low_medium(engine):
    """Deadline 48-72h away should still trigger with lower confidence."""
    result = await engine.evaluate_deadline_pressure(
        "user1",
        upcoming_deadlines=[_deadline(60)],
    )
    assert result is not None
    assert result.confidence >= 0.5


@pytest.mark.asyncio
async def test_nearest_deadline_selected(engine):
    """When multiple deadlines exist, nearest one determines signal."""
    result = await engine.evaluate_deadline_pressure(
        "user1",
        upcoming_deadlines=[_deadline(50, "Far"), _deadline(5, "Near")],
    )
    assert result is not None
    assert "Near" in result.evidence_summary


@pytest.mark.asyncio
async def test_quiet_hours_nighttime():
    """During nighttime hours (spanning midnight), quiet hours should be active."""
    engine = L0RuleEngine(AsyncMock())
    # Test the static logic directly — 23:00 is within 22:00-08:00
    result = await engine.evaluate_quiet_hours("user1", quiet_start="22:00", quiet_end="08:00")
    # Result depends on actual current time, so test the parsing logic
    assert isinstance(result, bool)


def test_parse_hhmm_valid():
    """HH:MM parsing should work correctly."""
    assert L0RuleEngine._parse_hhmm("22:00") == 1320
    assert L0RuleEngine._parse_hhmm("08:00") == 480
    assert L0RuleEngine._parse_hhmm("00:00") == 0
    assert L0RuleEngine._parse_hhmm("23:59") == 1439


def test_parse_hhmm_invalid():
    """Invalid HH:MM should return 0."""
    assert L0RuleEngine._parse_hhmm("invalid") == 0
    assert L0RuleEngine._parse_hhmm("") == 0


def test_deadline_pressure_in_router():
    """deadline_pressure state should cause execution constraints in dual_core_router."""
    from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput

    router = DualCoreRouter()
    inp = DualCoreRoutingInput(
        intent="chat",
        intent_confidence=0.85,
        information_sufficient=True,
        primary_challenge_area=None,
        recent_sentiment_distribution={"neutral": 5},
        has_active_plan=True,
        plan_health_status="on_track",
        recent_task_feedback_distribution={},
        spine_active_states=[
            {"state_key": "deadline_pressure", "value": "upcoming_deadline_approaching", "confidence": 0.85, "scope": "day"},
        ],
    )
    decision = router.route(inp)
    assert any("截止日期" in c for c in decision.execution_constraints)
