from __future__ import annotations

import json

from app.services.analytics.belief_trace_inspector import BeliefTraceInspector


def test_belief_trace_inspector_counts_disagreements_and_types() -> None:
    traces = [
        json.dumps(
            {
                "trace_id": "t1",
                "actual_router_mode": "execution_first",
                "router_shadow_projection": {
                    "shadow_mode": "cognitive_first",
                    "support_pressure_score": 0.82,
                    "execution_readiness_score": 0.41,
                },
                "outcome": "unknown",
                "reward": {"signal_type": "unknown", "reward_category": "unknown", "total_reward": 0.0},
                "belief_source_breakdown": {
                    "total": {"conversational_implicit": 2},
                    "by_target": {"emotional_block": {"conversational_implicit": 2}},
                },
                "evidence_metadata_summary": {
                    "cognitive_load_type_counts": {"extraneous": 1},
                    "stage_of_change_counts": {"preparation": 1},
                    "extraneous_load_rate": 1.0,
                    "same_source_correlation_discount_count": 2,
                    "same_source_correlation_group_count": 1,
                    "same_source_correlation_max_group_size": 3,
                },
                "belief_projection_diagnostics": {
                    "projected_target_count": 1,
                    "projected_targets": {
                        "emotional_block": {
                            "projected_mean": 1.0,
                            "unbounded_mean": 1.04,
                        }
                    },
                },
                "belief_uncertainty_vector": {"emotional_block": 0.21},
            }
        ),
        json.dumps(
            {
                "trace_id": "t2",
                "actual_router_mode": "cognitive_first",
                "router_shadow_projection": {"shadow_mode": "execution_first"},
                "outcome": "task_abandonment",
                "training_eligible": True,
                "reward": {"signal_type": "task.abandoned", "reward_category": "task_outcome", "total_reward": -1.0},
                "belief_variable_evidence_counts": {"task_aversion": 3},
                "belief_uncertainty_vector": {"task_aversion": 0.24},
            }
        ),
        json.dumps(
            {
                "trace_id": "t3",
                "actual_router_mode": "balanced",
                "router_shadow_projection": {"shadow_mode": "balanced"},
                "outcome": "task_completion",
                "training_eligible": True,
                "reward": {"signal_type": "task.completed", "reward_category": "task_outcome", "total_reward": 1.0},
                "belief_uncertainty_vector": {"goal_clarity": 0.05},
            }
        ),
        "not-json",
    ]

    summary = BeliefTraceInspector().summarize(traces)

    assert summary["total_traces"] == 4
    assert summary["parse_errors"] == 1
    assert summary["comparable_traces"] == 3
    assert summary["disagreements"] == 2
    assert summary["disagreement_type_counts"]["type_1_over_hard"] == 1
    assert summary["disagreement_type_counts"]["type_2_over_support"] == 1
    assert summary["observed_outcomes"] == 2
    assert summary["training_eligible_traces"] == 2
    assert summary["reward_signal_counts"]["task.completed"] == 1
    assert summary["reward_category_counts"]["task_outcome"] == 2
    assert summary["evidence_source_counts"]["conversational_implicit"] == 2
    assert summary["llm_evidence_count"] == 2
    assert summary["llm_evidence_rate"] == 1.0
    assert summary["heuristic_fallback_evidence_rate"] == 0.0
    assert summary["same_source_correlation_discount_count"] == 2
    assert summary["same_source_correlation_group_count"] == 1
    assert summary["same_source_correlation_max_group_size"] == 3
    assert summary["belief_projection_count"] == 1
    assert summary["belief_projection_target_counts"]["emotional_block"] == 1
    assert summary["target_evidence_counts"]["emotional_block"] == 2
    assert summary["target_evidence_counts"]["task_aversion"] == 3
    assert summary["cognitive_load_type_counts"]["extraneous"] == 1
    assert summary["stage_of_change_counts"]["preparation"] == 1
    assert summary["extraneous_load_rate"] == 1.0
    assert summary["absolute_quality"]["mode_outcome_counts"]["balanced"]["task_completion"] == 1
    assert summary["high_uncertainty_targets"][0] == ("task_aversion", 0.24)
    assert summary["f1_quality_gate"]["passed"] is True
    assert summary["examples"][0]["trace_id"] == "t1"


def test_belief_trace_inspector_reports_missing_fields() -> None:
    summary = BeliefTraceInspector().summarize([{"trace_id": "missing"}])

    assert summary["missing_field_counts"]["actual_router_mode"] == 1
    assert summary["missing_field_counts"]["router_shadow_projection.shadow_mode"] == 1
    assert summary["missing_field_counts"]["reward"] == 1
    assert summary["comparable_traces"] == 0
    assert summary["f1_quality_gate"]["passed"] is False


def test_belief_trace_inspector_blocks_f1_when_fallback_dominates() -> None:
    traces = [
        {
            "trace_id": "fallback",
            "actual_router_mode": "execution_first",
            "router_shadow_projection": {"shadow_mode": "balanced"},
            "reward": {"signal_type": "unknown", "reward_category": "unknown", "total_reward": 0.0},
            "belief_source_breakdown": {
                "total": {"heuristic_fallback": 4},
                "by_target": {"cognitive_load": {"heuristic_fallback": 4}},
            },
            "belief_variable_evidence_counts": {"cognitive_load": 4},
        }
    ]

    summary = BeliefTraceInspector().summarize(traces)

    assert summary["heuristic_fallback_evidence_rate"] == 1.0
    assert summary["llm_evidence_rate"] == 0.0
    assert "llm_evidence_rate_below_25_percent" in summary["f1_quality_gate"]["blockers"]
