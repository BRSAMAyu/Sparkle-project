from app.orchestration.experience_packets import (
    attach_goal_realization_context,
    build_goal_realization_context,
)


def _sample_user_context() -> dict:
    return {
        "active_goals": [{"id": "goal-1", "title": "零基础通过网络考试"}],
        "active_plans": [{"id": "plan-1", "title": "7 天冲刺"}],
        "next_actions": [{"id": "task-1", "title": "先补 TCP 三次握手"}],
        "document_context": {"used": True},
        "aurora_everyday_presence": {
            "summary": "你更像是卡在不会做，而不是没时间。",
            "chat_hint": "我可能误读了，你更像是卡在不会做，而不是没时间。",
            "uncertainty_level": "high",
            "evidence_chain": ["最近两次任务都停在第一步", "资料里 TCP 状态机是薄弱点"],
            "next_step_suggestion": "先确认前置知识缺口",
        },
        "recent_corrections": [
            {
                "semantic_value": "skill_gap_not_time",
                "freeform_text": "不是没时间，是完全不会做。",
            }
        ],
        "episodic_memories": [
            {
                "id": "mem-1",
                "summary": "用户确认晚上更适合做深度学习。",
                "user_confirmed": True,
                "confidence": 0.91,
            },
            {
                "id": "mem-2",
                "summary": "用户纠正过：不要把不会做误判成拖延。",
                "correction_count": 2,
                "confidence": 0.88,
            },
        ],
        "learning_gaps_summary": {
            "weak_nodes": [{"id": "node-1", "title": "TCP 状态迁移"}],
            "recommended_nodes": [{"id": "node-2", "title": "三次握手"}],
        },
    }


def _sample_state_context() -> dict:
    return {
        "context_plan": {"retrieval_mode": "targeted_source_rag"},
        "document_context_retrieval": {
            "entities": [{"id": "node-1", "title": "TCP 状态迁移"}],
            "context_receipt": {
                "answer_basis": "source_grounded",
                "loaded": [
                    {
                        "document_id": "doc-1",
                        "title": "TCP 讲义",
                        "confidence": 0.84,
                    }
                ],
                "correction_hint": "如果引用错了，可以直接纠正资料来源。",
            },
        },
    }


def test_goal_realization_context_unifies_aurora_memory_graph_and_sources():
    packet = build_goal_realization_context(
        user_context_payload=_sample_user_context(),
        state_context=_sample_state_context(),
    )

    assert packet is not None
    payload = packet.to_dict()
    assert payload["active_goal"]["title"] == "零基础通过网络考试"
    assert payload["aurora"]["next_strategy"] == "diagnose_before_advice"
    assert payload["source_receipt"]["answer_basis"] == "source_grounded"
    assert payload["source_receipt"]["context_plan_mode"] == "targeted_source_rag"
    assert payload["graph_trace"]["graph_state"] == "active"
    assert payload["graph_trace"]["affects"] == [
        "next_task",
        "rag_scope",
        "plan_feasibility",
        "aurora_read",
    ]
    assert {claim["kind"] for claim in payload["memory_claims"]} == {
        "confirmed",
        "correction_derived",
    }
    assert "source_document" in payload["card_protocol"]["required_types"]
    assert "知识图谱会参与下一步选择" in payload["user_visible_summary"]


def test_attach_goal_realization_context_writes_both_user_and_state_contexts():
    user_context = _sample_user_context()
    state_context = _sample_state_context()

    returned = attach_goal_realization_context(
        user_context_payload=user_context,
        state_context=state_context,
    )

    assert returned is user_context
    assert user_context["goal_realization_context"]["active_goal"]["id"] == "goal-1"
    assert user_context["aurora_experience_packet"]["uncertainty_level"] == "high"
    assert state_context["goal_realization_context"]["source_receipt"]["loaded_sources"][0]["document_id"] == "doc-1"
    assert state_context["graph_decision_trace"]["decision_scope"] == "goal_realization_turn"


def test_goal_realization_context_ignores_missing_user_context():
    assert build_goal_realization_context(user_context_payload=None, state_context={}) is None
    assert attach_goal_realization_context(user_context_payload=None, state_context={}) is None
