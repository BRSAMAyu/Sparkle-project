from __future__ import annotations

import json

from app.services.analytics.signal_inventory import ProductionSignalInventory


def test_configured_signal_inventory_lists_real_code_paths() -> None:
    inventory = ProductionSignalInventory.configured_inventory()

    assert inventory["evidence_route_count"] > 0
    assert inventory["evidence_source_counts"]["heuristic_fallback"] >= 1
    assert inventory["evidence_source_counts"]["outcome"] >= 1
    assert inventory["evidence_target_counts"]["cognitive_load"] >= 1
    assert inventory["evidence_target_counts"]["task_completion_state"] >= 1
    assert inventory["reward_signal_counts"]["task.completed"] == 1
    assert inventory["reward_signal_counts"]["task.abandoned"] == 1
    assert inventory["reward_category_counts"]["task_outcome"] == 2
    assert inventory["reward_category_counts"]["chat_feedback"] == 2
    assert inventory["currently_missing_or_weak"]


def test_observed_signal_inventory_reads_trace_breakdowns() -> None:
    traces = [
        json.dumps(
            {
                "outcome": "task_completion",
                "reward": {"signal_type": "task.completed", "reward_category": "task_outcome"},
                "belief_source_breakdown": {
                    "total": {"outcome": 2, "conversational_implicit": 1},
                    "by_target": {
                        "task_completion_state": {"outcome": 1},
                        "execution_capacity": {"outcome": 1, "conversational_implicit": 1},
                    },
                },
            }
        )
    ]

    observed = ProductionSignalInventory.observed_from_traces(traces)

    assert observed["total_traces"] == 1
    assert observed["observed_reward_signal_counts"]["task.completed"] == 1
    assert observed["observed_reward_category_counts"]["task_outcome"] == 1
    assert observed["observed_evidence_source_counts"]["outcome"] == 2
    assert observed["observed_target_evidence_counts"]["execution_capacity"] == 2
