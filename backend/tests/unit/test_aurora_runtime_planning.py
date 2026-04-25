from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.aurora.runtime_v1 import AuroraRuntimePlanningAdapter
from app.aurora.runtime_v1.service import AuroraRuntimeV1Service
from app.aurora.runtime_v1.chat_adapter import ChatLayerAdapter
from app.aurora.runtime_v1.control_surface import ActivityProfile, AuroraHardBounds, ControlSurfaceReading
from app.aurora.runtime_v1.dashboard import DashboardReadoutBuilder
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.orchestration.planning_workflow import PlanningSession, PlanningWorkflowManager


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_sprint_pack_first_question_skips_scope_and_asks_baseline() -> None:
    redis = FakeRedis()
    adapter = AuroraRuntimePlanningAdapter(redis_client=redis)

    state = await adapter.get_or_create_state(
        user_id="user-fast-track-first-question",
        conversation_id="aurora-planning-pack-first-question",
        planning_session_id="planning-pack-first-question",
        goal_raw="7天后考计算机网络",
        profile_context={},
        collected={
            "subject": "计算机网络",
            "sprint_pack_id": "computer_networks@v1",
            "sprint_pack_subject": "计算机网络",
            "fast_track_exam_sprint": True,
        },
    )

    prompt, domain = adapter.build_next_prompt(state)

    assert domain == "knowledge_baseline"
    assert "计算机网络" in prompt
    assert "Sprint Pack" in prompt
    assert "水平" in prompt


@pytest.mark.asyncio
async def test_detour_keeps_latent_thread_for_planning_surface() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "aurora-planning-detour"

    first_turn = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )

    detour_turn = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="先帮我查一下这个任务完成没有",
        context={},
    )

    state = await manager.runtime_adapter.load_state(user_id=str(user_id), conversation_id=conversation_id)
    scaffold = manager.runtime_adapter.build_detour_scaffold(state) if state is not None else {}

    assert first_turn is not None
    assert detour_turn is not None and detour_turn["bypass_planning"] is True
    assert state is not None
    assert scaffold["top_tension"]["domain"] in {"exam_scope", "knowledge_baseline", "time_available"}
    assert scaffold["top_latent_thread"] is not None
    assert "Treat this as state context, not final user wording." in (scaffold.get("detour_instruction") or "")
    assert state.surface == "aurora_planning"
    assert any(thread.status == "active" for thread in state.latent_threads)
    assert state.activity_profile.agenda_priority in {"exam_scope", "knowledge_baseline", "time_available"}


@pytest.mark.asyncio
async def test_detour_decision_can_wait_soft_return_or_drop_thread() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "aurora-planning-detour-decision"

    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )
    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="先帮我查一下这个任务完成没有",
        context={},
    )

    state = await manager.runtime_adapter.load_state(user_id=str(user_id), conversation_id=conversation_id)
    assert state is not None

    wait_state = await manager.runtime_adapter.apply_detour_decision(
        state=state,
        db=None,  # type: ignore[arg-type]
        action="wait",
        chat_directive={"intent": "handle_current_task_first"},
    )
    assert wait_state.current_intent["intent_type"] == "wait"
    assert any(thread.status == "active" for thread in wait_state.latent_threads)

    soft_return_state = await manager.runtime_adapter.apply_detour_decision(
        state=wait_state,
        db=None,  # type: ignore[arg-type]
        action="soft_return_topic",
        chat_directive={"intent": "recover_planning_naturally"},
    )
    top_tension = manager.runtime_adapter.select_next_tension(soft_return_state)
    assert soft_return_state.current_intent["intent_type"] == "soft_return"
    assert top_tension is not None and top_tension.last_attempted_at is not None

    dropped_state = await manager.runtime_adapter.apply_detour_decision(
        state=soft_return_state,
        db=None,  # type: ignore[arg-type]
        action="drop_thread",
        chat_directive={"intent": "drop_stale_followup"},
    )
    assert dropped_state.current_intent["intent_type"] == "drop_thread"
    assert not any(thread.status == "active" for thread in dropped_state.latent_threads)


@pytest.mark.asyncio
async def test_user_supplied_info_resolves_tension_without_reasking_same_domain() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    user_id = uuid4()
    conversation_id = "aurora-planning-fill-gap"

    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )

    await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="考传输层、网络层和应用层",
        context={},
    )

    reply = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=user_id,
        chat_session_id=conversation_id,
        message="我是零基础",
        context={},
    )

    state = await manager.runtime_adapter.load_state(user_id=str(user_id), conversation_id=conversation_id)
    scaffold = manager.runtime_adapter.build_detour_scaffold(state) if state is not None else {}

    assert reply is not None
    assert "每天大概能投入多少时间" in reply["message"]
    assert "基础大概在哪个位置" not in reply["message"]
    assert state is not None
    assert scaffold["top_tension"]["domain"] == "time_available"
    assert all(item["domain"] != "knowledge_baseline" for item in scaffold["open_tensions"])
    baseline_tension = next(item for item in state.informational_tensions if item.domain == "knowledge_baseline")
    time_tension = next(item for item in state.informational_tensions if item.domain == "time_available")
    assert baseline_tension.status == "resolved"
    assert time_tension.status == "open"


def test_dashboard_covers_goal_scope_and_baseline_from_natural_two_turn_modeling() -> None:
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
        user_message="我完全没学过，想考传输层和网络层",
        request_extra_context={
            "informational_tensions": [
                {"domain": "scope", "status": "open"},
                {"domain": "baseline", "status": "open"},
                {"domain": "time", "status": "open"},
            ]
        },
        conversation_context={"messages": [{"role": "user", "content": "7天后考计算机网络，帮我规划一下"}]},
        user_context_payload={},
        control_surface_reading=reading,
        activity_profile={},
        candidate_affordances=[],
    )

    assert {"goal", "scope", "baseline"}.issubset(set(readout.covered_domains))
    assert "time" in readout.missing_domains


@pytest.mark.asyncio
async def test_chat_fallback_uses_natural_transition_after_zero_baseline_and_scope() -> None:
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
        user_message="我完全没学过，想考传输层和网络层",
        request_extra_context={
            "informational_tensions": [
                {"domain": "scope", "status": "open"},
                {"domain": "baseline", "status": "open"},
                {"domain": "time", "status": "open"},
            ]
        },
        conversation_context={"messages": [{"role": "user", "content": "7天后考计算机网络，帮我规划一下"}]},
        user_context_payload={},
        control_surface_reading=reading,
        activity_profile={},
        candidate_affordances=[],
    )
    decision = AuroraDecision(
        action="emit_message",
        chat_directive={"intent": "ask_baseline", "target_domain": "baseline"},
    )

    messages = await ChatLayerAdapter()._fallback_messages(decision, readout)

    assert messages
    assert "好，零基础的话，咱们" in messages[0]
    assert "请告诉我你的基础" not in messages[0]
    assert "每天大概能拿出多少时间" in messages[0]


@pytest.mark.asyncio
async def test_review_node_context_generates_first_turn_targeted_review_task() -> None:
    service = AuroraRuntimeV1Service()

    plan = await service.plan_turn(
        active_db=None,
        user_id="review-user",
        surface="chat",
        conversation_id="review-conversation",
        request_id="review-request",
        user_message="带我复习 TCP 流量控制",
        request_extra_context={
            "review_node": "cn.tcp_flow",
            "node_label": "TCP 流量控制",
        },
        conversation_context={},
        user_context_payload={},
    )

    assert plan.messages
    assert "TCP 流量控制" in plan.messages[0]
    assert "15 分钟" in plan.messages[0]
    assert "短检查点" in plan.messages[0]


@pytest.mark.asyncio
async def test_strategy_and_task_prompt_consume_richer_aurora_runtime_state() -> None:
    redis = FakeRedis()
    manager = PlanningWorkflowManager(redis_client=redis)
    session = PlanningSession(
        planning_session_id="planning-runtime-rich",
        chat_session_id="planning-runtime-rich-chat",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划",
        collected={
            "time_constraint_days": 7,
            "daily_available_hours": 2,
            "subject": "计算机网络",
            "exam_scope": "考传输层、网络层、应用层",
            "knowledge_baseline": "完全没学过",
            "time_available": "每天约 2 小时",
            "available_materials": ["真题", "课件"],
            "blocked_days": ["周三下午有实验"],
        },
    )

    state = await manager.runtime_adapter.get_or_create_state(
        user_id=session.user_id,
        conversation_id=session.chat_session_id,
        planning_session_id=session.planning_session_id,
        goal_raw=session.goal_raw,
        profile_context={},
        collected=session.collected,
    )

    strategy = manager._build_strategy(session, aurora_state=state)
    daily_specs = manager._daily_task_specs(strategy["phases"][0], phase_index=1)
    guide_json = manager._build_task_guide_json(
        session=session,
        phase=strategy["phases"][0],
        phase_index=1,
        default_daily_hours=2,
        day_number=daily_specs[0]["day"],
        day_focus=daily_specs[0]["focus"],
        day_spec=daily_specs[0],
        aurora_state=state,
    )
    task_prompt = manager._build_task_ai_prompt(
        session=session,
        phase=strategy["phases"][0],
        guide_json=guide_json,
        aurora_state=state,
    )

    assert strategy["user_context_digest"]["available_materials"] == ["真题", "课件"]
    assert strategy["sprint_policy"]["sprint_mode"] == "seven_day_survival"
    assert strategy["sprint_policy"]["retrieval_policy"]["allow_deep_learn"] is False
    assert any("defer_or_skip" in note for note in strategy["strategy_notes"])
    assert daily_specs[0]["task_kind"] == "diagnostic_triage"
    assert daily_specs[0]["estimated_minutes"] <= 55
    assert guide_json["retrieval_first"] is True
    assert guide_json["output_action"].startswith("先做 5 题探针")
    assert "三栏清单" in guide_json["success_criteria"]
    assert "探针" in guide_json["micro_contract"]
    assert guide_json["why_now"]
    assert "只剩 20 分钟" in guide_json["fail_safe_rule"]
    assert "有三栏清单" in guide_json["success_checklist"][0]
    assert len(guide_json["steps"]) == 4
    assert len(guide_json["done_criteria"]) >= 3
    assert len(guide_json["mini_quiz"]["items"]) == 3
    assert len(guide_json["fallback_if_stuck"]) >= 2
    assert any("闭卷" in step or "小测" in step or "复述" in step for step in guide_json["method_steps"])
    assert "周三下午有实验" in strategy["checkpoints"][0]["description"]
    assert "真题" in strategy["phases"][0]["method"]
    assert "手头资料包括：真题、课件" in task_prompt
    assert "已知忙碌时段：周三下午有实验" in task_prompt
    assert "闭卷" in task_prompt
    assert "今天的输出动作" in task_prompt
    assert "失手时降压规则" in task_prompt


def test_fourteen_day_strategy_uses_build_and_spaced_retrieval_mode() -> None:
    manager = PlanningWorkflowManager(redis_client=FakeRedis())
    session = PlanningSession(
        planning_session_id="planning-runtime-14-day",
        chat_session_id="planning-runtime-14-day-chat",
        user_id=str(uuid4()),
        state="CLARIFYING",
        goal_raw="14天后考操作系统，帮我规划",
        collected={
            "time_constraint_days": 14,
            "daily_available_hours": 3,
            "subject": "操作系统",
            "exam_scope": "进程、内存、文件系统",
            "knowledge_baseline": "学过一些",
            "time_available": "每天约 3 小时",
            "available_materials": ["课件"],
        },
    )

    strategy = manager._build_strategy(session)
    phase_two_specs = manager._daily_task_specs(strategy["phases"][1], phase_index=2)
    deep_learn_spec = phase_two_specs[0]
    guide_json = manager._build_task_guide_json(
        session=session,
        phase=strategy["phases"][1],
        phase_index=2,
        default_daily_hours=3,
        day_number=deep_learn_spec["day"],
        day_focus=deep_learn_spec["focus"],
        day_spec=deep_learn_spec,
    )

    assert strategy["sprint_policy"]["sprint_mode"] == "fourteen_day_build_and_retrieve"
    assert strategy["sprint_policy"]["retrieval_policy"]["spaced_retrieval"] == "multi_day_successive_relearning"
    assert strategy["sprint_policy"]["retrieval_policy"]["allow_deep_learn"] is True
    assert any("deep learn" in note for note in strategy["strategy_notes"])
    assert deep_learn_spec["task_kind"] == "deep_learn_retrieval"
    assert any(spec["task_kind"] == "spaced_retrieval" for spec in phase_two_specs)
    assert all("阅读完成" not in spec["focus"] for spec in phase_two_specs)
    assert "limited deep learn" in deep_learn_spec["focus"]
    assert "先复测 6 个旧点" in guide_json["output_action"]
    assert "旧点至少 4/6 可提取" in guide_json["success_criteria"]
    assert "旧点没过，不追加第二个新难点" in guide_json["micro_contract"]
    assert guide_json["why_now"]
    assert guide_json["time_estimate_minutes"] >= 45


@pytest.mark.asyncio
async def test_planning_runtime_state_isolated_from_other_surfaces() -> None:
    redis = FakeRedis()
    adapter = AuroraRuntimePlanningAdapter(redis_client=redis)

    planning_state = await adapter.get_or_create_state(
        user_id="user-1",
        conversation_id="shared-conv",
        planning_session_id="planning-session",
        goal_raw="帮我做规划",
        profile_context={},
        collected={"knowledge_baseline": "完全没学过"},
    )

    modeling_key = adapter.runtime_key(user_id="user-1", conversation_id="shared-conv", surface="aurora_modeling")
    checkpoint_key = adapter.runtime_key(user_id="user-1", conversation_id="shared-conv", surface="aurora_checkpoint")
    await redis.setex(
        modeling_key,
        60,
        json.dumps(
            {
                **planning_state.to_dict(),
                "surface": "aurora_modeling",
                "user_model_snapshot": {"knowledge_baseline": "建模面里的值"},
            },
            ensure_ascii=False,
        ),
    )
    await redis.setex(
        checkpoint_key,
        60,
        json.dumps(
            {
                **planning_state.to_dict(),
                "surface": "aurora_checkpoint",
                "user_model_snapshot": {"knowledge_baseline": "checkpoint 面里的值"},
            },
            ensure_ascii=False,
        ),
    )

    reloaded = await adapter.load_state(user_id="user-1", conversation_id="shared-conv")

    assert modeling_key != adapter.runtime_key(user_id="user-1", conversation_id="shared-conv")
    assert checkpoint_key != adapter.runtime_key(user_id="user-1", conversation_id="shared-conv")
    assert reloaded is not None
    assert reloaded.surface == "aurora_planning"
    assert reloaded.user_model_snapshot["knowledge_baseline"] == "完全没学过"


def test_mastery_to_difficulty_mastery_buckets() -> None:
    fn = PlanningWorkflowManager._mastery_to_difficulty
    # Mastery-based buckets
    assert fn(10.0, 0) == 5   # < 20  → hardest
    assert fn(20.0, 0) == 4   # 20-39
    assert fn(39.9, 0) == 4
    assert fn(40.0, 0) == 3   # 40-59
    assert fn(59.9, 0) == 3
    assert fn(60.0, 0) == 2   # 60-79
    assert fn(79.9, 0) == 2
    assert fn(80.0, 0) == 1   # ≥ 80  → easiest
    assert fn(100.0, 0) == 1


def test_mastery_to_difficulty_phase_fallback() -> None:
    fn = PlanningWorkflowManager._mastery_to_difficulty
    # No mastery → phase-index formula: min(5, 2 + phase_index)
    assert fn(None, 0) == 2
    assert fn(None, 1) == 3
    assert fn(None, 2) == 4
    assert fn(None, 3) == 5
    assert fn(None, 10) == 5   # capped at 5
