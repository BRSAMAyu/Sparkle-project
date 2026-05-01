from __future__ import annotations

import json

import pytest

from app.signals.policy_engine import PolicyEngine
from app.signals.types import ActionableSignal


def _timeout_signal() -> ActionableSignal:
    return ActionableSignal(
        signal_id="sig_timeout",
        source_event_ids=["task1"],
        source_system="test",
        state_key="task_granularity_fit",
        claim="recent_task_too_large",
        confidence=0.82,
        scope="current_sprint",
        ttl_hours=48,
        evidence_summary="Task took too long.",
        possible_effects=["adjust_task_size"],
        priority="medium",
    )


@pytest.mark.asyncio
async def test_policy_engine_applies_aurora_decision_as_soft_bias() -> None:
    decision, directive = await PolicyEngine().evaluate(
        _timeout_signal(),
        context={
            "consecutive": 2,
            "aurora_decisions": [
                {"action": "reduce_load", "surface": "fatigue_check"},
            ],
        },
    )

    assert directive.hard_constraints["max_task_duration_min"] == 25
    assert decision.soft_biases["aurora_recent_action"] == "reduce_load"
    assert decision.soft_biases["aurora_recent_surface"] == "fatigue_check"
    assert decision.soft_biases["tone"] == "low_pressure"
    assert decision.soft_biases["nudge_style"] == "minimal"


@pytest.mark.asyncio
async def test_spine_pipeline_passes_aurora_decisions_to_policy_engine() -> None:
    from app.signals.spine_orchestrator import SpineOrchestrator
    from tests.unit.spine._helpers import FakeRedis

    redis = FakeRedis()
    await redis.rpush(
        "spine:aurora_decisions:u1",
        json.dumps({"action": "reduce_load", "surface": "fatigue_check"}),
    )
    spine = SpineOrchestrator(redis)

    captured_context = {}

    async def fake_evaluate(signal, context=None, recent_policy_effects=None, strategy_beliefs=None):
        captured_context.update(context or {})
        return None

    spine.policy_engine.evaluate = fake_evaluate
    await spine._run_signal_pipeline(user_id="u1", signal=_timeout_signal())

    assert captured_context["aurora_decisions"] == [{"action": "reduce_load", "surface": "fatigue_check"}]
