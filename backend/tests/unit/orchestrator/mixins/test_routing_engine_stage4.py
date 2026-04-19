from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.orchestration.routing_engine import RoutingEngineMixin
from app.orchestration.schemas import RouteDecision


class MinimalStage4RoutingOrchestrator(RoutingEngineMixin):
    def __init__(self):
        self.redis = MagicMock()
        self.dual_core_router = MagicMock()


@pytest.fixture
def orchestrator() -> MinimalStage4RoutingOrchestrator:
    return MinimalStage4RoutingOrchestrator()


def test_stage4_routing_mode_keeps_direct_behavior_when_flag_is_off(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", False):
        updated = orchestrator._apply_stage4_routing_mode(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="帮我把这周复习计划拆成每天三步。",
            conversation_context=None,
        )

    assert updated.execution_mode == "direct"
    assert state.context_data["stage4_routing_mode"]["routing_mode"] == "workflow"
    assert state.context_data["stage4_routing_mode"]["feature_enabled"] is False


def test_stage4_routing_mode_promotes_planning_request_to_workflow_when_flag_on(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = orchestrator._apply_stage4_routing_mode(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="帮我把这周复习计划拆成每天三步。",
            conversation_context=None,
        )

    assert updated.execution_mode == "langgraph"
    assert updated.risk_level == "medium"
    assert "stage4_routing_mode:workflow" in updated.reason
    assert state.context_data["stage4_routing_mode"]["routing_mode"] == "workflow"


def test_stage4_routing_mode_marks_task_assistant_candidate_without_workflow_jump(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = orchestrator._apply_stage4_routing_mode(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="不用重做计划，我就想把当前这张任务卡顺下来。",
            conversation_context=None,
        )

    assert updated.execution_mode == "direct"
    assert "stage4_routing_mode:task_assistant" in updated.reason
    assert state.context_data["stage4_routing_mode"]["routing_mode"] == "task_assistant"
    assert state.context_data["stage4_task_assistant_candidate"] is True
