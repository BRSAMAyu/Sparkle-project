from __future__ import annotations

from app.orchestration.prompts import (
    _estimate_prompt_tokens,
    _format_intervention_language_contract_section,
    build_system_prompt,
)


def _failure_signal_context() -> dict:
    return {
        "current_query": "我最近总在同一个点上卡住，帮我看看怎么重启。",
        "profile_context": {},
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
                }
            ],
        },
    }


def _mastery_signal_context() -> dict:
    return {
        "current_query": "我最近好像有一点起色，帮我把下一步收稳。",
        "profile_context": {},
        "cognitive_context": {
            "recent_mastery_changes": [
                {
                    "node_name": "热机效率",
                    "old_mastery": 31,
                    "new_mastery": 46,
                }
            ],
        },
    }


def _mixed_signal_context() -> dict:
    return {
        "current_query": "我一边在卡住，一边又好像有点进步，帮我看看怎么接。",
        "profile_context": {},
        "cognitive_context": {
            "error_summary": {
                "total_errors": 6,
                "need_review_count": 2,
                "subject_distribution": {"thermo": 4},
            },
            "recent_errors": [
                {
                    "question_preview": "可逆过程条件",
                    "subject": "thermo",
                    "error_type": "推理跳步",
                }
            ],
            "recent_mastery_changes": [
                {
                    "node_name": "卡诺循环",
                    "old_mastery": 40,
                    "new_mastery": 55,
                }
            ],
        },
    }


def test_intervention_language_contract_handles_recent_failure_without_shame() -> None:
    user_context = _failure_signal_context()

    prompt = build_system_prompt(
        user_context=user_context,
        conversation_history={"messages": []},
    )
    section = _format_intervention_language_contract_section(
        user_context=user_context,
        prompt_signal_telemetry=user_context["prompt_signal_telemetry"],
    )

    assert "【近期痛点】" in prompt
    assert prompt.count("## 干预语言契约") == 1
    assert "不审判" in section
    assert "不羞辱" in section
    assert "不替用户做道德评价" in section
    assert "不先说“你又失败了”" in section
    assert "先站到用户同侧" in section
    assert "好奇和重新启动" in section
    assert "朋友" in section
    assert "a friend helping me restart" in section
    assert _estimate_prompt_tokens(section) <= 220


def test_intervention_language_contract_handles_recent_mastery_with_restart_bias() -> None:
    user_context = _mastery_signal_context()

    prompt = build_system_prompt(
        user_context=user_context,
        conversation_history={"messages": []},
    )
    section = _format_intervention_language_contract_section(
        user_context=user_context,
        prompt_signal_telemetry=user_context["prompt_signal_telemetry"],
    )

    assert "【近期进展】" in prompt
    assert prompt.count("## 干预语言契约") == 1
    assert "信号：进展主导" in section
    assert "先肯定已有推进" in section
    assert "先承接已有进展" in section
    assert "好奇" in section
    assert "重新启动" in section
    assert _estimate_prompt_tokens(section) <= 220


def test_intervention_language_contract_handles_mixed_pain_and_progress_evidence() -> None:
    user_context = _mixed_signal_context()

    prompt = build_system_prompt(
        user_context=user_context,
        conversation_history={"messages": []},
    )
    section = _format_intervention_language_contract_section(
        user_context=user_context,
        prompt_signal_telemetry=user_context["prompt_signal_telemetry"],
    )

    assert "【近期痛点】" in prompt
    assert "【近期进展】" in prompt
    assert prompt.count("## 干预语言契约") == 1
    assert user_context["prompt_signal_telemetry"]["prompt_visible_high_value_fields"] == [
        "error_summary",
        "recent_errors",
        "recent_mastery_changes",
    ]
    assert "信号：痛点+进展并存" in section
    assert "执行：先承接已有进展，再给最小可行改动" in section
    assert "不先说“你又失败了”" in section
    assert "好奇和重新启动" in section
    assert _estimate_prompt_tokens(section) <= 220
