from app.core.unified_intent_router import IntentRoutingResult
from app.orchestration.schemas import RouteDecision


def to_route_decision(result: IntentRoutingResult) -> RouteDecision:
    return RouteDecision(
        execution_mode=result.execution_mode,
        reason=f"unified:{result.primary_intent.value}",
        risk_level=result.risk_level,
        confidence=result.confidence,
        context_version=result.context_version,
    )
