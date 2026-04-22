from __future__ import annotations

from app.orchestration.prompts import build_system_prompt


def test_build_system_prompt_injects_top_three_live_idiographic_lines_only() -> None:
    user_context = {
        "current_query": "帮我复盘最近的学习节奏",
        "profile_context": {
            "idiographic_summary": {
                "mode": "live",
                "confidence": 0.66,
                "disclaimer_text": "这只是你数据中的模式，不代表因果关系。",
                "top_associations": [
                    {
                        "dim_pair": "a",
                        "correlation": 0.44,
                        "displayed": True,
                        "rendered_text": "观察 1",
                    },
                    {
                        "dim_pair": "b",
                        "correlation": 0.41,
                        "displayed": True,
                        "rendered_text": "观察 2",
                    },
                    {
                        "dim_pair": "c",
                        "correlation": 0.39,
                        "displayed": True,
                        "rendered_text": "观察 3",
                    },
                    {
                        "dim_pair": "d",
                        "correlation": 0.38,
                        "displayed": True,
                        "rendered_text": "观察 4",
                    },
                ],
            },
        },
    }

    prompt = build_system_prompt(
        user_context=user_context,
        conversation_history={"messages": []},
    )

    assert "## 个体内关联观察 [L2 引导]" in prompt
    assert "观察 1" in prompt
    assert "观察 2" in prompt
    assert "观察 3" in prompt
    assert "观察 4" not in prompt
    assert user_context["idiographic_associations_injected"] == [
        {"dim_pair": "a", "r_rounded": 0.44, "displayed": True},
        {"dim_pair": "b", "r_rounded": 0.41, "displayed": True},
        {"dim_pair": "c", "r_rounded": 0.39, "displayed": True},
    ]


def test_build_system_prompt_skips_shadow_idiographic_payload() -> None:
    user_context = {
        "current_query": "帮我复盘最近的学习节奏",
        "profile_context": {
            "idiographic_summary": {
                "mode": "shadow",
                "confidence": 0.72,
                "disclaimer_text": "这只是你数据中的模式，不代表因果关系。",
                "top_associations": [
                    {
                        "dim_pair": "a",
                        "correlation": 0.44,
                        "displayed": True,
                        "rendered_text": "观察 1",
                    },
                ],
            },
        },
    }

    prompt = build_system_prompt(
        user_context=user_context,
        conversation_history={"messages": []},
    )

    assert "## 个体内关联观察 [L2 引导]" not in prompt
    assert user_context["idiographic_associations_injected"] == []
