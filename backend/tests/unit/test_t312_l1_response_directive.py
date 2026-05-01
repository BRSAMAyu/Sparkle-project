"""
Tests for T3.1.2: L1 Light Aurora — state-aware ResponseDirective.
"""
import pytest

from app.signals.policy_engine import PolicyEngine
from app.signals.types import ActionableSignal


def _signal(state_key="task_granularity_fit", claim="recent_task_too_large") -> ActionableSignal:
    return ActionableSignal(
        signal_id="sig1",
        source_event_ids=["e1"],
        source_system="test",
        state_key=state_key,
        claim=claim,
        confidence=0.8,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="test",
        possible_effects=[],
        priority="medium",
    )


@pytest.mark.asyncio
async def test_fatigue_state_softens_tone():
    """Fatigue in active_states should override tone to encouraging_low_pressure."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result

    directive = engine.build_response_directive(
        decision, signal,
        active_states=[
            {"state_key": "fatigue_accumulated", "value": "high", "confidence": 0.75, "scope": "session"},
        ],
    )
    assert directive is not None
    assert directive.tone == "encouraging_low_pressure"


@pytest.mark.asyncio
async def test_deadline_pressure_urgent_tone():
    """High-confidence deadline_pressure should produce calm_urgent tone."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result

    directive = engine.build_response_directive(
        decision, signal,
        active_states=[
            {"state_key": "deadline_pressure", "value": "approaching", "confidence": 0.85, "scope": "day"},
        ],
    )
    assert directive is not None
    assert directive.tone == "calm_urgent"


@pytest.mark.asyncio
async def test_no_active_states_default_tone():
    """Without active_states, tone should come from decision soft_biases."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result

    directive = engine.build_response_directive(decision, signal)
    assert directive is not None
    assert isinstance(directive.tone, str)


@pytest.mark.asyncio
async def test_low_confidence_state_ignored():
    """Active states below 0.5 confidence should not affect tone."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result

    default_directive = engine.build_response_directive(decision, signal)
    state_directive = engine.build_response_directive(
        decision, signal,
        active_states=[
            {"state_key": "fatigue_accumulated", "value": "high", "confidence": 0.3, "scope": "session"},
        ],
    )
    assert state_directive is not None
    assert default_directive is not None
    assert state_directive.tone == default_directive.tone


@pytest.mark.asyncio
async def test_notification_fatigue_softens_tone():
    """notification_fatigue active state should produce encouraging_low_pressure."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result

    directive = engine.build_response_directive(
        decision, signal,
        active_states=[
            {"state_key": "notification_fatigue", "value": "consecutive_dismissal", "confidence": 0.7, "scope": "session"},
        ],
    )
    assert directive is not None
    assert directive.tone == "encouraging_low_pressure"


@pytest.mark.asyncio
async def test_deadline_fatigue_conflict_fatigue_wins():
    """When both fatigue and deadline present, fatigue takes precedence (user wellbeing)."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result

    directive = engine.build_response_directive(
        decision, signal,
        active_states=[
            {"state_key": "fatigue_accumulated", "value": "high", "confidence": 0.7, "scope": "session"},
            {"state_key": "deadline_pressure", "value": "approaching", "confidence": 0.8, "scope": "day"},
        ],
    )
    assert directive is not None
    assert directive.tone == "encouraging_low_pressure"
