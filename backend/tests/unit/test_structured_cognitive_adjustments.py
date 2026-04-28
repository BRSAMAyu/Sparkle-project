from __future__ import annotations

from app.orchestration.dual_core_router import CognitiveAdjustment, DualCoreDecision


def test_cognitive_adjustment_to_text() -> None:
    ca = CognitiveAdjustment(
        dimension="tone",
        value="gentle",
        reason="user fatigue detected",
        evidence=["3 tasks failed in a row"],
        scope="session",
        user_visible=True,
    )
    assert ca.to_text() == "tone=gentle (user fatigue detected)"
    d = ca.to_dict()
    assert d["dimension"] == "tone"
    assert d["user_visible"] is True


def test_cognitive_adjustment_defaults() -> None:
    ca = CognitiveAdjustment(dimension="verbosity", value="low", reason="high cognitive load")
    assert ca.scope == "turn"
    assert ca.user_visible is False
    assert ca.ttl is None
    assert ca.evidence == []


def test_dual_core_decision_structured_adjustments_default_empty() -> None:
    decision = DualCoreDecision("balanced", "test", ["tone=gentle"], [])
    assert decision.structured_adjustments == []
    d = decision.to_dict()
    assert d["structured_adjustments"] == []


def test_dual_core_decision_with_structured_adjustments() -> None:
    ca = CognitiveAdjustment(
        dimension="challenge_level",
        value=-0.2,
        reason="deadline pressure high, user making mistakes",
        evidence=["quiz_accuracy=0.4", "deadline_hours=48"],
        scope="sprint",
        user_visible=True,
        ttl="72h",
    )
    decision = DualCoreDecision(
        "balanced",
        "test",
        ["challenge_level=reduce"],
        [],
        structured_adjustments=[ca],
    )
    serialized = decision.to_dict()
    assert len(serialized["structured_adjustments"]) == 1
    sa = serialized["structured_adjustments"][0]
    assert sa["dimension"] == "challenge_level"
    assert sa["value"] == -0.2
    assert sa["scope"] == "sprint"
    assert sa["ttl"] == "72h"


def test_structured_adjustments_preserved_across_overlay() -> None:
    from app.orchestration.routing_engine import RoutingEngineMixin

    ca = CognitiveAdjustment(dimension="tone", value="warm", reason="streak bonus")
    decision = DualCoreDecision(
        "balanced",
        "base",
        ["tone=warm"],
        [],
        structured_adjustments=[ca],
    )
    overlaid = RoutingEngineMixin._overlay_stage33_social_constraints(
        decision=decision,
        added_cognitive=["peer_mistake_hint"],
        added_execution=[],
        added_strategy_adjustments=[],
        candidate_mode="balanced",
    )
    assert overlaid.structured_adjustments == [ca]
    assert "peer_mistake_hint" in overlaid.cognitive_adjustments
