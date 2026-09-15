from app.semantic.state_primitives import PRIMITIVE_SOURCE_MAPPING, StudyDomainSemanticAdapter


def test_study_domain_semantic_adapter_maps_context_to_universal_primitives() -> None:
    bundle = StudyDomainSemanticAdapter().map_from_context(
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
        progress_snapshot={
            "highlights": ["最近 7 天你在 3 个知识点上有推进。"],
            "attention_areas": ["知识掌握推进速度比上一周期慢了一些。"],
        },
        visible_update_context={
            "proactive_opening_message": "我注意到你最近在条件判断题上连续卡住了几次。",
        },
        adaptation_records=[{"strategy_name": "降载微调", "effectiveness": "accepted"}],
    ).to_dict()

    assert bundle["adapter_name"] == "study_domain_v1"
    assert bundle["source_mapping"] == PRIMITIVE_SOURCE_MAPPING
    assert bundle["vision"]["primary_goal"] == "在期中前拿下热力学第二章"
    assert bundle["current_state"]["focus_mode"] == "knowledge_focus"
    assert bundle["obstacle"]["source"] == "user_context.learning_gaps_summary"
    assert bundle["evidence"]["freshest_items"]
    assert bundle["intervention"]["intervention_id"] == "iv-1"
    assert bundle["intervention"]["active"] is True
    assert bundle["outcome"]["status"] == "progressing"
    assert bundle["outcome"]["source"] == "feedback_binding"
