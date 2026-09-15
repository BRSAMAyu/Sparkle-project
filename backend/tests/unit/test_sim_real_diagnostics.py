from __future__ import annotations

import json

from app.services.analytics.sim_real_diagnostics import SimRealDiagnostics


def test_sim_real_diagnostics_extracts_vectors_and_reports_distance() -> None:
    traces = [
        json.dumps(
            {
                "belief_state_vector": {
                    "emotional_block_mean": 0.2,
                    "task_aversion_mean": 0.3,
                    "cognitive_load_mean": 0.4,
                }
            }
        ),
        json.dumps(
            {
                "belief_state_vector": {
                    "emotional_block_mean": 0.3,
                    "task_aversion_mean": 0.35,
                    "cognitive_load_mean": 0.45,
                }
            }
        ),
    ]
    sim_steps = [
        {
            "belief_estimate": {
                "emotional_block": 0.25,
                "task_aversion": 0.32,
                "cognitive_load": 0.42,
            }
        },
        {
            "belief_estimate": {
                "emotional_block": 0.35,
                "task_aversion": 0.4,
                "cognitive_load": 0.5,
            }
        },
    ]

    real_vectors = SimRealDiagnostics.vectors_from_traces(traces)
    sim_vectors = SimRealDiagnostics.vectors_from_simulation_steps(sim_steps)
    report = SimRealDiagnostics().evaluate(real_vectors=real_vectors, sim_vectors=sim_vectors).to_dict()

    assert len(real_vectors) == 2
    assert len(sim_vectors) == 2
    assert report["diagonal_w2"] > 0.0
    assert report["stress_cluster_w2"] > 0.0
    assert {item["target"] for item in report["target_diagnostics"]} == {
        "emotional_block",
        "task_aversion",
        "cognitive_load",
    }
    assert "policy-effectiveness proof" in report["caveat"]
