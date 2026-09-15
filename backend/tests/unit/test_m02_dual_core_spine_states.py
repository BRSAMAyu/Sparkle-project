"""Tests for M-02: dual_core_router consumes Spine StateRegister data."""

from app.orchestration.dual_core_router import DualCoreDecision, DualCoreRouter, DualCoreRoutingInput


def _base_input(**overrides) -> DualCoreRoutingInput:
    defaults = {
        "intent": "chat",
        "intent_confidence": 0.85,
        "information_sufficient": True,
        "primary_challenge_area": None,
        "recent_sentiment_distribution": {"neutral": 5},
        "has_active_plan": True,
        "plan_health_status": "on_track",
        "recent_task_feedback_distribution": {},
    }
    defaults.update(overrides)
    return DualCoreRoutingInput(**defaults)


def test_no_spine_states_passes_through():
    """Without Spine states, routing should proceed normally."""
    router = DualCoreRouter()
    inp = _base_input(spine_active_states=[])
    decision = router.route(inp)
    assert isinstance(decision, DualCoreDecision)
    assert decision.mode in ("execution_first", "balanced", "cognitive_first")


def test_fatigue_state_softens_intensity():
    """Fatigue Spine state should recommend low intervention_intensity."""
    router = DualCoreRouter()
    inp = _base_input(
        spine_active_states=[
            {"state_key": "fatigue_accumulated", "value": "high", "confidence": 0.75, "scope": "session"},
        ],
    )
    decision = router.route(inp)
    fields = [s["field"] for s in decision.strategy_adjustments]
    assert "intervention_intensity" in fields
    matching = [s for s in decision.strategy_adjustments if s["field"] == "intervention_intensity"]
    assert matching[0]["recommended_value"] == "low"


def test_execution_consistency_preserves_momentum():
    """Low execution_consistency state should recommend momentum_preserving."""
    router = DualCoreRouter()
    inp = _base_input(
        information_sufficient=False,
        spine_active_states=[
            {"state_key": "execution_consistency", "value": "low", "confidence": 0.7, "scope": "sprint"},
        ],
    )
    decision = router.route(inp)
    # execution_consistency adds execution_constraint + strategy recommend
    assert any("Spine" in c for c in decision.execution_constraints)


def test_knowledge_bottleneck_slows_explanation():
    """Knowledge bottleneck state should recommend step_by_step explanation."""
    router = DualCoreRouter()
    inp = _base_input(
        spine_active_states=[
            {"state_key": "knowledge_bottleneck", "value": "detected", "confidence": 0.6, "scope": "task"},
        ],
    )
    decision = router.route(inp)
    fields = [s["field"] for s in decision.strategy_adjustments]
    assert "explanation_style" in fields


def test_low_confidence_state_ignored():
    """Spine states below confidence 0.45 should be ignored."""
    router = DualCoreRouter()
    inp = _base_input(
        spine_active_states=[
            {"state_key": "fatigue_accumulated", "value": "high", "confidence": 0.3, "scope": "session"},
        ],
    )
    decision = router.route(inp)
    assert decision.routing_debug.get("spine_fatigue_detected") is False


def test_routing_debug_includes_spine_metrics():
    """Routing debug should include spine state metrics."""
    router = DualCoreRouter()
    inp = _base_input(
        spine_active_states=[
            {"state_key": "fatigue_accumulated", "value": "high", "confidence": 0.8, "scope": "session"},
        ],
    )
    decision = router.route(inp)
    assert "spine_state_count" in decision.routing_debug
    assert decision.routing_debug["spine_state_count"] == 1
    assert decision.routing_debug["spine_fatigue_detected"] is True
