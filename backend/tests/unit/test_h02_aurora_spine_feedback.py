"""
Tests for H-02: Aurora→Spine feedback wired to PolicyEngine.
"""
import pytest

from app.signals.policy_engine import PolicyEngine
from app.signals.types import ActionableSignal


def _signal(
    state_key="task_granularity_fit",
    claim="recent_task_too_large",
    confidence=0.8,
    priority="medium",
) -> ActionableSignal:
    return ActionableSignal(
        signal_id="sig1",
        source_event_ids=["e1"],
        source_system="test",
        state_key=state_key,
        claim=claim,
        confidence=confidence,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="test",
        possible_effects=[],
        priority=priority,
    )


@pytest.mark.asyncio
async def test_no_aurora_decisions_passes_through():
    """Without Aurora decisions, rule should pass through unchanged."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={})
    assert result is not None
    decision, _ = result
    assert decision.primary_strategy == "recover_execution_rhythm"


@pytest.mark.asyncio
async def test_aurora_fatigue_decision_softens_tone():
    """Aurora fatigue decision should soften tone to low_pressure."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(
        signal,
        context={
            "aurora_decisions": [
                {"action": "reduce_load", "surface": "fatigue_detected"},
            ],
        },
    )
    assert result is not None
    decision, _ = result
    assert decision.soft_biases.get("tone") == "low_pressure"
    assert "Aurora" in decision.reasoning_summary


@pytest.mark.asyncio
async def test_aurora_protect_user_action_softens():
    """Aurora protect_user action should soften tone."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(
        signal,
        context={
            "aurora_decisions": [
                {"action": "protect_user", "surface": "evening"},
            ],
        },
    )
    assert result is not None
    decision, _ = result
    assert decision.soft_biases.get("tone") == "low_pressure"


@pytest.mark.asyncio
async def test_aurora_normal_action_adds_metadata():
    """Normal Aurora action should add metadata to soft biases."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(
        signal,
        context={
            "aurora_decisions": [
                {"action": "emit_message", "surface": "plan_review"},
            ],
        },
    )
    assert result is not None
    decision, _ = result
    assert decision.soft_biases.get("aurora_recent_action") == "emit_message"
    assert decision.soft_biases.get("aurora_recent_surface") == "plan_review"
    # Should NOT override tone for non-fatigue actions
    assert decision.soft_biases.get("tone") != "low_pressure"


@pytest.mark.asyncio
async def test_aurora_empty_decisions_ignored():
    """Empty aurora_decisions list should not affect the rule."""
    engine = PolicyEngine()
    signal = _signal()
    result = await engine.evaluate(signal, context={"aurora_decisions": []})
    assert result is not None
    decision, _ = result
    assert "aurora_recent_action" not in decision.soft_biases
