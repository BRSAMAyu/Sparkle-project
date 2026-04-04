from app.semantic.state_primitives import StudyDomainSemanticAdapter
from app.orchestration.situation_brief import SituationBriefBuilder, format_situation_brief_section


def test_situation_brief_builder_uses_existing_context_sources() -> None:
    brief = SituationBriefBuilder().build(
        user_context_payload={
            "learning_gaps_summary": "热力学第二定律相关概念仍然容易混淆。",
            "context_focus": {
                "focus_mode": "knowledge_focus",
                "route_intent": "knowledge",
            },
            "profile_context": {
                "knowledge_summary": {
                    "weak_spots": [
                        {"node_name": "熵增方向判断", "mastery": 42},
                    ],
                    "recent_mastery_changes": [
                        {
                            "node_name": "热机效率",
                            "old_mastery": 31,
                            "new_mastery": 46,
                            "changed_at": "2026-04-04T08:30:00",
                        }
                    ],
                    "active_learning_subjects": ["热力学", "数学"],
                },
                "cognitive_summary": {
                    "active_patterns": [
                        {
                            "pattern_name": "完美主义回避循环",
                            "pattern_type": "execution",
                            "confidence": 0.76,
                        }
                    ]
                },
            },
            "active_goals": [{"title": "在期中前拿下热力学第二章"}],
            "evolution_highlights": ["最近 7 天你在 3 个知识点上有推进。"],
            "active_interventions": [
                {
                    "intervention_id": "iv-1",
                    "label": "降载微调",
                    "acceptance_status": "accepted",
                    "source": "pending_record",
                }
            ],
            "last_feedback_binding": {
                "intervention_id": "iv-1",
                "sentiment": "helped",
                "user_words": "这样轻一点我就能开始了。",
            },
        },
        plan_context={
            "plan_title": "热力学冲刺计划",
            "goal": "掌握热力学第二章",
            "plan_stage": "冲刺阶段",
        },
        focused_memory={},
        context_briefing_note="当前重点：先补第二定律，再推进题目训练。",
        visible_update_context={
            "proactive_opening_message": "我注意到你最近在条件判断题上连续卡住了几次。",
        },
        dual_core_snapshot={
            "decision": {"mode": "balanced"},
            "signal_snapshot": {"current_guidance": "先搭桥澄清概念卡点，再给执行动作。"},
            "prompt_instruction": "优先澄清概念，再推进执行。",
        },
        session_feedback_signal={"signal_type": "simplify"},
        progress_snapshot={
            "highlights": ["最近 7 天你在 3 个知识点上有推进。"],
            "attention_areas": ["知识掌握推进速度比上一周期慢了一些。"],
            "generated_at": "2026-04-04T09:00:00",
        },
        adaptation_records=[{"strategy_name": "降载微调", "effectiveness": "accepted"}],
    ).to_dict()

    assert "在期中前拿下热力学第二章" in brief["focus_question"]
    assert brief["summary"].startswith("目标图景是")
    assert brief["vision"]["active_plan"] == "热力学冲刺计划"
    assert brief["current_state"]["focus_mode"] == "knowledge_focus"
    assert brief["primary_obstacle"]["source"] == "dual_core_signal_snapshot.current_guidance"
    assert brief["intervention"]["active"] is True
    assert brief["outcome"]["status"] == "progressing"
    assert brief["sparkle_self_state"]["dual_core_mode"] == "balanced"
    assert brief["sparkle_self_state"]["confidence_estimate"] > 0.5
    assert "progress_snapshot" in brief["source_trace"]["used_sources"]
    assert brief["source_trace"]["semantic_layer"]["adapter_name"] == StudyDomainSemanticAdapter.adapter_name
    assert "vision" in brief["semantic_primitives"]["source_mapping"]


def test_format_situation_brief_section_renders_compact_prompt_block() -> None:
    section = format_situation_brief_section(
        {
            "focus_question": "为了继续推进「热力学第二章」，这轮最该先处理的阻力是什么，为什么是现在？",
            "summary": "目标图景是「热力学第二章」；当前状态是第二定律相关概念仍然容易混淆；主要阻力是概念混淆；最近证据是最近 7 天你在 3 个知识点上有推进；本轮宜先抓住最关键阻力，再给结构化推进。",
            "vision": {
                "primary_goal": "热力学第二章",
                "active_plan": "热力学冲刺计划",
                "why_now": "考试倒计时 12 天",
            },
            "current_state": {
                "snapshot": "热力学第二定律相关概念仍然容易混淆；最近 7 天你在 3 个知识点上有推进。",
            },
            "primary_obstacle": {
                "summary": "先搭桥澄清概念卡点，再给执行动作。",
            },
            "evidence": {
                "freshest_items": [
                    "最近 7 天你在 3 个知识点上有推进。",
                    "热机效率 最近掌握度变化约 +15.0",
                ]
            },
            "intervention": {
                "summary": "当前正在跟踪的支持动作是「降载微调」，状态 accepted，最近反馈 helped",
            },
            "outcome": {
                "summary": "最近结果信号显示 这样轻一点我就能开始了。",
            },
            "recommended_stance": {
                "stance": "先抓住最关键阻力，再给结构化推进。",
            },
        }
    )

    assert "## Situation Brief [L0 简报]" in section
    assert "目标图景: 热力学第二章 / 当前计划 热力学冲刺计划" in section
    assert "最新证据" in section
    assert "当前干预" in section
    assert "最近结果" in section
    assert "本轮站位" in section
