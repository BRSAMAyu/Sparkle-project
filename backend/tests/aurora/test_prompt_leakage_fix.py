from __future__ import annotations

from app.orchestration.prompts import _normalize_user_context, build_system_prompt


def test_normalize_user_context_lifts_profile_context_mastery_changes() -> None:
    context = {
        "profile_context": {
            "knowledge_summary": {
                "overall_mastery": 0.74,
                "active_learning_subjects": ["thermo"],
                "recent_mastery_changes": [
                    {
                        "node_name": "热机效率",
                        "old_mastery": 31,
                        "new_mastery": 46,
                    }
                ],
            },
            "error_summary": {"total_errors": 5, "need_review_count": 2},
            "recent_errors": [{"question_preview": "熵增方向判断", "subject": "thermo"}],
        }
    }

    normalized = _normalize_user_context(context)

    assert normalized["knowledge_summary"]["overall_mastery"] == 0.74
    assert normalized["recent_mastery_changes"][0]["node_name"] == "热机效率"
    assert normalized["error_summary"]["total_errors"] == 5


def test_build_system_prompt_renders_profile_context_mastery_changes() -> None:
    user_context = {
        "profile_context": {
            "knowledge_summary": {
                "overall_mastery": 0.74,
                "active_learning_subjects": ["thermo"],
                "recent_mastery_changes": [
                    {
                        "node_name": "热机效率",
                        "old_mastery": 31,
                        "new_mastery": 46,
                    }
                ],
            },
            "error_summary": {"total_errors": 5, "need_review_count": 2},
            "recent_errors": [{"question_preview": "熵增方向判断", "subject": "thermo"}],
        }
    }

    prompt = build_system_prompt(user_context=user_context, conversation_history={"messages": []})
    telemetry = user_context["prompt_signal_telemetry"]

    assert "【近期进展】" in prompt
    assert "热机效率 掌握度从 31% 提升到 46% (+15)" in prompt
    assert "recent_mastery_changes" in telemetry["collected_high_value_fields"]
    assert "recent_mastery_changes" in telemetry["prompt_visible_high_value_fields"]


def test_build_system_prompt_does_not_render_learning_state_fragment_payload() -> None:
    user_context = {
        "profile_context": {},
        "situation_brief": {
            "focus_question": "为了继续推进热力学，这轮最该先处理的阻力是什么？",
            "summary": "目标图景是热力学复习；当前状态是存在一些学习卡点。",
            "vision": {"primary_goal": "热力学复习"},
            "learning_state_fragment": {
                "status": "active",
                "available": True,
                "summary": "fragment-sentinel",
                "signals": [
                    {"kind": "pain", "text": "fragment-sentinel"},
                ],
                "recent_pain_points": ["fragment-sentinel"],
                "recent_wins": [],
                "source_signals": ["recent_errors"],
                "budget": {"truncated": True},
            },
        }
    }

    prompt = build_system_prompt(user_context=user_context, conversation_history={"messages": []})

    assert "## Situation Brief [L0 简报]" in prompt
    assert "fragment-sentinel" not in prompt
