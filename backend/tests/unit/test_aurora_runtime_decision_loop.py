from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pytest

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import AuroraHardBounds, ControlSurfaceReading, ActivityProfile, DndWindow
from app.aurora.runtime_v1.dashboard import DashboardReadout, DashboardReadoutBuilder
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.skills import AuroraSkillRegistry


class _FakeJsonLLM:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[list[dict[str, str]]] = []

    async def chat_json(self, messages, **kwargs):
        self.calls.append(messages)
        return self.payload


def _readout(
    *,
    hard_bounds: AuroraHardBounds | None = None,
    user_message: str = "7天后考计网，从没学过。",
    covered_domains: list[str] | None = None,
    missing_domains: list[str] | None = None,
    recently_asked_domains: list[str] | None = None,
) -> DashboardReadout:
    return DashboardReadout(
        surface="aurora_modeling",
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message=user_message,
        activity_profile={
            "conversation_style": "warm",
            "task_density_hint": 0.35,
        },
        hard_bounds=hard_bounds or AuroraHardBounds(),
        candidate_affordances=AuroraSkillRegistry().load_candidate_affordances("aurora_modeling"),
        cold_start_context={"goal_type": "exam"},
        informational_tensions=[{"domain": "exam_scope", "status": "open"}],
        covered_domains=list(covered_domains or ["goal"]),
        missing_domains=list(missing_domains or ["scope", "baseline", "time"]),
        recently_asked_domains=list(recently_asked_domains or []),
        sprint_policy_summary={"mode": "seven_day_survival", "days_remaining": 7},
        explicit_user_constraints={"hard_bounds": {"privacy_boundaries": []}},
    )


@pytest.mark.asyncio
async def test_decision_loop_prompt_contains_dashboard_boundaries_and_no_final_copy_instruction() -> None:
    fake = _FakeJsonLLM(
        {
            "action": "emit_message",
            "surface_complete": False,
            "modeling_complete": False,
            "chat_directive": {"intent": "ask_scope"},
            "metadata": {"reasoning_summary": "Need exam scope."},
        }
    )
    loop = AuroraDecisionLoop(llm_factory=lambda: fake)

    await loop.decide(_readout())

    serialized_prompt = json.dumps(fake.calls[0], ensure_ascii=False)
    assert "dashboard_readout" in serialized_prompt
    assert "hard_boundaries" in serialized_prompt
    assert "candidate_affordances" in serialized_prompt
    assert "covered_domains" in serialized_prompt
    assert "recently_asked_domains" in serialized_prompt
    assert "sprint_policy_summary" in serialized_prompt
    assert "Do not generate final user-facing text" in serialized_prompt
    assert '"messages"' not in serialized_prompt


@pytest.mark.asyncio
async def test_modeling_complete_comes_from_decision_not_keywords() -> None:
    decision_llm = _FakeJsonLLM(
        {
            "action": "emit_message",
            "surface_complete": False,
            "modeling_complete": False,
            "chat_directive": {"intent": "continue_modeling"},
            "metadata": {"reasoning_summary": "The user said completion words, but scope is still missing."},
        }
    )
    chat_llm = _FakeJsonLLM({"messages": ["我还差一点考试范围的信息，先不用讲很多：大概考哪些章节？"]})
    service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(llm_factory=lambda: decision_llm),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: chat_llm),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="就这些，差不多了。",
        request_extra_context={},
        conversation_context={},
        user_context_payload={},
    )

    assert plan.modeling_complete is False
    assert plan.surface_complete is False
    assert plan.messages == ["我还差一点考试范围的信息，先不用讲很多：大概考哪些章节？"]


@pytest.mark.asyncio
async def test_modeling_complete_is_resolved_by_dashboard_coverage_not_llm_flag() -> None:
    decision_llm = _FakeJsonLLM(
        {
            "action": "emit_message",
            "surface_complete": False,
            "modeling_complete": False,
            "chat_directive": {"intent": "continue_modeling", "target_domain": "time"},
            "metadata": {"reasoning_summary": "LLM forgot to close modeling."},
        }
    )
    chat_llm = _FakeJsonLLM({"messages": ["信息够用了。接下来我可以直接按这个状态给你做规划。"]})
    service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(llm_factory=lambda: decision_llm),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: chat_llm),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="每天3小时，主要考传输层和网络层。",
        request_extra_context={
            "task_state": {
                "goal_raw": "7天后通过计网考试",
                "subject": "计算机网络",
                "knowledge_baseline": "从没系统学过，但刷过一点题",
                "daily_available_hours": 3,
            },
            "informational_tensions": [
                {"domain": "goal", "status": "resolved"},
                {"domain": "exam_scope", "status": "resolved"},
                {"domain": "knowledge_baseline", "status": "resolved"},
                {"domain": "time_available", "status": "resolved"},
            ],
        },
        conversation_context={},
        user_context_payload={},
    )

    assert plan.modeling_complete is True
    assert plan.surface_complete is True


def test_decision_loop_retargets_repeated_or_resolved_domain() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        state_updates={"informational_tensions": [{"domain": "exam_scope", "status": "open"}]},
        chat_directive={"intent": "ask_scope", "target_domain": "exam_scope"},
    )

    validated = loop.validate_decision(
        decision,
        _readout(
            covered_domains=["goal", "scope"],
            missing_domains=["baseline", "time"],
            recently_asked_domains=["scope"],
        ),
    )

    assert validated.chat_directive["target_domain"] == "baseline"
    assert validated.harness_updates["agenda_priority"] == "baseline"
    assert validated.state_updates["informational_tensions"][0]["domain"] == "baseline"
    assert validated.metadata["retargeted_from_resolved_domain"] == "scope"


def test_decision_loop_sets_modeling_complete_false_while_core_domains_are_missing() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        modeling_complete=True,
        chat_directive={"intent": "close_modeling"},
    )

    validated = loop.validate_decision(
        decision,
        _readout(
            covered_domains=["goal", "scope"],
            missing_domains=["baseline", "time"],
        ),
    )

    assert validated.modeling_complete is False
    assert validated.surface_complete is False


def test_decision_loop_rejects_privacy_boundary_harness_update() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="update_harness",
        harness_updates={"agenda_priority": "family_conflict"},
        chat_directive={"intent": "probe_private_domain"},
    )

    validated = loop.validate_decision(
        decision,
        _readout(hard_bounds=AuroraHardBounds(privacy_boundaries=["family_conflict"])),
    )

    assert validated.action == "update_harness"
    assert validated.harness_updates == {}
    assert validated.metadata["harness_update_rejected"] is True


def test_decision_loop_rejects_privacy_blocked_domain_reintroduced_during_stabilization() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "continue_modeling"},
    )

    validated = loop.validate_decision(
        decision,
        _readout(
            hard_bounds=AuroraHardBounds(privacy_boundaries=["family_conflict"]),
            covered_domains=["goal"],
            missing_domains=["family_conflict", "time"],
        ),
    )

    assert validated.action == "wait"
    assert validated.metadata["fallback_reason"] == "privacy_blocked_domain"
    assert validated.harness_updates == {}


def test_decision_loop_suppresses_wake_inside_dnd_and_disabled_followup() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="schedule_wake",
        wake_schedule={"scheduled_at": datetime(2026, 4, 24, 23, 0).isoformat(), "reason": "follow-up"},
        chat_directive={"intent": "schedule_later"},
    )
    readout = _readout(
        hard_bounds=AuroraHardBounds(
            dnd_windows=[DndWindow(start="22:30", end="07:30")],
            timezone_name="Asia/Shanghai",
            disabled_actions=["proactive_follow_up"],
        )
    )

    validated = loop.validate_decision(decision, readout)

    assert validated.action == "wait"
    assert validated.wake_schedule is None
    assert validated.metadata["fallback_reason"] == "proactive_follow_up_disabled"


def test_decision_loop_rejects_forbidden_modeling_domains() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        state_updates={"clinical_diagnosis": "anxiety_disorder"},
        chat_directive={"intent": "diagnose_user"},
    )

    validated = loop.validate_decision(decision, _readout())

    assert validated.action == "wait"
    assert validated.metadata["fallback_reason"] == "forbidden_modeling_domain"


@pytest.mark.asyncio
async def test_chat_adapter_merges_split_messages_and_removes_overlap() -> None:
    chat_llm = _FakeJsonLLM(
        {
            "messages": [
                "我先接住你刚刚补进来的范围，",
                "这样我就能更稳地往下规划。",
                "这样我就能更稳地往下规划。",
                "这次主要考哪些章节？",
            ]
        }
    )
    adapter = ChatLayerAdapter(llm_factory=lambda: chat_llm)
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "ask_scope", "target_domain": "scope"},
        state_updates={"informational_tensions": [{"domain": "scope", "status": "open"}]},
    )

    messages = await adapter.render(decision, _readout())

    assert messages == [
        "我先接住你刚刚补进来的范围，这样我就能更稳地往下规划。",
        "这次主要考哪些章节？",
    ]


def test_slim_readout_for_aurora_modeling_excludes_task_and_checkpoint_state() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout()
    payload = loop._slim_readout_for_surface(readout)
    assert "task_state" not in payload
    assert "checkpoint_state" not in payload
    assert "exam_sprint_policy" not in payload
    assert "domain_coverage" in payload
    assert "informational_tensions" in payload


def test_informational_tension_accepts_importance_reasoning() -> None:
    from app.aurora.runtime_v1.state import InformationalTension
    t = InformationalTension(
        tension_id="t1",
        domain="baseline",
        description="还不清楚起点",
        priority=0.7,
        importance_reasoning="决定起点和难度梯度",
    )
    assert t.importance_reasoning == "决定起点和难度梯度"
    dumped = t.model_dump()
    assert dumped["importance_reasoning"] == "决定起点和难度梯度"


def test_dashboard_builder_enriches_tensions_with_importance_reasoning() -> None:
    from app.aurora.runtime_v1.dashboard import DashboardReadoutBuilder
    from app.aurora.runtime_v1.control_surface import AuroraHardBounds, ControlSurfaceReading, ActivityProfile

    builder = DashboardReadoutBuilder()
    reading = ControlSurfaceReading(
        adjustable=ActivityProfile(),
        hard_bounds=AuroraHardBounds(),
        runtime_enabled=True,
    )
    readout = builder.build(
        surface="aurora_modeling",
        user_id="u1",
        conversation_id="c1",
        request_id="r1",
        user_message="7天后考计网",
        request_extra_context={
            "informational_tensions": [
                {"domain": "baseline", "status": "open", "description": "还不清楚", "priority": 0.7}
            ]
        },
        conversation_context={},
        user_context_payload={},
        control_surface_reading=reading,
        activity_profile={},
        candidate_affordances=[],
    )
    tensions_with_reasoning = [t for t in readout.informational_tensions if t.get("importance_reasoning")]
    assert len(tensions_with_reasoning) >= 1
    assert "难度梯度" in tensions_with_reasoning[0]["importance_reasoning"]


def test_modeling_complete_requires_only_four_core_domains_not_motivation() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        modeling_complete=True,
        chat_directive={"intent": "close_modeling"},
    )
    validated = loop.validate_decision(
        decision,
        _readout(
            covered_domains=["goal", "scope", "baseline", "time"],
            missing_domains=["motivation"],
        ),
    )
    assert validated.modeling_complete is True
    assert validated.surface_complete is True


@pytest.mark.asyncio
async def test_service_keeps_wait_turn_silent_without_extra_fallback() -> None:
    decision_loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({"action": "wait"}))
    chat_adapter = ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["不应出现"]}))
    service = AuroraRuntimeV1Service(
        decision_loop=decision_loop,
        chat_adapter=chat_adapter,
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="你先等等，我再想想。",
        request_extra_context={},
        conversation_context={},
        user_context_payload={},
    )

    assert plan.messages == []


def test_extract_achievement_signals_falls_back_to_cognitive_context() -> None:
    builder = DashboardReadoutBuilder()
    user_context_payload = {
        "cognitive_context": {
            "achievement_summary": {
                "recent_unlocks": [{"name": "初学者", "rarity": "common"}],
                "in_progress_achievements": [{"name": "连续打卡7天", "progress": 0.6}],
                "total_achievement_score": 25.0,
            }
        }
    }
    signals = builder._extract_achievement_signals({}, user_context_payload)
    assert signals["in_progress_count"] == 1
    assert len(signals["recent_unlocks"]) == 1
    assert signals["momentum"] == pytest.approx(0.5)


def test_extract_achievement_signals_prefers_explicit_over_cognitive() -> None:
    builder = DashboardReadoutBuilder()
    explicit = {"active_streaks": ["daily_study"], "in_progress_count": 5, "recent_unlocks": [], "momentum": 0.9}
    user_context_payload = {
        "cognitive_context": {
            "achievement_summary": {"recent_unlocks": [], "in_progress_achievements": [], "total_achievement_score": 0}
        }
    }
    signals = builder._extract_achievement_signals({"achievement_signals": explicit}, user_context_payload)
    assert signals["in_progress_count"] == 5
    assert signals["momentum"] == pytest.approx(0.9)
