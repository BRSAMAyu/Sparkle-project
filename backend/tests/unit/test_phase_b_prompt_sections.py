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
    assert "goal_frame, assumptions, next_action" in prompt
