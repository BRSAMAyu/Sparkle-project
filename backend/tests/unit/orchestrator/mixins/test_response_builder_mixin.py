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
                "primary_action": "start"
            }
        },
        {
            "entity_card": {
                "entity_type": "task",
                "entity_id": "task-2",
                "schema_version": "1.0",
            }
        }
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
                "secondary_actions": ["complete", "archive"]
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
        }
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
