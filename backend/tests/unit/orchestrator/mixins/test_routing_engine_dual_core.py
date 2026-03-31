from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestration.dual_core_router import DualCoreDecision
from app.orchestration.routing_engine import RoutingEngineMixin
from app.orchestration.schemas import RouteDecision


class MinimalRoutingOrchestrator(RoutingEngineMixin):
    def __init__(self):
        self.redis = MagicMock()
        self.dual_core_router = MagicMock()
        self._get_recent_sentiment_distribution = AsyncMock(
            return_value={"anxious": 2, "calm": 1}
        )
        self._get_recent_task_feedback_distribution = AsyncMock(
            return_value={"too_long": 2, "too_difficult": 1}
        )


@pytest.fixture
def orchestrator() -> MinimalRoutingOrchestrator:
    return MinimalRoutingOrchestrator()


@pytest.mark.asyncio
async def test_build_dual_core_input_uses_active_plan_from_user_context(orchestrator):
    active_plan_id = uuid.uuid4()
    fake_report = SimpleNamespace(severity="warning")

    with patch("app.orchestration.routing_engine.PlanProgressService") as progress_service_cls:
        progress_service = progress_service_cls.return_value
        progress_service.evaluate_progress = AsyncMock(return_value=fake_report)

        routing_input = await orchestrator._build_dual_core_input(
            active_db=object(),
            user_id=str(uuid.uuid4()),
            plan_id=None,
            user_context_payload={
                "active_plans": [{"id": str(active_plan_id)}],
                "preferences": {"focus_duration_preference": 20, "difficulty_preference": 0.3},
            },
            plan_context={
                "user_profile": {"derived_insights": {"primary_challenge_area": "emotional"}},
            },
            unified_routing_result=SimpleNamespace(
                primary_intent=SimpleNamespace(value="plan"),
                confidence=0.88,
            ),
            information_sufficient=False,
        )

    assert routing_input.intent == "plan"
    assert routing_input.intent_confidence == pytest.approx(0.88)
    assert routing_input.has_active_plan is True
    assert routing_input.plan_health_status == "warning"
    assert routing_input.primary_challenge_area == "emotional"
    assert routing_input.session_length_preference == 20
    assert routing_input.difficulty_preference == pytest.approx(0.3)
    assert routing_input.recent_sentiment_distribution == {"anxious": 2, "calm": 1}
    assert routing_input.recent_task_feedback_distribution == {"too_long": 2, "too_difficult": 1}
    progress_service.evaluate_progress.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_dual_core_input_tolerates_plan_progress_failures(orchestrator):
    with patch("app.orchestration.routing_engine.PlanProgressService") as progress_service_cls:
        progress_service = progress_service_cls.return_value
        progress_service.evaluate_progress = AsyncMock(side_effect=RuntimeError("redis down"))

        routing_input = await orchestrator._build_dual_core_input(
            active_db=object(),
            user_id=str(uuid.uuid4()),
            plan_id=uuid.uuid4(),
            user_context_payload=None,
            plan_context=None,
            unified_routing_result=None,
            information_sufficient=True,
        )

    assert routing_input.intent == "chat"
    assert routing_input.intent_confidence == pytest.approx(0.5)
    assert routing_input.has_active_plan is True
    assert routing_input.plan_health_status is None


@pytest.mark.asyncio
async def test_apply_dual_core_routing_for_cognitive_first_rewrites_langgraph_route(orchestrator):
    decision = DualCoreDecision(
        mode="cognitive_first",
        reason="need emotional grounding first",
        cognitive_adjustments=["先减轻焦虑"],
        execution_constraints=["先不要给太重的任务"],
    )
    orchestrator.dual_core_router.route.return_value = decision
    state = SimpleNamespace(context_data={"plan_metadata": {"existing": "value"}})
    stream_callback = AsyncMock()

    route_decision = RouteDecision(
        execution_mode="langgraph",
        reason="complex plan flow",
        risk_level="medium",
        confidence=0.8,
    )

    updated = await orchestrator._apply_dual_core_routing(
        route_decision=route_decision,
        state=state,
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload=None,
        plan_context=None,
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="plan"),
            confidence=0.91,
        ),
        information_sufficient=False,
        stream_callback=stream_callback,
    )

    assert updated is route_decision
    assert updated.execution_mode == "direct"
    assert updated.reason.endswith("dual_core:cognitive_first")
    assert state.context_data["dual_core_decision"]["mode"] == "cognitive_first"
    assert "双核心认知调制" in state.context_data["dual_core_prompt_instruction"]
    assert state.context_data["dual_core_signal_snapshot"]["intent"] == "plan"
    assert state.context_data["plan_metadata"]["dual_core_mode"] == "cognitive_first"
    assert state.context_data["plan_metadata"]["dual_core_reason"] == "need emotional grounding first"
    stream_callback.assert_awaited_once()
    emitted = stream_callback.await_args.args[0]
    assert emitted.metadata
    assert "ux_progress" in emitted.metadata


@pytest.mark.asyncio
async def test_apply_dual_core_routing_short_circuits_general_chat_to_execution_first(orchestrator):
    state = SimpleNamespace(context_data={})
    stream_callback = AsyncMock()
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="simple answer path",
        risk_level="low",
        confidence=0.7,
    )

    updated = await orchestrator._apply_dual_core_routing(
        route_decision=route_decision,
        state=state,
        active_db=None,
        user_id=str(uuid.uuid4()),
        plan_id=None,
        user_context_payload=None,
        plan_context=None,
        unified_routing_result=SimpleNamespace(
            primary_intent=SimpleNamespace(value="chat"),
            confidence=0.8,
        ),
        information_sufficient=True,
        stream_callback=stream_callback,
    )

    assert updated.execution_mode == "direct"
    assert updated.reason.endswith("dual_core:execution_first")
    assert state.context_data["dual_core_decision"]["mode"] == "execution_first"
    orchestrator.dual_core_router.route.assert_not_called()
