from app.orchestration.prompts import build_system_prompt


def test_build_system_prompt_includes_phase_b_planning_strategy_section() -> None:
    prompt = build_system_prompt(
        user_context={
            "current_query": "帮我做一个两周热力学冲刺计划",
            "situation_brief": {
                "focus_question": "What is the best next planning move?",
                "summary": "Need a grounded sprint plan.",
                "vision": {"primary_goal": "Pass thermodynamics exam"},
                "current_state": {"snapshot": "Behind on chapter 2"},
                "primary_obstacle": {"summary": "Confusing core concepts"},
                "evidence": {},
                "intervention": {},
                "outcome": {},
                "sparkle_self_state": {},
                "recommended_stance": {},
                "decision_context": {
                    "planning_readiness": "high",
                    "planning_readiness_action": "proceed",
                },
                "semantic_primitives": {},
                "source_trace": {},
                "planning_strategy": {
                    "plan_mode": "full",
                    "plan_depth": "deep",
                    "pacing_profile": "steady",
                    "grounding_mode": "mandatory",
                    "fallback_policy": "revise",
                    "required_plan_sections": ["goal_frame", "assumptions", "next_action"],
                },
            },
        },
        conversation_history={"messages": []},
    )

    assert "## 规划生成约束 [L1 引导]" in prompt
    assert "这里适合给真实完整计划" in prompt
    assert "goal_frame, assumptions, next_action" not in prompt
    assert "grounding 要求" not in prompt


def test_build_system_prompt_hides_raw_strategy_state_fields_from_model_facing_sections() -> None:
    prompt = build_system_prompt(
        user_context={
            "current_query": "我最近总觉得信息太多了，帮我轻一点。",
            "user_strategy_state": {
                "session_mode": "recovery",
                "explanation_style": "step_by_step",
                "retrieval_emphasis": "user_materials",
                "push_vs_support": 0.2,
                "intervention_intensity": "low",
                "current_episode_note": "这段话不该进 prompt",
            },
            "situation_brief": {
                "summary": "Need a lighter turn.",
                "decision_context": {
                    "experience_mode": "stabilize",
                    "planning_readiness_action": "ask",
                },
                "planning_strategy": {
                    "plan_mode": "next_step_only",
                    "plan_depth": "light",
                    "pacing_profile": "light",
                    "grounding_mode": "mandatory",
                    "fallback_policy": "ask_more",
                    "required_plan_sections": ["withhold_reason", "next_action", "unlock_question"],
                },
            },
        },
        conversation_history={"messages": []},
    )

    assert "当前交互策略" in prompt
    assert "恢复模式" in prompt
    assert "按步骤解释" in prompt
    assert "用户自己的材料" in prompt
    assert "支持优先" in prompt
    assert "session_mode" not in prompt
    assert "push_vs_support" not in prompt
    assert "retrieval_emphasis" not in prompt
    assert "intervention_intensity" not in prompt
    assert "current_episode_note" not in prompt
