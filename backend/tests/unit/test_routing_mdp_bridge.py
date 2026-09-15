from __future__ import annotations

from app.orchestration.rl.routing_mdp import (
    ROUTING_TARGETS,
    RoutingMDPBridge,
    RoutingRewardSignal,
    RoutingRewardSource,
)
from app.services.analytics.user_state_model import RoutingMode, SimulatedOutcome, UserArchetype
from app.services.evidence.belief_state import BeliefState


def test_routing_state_vector_flattens_belief_context() -> None:
    state = BeliefState(user_id="u1")
    for target in ROUTING_TARGETS:
        variable = state.get_variable(target)
        variable.mean = 0.7
        variable.variance = 0.08

    vector = RoutingMDPBridge.state_from_belief(
        state,
        user_archetype=UserArchetype.FRAGILE.value,
        step_index=3,
    )

    assert len(vector.to_feature_vector()) == 17
    assert vector.user_archetype == "fragile"
    assert vector.step_index == 3
    assert vector.support_pressure > 0.0
    assert vector.context_bucket


def test_routing_action_converts_to_sim_action() -> None:
    action = RoutingMDPBridge.action_from_mode(RoutingMode.COGNITIVE_FIRST)

    sim_action = action.to_sim_action()

    assert action.arm.value == "cognitive_first"
    assert sim_action.mode == RoutingMode.COGNITIVE_FIRST
    assert sim_action.supportiveness > sim_action.directness


def test_routing_reward_marks_simulator_as_non_training() -> None:
    reward = RoutingRewardSignal.from_simulated_outcome(
        SimulatedOutcome.FORCED_ABANDON,
        next_state={"emotional_block": 0.95, "task_aversion": 0.9},
    )

    assert reward.reward == -2.0
    assert reward.source == RoutingRewardSource.SIMULATED_WIND_TUNNEL
    assert reward.training_eligible is False
    assert reward.simulated_only is True


def test_routing_wind_tunnel_recipe_runs_adversarial_case() -> None:
    recipe = RoutingMDPBridge.adversarial_recipes(steps=4, seed=5)[0]

    report = RoutingMDPBridge.run_wind_tunnel_recipe(recipe, action_mode=RoutingMode.EXECUTION_FIRST)

    assert report["schema_version"] == "routing_wind_tunnel_recipe.v1"
    assert report["simulated_only"] is True
    assert report["steps_run"] > 0
    assert "final_ground_truth" in report
