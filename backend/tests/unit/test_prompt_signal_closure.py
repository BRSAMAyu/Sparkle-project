from app.orchestration.prompts import _normalize_user_context, build_system_prompt, format_user_context


def _signal_context() -> dict:
    return {
        "current_query": "帮我看看我最近为什么总在热力学上卡住",
        "cognitive_context": {
            "error_summary": {
                "total_errors": 7,
                "need_review_count": 3,
                "subject_distribution": {"thermo": 4, "math": 2},
            },
            "recent_errors": [
                {
                    "question_preview": "熵增方向判断",
                    "subject": "thermo",
                    "error_type": "概念混淆",
                    "mastery": 0.35,
                },
                {
                    "question_preview": "可逆过程条件",
                    "subject": "thermo",
                    "error_type": "推理跳步",
                    "mastery": 0.42,
                },
            ],
            "recent_mastery_changes": [
                {
                    "node_name": "热机效率",
                    "old_mastery": 31,
                    "new_mastery": 46,
                },
                {
                    "node_name": "卡诺循环",
                    "old_mastery": 40,
                    "new_mastery": 55,
                },
            ],
        },
    }


def test_normalize_user_context_lifts_cognitive_context_signals() -> None:
    normalized = _normalize_user_context(_signal_context())

    assert normalized["error_summary"]["total_errors"] == 7
    assert normalized["recent_errors"][0]["question_preview"] == "熵增方向判断"
    assert normalized["recent_mastery_changes"][0]["node_name"] == "热机效率"


def test_format_user_context_renders_recent_pain_points_and_wins_with_caps() -> None:
    light = format_user_context(_signal_context(), context_level="light")
    full = format_user_context(_signal_context(), context_level="full")

    assert "【近期痛点】" in light
    assert "累计错题 7；待复习 3；高频科目 thermo(4)、math(2)" in light
    assert "熵增方向判断" not in light
    assert "【近期进展】" in light
    assert "热机效率 掌握度从 31% 提升到 46% (+15)" in light
    assert "卡诺循环" not in light

    assert "熵增方向判断" in full
    assert "可逆过程条件" in full
    assert "卡诺循环 掌握度从 40% 提升到 55% (+15)" in full


def test_build_system_prompt_records_prompt_signal_telemetry() -> None:
    user_context = _signal_context()

    prompt = build_system_prompt(
        user_context=user_context,
        conversation_history={"messages": []},
    )

    telemetry = user_context["prompt_signal_telemetry"]

    assert "【近期痛点】" in prompt
    assert "【近期进展】" in prompt
    assert telemetry["collected_high_value_fields"] == [
        "error_summary",
        "recent_errors",
        "recent_mastery_changes",
    ]
    assert telemetry["prompt_visible_high_value_fields"] == [
        "error_summary",
        "recent_errors",
        "recent_mastery_changes",
    ]
    assert telemetry["dropped_high_value_fields"] == []
    assert telemetry["model_facing_section_sizes"]["recent_pain_points"]["items"] == 3
    assert telemetry["model_facing_section_sizes"]["recent_wins"]["items"] == 2
