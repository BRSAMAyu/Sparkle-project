from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import (
    AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY,
    AURORA_DEEP_PATTERN_ALERTS_CONTEXT_KEY,
    DashboardReadout,
    DashboardReadoutBuilder,
)
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop
from app.models.error_book import ErrorRecord
from app.models.user import User
from app.services.error_replan_bridge import ErrorReplanBridge


async def _seed_tcp_state_recurring_errors(db_session):
    user = User(
        username="g14_tcp_user",
        email="g14_tcp_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    now = datetime.utcnow()
    db_session.add_all(
        [
            ErrorRecord(
                user_id=user.id,
                subject_code="computer_networks",
                chapter="transport",
                question_text=f"TCP 状态机错题 {index}",
                latest_analysis={
                    "node_id": "cn.tcp_state",
                    "cause_category": "trigger_condition_confusion",
                    "root_cause": "状态转换触发条件混淆",
                },
                created_at=now - timedelta(days=index),
            )
            for index in range(3)
        ]
    )
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_analyze_recurring_errors_flags_third_same_cause_category(db_session):
    user = await _seed_tcp_state_recurring_errors(db_session)

    result = await ErrorReplanBridge(db_session)._analyze_recurring_errors(
        user_id=user.id,
        node_id="cn.tcp_state",
    )

    assert result["recurring"] is True
    assert result["node_id"] == "cn.tcp_state"
    assert result["cause_category"] == "trigger_condition_confusion"
    assert result["occurrence_count"] == 3
    assert "状态机" in result["root_cause_hypothesis"]
    assert "20 分钟" in result["recommended_intervention"]


@pytest.mark.asyncio
async def test_dashboard_injects_deep_pattern_alerts_from_confirmed_weak_nodes(db_session):
    user = await _seed_tcp_state_recurring_errors(db_session)
    builder = DashboardReadoutBuilder()

    payload = await builder.with_deep_pattern_alerts_from_error_history(
        active_db=db_session,
        user_id=str(user.id),
        user_context_payload={AURORA_CONFIRMED_WEAK_NODES_CONTEXT_KEY: ["cn.tcp_state"]},
    )
    cold_start = builder._extract_cold_start_context(
        profile_context={},
        user_context_payload=payload,
    )

    assert AURORA_DEEP_PATTERN_ALERTS_CONTEXT_KEY in payload
    assert cold_start["confirmed_weak_nodes"] == ["cn.tcp_state"]
    assert cold_start["deep_pattern_alerts"][0]["node_id"] == "cn.tcp_state"
    assert cold_start["deep_pattern_alerts"][0]["cause_category"] == "trigger_condition_confusion"


def test_decision_loop_prioritizes_root_cause_intervention_for_deep_pattern_alerts():
    alert = {
        "recurring": True,
        "node_id": "cn.tcp_state",
        "cause_category": "trigger_condition_confusion",
        "occurrence_count": 3,
        "root_cause_hypothesis": "状态转换触发条件没有和 TCP 设计目标绑定起来。",
        "recommended_intervention": "从 TCP 设计目标出发重新理解状态。",
    }
    readout = DashboardReadout(
        surface="aurora_planning",
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="这道 TCP 状态转换题我又错了",
        activity_profile={},
        hard_bounds=AuroraHardBounds(),
        cold_start_context={"goal_type": "exam", "deep_pattern_alerts": [alert]},
        covered_domains=["goal"],
        missing_domains=["scope"],
        task_state={"stage": "task_card", "current_task_id": "tcp-state-card"},
        checkpoint_state={"last_status": "stable"},
    )
    loop = AuroraDecisionLoop()

    prompt = json.dumps(loop.build_prompt(readout), ensure_ascii=False)
    assert "deep_pattern_alerts" in prompt
    assert "root_cause_intervention" in prompt
    assert "根因干预" in prompt

    validated = loop.validate_decision(
        AuroraDecision(action="emit_message", chat_directive={"intent": "continue_current_task"}),
        readout,
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert validated.chat_directive["intent"] == "root_cause_intervention"
    assert contract["response_type"] == "diagnostic"
    assert contract["response_type"] != "task_help"
