from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pytest

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import ActivityProfile, AuroraHardBounds, ControlSurfaceReading, DndWindow
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
    surface: str = "aurora_modeling",
    user_message: str = "7天后考计网，从没学过。",
    activity_profile: dict[str, Any] | None = None,
    covered_domains: list[str] | None = None,
    missing_domains: list[str] | None = None,
    recently_asked_domains: list[str] | None = None,
    request_extra_context: dict[str, Any] | None = None,
    latent_thread_recovery_candidates: list[dict[str, Any]] | None = None,
    sprint_policy_summary: dict[str, Any] | None = None,
    exam_sprint_policy: dict[str, Any] | None = None,
    explicit_user_constraints: dict[str, Any] | None = None,
    task_state: dict[str, Any] | None = None,
    checkpoint_state: dict[str, Any] | None = None,
    achievement_signals: dict[str, Any] | None = None,
    self_model: dict[str, Any] | None = None,
) -> DashboardReadout:
    return DashboardReadout(
        surface=surface,
        user_id="user-1",
        conversation_id="conv-1",
        request_id="req-1",
        user_message=user_message,
        activity_profile={
            "conversation_style": "warm",
            "expression": {
                "tone_warmth": 0.78,
                "directness": 0.32,
                "brevity": 0.44,
                "friendliness": 0.82,
                "challenge_intensity": 0.28,
            },
            "task_density_hint": 0.35,
            **dict(activity_profile or {}),
        },
        hard_bounds=hard_bounds or AuroraHardBounds(),
        candidate_affordances=AuroraSkillRegistry().load_candidate_affordances("aurora_modeling"),
        cold_start_context={"goal_type": "exam"},
        informational_tensions=[{"domain": "exam_scope", "status": "open"}],
        covered_domains=list(covered_domains or ["goal"]),
        missing_domains=list(missing_domains or ["scope", "baseline", "time"]),
        recently_asked_domains=list(recently_asked_domains or []),
        sprint_policy_summary=dict(sprint_policy_summary or {"mode": "seven_day_survival", "days_remaining": 7}),
        explicit_user_constraints=dict(explicit_user_constraints or {"hard_bounds": {"privacy_boundaries": []}}),
        latent_thread_recovery_candidates=list(latent_thread_recovery_candidates or []),
        exam_sprint_policy=dict(exam_sprint_policy or {}),
        task_state=dict(task_state or {"stage": "triage"}),
        checkpoint_state=dict(checkpoint_state or {"last_status": "stable"}),
        request_extra_context=dict(request_extra_context or {}),
        achievement_signals=dict(achievement_signals or {"plan_completion_rate": 0.48}),
        self_model=dict(self_model or {}),
    )


@pytest.mark.asyncio
async def test_decision_loop_prompt_uses_masked_dashboard_context_and_no_final_copy_instruction() -> None:
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
    assert "user_message" in serialized_prompt
    assert "covered_domains" in serialized_prompt
    assert "missing_domains" in serialized_prompt
    assert "informational_tensions" in serialized_prompt
    assert "candidate_affordances" not in serialized_prompt
    assert "hard_boundaries" not in serialized_prompt
    assert "achievement_signals" not in serialized_prompt
    assert "sprint_policy_summary" not in serialized_prompt
    assert "strategy_defaults" in serialized_prompt
    assert "concept_first" in serialized_prompt
    assert "standard_layer_contract" in serialized_prompt
    assert "response_type" in serialized_prompt
    assert "Teaching strategy is a first-class decision" in serialized_prompt
    assert "Do not generate final user-facing text" in serialized_prompt
    assert '"messages"' not in serialized_prompt


def test_aurora_decision_round_trip_preserves_strategy_payload() -> None:
    payload = {
        "action": "emit_message",
        "harness_updates": {
            "strategy": {
                "concept_first": True,
                "problem_first": False,
                "worked_example_first": True,
                "retrieval_practice": True,
                "interleaving": False,
                "spaced_review": True,
                "error_analysis_required": True,
            }
        },
    }

    decision = AuroraDecision.from_payload(payload)

    assert decision.harness_updates["strategy"]["worked_example_first"] is True
    assert decision.harness_updates["strategy"]["spaced_review"] is True
    assert decision.to_payload()["harness_updates"]["strategy"] == payload["harness_updates"]["strategy"]


def test_decision_loop_defaults_modeling_strategy_and_high_urgency_worked_example() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "continue_modeling"})

    validated = loop.validate_decision(
        decision,
        _readout(
            sprint_policy_summary={"mode": "seven_day_survival", "days_remaining": 3},
            exam_sprint_policy={"triage_level": "emergency"},
        ),
    )

    strategy = validated.harness_updates["strategy"]
    assert strategy["concept_first"] is True
    assert strategy["worked_example_first"] is True


def test_decision_loop_defaults_planning_strategy_to_problem_first() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "tighten_plan"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            sprint_policy_summary={"mode": "standard_exam_sprint", "days_remaining": 14},
        ),
    )

    strategy = validated.harness_updates["strategy"]
    assert strategy["problem_first"] is True
    assert strategy["concept_first"] is False


def test_decision_loop_assigns_task_help_standard_layer_contract_for_active_task_card() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={
            "strategy": {
                "worked_example_first": True,
                "problem_first": True,
            }
        },
        chat_directive={"intent": "teach_with_example"},
    )

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            task_state={"stage": "task_card", "current_task_id": "tcp-congestion-1"},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "task_help"
    assert contract["must_include"] == ["worked_example", "three_practice_questions", "completion_check"]
    assert contract["must_not_include"] == ["full_week_replan", "long_motivational_speech"]
    assert contract["max_response_length"] == "extended"


def test_decision_loop_assigns_emotional_support_contract_after_repeated_failures() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "continue_current_task"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            checkpoint_state={"last_status": "failed", "recent_failures": 3},
            self_model={"task_failure_streak": 3},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "emotional_support"
    assert contract["must_include"] == ["emotional_acknowledgment", "one_concrete_next_step"]
    assert "blame_or_shame" in contract["must_not_include"]


def test_decision_loop_assigns_calibration_contract_when_self_model_needs_recalibration() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "safe_ack"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_modeling",
            self_model={
                "needs_recalibration": True,
                "strategy_confidence": 0.31,
            },
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "calibration"
    assert contract["must_include"] == ["explicit_uncertainty", "calibration_question_or_assumption_check"]
    assert contract["max_response_length"] == "brief"


def test_decision_loop_assigns_plan_discussion_contract_for_planning_turn() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "tighten_plan"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            task_state={"stage": "planning"},
            checkpoint_state={"last_status": "stable"},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "plan_discussion"
    assert contract["must_include"] == ["plan_delta_or_tradeoff", "one_decision_or_question"]
    assert "unsolicited_three_practice_questions" in contract["must_not_include"]


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
    assert "agenda_priority" not in validated.harness_updates
    assert "strategy" in validated.harness_updates
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
    assert "strategy" in validated.harness_updates
    assert "agenda_priority" not in validated.harness_updates


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


@pytest.mark.asyncio
async def test_chat_adapter_prompt_includes_expression_controls_and_same_turn_override() -> None:
    chat_llm = _FakeJsonLLM({"messages": ["好，先做 3 道题。"]})
    adapter = ChatLayerAdapter(llm_factory=lambda: chat_llm)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={
            "expression": {
                "tone_warmth": 0.22,
                "directness": 0.94,
                "brevity": 0.9,
                "friendliness": 0.28,
                "challenge_intensity": 0.76,
            }
        },
        chat_directive={"intent": "assign_questions"},
    )

    await adapter.render(decision, _readout(user_message="我知道了，给我题做"))

    user_prompt = json.loads(chat_llm.calls[0][1]["content"])
    assert user_prompt["expression_controls"]["directness"] == pytest.approx(0.94)
    assert user_prompt["expression_controls"]["tone_warmth"] == pytest.approx(0.22)
    assert user_prompt["activity_profile"]["expression"]["challenge_intensity"] == pytest.approx(0.76)
    assert "Do not add extra encouragement" in user_prompt["expression_instruction"]


@pytest.mark.asyncio
async def test_chat_adapter_prompt_includes_teaching_strategy() -> None:
    chat_llm = _FakeJsonLLM({"messages": ["我们先看一道完整例题。"]})
    adapter = ChatLayerAdapter(llm_factory=lambda: chat_llm)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={
            "strategy": {
                "concept_first": True,
                "problem_first": False,
                "worked_example_first": True,
                "retrieval_practice": False,
                "interleaving": False,
                "spaced_review": False,
                "error_analysis_required": False,
            }
        },
        chat_directive={"intent": "teach_with_example"},
    )

    await adapter.render(decision, _readout(user_message="TCP 拥塞控制我有点乱"))

    user_prompt = json.loads(chat_llm.calls[0][1]["content"])
    assert user_prompt["teaching_strategy"]["concept_first"] is True
    assert user_prompt["teaching_strategy"]["worked_example_first"] is True
    assert "strategy" in user_prompt["activity_profile"]


@pytest.mark.asyncio
async def test_chat_adapter_prompt_includes_standard_layer_contract_as_hard_constraint() -> None:
    chat_llm = _FakeJsonLLM({"messages": ["我们先看一道完整例题。"]})
    adapter = ChatLayerAdapter(llm_factory=lambda: chat_llm)
    decision = AuroraDecision(
        action="emit_message",
        harness_updates={
            "strategy": {
                "worked_example_first": True,
                "problem_first": True,
            }
        },
        chat_directive={"intent": "teach_with_example"},
    )

    await adapter.render(
        decision,
        _readout(
            surface="aurora_planning",
            task_state={"stage": "task_card", "current_task_id": "tcp-congestion-1"},
            user_message="TCP 拥塞控制这题我不会。",
        ),
    )

    system_prompt = chat_llm.calls[0][0]["content"]
    user_prompt = json.loads(chat_llm.calls[0][1]["content"])
    assert "standard_layer_contract is a hard contract" in system_prompt
    assert user_prompt["standard_layer_contract"]["response_type"] == "task_help"
    assert user_prompt["standard_layer_contract"]["must_include"] == [
        "worked_example",
        "three_practice_questions",
        "completion_check",
    ]
    assert "MUST include" in user_prompt["standard_layer_contract_instruction"]
    assert "MUST NOT include" in user_prompt["standard_layer_contract_instruction"]


def test_service_surface_defaults_include_distinct_expression_profiles() -> None:
    service = AuroraRuntimeV1Service()

    modeling_profile = service._build_activity_profile(surface="aurora_modeling", request_extra_context={})
    planning_profile = service._build_activity_profile(surface="aurora_planning", request_extra_context={})
    checkpoint_profile = service._build_activity_profile(surface="aurora_checkpoint", request_extra_context={})

    assert modeling_profile["expression"] != planning_profile["expression"]
    assert checkpoint_profile["expression"] != planning_profile["expression"]
    assert modeling_profile["expression"]["tone_warmth"] > planning_profile["expression"]["tone_warmth"]
    assert planning_profile["expression"]["directness"] > modeling_profile["expression"]["directness"]


@pytest.mark.asyncio
async def test_service_merges_expression_harness_updates_without_losing_surface_defaults() -> None:
    decision_loop = AuroraDecisionLoop(
        llm_factory=lambda: _FakeJsonLLM(
            {
                "action": "emit_message",
                "harness_updates": {"expression": {"directness": 0.91, "brevity": 0.87}},
                "chat_directive": {"intent": "assign_questions"},
            }
        )
    )
    chat_adapter = ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["先做 3 道题。"]}))
    service = AuroraRuntimeV1Service(
        decision_loop=decision_loop,
        chat_adapter=chat_adapter,
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_planning",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="我知道了，给我题做。",
        request_extra_context={},
        conversation_context={},
        user_context_payload={},
    )

    assert plan.activity_profile["expression"]["directness"] == pytest.approx(0.91)
    assert plan.activity_profile["expression"]["brevity"] == pytest.approx(0.87)
    assert plan.activity_profile["expression"]["tone_warmth"] == pytest.approx(0.34)
    assert plan.activity_profile["expression"]["friendliness"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_plan_turn_refuses_new_topic_in_last_24h_mode() -> None:
    service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({"action": "emit_message"})),
        chat_adapter=ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["不应该调用到这里"]})),
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_planning",
        conversation_id="conv-last-24h",
        request_id="req-last-24h",
        user_message="帮我讲一个全新的低频章节吧",
        request_extra_context={
            "exam_sprint_policy": {
                "days_left": 1,
                "subject": "计算机网络",
                "sprint_mode": "seven_day_survival",
            }
        },
        conversation_context={},
        user_context_payload={},
    )

    assert plan.messages == [
        "明天就考试了，现在看新章节的收益很低。建议先把你最容易丢分的 TCP 状态变化再过一遍。"
    ]
    strategy = plan.activity_profile["strategy"]
    assert strategy["new_topic_allowed"] is False
    assert strategy["drop_low_roi_topics"] is True
    assert strategy["error_analysis_required"] is True


def test_slim_readout_for_aurora_modeling_excludes_task_and_checkpoint_state() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout()
    payload = loop._slim_readout_for_surface(readout)
    assert "task_state" not in payload
    assert "checkpoint_state" not in payload
    assert "exam_sprint_policy" not in payload
    assert "sprint_policy_summary" not in payload
    assert "covered_domains" in payload
    assert "missing_domains" in payload
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


def test_planning_detour_surface_state_is_visible_to_decision_loop() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        surface="aurora_planning",
        covered_domains=["goal"],
        missing_domains=["scope"],
        request_extra_context={
            "planning_detour_scaffold": {
                "surface_state": {"in_detour": True},
                "recent_detours": ["先帮我查一下这个任务完成没有"],
            }
        },
    )

    payload = loop._slim_readout_for_surface(readout)

    assert payload["surface_state"]["in_detour"] is True
    assert "cold_start_context" not in payload
    assert "sprint_policy_summary" in payload
    assert "task_state" in payload


def test_dashboard_readout_emit_message_context_mask_excludes_unrelated_fields() -> None:
    payload = _readout().to_llm_payload(action="emit_message")

    assert "user_message" in payload
    assert "covered_domains" in payload
    assert "missing_domains" in payload
    assert "cold_start_context" in payload
    assert "informational_tensions" in payload
    assert "candidate_affordances" not in payload
    assert "hard_boundaries" not in payload
    assert "achievement_signals" not in payload
    assert "sprint_policy_summary" not in payload


def test_dashboard_readout_wait_context_mask_is_smaller_than_emit_message() -> None:
    emit_payload = _readout().to_llm_payload(action="emit_message")
    wait_payload = _readout().to_llm_payload(action="wait")

    assert "cold_start_context" not in wait_payload
    assert "informational_tensions" not in wait_payload
    assert len(json.dumps(wait_payload, ensure_ascii=False)) < len(json.dumps(emit_payload, ensure_ascii=False))


def test_dashboard_readout_schedule_wake_context_keeps_activity_and_constraints() -> None:
    payload = _readout().to_llm_payload(action="schedule_wake")

    assert "activity_profile" in payload
    assert "explicit_user_constraints" in payload
    assert "informational_tensions" not in payload
    assert "cold_start_context" not in payload


def test_dashboard_readout_planning_surface_includes_planning_fields_without_achievement_signals() -> None:
    payload = _readout(
        surface="aurora_planning",
        task_state={"stage": "planning"},
        achievement_signals={"plan_completion_rate": 0.48},
    ).to_llm_payload(action="emit_message")

    assert "sprint_policy_summary" in payload
    assert "task_state" in payload
    assert "achievement_signals" not in payload
    assert "cold_start_context" not in payload


def test_soft_return_topic_uses_latent_candidate_after_planning_detour() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="soft_return_topic", chat_directive={"intent": "recover_planning_naturally"})
    readout = _readout(
        surface="aurora_planning",
        covered_domains=["goal"],
        missing_domains=["scope"],
        request_extra_context={"surface_state": {"in_detour": True}},
        latent_thread_recovery_candidates=[
            {"thread_id": "thread-scope", "target_domain": "scope", "recovery_priority": 0.9}
        ],
    )

    validated = loop.validate_decision(decision, readout)

    assert validated.action == "soft_return_topic"
    assert validated.chat_directive["thread_id"] == "thread-scope"
    assert validated.chat_directive["target_domain"] == "scope"


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


@pytest.mark.asyncio
async def test_service_uses_chat_adapter_as_single_fallback_source() -> None:
    class EmptyRenderAdapter(ChatLayerAdapter):
        def __init__(self) -> None:
            super().__init__(llm_factory=lambda: _FakeJsonLLM({}))
            self.fallback_reason: str | None = None

        async def render(self, decision: AuroraDecision, readout: DashboardReadout) -> list[str]:
            return []

        async def _fallback_messages(
            self,
            decision: AuroraDecision,
            readout: DashboardReadout,
            *,
            reason: str | None = None,
        ) -> list[str]:
            self.fallback_reason = reason
            return ["adapter fallback"]

    adapter = EmptyRenderAdapter()
    service = AuroraRuntimeV1Service(
        decision_loop=AuroraDecisionLoop(
            llm_factory=lambda: _FakeJsonLLM(
                {
                    "action": "emit_message",
                    "chat_directive": {"intent": "ask_scope", "target_domain": "scope"},
                }
            )
        ),
        chat_adapter=adapter,
    )

    plan = await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_modeling",
        conversation_id="conv-1",
        request_id="req-1",
        user_message="我想备考。",
        request_extra_context={},
        conversation_context={},
        user_context_payload={},
    )

    assert plan.messages == ["adapter fallback"]
    assert adapter.fallback_reason == "empty_render"


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


# ---------------------------------------------------------------------------
# Last-24h mode — Aurora conversation layer wiring
# ---------------------------------------------------------------------------


def test_dashboard_builder_synthesizes_last_24h_mode_from_sprint_mode_cram() -> None:
    """DashboardReadout.last_24h_mode must be True when exam_sprint_policy.sprint_mode == 'last_24h_cram'."""
    from app.aurora.runtime_v1.control_surface import ActivityProfile, ControlSurfaceReading

    builder = DashboardReadoutBuilder()
    reading = ControlSurfaceReading(
        adjustable=ActivityProfile(),
        hard_bounds=AuroraHardBounds(),
        runtime_enabled=True,
    )
    readout = builder.build(
        surface="aurora_planning",
        user_id="u1",
        conversation_id="c1",
        request_id="r1",
        user_message="帮我快速复习最重要的几个点",
        request_extra_context={
            "exam_sprint_policy": {
                "sprint_mode": "last_24h_cram",
                "days_left": 0,
                "triage_level": "emergency",
            }
        },
        conversation_context={},
        user_context_payload={},
        control_surface_reading=reading,
        activity_profile={},
        candidate_affordances=[],
    )

    assert readout.last_24h_mode is True


def test_dashboard_builder_last_24h_mode_false_for_normal_sprint() -> None:
    """last_24h_mode must be False for all non-cram sprint modes."""
    from app.aurora.runtime_v1.control_surface import ActivityProfile, ControlSurfaceReading

    builder = DashboardReadoutBuilder()
    reading = ControlSurfaceReading(
        adjustable=ActivityProfile(),
        hard_bounds=AuroraHardBounds(),
        runtime_enabled=True,
    )
    for sprint_mode in ("seven_day_survival", "fourteen_day_build_and_retrieve", "standard_exam_sprint", ""):
        readout = builder.build(
            surface="aurora_planning",
            user_id="u1",
            conversation_id="c1",
            request_id="r1",
            user_message="帮我规划",
            request_extra_context={"exam_sprint_policy": {"sprint_mode": sprint_mode}},
            conversation_context={},
            user_context_payload={},
            control_surface_reading=reading,
            activity_profile={},
            candidate_affordances=[],
        )
        assert readout.last_24h_mode is False, f"expected last_24h_mode=False for sprint_mode={sprint_mode!r}"


def test_strategy_defaults_use_last_24h_overrides_for_cram_sprint_mode() -> None:
    """_strategy_defaults_for_readout must apply last-24h overrides when sprint_mode == 'last_24h_cram'."""
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        exam_sprint_policy={"sprint_mode": "last_24h_cram", "days_left": 0, "triage_level": "emergency"},
    )
    defaults = loop._strategy_defaults_for_readout(readout)

    assert defaults["worked_example_first"] is True
    assert defaults["retrieval_practice"] is True
    assert defaults["spaced_review"] is True
    assert defaults["error_analysis_required"] is True
    assert defaults["drop_low_roi_topics"] is True
    assert defaults["new_topic_allowed"] is False


def test_decision_loop_prompt_includes_last_24h_rule_for_cram_mode() -> None:
    """build_prompt() must inject the LAST-24H EXAM MODE rule when sprint_mode == 'last_24h_cram'."""
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        exam_sprint_policy={"sprint_mode": "last_24h_cram", "days_left": 0, "triage_level": "emergency"},
    )
    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])

    last_24h_rules = [r for r in prompt_payload["rules"] if "LAST-24H" in r]
    assert last_24h_rules, "Expected at least one LAST-24H EXAM MODE rule in prompt"
    assert "Do NOT probe for new information" in last_24h_rules[0]
    assert "calibration" in last_24h_rules[0].lower()


def test_decision_loop_prompt_no_last_24h_rule_for_normal_sprint() -> None:
    """build_prompt() must NOT inject the last-24h rule for non-cram sprint modes."""
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        exam_sprint_policy={"sprint_mode": "seven_day_survival", "days_left": 5, "triage_level": "high"},
    )
    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])

    last_24h_rules = [r for r in prompt_payload["rules"] if "LAST-24H" in r]
    assert not last_24h_rules, "LAST-24H rule must not appear for seven_day_survival"


def test_last_24h_mode_exposed_in_planning_surface_llm_payload() -> None:
    """last_24h_mode must appear in the LLM payload for aurora_planning surface."""
    import dataclasses

    readout = _readout(
        surface="aurora_planning",
        exam_sprint_policy={"sprint_mode": "last_24h_cram"},
    )
    # Rebuild with last_24h_mode=True using dataclasses.replace (avoids __dict__ on slotted class)
    readout = dataclasses.replace(readout, last_24h_mode=True)
    payload = readout.to_llm_payload()
    # For aurora_planning surface, last_24h_mode is in surface additions so it should appear
    assert "last_24h_mode" in payload
    assert payload["last_24h_mode"] is True
