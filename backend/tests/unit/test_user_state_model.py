from __future__ import annotations

import random

import pytest

from app.services.analytics.user_state_model import (
    InconsistentTrajectoryError,
    InternalState,
    RoutingAction,
    RoutingMode,
    SimulatedOutcome,
    UserArchetype,
    UserStateModel,
    UserTrait,
)


def test_archetype_traits_have_opposite_pressure_response() -> None:
    fragile = UserTrait.for_archetype(UserArchetype.FRAGILE, rng=random.Random(1))
    pressure_driven = UserTrait.for_archetype(UserArchetype.PRESSURE_DRIVEN, rng=random.Random(1))

    assert fragile.pressure_response < 0
    assert pressure_driven.pressure_response > 0
    assert fragile.vulnerability > pressure_driven.vulnerability


def test_execution_first_hurts_fragile_user_more_than_pressure_driven_user() -> None:
    initial = InternalState(
        emotional_block=0.35,
        cognitive_load=0.35,
        task_aversion=0.35,
        execution_capacity=0.55,
        goal_clarity=0.65,
        metacognition_accuracy=0.55,
    )
    fragile = UserStateModel(
        UserTrait.for_archetype(UserArchetype.FRAGILE, rng=random.Random(7), overrides={"baseline_noise": 0.0}),
        InternalState(**initial.to_dict()),
        rng_seed=7,
    )
    pressure_driven = UserStateModel(
        UserTrait.for_archetype(
            UserArchetype.PRESSURE_DRIVEN,
            rng=random.Random(7),
            overrides={"baseline_noise": 0.0},
        ),
        InternalState(**initial.to_dict()),
        rng_seed=7,
    )

    fragile_report = fragile.step(RoutingMode.EXECUTION_FIRST, context_pressure=0.8)
    pressure_report = pressure_driven.step(RoutingMode.EXECUTION_FIRST, context_pressure=0.8)

    assert fragile_report.next_state["emotional_block"] > pressure_report.next_state["emotional_block"]
    assert pressure_report.next_state["execution_capacity"] > fragile_report.next_state["execution_capacity"]


def test_cognitive_first_reduces_high_emotional_block_for_fragile_user() -> None:
    model = UserStateModel(
        UserTrait.for_archetype(UserArchetype.FRAGILE, overrides={"baseline_noise": 0.0}),
        InternalState(
            emotional_block=0.82,
            cognitive_load=0.68,
            task_aversion=0.62,
            execution_capacity=0.30,
            goal_clarity=0.40,
            metacognition_accuracy=0.45,
        ),
        rng_seed=11,
    )

    report = model.step(RoutingMode.COGNITIVE_FIRST, context_pressure=0.2)

    assert report.next_state["emotional_block"] < report.previous_state["emotional_block"]
    assert report.next_state["cognitive_load"] < report.previous_state["cognitive_load"]


def test_absorbing_state_triggers_and_locks_after_collapse_patience() -> None:
    model = UserStateModel(
        UserTrait.for_archetype(
            UserArchetype.FRAGILE,
            overrides={"baseline_noise": 0.0, "collapse_threshold": 0.80, "collapse_patience": 1},
        ),
        InternalState(
            emotional_block=0.86,
            cognitive_load=0.82,
            task_aversion=0.80,
            execution_capacity=0.20,
            goal_clarity=0.30,
            metacognition_accuracy=0.35,
        ),
        rng_seed=1,
    )

    first = model.step(RoutingMode.EXECUTION_FIRST, context_pressure=0.9)
    second = model.step(RoutingMode.BALANCED, context_pressure=0.1)

    assert first.outcome == SimulatedOutcome.FORCED_ABANDON
    assert first.absorbed is True
    assert second.outcome == SimulatedOutcome.FORCED_ABANDON
    assert second.next_state == first.next_state


def test_ground_truth_report_contains_llm_state_injection() -> None:
    model = UserStateModel.from_archetype(UserArchetype.AVOIDANT, rng_seed=3)

    report = model.generate_ground_truth_report()

    assert report["schema_version"] == "user_state_ground_truth.v1"
    assert report["true_state_vector"]["task_aversion"] >= 0.0
    assert "overrides generic helpful-assistant behavior" in report["llm_state_injection"]


def test_strict_guard_raises_on_severe_consistency_violation() -> None:
    model = UserStateModel(
        UserTrait.for_archetype(UserArchetype.MIXED, overrides={"baseline_noise": 0.0}),
        InternalState(
            emotional_block=0.95,
            cognitive_load=0.40,
            task_aversion=0.95,
            execution_capacity=0.95,
            goal_clarity=0.70,
            metacognition_accuracy=0.50,
        ),
        rng_seed=2,
        strict_guard=True,
    )

    with pytest.raises(InconsistentTrajectoryError):
        model.step(RoutingAction.from_mode(RoutingMode.BALANCED, supportiveness=0.5), context_pressure=0.5)


def test_from_persona_maps_keywords_to_archetype() -> None:
    model = UserStateModel.from_persona({"style": "拖延 avoid procrastination", "age": 18}, rng_seed=5)

    assert model.trait.archetype == UserArchetype.AVOIDANT
