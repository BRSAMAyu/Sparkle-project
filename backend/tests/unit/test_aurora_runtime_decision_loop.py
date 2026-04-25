from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import ActivityProfile, AuroraHardBounds, ControlSurfaceReading, DndWindow
from app.aurora.runtime_v1.dashboard import DashboardReadout, DashboardReadoutBuilder
from app.aurora.runtime_v1.decision_loop import AuroraDecision, AuroraDecisionLoop
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.skills import AuroraSkillRegistry
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService
from app.aurora.runtime_v1.write_pipeline import AURORA_CLAIM_KEY_TEMPLATE
from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager


class _FakeJsonLLM:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.calls: list[list[dict[str, str]]] = []

    async def chat_json(self, messages, **kwargs):
        self.calls.append(messages)
        return self.payload


class _CapturingDecisionLoop:
    def __init__(self) -> None:
        self.readouts: list[DashboardReadout] = []

    async def decide(self, readout: DashboardReadout) -> AuroraDecision:
        self.readouts.append(readout)
        return AuroraDecision(action="wait")


class _StaticDecisionLoop:
    def __init__(self, decision: AuroraDecision) -> None:
        self.decision = decision
        self.readouts: list[DashboardReadout] = []

    async def decide(self, readout: DashboardReadout) -> AuroraDecision:
        self.readouts.append(readout)
        return self.decision


class _StaticChatAdapter:
    async def render(self, decision: AuroraDecision, readout: DashboardReadout) -> list[str]:
        del decision, readout
        return ["收到。"]


class _FakeGalaxyService:
    def __init__(self) -> None:
        self.mastery_updates: list[dict[str, Any]] = []

    async def update_node_mastery(self, **kwargs) -> dict[str, Any]:
        self.mastery_updates.append(kwargs)
        return {"success": True, "new_mastery": kwargs["new_mastery"]}


class _StubSelfModelService:
    async def get_readout_summary(self, **kwargs) -> dict[str, Any]:
        return {}


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def lpush(self, key: str, value: str) -> None:
        bucket = self.lists.setdefault(key, [])
        bucket.insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        bucket = self.lists.setdefault(key, [])
        self.lists[key] = bucket[start : end + 1]

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        bucket = self.lists.get(key, [])
        if end == -1:
            return bucket[start:]
        return bucket[start : end + 1]

    async def expire(self, key: str, seconds: int) -> None:
        del key, seconds


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
    conversation_summary: dict[str, Any] | None = None,
    wake_policy: dict[str, Any] | None = None,
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
        conversation_summary=dict(conversation_summary or {}),
        wake_policy=dict(wake_policy or {}),
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


def test_decision_loop_diagnoses_stuck_task_instead_of_continuing_current_task() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "continue_current_task"},
    )

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            task_state={"stage": "stuck", "stuck_topic": "TCP状态机"},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert validated.chat_directive["intent"] == "diagnose_stuck_point"
    assert contract["response_type"] == "diagnostic"
    assert "mistake_diagnosis" in contract["must_include"]
    assert "one_targeted_fix" in contract["must_include"]
    assert "full_week_replan" in contract["must_not_include"]
    assert "three_practice_questions" in contract["must_not_include"]
    assert "three_practice_questions" not in contract["must_include"]


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


def test_decision_loop_reduces_pressure_when_achievement_momentum_stalls() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        surface="aurora_planning",
        task_state={"stage": "task_card", "current_task_id": "tcp-congestion-1"},
        achievement_signals={"momentum": 0.05, "streak_active": False},
    )
    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])
    prompt_rules = " ".join(prompt_payload["rules"])

    assert "emotional_support" in prompt_rules
    assert "three_practice_questions" in prompt_rules

    validated = loop.validate_decision(
        AuroraDecision(
            action="emit_message",
            chat_directive={
                "intent": "continue_current_task",
                "standard_layer_contract": {"must_include": ["three_practice_questions"]},
            },
        ),
        readout,
    )
    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "emotional_support"
    assert "three_practice_questions" in contract["must_not_include"]
    assert "three_practice_questions" not in contract["must_include"]


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


def test_decision_loop_acknowledges_recent_unlock_and_allows_streak_reminder() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        surface="aurora_planning",
        task_state={"stage": "planning"},
        achievement_signals={"momentum": 0.85, "recently_unlocked": True, "streak_active": True},
    )
    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])
    prompt_rules = " ".join(prompt_payload["rules"])

    assert "direct_answer_or_acknowledgment" in prompt_rules
    assert "连续打卡" in prompt_rules

    validated = loop.validate_decision(AuroraDecision(action="emit_message"), readout)
    contract = validated.chat_directive["standard_layer_contract"]
    assert "direct_answer_or_acknowledgment" in contract["must_include"]


def test_decision_loop_adds_high_streak_challenge_modulation_rule() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        surface="aurora_planning",
        task_state={"stage": "planning"},
        achievement_signals={"current_streak_days": 6},
    )

    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])
    prompt_rules = " ".join(prompt_payload["rules"])

    assert "current_streak_days >= 5" in prompt_rules
    assert "retrieval_practice = true" in prompt_rules
    assert "direct_answer_or_acknowledgment" in prompt_rules
    assert prompt_payload["strategy_defaults"]["retrieval_practice"] is True

    validated = loop.validate_decision(AuroraDecision(action="emit_message"), readout)
    assert validated.harness_updates["strategy"]["retrieval_practice"] is True
    assert "direct_answer_or_acknowledgment" in validated.chat_directive["standard_layer_contract"]["must_include"]


def test_decision_loop_reduces_pressure_after_study_gap() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        surface="aurora_planning",
        activity_profile={"task_density_hint": 0.6},
        task_state={"stage": "planning"},
        achievement_signals={"gap_since_last_study_days": 4},
    )

    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])
    prompt_rules = " ".join(prompt_payload["rules"])

    assert "gap_since_last_study_days >= 3" in prompt_rules
    assert "减压" in prompt_rules
    assert "task_density_hint by 0.1" in prompt_rules
    assert "response_type=emotional_support" in prompt_rules
    assert "one_concrete_next_step" in prompt_rules

    validated = loop.validate_decision(AuroraDecision(action="emit_message"), readout)
    contract = validated.chat_directive["standard_layer_contract"]
    assert validated.harness_updates["task_density_hint"] == pytest.approx(0.5)
    assert contract["response_type"] == "emotional_support"
    assert "one_concrete_next_step" in contract["must_include"]


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


@pytest.mark.asyncio
async def test_plan_turn_sets_sleep_guard_for_late_china_timestamp() -> None:
    decision_loop = _CapturingDecisionLoop()
    service = AuroraRuntimeV1Service(
        decision_loop=decision_loop,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_planning",
        conversation_id="conv-sleep",
        request_id="req-sleep-late",
        user_message="我还想再聊一会儿计划。",
        request_extra_context={
            "timestamp": "2026-04-25T23:30:00 CST",
            "sprint_policy": {"sleep_guard_hint": "保留睡眠和低负荷收尾窗口；晚间不追加新难点。"},
        },
        conversation_context={},
        user_context_payload={},
    )

    context = decision_loop.readouts[0].request_extra_context
    assert context["sleep_guard_active"] is True
    assert context["sleep_guard_hint"] == "保留睡眠和低负荷收尾窗口；晚间不追加新难点。"


@pytest.mark.asyncio
async def test_plan_turn_does_not_set_sleep_guard_for_daytime_china_timestamp() -> None:
    decision_loop = _CapturingDecisionLoop()
    service = AuroraRuntimeV1Service(
        decision_loop=decision_loop,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id="user-1",
        surface="aurora_planning",
        conversation_id="conv-sleep",
        request_id="req-sleep-day",
        user_message="上午继续看看计划。",
        request_extra_context={
            "timestamp": "2026-04-25T10:00:00+08:00",
            "sprint_policy": {"sleep_guard_hint": "晚间不追加新难点。"},
        },
        conversation_context={},
        user_context_payload={},
    )

    context = decision_loop.readouts[0].request_extra_context
    assert "sleep_guard_active" not in context
    assert "sleep_guard_hint" not in context


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


@pytest.mark.asyncio
async def test_chat_adapter_stuck_prompt_includes_sprint_pack_mistake_candidates() -> None:
    chat_llm = _FakeJsonLLM({"messages": ["先定位卡点。"]})
    adapter = ChatLayerAdapter(llm_factory=lambda: chat_llm)
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "diagnose_stuck_point"},
    )

    await adapter.render(
        decision,
        _readout(
            surface="aurora_planning",
            user_message="我不会做 TCP 状态机这道题。",
            task_state={"stage": "stuck", "stuck_topic": "TCP状态机"},
            checkpoint_state={
                "sprint_pack_id": "computer_networks@v1",
                "today_nodes": ["cn.tcp_three_way", "cn.tcp_four_way"],
            },
        ),
    )

    user_prompt = json.loads(chat_llm.calls[0][1]["content"])
    serialized_context = json.dumps(user_prompt["task_help_context"], ensure_ascii=False)
    assert user_prompt["task_help_context"]["micro_teaching"]["mode"] == "diagnose_then_targeted_fix"
    assert "candidate_mistake_types" in user_prompt["task_help_context"]
    assert "tcp_state_diagram" in serialized_context


@pytest.mark.asyncio
async def test_chat_adapter_system_prompt_includes_conversation_memory_when_summary_exists() -> None:
    chat_llm = _FakeJsonLLM({"messages": ["这和你前面提到的 TCP 状态机可以用同一种画状态图方法。"]})
    adapter = ChatLayerAdapter(llm_factory=lambda: chat_llm)
    messages = [
        {"role": "user", "content": "TCP状态机很难。"},
        {"role": "assistant", "content": "我们先拆状态和迁移。"},
        {"role": "user", "content": "目标是能做对连接管理选择题。"},
        {"role": "assistant", "content": "可以。"},
        {"role": "user", "content": "OSI 模型闭卷复述已经完成了。"},
        {"role": "assistant", "content": "收到。"},
    ]

    await adapter.render(
        AuroraDecision(action="emit_message", chat_directive={"intent": "teach_by_analogy"}),
        _readout(
            user_message="那拥塞控制怎么理解？",
            conversation_summary={"message_count": len(messages), "recent_messages": messages},
        ),
    )

    system_prompt = chat_llm.calls[0][0]["content"]
    assert "在适当时机自然地引用用户之前提到的具体内容" in system_prompt
    assert "## 对话记忆片段" in system_prompt
    assert "- 困难：TCP状态机" in system_prompt
    assert "- 已完成：OSI模型闭卷复述" in system_prompt
    assert "TCP状态机很难" not in system_prompt


def test_chat_adapter_system_prompt_stays_light_without_conversation_summary() -> None:
    adapter = ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": ["ok"]}))

    prompt = adapter._build_prompt(AuroraDecision(action="emit_message"), _readout())
    system_prompt = prompt[0]["content"]
    empty_history_prompt = adapter._build_prompt(
        AuroraDecision(action="emit_message"),
        _readout(conversation_summary={"message_count": 0, "recent_messages": []}),
    )[0]["content"]

    assert "在适当时机自然地引用用户之前提到的具体内容" not in system_prompt
    assert "## 对话记忆片段" not in system_prompt
    assert empty_history_prompt == system_prompt


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

    assert plan.messages == ["明天就考试了，现在看新章节的收益很低。建议先把你最容易丢分的 TCP 状态变化再过一遍。"]
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


def test_motivation_guidance_is_in_decision_loop_system_prompt() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))

    prompt = loop.build_prompt(
        _readout(
            covered_domains=["goal", "scope", "baseline", "time"],
            missing_domains=["motivation"],
        )
    )

    system_prompt = prompt[0]["content"]
    assert "motivation domain is optional" in system_prompt
    assert "value is '必须过'" in system_prompt
    assert "response_type=emotional_support" in system_prompt
    assert "safety margin" in system_prompt
    assert "value is '想拿高分'" in system_prompt
    assert "allow deep learn" in system_prompt


def test_motivation_must_pass_prefers_emotional_support_with_safety_margin() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "motivation_adjusted_reply"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            user_message="这次必须过。",
            covered_domains=["goal", "scope", "baseline", "time", "motivation"],
            missing_domains=[],
            request_extra_context={"motivation_context": "必须过"},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "emotional_support"
    assert "safety_margin" in contract["must_include"]


def test_motivation_high_score_prefers_task_help_and_deep_learn() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "motivation_adjusted_reply"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            user_message="我想拿高分。",
            covered_domains=["goal", "scope", "baseline", "time", "motivation"],
            missing_domains=[],
            request_extra_context={"motivation_context": "想拿高分"},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert contract["response_type"] == "task_help"
    assert "deep_learn_allowed" in contract["must_include"]


@pytest.mark.asyncio
async def test_motivation_fallback_question_uses_required_wording() -> None:
    adapter = ChatLayerAdapter(llm_factory=lambda: _FakeJsonLLM({"messages": []}))
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "ask_motivation", "target_domain": "motivation"},
    )

    messages = await adapter._fallback_messages(
        decision,
        _readout(
            covered_domains=["goal", "scope", "baseline", "time"],
            missing_domains=["motivation"],
        ),
    )

    assert messages == ["最后一个问题：这次考试对你来说意味着什么？是一定要过还是想尽量考高分？"]


def test_motivation_answer_marks_dashboard_domain_covered() -> None:
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
        user_message="必须过",
        request_extra_context={
            "informational_tensions": [
                {"domain": "goal", "status": "resolved"},
                {"domain": "scope", "status": "resolved"},
                {"domain": "baseline", "status": "resolved"},
                {"domain": "time", "status": "resolved"},
            ]
        },
        conversation_context={},
        user_context_payload={},
        control_surface_reading=reading,
        activity_profile={},
        candidate_affordances=[],
    )

    assert "motivation" in readout.covered_domains


@pytest.mark.asyncio
async def test_fast_track_planning_session_skips_motivation_after_core_fields(monkeypatch) -> None:
    from app.orchestration import bottleneck_analyzer as bottleneck_module

    async def _fail_bottleneck_analysis(**kwargs):
        raise RuntimeError("force deterministic fallback")

    monkeypatch.setattr(bottleneck_module.bottleneck_analyzer, "analyze", _fail_bottleneck_analysis)

    redis = _FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "aurora-planning-motivation"

    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，从来没学过，帮我规划一下",
        context={},
    )

    reply = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="每天2小时",
        context={},
    )

    state = await manager.runtime_adapter.load_state(user_id=str(user_id), conversation_id=conversation_id)
    persisted = await manager.get_active_session(conversation_id)
    assert reply is not None
    assert "这次考试对你来说意味着什么" not in reply["message"]
    assert persisted is not None
    assert persisted.state == "PLANNING"
    assert state is not None


@pytest.mark.asyncio
async def test_motivation_planning_state_covers_must_pass_answer() -> None:
    redis = _FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    state = await manager.runtime_adapter.get_or_create_state(
        user_id="user-motivation",
        conversation_id="conv-motivation",
        planning_session_id="plan-motivation",
        goal_raw="7天后考计算机网络",
        profile_context={},
        collected={
            "exam_scope": "传输层、网络层",
            "knowledge_baseline": "完全没学过",
            "time_available": "每天约 2 小时",
        },
    )

    updated = await manager.runtime_adapter.absorb_user_turn(
        state=state,
        db=None,  # type: ignore[arg-type]
        message="必须过",
        extracted_fields={"motivation_context": "必须过"},
        is_detour=False,
    )

    assert "motivation" in updated.covered_domains
    assert "motivation" not in updated.missing_domains


def test_motivation_context_adds_safety_margin_to_task_prompt() -> None:
    manager = PlanningWorkflowManager(redis_client=_FakeRedis())
    session = PlanningSession(
        planning_session_id="planning-motivation-prompt",
        chat_session_id="planning-motivation-prompt-chat",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "exam_scope": "传输层、网络层",
            "knowledge_baseline": "完全没学过",
            "time_available": "每天约 2 小时",
            "motivation_context": "必须过",
        },
    )

    prompt = manager._build_task_ai_prompt(
        session=session,
        phase={"label": "保底冲刺", "focus": "先拿高频必得分", "sprint_mode": "seven_day_survival"},
        guide_json={
            "minimum_output": "闭卷复述",
            "output_action": "先做 5 题探针",
            "micro_contract": "只推进一个最小动作",
            "fail_safe_rule": "只剩 20 分钟就回到错题",
            "objective": "稳住过线能力",
            "success_criteria": "能说清三栏清单",
        },
    )

    assert "【核心驱动】必须过" in prompt
    assert "保底规划" in prompt
    assert "安全边际" in prompt


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


def test_dashboard_readout_context_budget_masks_compact_more_aggressively() -> None:
    readout = _readout(
        surface="aurora_planning",
        wake_policy={"context_budget": "compact"},
        task_state={"stage": "task_card", "current_error": "tcp-handshake"},
        conversation_summary={"message_count": 8},
    )

    compact_payload = readout.to_llm_payload(context_budget="compact")
    extended_payload = readout.to_llm_payload(context_budget="extended")

    assert set(compact_payload) == {"user_message", "task_state", "wake_policy"}
    assert len(compact_payload) <= 5
    assert len(extended_payload) >= 10
    assert len(compact_payload) < len(extended_payload)


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


def test_slim_readout_for_compact_budget_keeps_only_high_signal_fields() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(
        surface="aurora_planning",
        wake_policy={"context_budget": "compact"},
        task_state={"stage": "task_card", "current_error": "tcp-handshake"},
        request_extra_context={"surface_state": {"in_detour": True}},
    )
    readout.informational_tensions = [
        {"domain": "baseline", "status": "open"},
        {"domain": "time", "status": "open"},
        {"domain": "scope", "status": "open"},
    ]

    payload = loop._slim_readout_for_surface(readout)

    assert set(payload) == {"user_message", "task_state", "informational_tensions", "wake_policy"}
    assert len(payload["informational_tensions"]) == 2
    assert "surface_state" not in payload
    assert "covered_domains" not in payload
    assert "cold_start_context" not in payload
    assert "sprint_policy_summary" not in payload


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


@pytest.mark.asyncio
async def test_plan_turn_updates_galaxy_mastery_for_correct_answer_node() -> None:
    galaxy_service = _FakeGalaxyService()
    service = AuroraRuntimeV1Service(
        decision_loop=_StaticDecisionLoop(
            AuroraDecision(
                action="emit_message",
                state_updates={"correct_answer_node": "cn.tcp_handshake"},
                chat_directive={"intent": "completion_check"},
            )
        ),
        chat_adapter=_StaticChatAdapter(),
        galaxy_service=galaxy_service,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id=str(uuid4()),
        surface="aurora_modeling",
        conversation_id="conv-correct-answer",
        request_id="req-correct-answer",
        user_message="SYN，SYN+ACK，ACK。",
        request_extra_context={
            "cold_start_context": {
                "goal_type": "exam",
                "sprint_pack_nodes": ["cn.tcp_handshake"],
                "galaxy_mastery": {"cn.tcp_handshake": 0.4},
            }
        },
        conversation_context={},
        user_context_payload={},
    )

    assert len(galaxy_service.mastery_updates) == 1
    update = galaxy_service.mastery_updates[0]
    assert update["node_id"] == "cn.tcp_handshake"
    assert update["new_mastery"] == pytest.approx(0.55)
    assert update["reason"] == "aurora_completion_check_correct"


@pytest.mark.asyncio
async def test_plan_turn_dedupes_correct_answer_node_per_turn() -> None:
    galaxy_service = _FakeGalaxyService()
    service = AuroraRuntimeV1Service(
        decision_loop=_StaticDecisionLoop(
            AuroraDecision(
                action="emit_message",
                state_updates={
                    "correct_answer_node": ["cn.tcp_handshake", "cn.tcp_handshake"],
                    "correct_answer_nodes": ["cn.tcp_handshake"],
                },
                chat_directive={"intent": "completion_check"},
            )
        ),
        chat_adapter=_StaticChatAdapter(),
        galaxy_service=galaxy_service,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id=str(uuid4()),
        surface="aurora_modeling",
        conversation_id="conv-dedupe",
        request_id="req-dedupe",
        user_message="三次握手是 SYN、SYN ACK、ACK。",
        request_extra_context={
            "cold_start_context": {
                "goal_type": "exam",
                "sprint_pack_nodes": ["cn.tcp_handshake"],
            }
        },
        conversation_context={},
        user_context_payload={},
    )

    assert len(galaxy_service.mastery_updates) == 1
    assert galaxy_service.mastery_updates[0]["new_mastery"] == pytest.approx(0.15)


@pytest.mark.asyncio
async def test_plan_turn_skips_correct_answer_node_outside_sprint_pack() -> None:
    galaxy_service = _FakeGalaxyService()
    service = AuroraRuntimeV1Service(
        decision_loop=_StaticDecisionLoop(
            AuroraDecision(
                action="emit_message",
                state_updates={"correct_answer_node": "cn.hallucinated_node"},
                chat_directive={"intent": "completion_check"},
            )
        ),
        chat_adapter=_StaticChatAdapter(),
        galaxy_service=galaxy_service,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id=str(uuid4()),
        surface="aurora_modeling",
        conversation_id="conv-skip",
        request_id="req-skip",
        user_message="我答对了。",
        request_extra_context={
            "cold_start_context": {
                "goal_type": "exam",
                "sprint_pack_nodes": ["cn.tcp_handshake"],
            }
        },
        conversation_context={},
        user_context_payload={},
    )

    assert galaxy_service.mastery_updates == []


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
    assert signals["recently_unlocked"] is True
    assert signals["streak_active"] is False


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
    assert signals["streak_active"] is True


def test_extract_achievement_signals_derives_streak_and_recent_unlock_flags() -> None:
    builder = DashboardReadoutBuilder()

    signals = builder._extract_achievement_signals(
        {
            "achievement_signals": {
                "momentum": 0.85,
                "recently_unlocked": True,
                "active_streaks": ["daily_study"],
            }
        },
        {},
    )

    assert signals["streak_active"] is True
    assert signals["recently_unlocked"] is True


def test_extract_achievement_signals_derives_current_streak_and_gap_from_user_context() -> None:
    builder = DashboardReadoutBuilder()

    signals = builder._extract_achievement_signals(
        {},
        {
            "achievement": {
                "streak": {
                    "current_streak": "6",
                    "gap_since_last_study_days": "4",
                }
            }
        },
    )

    assert signals["current_streak_days"] == 6
    assert signals["gap_since_last_study_days"] == 4
    assert signals["streak_active"] is True


def test_extract_cold_start_context_injects_redis_weak_node_claim() -> None:
    redis = _FakeRedis()
    user_id = "dashboard-user"
    node_id = "node-tcp-three-way"
    key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="weak_node")
    redis.store[key] = json.dumps(
        {
            "user_id": user_id,
            "domain": "weak_node",
            "claims": [
                {
                    "domain": "weak_node",
                    "value": node_id,
                    "status": "confirmed",
                    "evidence_type": "error_replan_signal",
                }
            ],
        },
        ensure_ascii=False,
    )

    context = DashboardReadoutBuilder()._extract_cold_start_context(
        {"cold_start_context": {"goal_type": "exam"}},
        {},
        user_id=user_id,
        redis_client=redis,
    )

    assert context["goal_type"] == "exam"
    assert context["confirmed_weak_nodes"] == [node_id]


@pytest.mark.asyncio
async def test_plan_turn_loads_redis_weak_node_claim_into_readout() -> None:
    redis = _FakeRedis()
    decision_loop = _CapturingDecisionLoop()
    user_id = "runtime-user"
    node_id = "node-congestion-control"
    key = AURORA_CLAIM_KEY_TEMPLATE.format(user_id=user_id, domain="weak_node")
    redis.store[key] = json.dumps(
        {
            "user_id": user_id,
            "domain": "weak_node",
            "values": [node_id],
            "claims": [{"domain": "weak_node", "value": node_id, "status": "confirmed"}],
        },
        ensure_ascii=False,
    )
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=decision_loop,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id=user_id,
        surface="aurora_modeling",
        conversation_id="conv-weak-node",
        request_id="req-weak-node",
        user_message="继续帮我复习。",
        request_extra_context={},
        conversation_context={},
        user_context_payload={"profile_context": {"cold_start_context": {"goal_type": "exam"}}},
    )

    assert decision_loop.readouts[0].cold_start_context["confirmed_weak_nodes"] == [node_id]


@pytest.mark.asyncio
async def test_plan_turn_injects_strategy_recalibration_from_stale_telemetry() -> None:
    redis = _FakeRedis()
    decision_loop = _CapturingDecisionLoop()
    user_id = "runtime-user"
    conversation_id = "conv-stale-strategy"
    key = AuroraDecisionTelemetryService.recent_telemetry_key(
        user_id=user_id,
        conversation_id=conversation_id,
    )
    for request_id in ("req-1", "req-2", "req-3"):
        await redis.lpush(
            key,
            json.dumps(
                {
                    "request_id": request_id,
                    "response_type": "task_help",
                    "target_domain": "tcp",
                    "covered_domains": ["goal", "scope"],
                },
                ensure_ascii=False,
            ),
        )
    service = AuroraRuntimeV1Service(
        redis_client=redis,
        decision_loop=decision_loop,
        self_model_service=_StubSelfModelService(),
    )

    await service.plan_turn(
        active_db=None,
        user_id=user_id,
        surface="aurora_modeling",
        conversation_id=conversation_id,
        request_id="req-4",
        user_message="我还是卡在 TCP。",
        request_extra_context={},
        conversation_context={},
        user_context_payload={},
    )

    context = decision_loop.readouts[0].request_extra_context
    assert context["strategy_recalibration_needed"] is True
    assert context["stuck_domain"] == "tcp"


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


def test_decision_loop_prompt_includes_sleep_guard_rule_when_active() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    hint = "保留睡眠和低负荷收尾窗口；晚间不追加新难点。"
    readout = _readout(request_extra_context={"sleep_guard_active": True, "sleep_guard_hint": hint})

    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])

    sleep_guard_rules = [rule for rule in prompt_payload["rules"] if "睡眠守卫激活" in rule]
    assert sleep_guard_rules
    assert hint in sleep_guard_rules[0]
    assert prompt_payload["chat_directive_constraints"]["must_not_include"] == [
        "full_week_replan",
        "three_practice_questions",
    ]


def test_decision_loop_prompt_includes_strategy_recalibration_system_rule() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    readout = _readout(request_extra_context={"strategy_recalibration_needed": True, "stuck_domain": "tcp"})

    messages = loop.build_prompt(readout)
    prompt_payload = json.loads(messages[1]["content"])

    assert "当前策略已失效（连续 3 轮相同策略）" in messages[0]["content"]
    assert "必须切换到不同的 response_type 和不同的教学策略" in messages[0]["content"]
    assert any("stuck_domain=tcp" in rule for rule in prompt_payload["rules"])


def test_decision_loop_prompt_instructs_correct_answer_node_writeback() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))

    messages = loop.build_prompt(_readout())

    assert "state_updates.correct_answer_node" in messages[0]["content"]
    assert "cold_start_context.sprint_pack_nodes" in messages[0]["content"]


def test_validate_decision_normalizes_correct_answer_node_mapping() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))

    decision = loop.validate_decision(
        AuroraDecision(
            action="emit_message",
            state_updates={"correct_answer_node": {"node_id": "cn.tcp_handshake"}},
        ),
        _readout(),
    )

    assert decision.state_updates["correct_answer_node"] == "cn.tcp_handshake"


def test_sleep_guard_contract_blocks_full_replan_and_three_question_drill() -> None:
    loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
    decision = AuroraDecision(action="emit_message", chat_directive={"intent": "teach_with_example"})

    validated = loop.validate_decision(
        decision,
        _readout(
            surface="aurora_planning",
            task_state={"stage": "task_card", "current_task_id": "tcp-1"},
            request_extra_context={"sleep_guard_active": True, "sleep_guard_hint": "晚间不追加新难点。"},
        ),
    )

    contract = validated.chat_directive["standard_layer_contract"]
    assert "full_week_replan" in contract["must_not_include"]
    assert "three_practice_questions" in contract["must_not_include"]
    assert "three_practice_questions" not in contract["must_include"]
    assert contract["max_response_length"] == "brief"


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


# ---------------------------------------------------------------------------
# F18: Sprint Pack auto-detection + injection tests
# ---------------------------------------------------------------------------


def _build_readout_via_builder(
    *,
    goal_type: str = "exam",
    subject: str = "计算机网络",
    surface: str = "aurora_modeling",
    user_message: str = "我要备考计算机网络",
) -> DashboardReadout:
    """Build a DashboardReadout via DashboardReadoutBuilder with minimal stubs."""
    from app.aurora.runtime_v1.control_surface import ControlSurfaceReading

    builder = DashboardReadoutBuilder(redis_client=None)
    profile_context: dict[str, Any] = {
        "cold_start_context": {"goal_type": goal_type, "subject": subject},
    }
    return builder.build(
        surface=surface,
        user_id="user-f18",
        conversation_id="conv-f18",
        request_id="req-f18",
        user_message=user_message,
        request_extra_context={},
        conversation_context={"messages": []},
        user_context_payload={"profile_context": profile_context},
        control_surface_reading=ControlSurfaceReading(
            runtime_enabled=True,
            hard_bounds=AuroraHardBounds(),
            adjustable=ActivityProfile(),
        ),
        activity_profile={"conversation_style": "warm"},
        candidate_affordances=[],
    )


class TestSprintPackAutoInjection:
    """F18: Sprint Pack auto-detection and injection into cold_start_context."""

    def test_pack_found_injects_minimum_output(self) -> None:
        """When goal_type=exam and subject=计算机网络, sprint_pack_minimum_output is injected."""
        readout = _build_readout_via_builder(subject="计算机网络")
        csc = readout.cold_start_context
        assert (
            "sprint_pack_minimum_output" in csc
        ), f"sprint_pack_minimum_output missing from cold_start_context, got keys: {sorted(csc.keys())}"
        assert "闭卷输出" in csc["sprint_pack_minimum_output"]

    def test_pack_found_injects_aurora_hint(self) -> None:
        """sprint_pack_aurora_hint is injected from aurora_rules.medium_aurora."""
        readout = _build_readout_via_builder(subject="计算机网络")
        csc = readout.cold_start_context
        assert "sprint_pack_aurora_hint" in csc, f"sprint_pack_aurora_hint missing, got keys: {sorted(csc.keys())}"
        assert "触发条件" in csc["sprint_pack_aurora_hint"]
        assert "介入动作" in csc["sprint_pack_aurora_hint"]

    def test_no_pack_no_error(self) -> None:
        """When subject has no matching pack, no fields are injected and no error occurs."""
        readout = _build_readout_via_builder(subject="物理")
        csc = readout.cold_start_context
        assert "sprint_pack_minimum_output" not in csc
        assert "sprint_pack_aurora_hint" not in csc

    def test_non_exam_goal_type_skips_injection(self) -> None:
        """When goal_type is not 'exam', sprint pack is not loaded."""
        readout = _build_readout_via_builder(goal_type="skill_building", subject="计算机网络")
        csc = readout.cold_start_context
        assert "sprint_pack_minimum_output" not in csc
        assert "sprint_pack_aurora_hint" not in csc

    def test_empty_subject_skips_injection(self) -> None:
        """When subject is empty, sprint pack is not loaded."""
        readout = _build_readout_via_builder(subject="")
        csc = readout.cold_start_context
        assert "sprint_pack_minimum_output" not in csc

    def test_prompt_contains_aurora_hint(self) -> None:
        """build_prompt() system message includes sprint_pack_aurora_hint content."""
        readout = _build_readout_via_builder(subject="计算机网络")
        loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
        messages = loop.build_prompt(readout)
        system_msg = messages[0]["content"]
        assert "Sprint Pack自适应提示" in system_msg
        assert "触发条件" in system_msg

    def test_prompt_no_aurora_hint_without_pack(self) -> None:
        """build_prompt() system message does not include hint when no pack is loaded."""
        readout = _build_readout_via_builder(subject="物理")
        loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
        messages = loop.build_prompt(readout)
        system_msg = messages[0]["content"]
        assert "Sprint Pack自适应提示" not in system_msg


# ---------------------------------------------------------------------------
# F20: Aurora checkpoint Sprint Pack mistake detection
# ---------------------------------------------------------------------------


class TestSprintPackMistakeInjection:
    """F20: Sprint Pack mistake types are injected into checkpoint_state."""

    def _build_checkpoint_readout(
        self,
        *,
        sprint_pack_id: str = "computer_networks@v1",
        today_nodes: list[str] | None = None,
    ) -> DashboardReadout:
        """Build a DashboardReadout via builder with checkpoint_state populated."""
        from app.aurora.runtime_v1.control_surface import ControlSurfaceReading

        builder = DashboardReadoutBuilder(redis_client=None)
        checkpoint_state: dict[str, Any] = {}
        if sprint_pack_id:
            checkpoint_state["sprint_pack_id"] = sprint_pack_id
        if today_nodes is not None:
            checkpoint_state["today_nodes"] = today_nodes
        return builder.build(
            surface="aurora_checkpoint",
            user_id="user-f20",
            conversation_id="conv-f20",
            request_id="req-f20",
            user_message="我刚学了 TCP 流量控制",
            request_extra_context={"checkpoint_state": checkpoint_state},
            conversation_context={"messages": []},
            user_context_payload={},
            control_surface_reading=ControlSurfaceReading(
                runtime_enabled=True,
                hard_bounds=AuroraHardBounds(),
                adjustable=ActivityProfile(),
            ),
            activity_profile={"conversation_style": "warm"},
            candidate_affordances=[],
        )

    def test_mistakes_injected_for_matching_nodes(self) -> None:
        """When sprint_pack_id and today_nodes match, sprint_pack_mistakes is populated."""
        readout = self._build_checkpoint_readout(today_nodes=["cn.tcp_flow_control"])
        mistakes = readout.checkpoint_state.get("sprint_pack_mistakes")
        assert mistakes, "Expected sprint_pack_mistakes to be non-empty for cn.tcp_flow_control"
        assert isinstance(mistakes, list)
        # cn.tcp_flow_control has related mistakes: window_variable_confusion, flow_congestion_confusion
        mistake_ids = [m.get("mistake_id") for m in mistakes]
        assert "mistake.window_variable_confusion" in mistake_ids

    def test_mistakes_limited_to_five(self) -> None:
        """sprint_pack_mistakes is capped at 5 entries."""
        readout = self._build_checkpoint_readout(
            today_nodes=[
                "cn.osi_model",
                "cn.tcp_ip_model",
                "cn.protocol_stack_concepts",
                "cn.tcp_flow_control",
                "cn.tcp_congestion_control",
                "cn.subnetting",
            ],
        )
        mistakes = readout.checkpoint_state.get("sprint_pack_mistakes", [])
        assert len(mistakes) <= 5

    def test_no_mistakes_without_sprint_pack_id(self) -> None:
        """When sprint_pack_id is absent, sprint_pack_mistakes is not injected."""
        readout = self._build_checkpoint_readout(sprint_pack_id="", today_nodes=["cn.tcp_flow_control"])
        assert "sprint_pack_mistakes" not in readout.checkpoint_state

    def test_no_mistakes_without_today_nodes(self) -> None:
        """When today_nodes is absent, sprint_pack_mistakes is not injected."""
        readout = self._build_checkpoint_readout(today_nodes=None)
        assert "sprint_pack_mistakes" not in readout.checkpoint_state

    def test_no_mistakes_for_unknown_pack(self) -> None:
        """When sprint_pack_id has no matching pack, sprint_pack_mistakes is not injected."""
        readout = self._build_checkpoint_readout(
            sprint_pack_id="quantum_physics@v1",
            today_nodes=["qp.superposition"],
        )
        assert "sprint_pack_mistakes" not in readout.checkpoint_state

    def test_error_analysis_required_when_mistakes_present(self) -> None:
        """_strategy_defaults_for_readout forces error_analysis_required=True when sprint_pack_mistakes is non-empty."""
        loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
        readout = _readout(
            surface="aurora_checkpoint",
            checkpoint_state={
                "sprint_pack_id": "computer_networks@v1",
                "today_nodes": ["cn.tcp_flow_control"],
                "sprint_pack_mistakes": [
                    {"mistake_id": "mistake.window_variable_confusion", "label": "混淆 rwnd 与 cwnd"}
                ],
            },
        )
        defaults = loop._strategy_defaults_for_readout(readout)
        assert defaults["error_analysis_required"] is True

    def test_error_analysis_not_forced_without_mistakes(self) -> None:
        """_strategy_defaults_for_readout does not force error_analysis_required when sprint_pack_mistakes is empty."""
        loop = AuroraDecisionLoop(llm_factory=lambda: _FakeJsonLLM({}))
        readout = _readout(
            surface="aurora_modeling",
            checkpoint_state={"last_status": "stable"},
        )
        defaults = loop._strategy_defaults_for_readout(readout)
        # aurora_modeling defaults concept_first=True but error_analysis_required stays default (False)
        assert defaults["concept_first"] is True
        assert defaults["error_analysis_required"] is False
