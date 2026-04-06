from __future__ import annotations

from app.orchestration.ai_strategy_renderer import build_semantic_control, format_semantic_control_lines


def test_renderer_builds_strategy_doctrine_from_governed_terms_only() -> None:
    semantic_control = build_semantic_control(
        decision_context={
            "experience_mode": "stabilize",
            "planning_readiness_action": "ask",
        },
        planning_strategy={
            "plan_mode": "next_step_only",
            "grounding_mode": "mandatory",
        },
        user_strategy_state={
            "session_mode": "recovery",
            "explanation_style": "step_by_step",
            "retrieval_emphasis": "user_materials",
            "push_vs_support": 0.2,
            "intervention_intensity": "low",
            "current_episode_note": "This should stay runtime-only.",
            "meta": {"adaptive_summary": "This should also stay runtime-only."},
        },
        language="zh",
    ).to_dict()

    strategy_lines = format_semantic_control_lines(semantic_control, language="zh", section="strategy")
    joined = " ".join(strategy_lines)
    selected_terms = {item["term"] for item in semantic_control["selected_terms"]}
    summary = semantic_control["rendered_doctrine_summary"]["summary"]

    assert {"session_mode", "explanation_style", "retrieval_emphasis", "intervention_intensity", "support_posture"} <= selected_terms
    assert strategy_lines
    assert "恢复模式" in joined
    assert "按步骤解释" in joined
    assert "用户自己的材料" in joined
    assert "支持优先" in joined
    assert "轻量" in joined
    assert "current_episode_note" not in summary
    assert "adaptive_summary" not in summary
    assert "This should stay runtime-only." not in summary


def test_renderer_ignores_dict_shaped_learning_inputs() -> None:
    semantic_control = build_semantic_control(
        decision_context={
            "five_layer_growth_summary": {
                "active_conflicts": [{"conflict_id": "should-not-leak", "label": "Unsafe"}],
            }
        },
        planning_strategy={"plan_mode": "full"},
        outcome_learning={
            "plan_generation_hints_from_outcomes": [
                {"bad": "shape"},
                "Use lighter first steps.",
            ]
        },
        language="en",
    ).to_dict()

    learning_lines = semantic_control["rendered_doctrine_summary"]["learning_doctrine"]
    summary = semantic_control["rendered_doctrine_summary"]["summary"]

    assert learning_lines == ["Carry this validated learning hint into the response: Use lighter first steps."]
    assert "should-not-leak" not in summary
    assert "{'bad': 'shape'}" not in summary


def test_renderer_does_not_fallback_to_active_conflict_dicts_when_learning_hints_missing() -> None:
    semantic_control = build_semantic_control(
        decision_context={
            "five_layer_growth_summary": {
                "active_conflicts": [{"conflict_id": "companion-conflict"}],
            }
        },
        planning_strategy={"plan_mode": "full"},
        outcome_learning={},
        language="zh",
    ).to_dict()

    assert semantic_control["rendered_doctrine_summary"]["learning_doctrine"] == []
    assert "companion-conflict" not in semantic_control["rendered_doctrine_summary"]["summary"]
