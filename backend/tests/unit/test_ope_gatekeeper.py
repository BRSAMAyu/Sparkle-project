from __future__ import annotations

import json

from app.services.analytics.ope_gatekeeper import OPEGatekeeper


def _trace(trace_id: str, actual: str, shadow: str, signal_type: str, reward: float) -> str:
    return json.dumps(
        {
            "trace_id": trace_id,
            "actual_router_mode": actual,
            "router_shadow_projection": {"shadow_mode": shadow},
            "outcome": signal_type.replace(".", "_"),
            "training_eligible": True,
            "reward": {
                "signal_type": signal_type,
                "outcome_label": signal_type,
                "total_reward": reward,
                "is_censored": False,
            },
        }
    )


def test_ope_gatekeeper_counts_labeled_disagreement_wins() -> None:
    traces = [
        _trace("a", "execution_first", "cognitive_first", "task.abandoned", -1.0),
        _trace("b", "execution_first", "cognitive_first", "task.abandoned", -1.0),
        _trace("c", "cognitive_first", "execution_first", "task.completed", 1.0),
        _trace("d", "balanced", "balanced", "task.completed", 1.0),
        json.dumps({"trace_id": "e", "actual_router_mode": "balanced"}),
    ]

    report = OPEGatekeeper(min_labeled_divergence=2).evaluate(traces).to_dict()

    assert report["comparable_traces"] == 4
    assert report["divergence_points"] == 3
    assert report["labeled_divergence_points"] == 3
    assert report["shadow_wins"] == 2
    assert report["production_wins"] == 1
    assert report["blockers"] == []


def test_ope_gatekeeper_blocks_unlabeled_data() -> None:
    traces = [
        json.dumps(
            {
                "actual_router_mode": "execution_first",
                "router_shadow_projection": {"shadow_mode": "cognitive_first"},
                "reward": {"signal_type": "unknown", "is_censored": True},
            }
        )
    ]

    report = OPEGatekeeper(min_labeled_divergence=2).evaluate(traces).to_dict()

    assert report["divergence_points"] == 1
    assert report["labeled_divergence_points"] == 0
    assert "insufficient_labeled_divergence_points" in report["blockers"]
