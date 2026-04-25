from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import AuroraHardBounds
from app.aurora.runtime_v1.dashboard import DashboardReadout
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.core.context_manager import ContextOrchestrator
from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext
from app.models.plan import Plan, PlanStage, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.orchestration.prompts import build_system_prompt
from app.orchestration.task_card_generator import TaskCardGenerator


class _WakeDecisionStub:
    def to_payload(self) -> dict[str, str]:
        return {"energy": "moderate"}


class _WakePolicyStub:
    async def evaluate(self, **kwargs):
        return _WakeDecisionStub()


def _readout(
    *,
    user_message: str,
    covered_domains: list[str],
    missing_domains: list[str],
    recently_asked_domains: list[str],
    request_extra_context: dict | None = None,
) -> DashboardReadout:
    return DashboardReadout(
        surface="aurora_modeling",
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message=user_message,
        activity_profile={"conversation_style": "warm"},
        hard_bounds=AuroraHardBounds(),
        covered_domains=covered_domains,
        missing_domains=missing_domains,
        recently_asked_domains=recently_asked_domains,
        request_extra_context=request_extra_context or {},
    )


@pytest.mark.asyncio
async def test_h6_scenario1_context_aware_fallback_does_not_reask_covered_domain() -> None:
    adapter = ChatLayerAdapter()
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "ask_scope", "target_domain": "scope"},
    )
    readout = _readout(
        user_message="7天后考计算机网络，主要考传输层，我之前完全没学过。",
        covered_domains=["goal", "scope", "baseline", "time", "motivation"],
        missing_domains=["scope"],
        recently_asked_domains=["goal", "scope", "baseline", "time", "motivation"],
        request_extra_context={"exam_scope": "传输层"},
    )

    assert adapter._context_aware_fallback_question(decision, readout) is None

    fallback = await adapter._fallback_messages(decision, readout)

    assert fallback == ["我先把这部分记住。你不用一次讲完整，我们会边走边把关键线索补齐。"]


@pytest.mark.asyncio
async def test_h6_scenario2_daily_startup_includes_name_completion_and_plan_context(db_session) -> None:
    session_day = date.today()
    user = User(
        id=uuid4(),
        username=f"h6_daily_{uuid4().hex[:8]}",
        nickname="阿泽",
        email=f"h6_daily_{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
    )
    plan = Plan(
        name="2天计算机网络冲刺",
        user_id=user.id,
        type=PlanType.SPRINT,
        subject="计算机网络",
        target_date=session_day + timedelta(days=1),
        daily_available_minutes=50,
        plan_stage=PlanStage.SPRINT,
        is_active=True,
        source_metadata={
            "exam_sprint_intake": {"goal_model": {"days_left": 2}},
            "plan_context": {
                "daily_startup": {
                    "2": {
                        "today_focus": "TCP 流量控制",
                        "recommendation": "先把窗口与确认机制串起来，再做 1 道小题。",
                    }
                }
            },
        },
    )
    db_session.add_all([user, plan])
    await db_session.flush()

    for index in range(10):
        db_session.add(
            Task(
                user_id=user.id,
                plan_id=plan.id,
                title=f"Day 1 · 昨日任务 {index + 1}",
                type=TaskType.LEARNING,
                tags=["规划生成", "day:1"],
                estimated_minutes=10,
                difficulty=1,
                energy_cost=1,
                status=TaskStatus.COMPLETED if index < 7 else TaskStatus.PENDING,
                order_index=1000 + index,
            )
        )

    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 2 · 复测 1 题",
            type=TaskType.LEARNING,
            tags=["规划生成", "day:2"],
            estimated_minutes=35,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            order_index=2001,
        )
    )
    await db_session.commit()

    payload = await AuroraRuntimeV1Service(wake_policy_service=_WakePolicyStub()).get_daily_startup_message(
        active_db=db_session,
        user_id=user.id,
        plan_id=plan.id,
        session_date=session_day,
    )

    assert payload["today_focus"] == "TCP 流量控制"
    assert "阿泽" in payload["message"]
    assert "70%" in payload["message"]
    assert "TCP 流量控制" in payload["message"]
    assert "窗口与确认机制" in payload["message"]


def test_h6_scenario3_stuck_help_sheet_content_is_dynamic_aurora_guidance() -> None:
    result = TaskCardGenerator().generate(
        guide_json={
            "objective": "Day 2：TCP 三次握手流程追踪",
            "common_mistakes": ["把 SYN、ACK 的作用混在一起。"],
            "method_steps": [
                "先写角色和目的。",
                "再画完整时序。",
                "最后闭卷重画。",
            ],
        },
        task_kind="retrieval_drill",
        subject="计算机网络",
        focus="TCP 状态机",
        knowledge_state={"weak_nodes": [{"node_name": "TCP 三次握手"}]},
        aurora_control_signal={},
    )

    stuck_help = result["stuck_help"]

    assert "TCP 状态机" in stuck_help["diagnosis_question"]
    assert "状态/步骤" in stuck_help["diagnosis_question"]
    assert "SYN、ACK" in stuck_help["targeted_fix"]
    assert "TCP 三次握手" in stuck_help["check_question"]


@pytest.mark.asyncio
async def test_h6_scenario4_cross_session_memory_reaches_prompt_in_practice(db_session, monkeypatch) -> None:
    redis_client = AsyncMock()
    redis_client.get.return_value = None
    orchestrator = ContextOrchestrator(db_session, redis_client)
    profile_context = ProfileContext(
        preferences={"depth": "high"},
        preference_version=3,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.52,
            active_learning_subjects=["computer_networks"],
            weak_spots=[],
            recent_mastery_changes=[],
        ),
        cognitive_summary=CognitiveSummary(),
    )

    monkeypatch.setattr(orchestrator, "_get_profile_context", AsyncMock(return_value=profile_context))
    monkeypatch.setattr(orchestrator, "_get_error_profile", AsyncMock(return_value={}))
    monkeypatch.setattr(orchestrator, "_get_task_profile", AsyncMock(return_value={"tasks": [], "focus": {}}))
    monkeypatch.setattr(orchestrator, "_get_user_metrics", AsyncMock(return_value={}))
    monkeypatch.setattr(orchestrator, "_get_community_profile", AsyncMock(return_value={}))
    monkeypatch.setattr(orchestrator, "_get_social_context_v1", AsyncMock(return_value={}))
    monkeypatch.setattr(orchestrator, "_get_achievement_context", AsyncMock(return_value={}))
    monkeypatch.setattr(orchestrator, "_get_calendar_context", AsyncMock(return_value={}))
    monkeypatch.setattr(
        "app.core.context_manager.MemoryService.get_recent_episodic",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=uuid4(),
                    summary="你之前提过 TCP 状态转换最容易断链，要先盯触发条件。",
                    subject_type="learning_profile",
                    source_type="chat_turn",
                    occurred_at=None,
                    tags=["aurora", "memory"],
                )
            ]
        ),
    )

    context = await orchestrator.get_context(str(uuid4()))
    prompt = build_system_prompt(
        user_context=context.model_dump(mode="python"),
        conversation_history={"messages": []},
    )

    assert context.past_session_memory[0]["summary"].startswith("你之前提过 TCP 状态转换最容易断链")
    assert "你之前了解的关于用户的信息" in prompt
    assert "TCP 状态转换最容易断链" in prompt
