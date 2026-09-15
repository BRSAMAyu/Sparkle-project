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


async def test_stage4_routing_mode_keeps_direct_behavior_when_flag_is_off(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", False):
        updated = await orchestrator._apply_stage4_routing_mode(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="帮我把这周复习计划拆成每天三步。",
            conversation_context=None,
        )

    assert updated.execution_mode == "direct"
    assert state.context_data["stage4_routing_mode"]["routing_mode"] == "workflow"
    assert state.context_data["stage4_routing_mode"]["feature_enabled"] is False


async def test_stage4_routing_mode_promotes_planning_request_to_workflow_when_flag_on(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_routing_mode(
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


async def test_stage4_routing_mode_marks_task_assistant_candidate_without_workflow_jump(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_routing_mode(
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


async def test_stage4_routing_mode_keeps_frustration_signal_direct_until_ws_b2(orchestrator):
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_routing_mode(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="我有点卡住了，但现在先别切模式。",
            conversation_context=None,
        )

    assert updated.execution_mode == "direct"
    assert updated.reason == "unified:fallback"
    assert state.context_data["stage4_routing_mode"]["routing_mode"] == "direct"
    assert "stage4_task_assistant_candidate" not in state.context_data


# ======================================================================
# WS-B.2 Escalation tests
# ======================================================================


async def test_stage4_escalation_fires_on_explicit_planning_request(orchestrator):
    """WS-B.2 trigger 1: explicit planning request promotes direct → langgraph."""
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_escalation(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="别直答了，帮我做成方案一步步跟着做。",
            conversation_context=None,
        )

    assert updated.execution_mode == "langgraph"
    assert updated.risk_level == "medium"
    assert "escalation:explicit_planning_request" in updated.reason
    assert state.context_data["stage4_escalation"]["should_escalate"] is True
    assert state.context_data["stage4_escalation"]["trigger"] == "explicit_planning_request"


async def test_stage4_escalation_fires_on_structural_topic_turns(orchestrator):
    """WS-B.2 trigger 2: 2+ structural-topic turns promote direct → langgraph."""
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )
    conversation_context = {
        "messages": [
            {"role": "user", "content": "这三块拆开，顺序怎么定？"},
            {"role": "assistant", "content": "可以按难度排序。"},
            {"role": "user", "content": "那分类呢？先做哪个？"},
        ]
    }

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_escalation(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="继续刚才的讨论。",
            conversation_context=conversation_context,
        )

    assert updated.execution_mode == "langgraph"
    assert "escalation:structural_topic_turns" in updated.reason
    assert state.context_data["stage4_escalation"]["trigger"] == "structural_topic_turns"


async def test_stage4_escalation_fires_on_frustration_text(orchestrator):
    """WS-B.2 trigger 3: frustration text markers promote direct → langgraph."""
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_escalation(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="我真的有点做不下去了，这样聊完全帮不到我。",
            conversation_context=None,
        )

    assert updated.execution_mode == "langgraph"
    assert "escalation:frustration_blockage" in updated.reason
    assert state.context_data["stage4_escalation"]["trigger"] == "frustration_blockage"


async def test_stage4_escalation_no_fire_when_flag_off(orchestrator):
    """Escalation verdict is recorded but mode stays direct when flag is off."""
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", False):
        updated = await orchestrator._apply_stage4_escalation(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="别直答了，帮我做成方案一步步跟着做。",
            conversation_context=None,
        )

    assert updated.execution_mode == "direct"
    # Verdict is still recorded for observability
    assert state.context_data["stage4_escalation"]["should_escalate"] is True
    assert state.context_data["stage4_escalation"]["feature_enabled"] is False


async def test_stage4_escalation_no_fire_when_already_workflow(orchestrator):
    """Escalation does not fire when WS-B.1 already promoted to workflow."""
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="langgraph",
        reason="stage4_routing_mode:workflow",
        risk_level="medium",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_escalation(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="别直答了，帮我做成方案。",
            conversation_context=None,
        )

    assert updated.execution_mode == "langgraph"
    assert updated.reason == "stage4_routing_mode:workflow"
    assert "stage4_escalation" not in state.context_data


async def test_stage4_escalation_no_fire_without_trigger(orchestrator):
    """No escalation when no trigger is present."""
    state = SimpleNamespace(context_data={})
    route_decision = RouteDecision(
        execution_mode="direct",
        reason="unified:fallback",
        risk_level="low",
        confidence=0.7,
    )

    with patch("app.orchestration.routing_engine.aurora_flags.AURORA_ROUTING_MODE_ENABLED", True):
        updated = await orchestrator._apply_stage4_escalation(
            route_decision=route_decision,
            state=state,
            user_id=str(uuid.uuid4()),
            user_message="今天状态一般，先陪我简单聊两句。",
            conversation_context=None,
        )

    assert updated.execution_mode == "direct"
    assert state.context_data["stage4_escalation"]["should_escalate"] is False
