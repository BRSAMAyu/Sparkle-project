from __future__ import annotations

from app.services.analytics.observation_firewall import ObservationQualityFirewall


def test_observation_firewall_passes_plausible_real_trace_summary() -> None:
    real = {
        "comparable_traces": 80,
        "average_belief_mean_by_target": {
            "emotional_block": 0.42,
            "task_aversion": 0.38,
        },
        "average_evidence_per_trace": 3.1,
        "actual_mode_counts": {"execution_first": 30, "balanced": 30, "cognitive_first": 20},
    }
    sim = {
        "average_belief_mean_by_target": {
            "emotional_block": 0.48,
            "task_aversion": 0.41,
        },
        "avg_evidence_per_step": 6.0,
        "route_mode_counts": {"execution_first": 25, "balanced": 35, "cognitive_first": 20},
    }

    report = ObservationQualityFirewall(min_comparable_traces=20).evaluate(
        real_trace_summary=real,
        simulation_summary=sim,
    )

    assert report.passed is True
    assert report.to_dict()["recommendation"] == "eligible_for_ope"


def test_observation_firewall_blocks_sparse_and_mismatched_data() -> None:
    real = {
        "comparable_traces": 3,
        "average_belief_mean_by_target": {"emotional_block": 0.1},
        "average_evidence_per_trace": 0.5,
        "actual_mode_counts": {"execution_first": 10},
    }
    sim = {
        "average_belief_mean_by_target": {"emotional_block": 0.8},
        "avg_evidence_per_step": 6.0,
        "route_mode_counts": {"cognitive_first": 10},
    }

    report = ObservationQualityFirewall(min_comparable_traces=20).evaluate(
        real_trace_summary=real,
        simulation_summary=sim,
    ).to_dict()

    assert report["passed"] is False
    assert "insufficient_actual_shadow_comparable_traces" in report["blockers"]
    assert "sparse_real_evidence" in report["blockers"]
    assert "target_mean_level_mismatch:emotional_block" in report["blockers"]
    assert "action_distribution_mismatch:execution_first" in report["blockers"]
