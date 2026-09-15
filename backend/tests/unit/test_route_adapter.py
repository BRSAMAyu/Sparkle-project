from app.core.unified_intent_router import IntentRoutingResult, UnifiedIntentType
from app.orchestration.route_adapter import to_route_decision


def test_to_route_decision_maps_fields():
    result = IntentRoutingResult(
        primary_intent=UnifiedIntentType.PLAN,
        confidence=0.81,
        routing_layer="rule",
        execution_mode="langgraph",
        risk_level="medium",
        context_version="v12",
    )
    decision = to_route_decision(result)

    assert decision.execution_mode == "langgraph"
    assert decision.risk_level == "medium"
    assert decision.confidence == 0.81
    assert decision.context_version == "v12"
    assert decision.reason == "unified:plan"
