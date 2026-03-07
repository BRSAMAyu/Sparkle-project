from types import SimpleNamespace

from app.orchestration.ux_envelope import ux_envelope_builder
from app.orchestration.schemas import RouteDecision
from app.orchestration.statechart_engine import WorkflowState


def test_ux_envelope_builder_returns_core_sections() -> None:
    final_state = WorkflowState(
        messages=[
            {"role": "user", "content": "帮我做一份下周的学习计划"},
            {"role": "assistant", "content": "好的，我先帮你拆目标。"},
        ],
        context_data={
            "chat_mode": "study_plan",
            "selected_experts": ["galaxy_guide", "time_tutor"],
            "dual_core_decision": {
                "mode": "execution_first",
                "reason": "目标清晰且没有明显阻塞，适合直接推进执行路径。",
            },
            "plan_context": {"plan_id": "plan-1", "plan_name": "考研冲刺"},
            "conversation_context": {"messages": [{"role": "user", "content": "昨天我们聊过节奏安排"}]},
            "include_references": True,
            "file_ids": ["file-1"],
            "adaptation_records": [
                {
                    "what_changed": "把任务难度偏移调整为 -0.1",
                    "why": "最近 3 次反馈都觉得太难",
                    "expected_effect": "降低任务启动门槛",
                    "user_facing_message": "我发现你最近的任务偏难了，帮你调轻了一些。",
                    "source": "adaptive_replanner",
                }
            ],
        },
    )
    route_decision = RouteDecision(
        execution_mode="hybrid",
        reason="study_plan_mode",
        risk_level="low",
        confidence=0.82,
    )
    executable_plan = SimpleNamespace(confidence=0.88, tool_calls=[{"name": "create_task"}])

    envelope = ux_envelope_builder.build(
        user_message="帮我做一份下周的学习计划",
        full_response="这是你的下周学习计划。",
        final_state=final_state,
        executable_plan=executable_plan,
        route_decision=route_decision,
        include_references=True,
        file_ids=["file-1"],
        execution_validation={"quality_score": 0.91, "failed_steps": 0, "total_steps": 2},
        conversation_context=final_state.context_data["conversation_context"],
        plan_context=final_state.context_data["plan_context"],
        user_context_payload={"preference_version": 3},
    )

    assert envelope["ux_turn"]["mode_label"] == "学习计划"
    assert envelope["ux_turn"]["dual_core_mode"] == "execution"
    assert envelope["ux_turn"]["mode_reason"] == "目标清晰且没有明显阻塞，适合直接推进执行路径。"
    assert envelope["ux_result"]["answer_kind"] == "action_bundle"
    assert envelope["ux_result"]["confidence_band"] == "high"
    assert envelope["ux_sources"]["reference_scope"] == "file_only"
    assert envelope["ux_followthrough"]["next_actions"]
    assert envelope["ux_followthrough"]["memory_updates"]["adaptation_records"]
    assert envelope["ux_evolution"]["adaptation_records"]
    assert envelope["continuity_banner"]["kind"] == "plan_context"
    assert envelope["mode_explanation"]["mode"] == "study_plan"
    assert envelope["collaboration_summary"]["selected_experts"] == ["galaxy_guide", "time_tutor"]
    assert envelope["ux_result"]["first_screen_focus"] == "先给阶段目标，再落到今天和本周的动作。"
    assert envelope["ux_followthrough"]["next_actions_title"] == "先把计划落地到这几步"


def test_ux_envelope_builder_mode_specific_headlines_and_recovery() -> None:
    cases = [
        ("standard", "我会先直接回答你的当前问题，再补依据和下一步。", "none"),
        ("deep_analysis", "我会先给综合判断，再把依据、反例和风险摊开。", "none"),
        ("study_plan", "我会先把目标拆成阶段，再落到今天就能开始的动作。", "none"),
        ("error_diagnosis", "我会先判断错因，再给你一条最省力的修复路径。", "none"),
        ("expert_auto", "我会先给综合结论，再说明主要专家贡献。", "none"),
    ]

    for chat_mode, expected_headline_prefix, expected_failure_kind in cases:
        final_state = WorkflowState(
            messages=[{"role": "user", "content": "测试问题"}],
            context_data={"chat_mode": chat_mode},
        )
        envelope = ux_envelope_builder.build(
            user_message="测试问题",
            full_response="测试回答",
            final_state=final_state,
            executable_plan=None,
            route_decision=RouteDecision(execution_mode="direct", reason=f"{chat_mode}_mode", risk_level="low"),
            include_references=False,
            file_ids=[],
            execution_validation=None,
            conversation_context=None,
            plan_context=None,
            user_context_payload=None,
        )

        assert envelope["ux_result"]["headline"].startswith(expected_headline_prefix)
        assert envelope["ux_result"]["failure_kind"] == expected_failure_kind
        assert envelope["ux_followthrough"]["next_actions_title"]


def test_ux_envelope_builder_marks_tool_failure_and_recovery_copy() -> None:
    final_state = WorkflowState(
        messages=[{"role": "user", "content": "帮我执行这个计划"}],
        context_data={"chat_mode": "expert_auto", "selected_experts": ["planner", "reviewer"]},
    )
    envelope = ux_envelope_builder.build(
        user_message="帮我执行这个计划",
        full_response="这是当前可确认的结果。",
        final_state=final_state,
        executable_plan=SimpleNamespace(confidence=0.7, tool_calls=[{"name": "create_task"}]),
        route_decision=RouteDecision(execution_mode="hybrid", reason="expert_auto_fallback_provider", risk_level="medium"),
        include_references=False,
        file_ids=[],
        execution_validation={"failed_steps": 1, "total_steps": 2, "quality_score": 0.58},
        conversation_context=None,
        plan_context=None,
        user_context_payload=None,
    )

    assert envelope["ux_result"]["completion_state"] == "partial"
    assert envelope["ux_result"]["failure_kind"] == "partial_tool_failure"
    assert "综合结论已可用" in envelope["ux_followthrough"]["recovery_message"]
    assert envelope["ux_followthrough"]["retry_options"][0] == "换一种执行方式"


def test_ux_envelope_builder_exposes_preference_learning_in_evolution() -> None:
    final_state = WorkflowState(
        messages=[{"role": "user", "content": "以后请更简洁一点"}],
        context_data={
            "chat_mode": "standard",
            "dual_core_decision": {
                "mode": "balanced",
                "reason": "当前同时存在推进任务和理解用户状态的需求，先保持双核心并行。",
            },
            "preference_learnings": [
                {
                    "what_changed": "把 depth preference 从“深入详尽”更新为“简洁概览”",
                    "why": "你最近明确要求更简洁的回答方式。",
                    "expected_effect": "后续回答会更快收敛到结论。",
                    "user_facing_message": "我记住了你更喜欢简洁的回答方式。",
                    "source": "memory_preference",
                }
            ],
        },
    )

    envelope = ux_envelope_builder.build(
        user_message="以后请更简洁一点",
        full_response="好的，之后我会更简洁。",
        final_state=final_state,
        executable_plan=None,
        route_decision=RouteDecision(execution_mode="direct", reason="chat", risk_level="low"),
        include_references=False,
        file_ids=[],
        execution_validation=None,
        conversation_context=None,
        plan_context=None,
        user_context_payload={"preference_version": 4},
    )

    assert envelope["ux_turn"]["dual_core_mode"] == "balanced"
    assert envelope["ux_followthrough"]["memory_updates"]["preference_learnings"][0]["user_facing_message"] == "我记住了你更喜欢简洁的回答方式。"
    assert envelope["ux_evolution"]["preference_learnings"][0]["source"] == "memory_preference"


def test_ux_envelope_builder_merges_evolution_highlights() -> None:
    final_state = WorkflowState(
        messages=[{"role": "user", "content": "我刚完成了群组冲刺任务"}],
        context_data={
            "chat_mode": "standard",
            "evolution_highlights": [
                "你在群组中的贡献已计入个人成就。",
                "你刚刚解锁了「冲刺先锋」。",
            ],
        },
    )

    envelope = ux_envelope_builder.build(
        user_message="我刚完成了群组冲刺任务",
        full_response="我已经同步了你的群组进度。",
        final_state=final_state,
        executable_plan=None,
        route_decision=RouteDecision(execution_mode="direct", reason="chat", risk_level="low"),
        include_references=False,
        file_ids=[],
        execution_validation=None,
        conversation_context=None,
        plan_context=None,
        user_context_payload=None,
    )

    assert "你在群组中的贡献已计入个人成就。" in envelope["ux_followthrough"]["memory_updates"]["highlights"]
    assert "你刚刚解锁了「冲刺先锋」。" in envelope["ux_followthrough"]["memory_updates"]["highlights"]
