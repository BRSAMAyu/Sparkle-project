from __future__ import annotations

import random

from app.services.analytics.belief_recovery_simulator import (
    STATE_TARGETS,
    BeliefRecoverySimulator,
    ObservationModelConfig,
)
from app.services.analytics.user_state_model import InternalState, RoutingMode, UserArchetype


def test_belief_recovery_simulator_generates_ground_truth_evidence() -> None:
    simulator = BeliefRecoverySimulator(
        observation_config=ObservationModelConfig(noise_sigma=0.0, confidence=0.9)
    )
    state = InternalState(
        emotional_block=0.8,
        cognitive_load=0.7,
        task_aversion=0.6,
        execution_capacity=0.3,
        goal_clarity=0.4,
        metacognition_accuracy=0.5,
    )

    evidence = simulator.evidence_from_state(
        state,
        rng=random.Random(1),
        step_index=0,
        archetype=UserArchetype.FRAGILE.value,
    )

    assert len(evidence) == len(STATE_TARGETS)
    payloads = {item.target_latent_variable.value: item for item in evidence}
    assert payloads["emotional_block"].strength == 0.8
    assert payloads["emotional_block"].metadata["ground_truth"] == 0.8
    assert payloads["emotional_block"].scope["simulated"] is True


def test_belief_recovery_simulator_measures_recovery_error() -> None:
    simulator = BeliefRecoverySimulator(
        observation_config=ObservationModelConfig(noise_sigma=0.02, confidence=0.9)
    )

    report = simulator.run_batch(
        samples_per_archetype=2,
        steps=8,
        seed=9,
        policy=RoutingMode.BALANCED.value,
        archetypes=[UserArchetype.FRAGILE, UserArchetype.RESILIENT],
    )

    assert report["schema_version"] == "belief_recovery_simulation.v1"
    assert report["run_count"] == 4
    assert report["step_count"] > 0
    assert report["overall_mse"] < 0.04
    assert set(report["per_target"]) == set(STATE_TARGETS)
    assert report["avg_evidence_per_step"] == len(STATE_TARGETS)


def test_belief_recovery_simulator_can_drive_router_policy() -> None:
    simulator = BeliefRecoverySimulator(
        observation_config=ObservationModelConfig(noise_sigma=0.04, confidence=0.85)
    )

    report = simulator.run_batch(
        samples_per_archetype=1,
        steps=6,
        seed=14,
        policy="router",
        archetypes=[UserArchetype.FRAGILE, UserArchetype.PRESSURE_DRIVEN],
    )

    assert report["step_count"] > 0
    assert report["route_mode_counts"]
    assert all(mode in {"execution_first", "balanced", "cognitive_first"} for mode in report["route_mode_counts"])


def test_belief_recovery_simulator_supports_block_diagonal_fusion() -> None:
    simulator = BeliefRecoverySimulator(
        observation_config=ObservationModelConfig(noise_sigma=0.03, confidence=0.82, missing_rate=0.15),
        fusion_model="block_diagonal",
    )

    report = simulator.run_batch(
        samples_per_archetype=2,
        steps=8,
        seed=19,
        policy=RoutingMode.BALANCED.value,
        archetypes=[UserArchetype.FRAGILE, UserArchetype.AVOIDANT],
    )

    assert report["fusion_model"] == "block_diagonal"
    assert report["step_count"] > 0
    assert report["overall_mse"] < 0.08
