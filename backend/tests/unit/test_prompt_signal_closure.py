"""WS-RP1: Signal closure tests — verify compiled state and fallback paths."""

from __future__ import annotations

from app.core.user_insight_state import InsightSignalEvidence, UserInsightState
from app.orchestration.prompts import _normalize_user_context, build_system_prompt


def test_normalize_user_context_lifts_profile_context_mastery_changes() -> None:
    """Original fallback path: profile_context.knowledge_summary.recent_mastery_changes still works."""
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
    """Original path: system prompt renders mastery changes from profile_context."""
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


def test_build_system_prompt_emits_stage9_prompt_utilization_snapshot() -> None:
    user_context = {
        "current_query": "我最近热力学总卡住，帮我看现在最该补哪块。",
        "profile_context": {
            "knowledge_summary": {
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
        },
        "situation_brief": {
            "focus_question": "现在最值得先补哪块？",
            "summary": "热力学有持续卡点，但最近也有一点回升。",
            "vision": {"primary_goal": "热力学冲刺"},
            "current_state": {"snapshot": "最近错题集中在熵和热机效率"},
            "primary_obstacle": {"summary": "概念判断容易混淆"},
            "evidence": {"freshest_items": ["近期痛点：熵增方向判断", "近期进展：热机效率掌握度回升"]},
            "intervention": {"summary": "先稳住概念判断"},
            "outcome": {"summary": "最近开始有一点恢复"},
            "sparkle_self_state": {},
            "recommended_stance": {},
            "decision_context": {"what_matters_now": "先补熵增方向判断"},
            "semantic_primitives": {},
            "source_trace": {},
        },
    }

    build_system_prompt(user_context=user_context, conversation_history={"messages": []})
    telemetry = user_context["prompt_signal_telemetry"]
    utilization = telemetry["utilization"]

    assert utilization["selected_signal_block_count"] >= 2
    assert utilization["rendered_signal_block_count"] >= 2
    assert "situation_brief" in utilization["selected_signal_blocks"]
    assert "recent_errors" in utilization["selected_high_value_fields"]
    assert "recent_mastery_changes" in utilization["prompt_visible_high_value_fields"]


def test_build_system_prompt_does_not_render_learning_state_fragment_payload() -> None:
    """Learning state fragment payload is not dumped raw into prompt."""
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


def test_canonical_insight_state_enriches_goals_and_tools() -> None:
    """Canonical state injects goals, tools, and exam urgency when raw dict lacks them."""
    insight = UserInsightState(
        goals=[{"id": "goal:1", "type": "exam", "label": "期末考试冲刺"}],
        inferred_work_style={"preferred_tools": ["flashcard"]},
        temporal_patterns={"calendar": {"exam_urgency": {"days_left": 5, "urgent": True}}},
    )
    context = {"user_insight_state": insight}
    normalized = _normalize_user_context(context)

    assert normalized["active_goals"][0]["title"] == "期末考试冲刺"
    assert normalized["preferred_tools"] == ["flashcard"]
    assert normalized["exam_urgency"]["days_left"] == 5


def test_canonical_insight_state_does_not_override_existing_goals() -> None:
    """When raw dict already provides goals, canonical does not override."""
    insight = UserInsightState(
        goals=[{"id": "goal:canonical", "type": "exam", "label": "Canonical Goal"}],
    )
    context = {
        "user_insight_state": insight,
        "active_goals": [{"title": "Raw Dict Goal", "status": "active"}],
    }
    normalized = _normalize_user_context(context)

    # Raw dict goal wins
    assert normalized["active_goals"][0]["title"] == "Raw Dict Goal"


def test_canonical_insight_state_via_profile_context_dict() -> None:
    """UserInsightState embedded as dict in profile_context is extracted."""
    insight = UserInsightState(
        signal_evidence=[
            InsightSignalEvidence(
                signal_id="error_summary",
                family="error",
                label="Errors",
                source="test",
                value={"total_errors": 4},
                confidence=0.9,
            ),
        ],
    )
    context = {
        "profile_context": {
            "user_insight_state": insight.model_dump(),
        },
    }
    normalized = _normalize_user_context(context)

    assert normalized["error_summary"]["total_errors"] == 4


def test_build_system_prompt_renders_stage22_achievement_and_calendar_context() -> None:
    user_context = {
        "achievement_summary": {
            "recent_unlocks": [{"name": "七日连胜"}],
            "in_progress_achievements": [{"name": "百小时学习", "progress": 0.62}],
            "total_achievement_score": 4.5,
        },
        "calendar_context": {
            "upcoming_deadlines": [{"title": "热力学计划复盘", "start_time": "2026-04-23T19:00:00"}],
            "time_blocks_today": [{"start": "19:00", "end": "21:00"}],
            "workload_density": "medium",
            "exam_urgency": {"days_left": 12, "urgent": True},
        },
    }

    prompt = build_system_prompt(user_context=user_context, conversation_history={"messages": []})
    telemetry = user_context["prompt_signal_telemetry"]

    assert "七日连胜" in prompt
    assert "【时间约束】" in prompt
    assert "19:00-21:00" in prompt
    assert telemetry["high_value_fields"]["achievement_summary"]["rendered"] is True
    assert telemetry["high_value_fields"]["calendar_context"]["rendered"] is True
    assert telemetry["field_render_coverage_ratio"] > 0


def test_build_system_prompt_renders_stage33_social_signal_section_when_live() -> None:
    user_context = {
        "aurora_stage33_modes": {"mode": "shadow", "social": "live"},
        "cognitive_context": {
            "social_context_v1": {
                "mention_count": 2,
                "relationship_count": 1,
                "pending_commitments_count": 1,
                "summary_lines": [
                    "最近 7 天提到过 2 位学习相关人物。",
                    "目前有 1 条到期承诺待跟进。",
                ],
            }
        },
    }

    prompt = build_system_prompt(user_context=user_context, conversation_history={"messages": []})
    telemetry = user_context["prompt_signal_telemetry"]

    assert "## 社群信号 [L2 引导]" in prompt
    assert "最近 7 天提到过 2 位学习相关人物。" in prompt
    assert "social_signals_summary" in telemetry["prompt_visible_high_value_fields"]
    assert telemetry["high_value_fields"]["social_signals_summary"]["rendered"] is True


def test_build_system_prompt_renders_stage33_srl_phase_section_when_live() -> None:
    user_context = {
        "aurora_stage33_modes": {"mode": "shadow", "srl": "live"},
        "profile_context": {
            "user_insight_state": {
                "srl_phase": {
                    "current_phase": "SELF_REFLECTION",
                    "confidence": 0.82,
                    "source": "aggregator",
                    "freshness_seconds": 11,
                }
            }
        },
    }

    prompt = build_system_prompt(user_context=user_context, conversation_history={"messages": []})
    telemetry = user_context["prompt_signal_telemetry"]

    assert "## 学习自调节阶段" in prompt
    assert "当前阶段：复盘反思（reflection）" in prompt
    assert "srl_phase" in telemetry["prompt_visible_high_value_fields"]
    assert telemetry["high_value_fields"]["srl_phase"]["rendered"] is True


def test_build_system_prompt_renders_stage33_working_memory_section_with_budget_cap() -> None:
    user_context = {
        "aurora_stage33_modes": {"mode": "shadow", "wm_prompt": "live"},
        "working_memory_snapshot": {
            "active_session_id": "session-1",
            "items": [
                {
                    "summary": "准备本周末补完高数真题，并且先把错题按题型重新归档，避免继续混在一起导致复盘效率太低。",
                    "subject_type": "commitment",
                },
                {
                    "summary": "和同学约好今晚对一遍热力学公式推导，看看到底卡在概念还是计算。",
                    "subject_type": "social",
                },
            ],
        },
    }

    prompt = build_system_prompt(user_context=user_context, conversation_history={"messages": []})
    telemetry = user_context["prompt_signal_telemetry"]

    assert "## 工作记忆（近 30 分钟）" in prompt
    assert "commitment:" in prompt
    assert "working_memory_snapshot" in telemetry["prompt_visible_high_value_fields"]
    assert telemetry["high_value_fields"]["working_memory_snapshot"]["rendered"] is True
    assert telemetry["section_sizes"]["working_memory_snapshot"]["approx_tokens"] <= 300


def test_normalize_user_context_preserves_top_level_stage34_goal_and_episodic_payloads() -> None:
    normalized = _normalize_user_context(
        {
            "active_goals": [{"title": "14 天内稳住热力学第二章", "status": "active"}],
            "episodic_memories": [{"summary": "昨晚已经把热机效率错题重新按题型分组。"}],
        }
    )

    assert normalized["active_goals"][0]["title"] == "14 天内稳住热力学第二章"
    assert normalized["episodic_memories"][0]["summary"] == "昨晚已经把热机效率错题重新按题型分组。"
