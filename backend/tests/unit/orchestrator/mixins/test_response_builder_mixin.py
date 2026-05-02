"""
Unit tests for ResponseBuilderMixin.

Tests the response-building and cleanup helpers for the orchestrator.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.orchestration.response_builder import ResponseBuilderMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(ResponseBuilderMixin):
    """Minimal orchestrator with ResponseBuilderMixin for testing."""

    def __init__(self):
        pass


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


def test_extract_response_outcome_stats_with_none_state(orchestrator):
    """Test _extract_response_outcome_stats returns zeros for None state."""
    result = orchestrator._extract_response_outcome_stats(None)

    assert result == {
        "task_count": 0,
        "plan_count": 0,
        "execution_count": 0,
    }


def test_extract_response_outcome_stats_with_empty_state(orchestrator):
    """Test _extract_response_outcome_stats with empty WorkflowState."""
    mock_state = MagicMock()
    mock_state.messages = []
    mock_state.context_data = {}

    result = orchestrator._extract_response_outcome_stats(mock_state)

    assert result["task_count"] == 0
    assert result["plan_count"] == 0
    assert result["execution_count"] == 0


def test_extract_response_outcome_stats_counts_task_entities(orchestrator):
    """Test _extract_response_outcome_stats correctly counts task entities."""
    mock_state = MagicMock()
    mock_state.messages = [
        {
            "entity_card": {
                "entity_type": "task",
                "entity_id": "task-1",
                "schema_version": "1.0",
                "primary_action": "start",
            }
        },
        {
            "entity_card": {
                "entity_type": "task",
                "entity_id": "task-2",
                "schema_version": "1.0",
            }
        },
    ]
    mock_state.context_data = {}

    result = orchestrator._extract_response_outcome_stats(mock_state)

    assert result["task_count"] == 2
    assert result["plan_count"] == 0


def test_extract_response_outcome_stats_counts_plan_entities(orchestrator):
    """Test _extract_response_outcome_stats correctly counts plan entities."""
    mock_state = MagicMock()
    mock_state.messages = []
    mock_state.context_data = [
        {
            "entity_card": {
                "entity_type": "plan",
                "entity_id": "plan-1",
                "schema_version": "1.0",
            }
        }
    ]

    result = orchestrator._extract_response_outcome_stats(mock_state)

    assert result["task_count"] == 0
    assert result["plan_count"] == 1


def test_extract_response_outcome_stats_counts_execution_actions(orchestrator):
    """Test _extract_response_outcome_stats counts entities with actions."""
    mock_state = MagicMock()
    mock_state.messages = [
        {
            "entity_card": {
                "entity_type": "task",
                "entity_id": "task-1",
                "schema_version": "1.0",
                "secondary_actions": ["complete", "archive"],
            }
        }
    ]
    mock_state.context_data = {}

    result = orchestrator._extract_response_outcome_stats(mock_state)

    assert result["task_count"] == 1
    assert result["execution_count"] == 1


def test_extract_response_outcome_stats_deduplicates_entities(orchestrator):
    """Test _extract_response_outcome_stats deduplicates entities by key."""
    mock_state = MagicMock()
    mock_state.messages = [
        {
            "entity_card": {
                "entity_type": "task",
                "entity_id": "task-1",
                "schema_version": "1.0",
            }
        },
        {
            "entity_card": {
                "entity_type": "task",
                "entity_id": "task-1",
                "schema_version": "1.0",
            }
        },
    ]
    mock_state.context_data = {}

    result = orchestrator._extract_response_outcome_stats(mock_state)

    # Same entity should only be counted once
    assert result["task_count"] == 1


def test_roundtrip_ms_calculates_elapsed_time(orchestrator):
    """Test time calculation for elapsed milliseconds."""
    import time

    from app.orchestration.observability_mixin import ObservabilityMixin

    started_at = time.perf_counter()
    time.sleep(0.01)  # Sleep 10ms

    # Use the method from ObservabilityMixin
    mixin = ObservabilityMixin()
    result = mixin._roundtrip_ms(started_at)

    # Should be approximately 10ms (with some tolerance)
    assert result >= 8
    assert result < 50  # Upper bound for safety


def test_roundtrip_ms_returns_zero_for_future_time(orchestrator):
    """Test time calculation returns 0 for future start time."""
    import time

    from app.orchestration.observability_mixin import ObservabilityMixin

    future_time = time.perf_counter() + 1000

    mixin = ObservabilityMixin()
    result = mixin._roundtrip_ms(future_time)

    # Should return 0 instead of negative
    assert result == 0


def test_capability_selection_metadata_stays_in_response_metadata(orchestrator):
    metadata = orchestrator._capability_selection_metadata(
        {
            "capability_selection_report": {
                "summary": {
                    "retrieval_mode": "user_materials_first",
                    "preferred_model_tier": "standard",
                },
                "why_this_path": "Used your materials first because this turn needed grounded evidence.",
            }
        }
    )

    assert "capability_selection_report" in metadata
    assert "capability_selection_summary" in metadata
    assert metadata["why_this_path"].startswith("Used your materials first")


def test_dual_core_response_metadata_exposes_decision_and_structured_adjustments(orchestrator):
    metadata = orchestrator._dual_core_response_metadata(
        {
            "dual_core_decision": {
                "mode": "cognitive_first",
                "reason": "high cognitive load",
                "cognitive_adjustments": ["先降负荷"],
                "structured_adjustments": [
                    {
                        "dimension": "explanation_depth",
                        "value": "shallow",
                        "reason": "cognitive load is high",
                        "evidence": ["state_register:cognitive_load"],
                        "scope": "turn",
                        "user_visible": True,
                        "ttl": None,
                    }
                ],
                "execution_constraints": ["不要一次给超过一个任务"],
            }
        }
    )

    assert json.loads(metadata["dual_core_decision"])["mode"] == "cognitive_first"
    structured = json.loads(metadata["structured_cognitive_adjustments"])
    assert structured[0]["dimension"] == "explanation_depth"


def test_unified_aurora_receipts_normalize_all_receipt_lanes(orchestrator):
    metadata = {
        "adaptation_summary": json.dumps(
            {
                "title": "我刚做了一个调整",
                "summary": "这轮改成更短的推进方式。",
                "what_changed": ["降低解释密度"],
            },
            ensure_ascii=False,
        ),
        "memory_reference_receipt": json.dumps(
            {
                "response_id": "resp-1",
                "used_count": 1,
                "decision_reason": "Aurora 引用了相关记忆。",
                "referenced_memories": [{"id": "mem-1", "content": "明天考高数"}],
            },
            ensure_ascii=False,
        ),
        "context_receipt": json.dumps(
            {
                "used_count": 1,
                "used_names": ["线性代数课件"],
                "decision_reason": "已优先引用课件",
            },
            ensure_ascii=False,
        ),
        "spine_receipt": json.dumps(
            {
                "receipt_id": "rcpt-1",
                "summary": "已把下一步拆小。",
                "correctable": True,
                "correction_options": ["这个判断不准确"],
            },
            ensure_ascii=False,
        ),
    }

    receipts = orchestrator._build_unified_aurora_receipts(metadata)

    assert [receipt["receipt_type"] for receipt in receipts] == [
        "aurora_experience_receipt",
        "memory_reference_receipt",
        "source_context_receipt",
        "next_action_changed_by_aurora",
    ]
    assert receipts[0]["what_changed"] == ["降低解释密度"]
    assert receipts[1]["referenced_memories"][0]["content"] == "明天考高数"
    assert receipts[2]["source_key"] == "context_receipt"
    assert receipts[3]["correction_actions"][0]["label"] == "这个判断不准确"


def test_unified_aurora_receipts_keep_social_receipt_privacy_boundary(orchestrator):
    metadata = {
        "social_context_receipt": {
            "type": "social_context_receipt",
            "used_count": 1,
            "used_names": ["学习伙伴动态"],
            "decision_reason": "参考了学习伙伴的动态",
            "privacy_boundary": "只使用匿名角色标签，不展示伙伴姓名、原文或联系方式。",
        }
    }

    receipts = orchestrator._build_unified_aurora_receipts(metadata)

    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["receipt_type"] == "source_context_receipt"
    assert receipt["source_kind"] == "social"
    assert receipt["privacy_boundary"] == "只使用匿名角色标签，不展示伙伴姓名、原文或联系方式。"
    assert "不需要参考他的进度" in receipt["correction_actions"][0]["label"]


def test_aurora_everyday_presence_becomes_correctable_receipt(orchestrator):
    metadata = orchestrator._aurora_everyday_presence_metadata(
        {
            "aurora_everyday_presence": {
                "overall_status": "needs_confirm",
                "summary": "Aurora 有一个判断需要你确认。",
                "chat_hint": "我可能在误读当前状态：你现在更像是卡在不会做，而不是没时间。",
                "uncertainty_level": "high",
                "scene_alignment": "matched",
                "evidence_chain": ["最近两次任务都停在第一步", "薄弱点：TCP 状态机"],
                "memory_references": ["最近目标锚点：把 TCP 状态迁移彻底吃透"],
                "next_step_suggestion": "先确认卡住原因，再拆一个 10 分钟动作。",
                "last_correction_effect": {
                    "visible": True,
                    "affected_state_keys": ["difficulty_assumption", "support_level"],
                },
                "should_surface": True,
            }
        }
    )

    assert "aurora_everyday_presence" in metadata
    receipts = orchestrator._build_unified_aurora_receipts(metadata)

    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["receipt_type"] == "aurora_experience_receipt"
    assert receipt["source_key"] == "aurora_everyday_presence"
    assert receipt["uncertainty_level"] == "high"
    assert "误读当前状态" in receipt["summary"]
    assert receipt["evidence_chain"][0] == "最近两次任务都停在第一步"
    assert receipt["correction_actions"][0]["label"] == "这个判断不对"


def test_aurora_everyday_presence_stays_quiet_when_not_needed(orchestrator):
    metadata = orchestrator._aurora_everyday_presence_metadata(
        {
            "aurora_everyday_presence": {
                "chat_hint": "我会按当前目标继续推进。",
                "should_surface": False,
            }
        }
    )

    assert metadata == {}


def test_goal_realization_context_metadata_exports_vertical_packets(orchestrator):
    metadata = orchestrator._goal_realization_metadata(
        {
            "goal_realization_context": {
                "active_goal": {"id": "goal-1", "title": "零基础通过考试"},
                "aurora": {"current_read": "用户更像是卡在不会做，而不是没时间。"},
                "source_receipt": {
                    "context_plan_mode": "targeted_source_rag",
                    "answer_basis": "source_grounded",
                },
                "graph_trace": {
                    "decision_scope": "goal_realization_turn",
                    "affects": ["next_task", "rag_scope", "plan_feasibility", "aurora_read"],
                },
                "user_visible_summary": "当前目标：零基础通过考试",
            }
        }
    )

    assert "goal_realization_context" in metadata
    assert "aurora_experience_packet" in metadata
    assert "knowledge_source_receipt" in metadata
    assert "graph_decision_trace" in metadata
    assert metadata["goal_realization_summary"] == "当前目标：零基础通过考试"
    assert "不会做" in metadata["aurora_experience_packet"]


def test_semantic_control_trace_metadata_is_emitted(orchestrator):
    metadata = orchestrator._semantic_control_trace_metadata(
        {
            "situation_brief": {
                "semantic_control": {
                    "selected_terms": [{"term": "experience_mode", "value": "clarify"}],
                    "rendered_doctrine_summary": {"summary": "Ask one high-value question first."},
                    "response_contract": {"should_ask_high_value_question_first": True},
                    "compliance_expectations": {"expect_explicit_unlock_question": True},
                }
            }
        }
    )

    assert "semantic_control_trace" in metadata
    assert "clarify" in metadata["semantic_control_trace"]
    trace = json.loads(metadata["semantic_control_trace"])
    assert "observed_compliance_flags" not in trace


def test_semantic_control_trace_metadata_includes_observed_flags_only_when_present(orchestrator):
    metadata = orchestrator._semantic_control_trace_metadata(
        {
            "situation_brief": {
                "semantic_control": {
                    "selected_terms": [{"term": "experience_mode", "value": "clarify"}],
                    "rendered_doctrine_summary": {"summary": "Ask one high-value question first."},
                    "response_contract": {"should_ask_high_value_question_first": True},
                    "compliance_expectations": {"expect_explicit_unlock_question": True},
                }
            },
            "semantic_control_compliance": {
                "checks": {
                    "clarify_question_first": True,
                }
            },
        }
    )

    trace = json.loads(metadata["semantic_control_trace"])
    assert trace["observed_compliance_flags"] == {"clarify_question_first": True}
    assert trace["observed_compliance_source"] == "plan_quality_gate"
