from app.orchestration.prompts import build_system_prompt


def test_build_system_prompt_includes_stage39_scaffolding_section_when_live() -> None:
    prompt = build_system_prompt(
        user_context={
            "scaffolding_fsm_snapshot": {
                "mode": "live",
                "current_scaffolding_stage": "flow",
                "intervention_intensity": "medium",
                "template_support_level": 3,
                "reflection_prompt_style": "default",
            },
        },
        conversation_history={"messages": []},
    )

    assert "## 脚手架状态 [L2 引导]" in prompt
    assert "当前脚手架阶段: flow" in prompt
    assert "当前干预强度: medium" in prompt


def test_build_system_prompt_hides_stage39_galaxy_section_when_shadow() -> None:
    prompt = build_system_prompt(
        user_context={
            "galaxy_snapshot": {
                "mode": "shadow",
                "nodes": [
                    {
                        "name": "熵增",
                        "role": "goal_anchor",
                        "mastery_score": 58.0,
                        "description": "不应在 shadow 模式直接进 prompt。",
                    }
                ],
            },
        },
        conversation_history={"messages": []},
    )

    assert "## 知识星图节点 [L2 引导]" not in prompt
