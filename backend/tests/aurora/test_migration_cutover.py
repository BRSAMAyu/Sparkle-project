from __future__ import annotations

from unittest.mock import patch

from app.aurora.migration import (
    build_shadow_snapshot_from_routing_input,
    project_aurora_to_dual_core_mode,
    prepare_shadow_pre_response_formatting_hook,
    prepare_shadow_pre_tool_selection_hook,
    record_shadow_divergence_if_needed,
    resolve_cutover_state,
    route_dual_core_via_aurora,
)
from app.aurora.observability import AURORA_SHADOW_DIVERGENCE_TOTAL, AURORA_SHADOW_HOOK_TOTAL
from app.orchestration.dual_core_router import DualCoreDecision, DualCoreRoutingInput


def _routing_input(**overrides) -> DualCoreRoutingInput:
    payload = {
        "intent": "plan",
        "intent_confidence": 0.92,
        "information_sufficient": True,
        "primary_challenge_area": "execution",
        "recent_sentiment_distribution": {"neutral": 3},
        "has_active_plan": True,
        "plan_health_status": "healthy",
        "recent_task_feedback_distribution": {"just_right": 1},
        "session_length_preference": 25,
        "difficulty_preference": 0.5,
    }
    payload.update(overrides)
    return DualCoreRoutingInput(**payload)


def _shadow_counter_total() -> float:
    collected = AURORA_SHADOW_DIVERGENCE_TOTAL.collect()
    if not collected:
        return 0.0
    return sum(
        sample.value
        for sample in collected[0].samples
        if sample.name == "sparkle_aurora_shadow_divergence_total"
    )


def _shadow_hook_total(hook_point: str, trigger_point: str) -> float:
    collected = AURORA_SHADOW_HOOK_TOTAL.collect()
    if not collected:
        return 0.0
    return sum(
        sample.value
        for sample in collected[0].samples
        if sample.name == "sparkle_aurora_shadow_hook_total"
        and sample.labels.get("hook_point") == hook_point
        and sample.labels.get("trigger_point") == trigger_point
    )


def test_resolve_cutover_state_defaults_to_legacy_when_flags_are_off() -> None:
    with (
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE", False),
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_MODE", False),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE_USER_IDS", []),
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_USER_IDS", []),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE_COHORT_PERCENT", 0),
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_COHORT_PERCENT", 0),
    ):
        state = resolve_cutover_state("00000000-0000-0000-0000-000000000001")

    assert state.mode == "legacy"
    assert state.reason == "aurora_disabled_for_user"


def test_resolve_cutover_state_prefers_active_allowlist_over_shadow() -> None:
    user_id = "00000000-0000-0000-0000-000000000042"
    with (
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE", True),
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_MODE", True),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE_USER_IDS", [user_id]),
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_USER_IDS", [user_id]),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE_COHORT_PERCENT", 0),
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_COHORT_PERCENT", 100),
    ):
        state = resolve_cutover_state(user_id)

    assert state.mode == "active"
    assert state.reason == "active_cohort_selected"


def test_route_dual_core_via_aurora_projects_execution_first_for_clear_plan() -> None:
    result = route_dual_core_via_aurora(
        _routing_input(current_guidance="每天三步 25分钟 冲刺任务"),
        user_id="00000000-0000-0000-0000-000000000111",
    )

    assert result.projected_decision.mode == "execution_first"
    assert result.transition_decision.decision_type == "stay"
    assert result.snapshot.snapshot_hash.startswith("aurora_dual_core_")


def test_route_dual_core_via_aurora_projects_cognitive_first_for_emotional_block() -> None:
    routing_input = _routing_input(
        information_sufficient=False,
        primary_challenge_area="emotional",
        recent_sentiment_distribution={"stressed": 2},
        recent_task_feedback_distribution={"too_long": 1},
        emotional_block_detected=True,
    )
    result = route_dual_core_via_aurora(
        routing_input,
        user_id="00000000-0000-0000-0000-000000000222",
    )

    assert result.projected_decision.mode == "cognitive_first"
    assert project_aurora_to_dual_core_mode(result.snapshot, result.transition_decision, routing_input) == "cognitive_first"


def test_record_shadow_divergence_only_increments_when_modes_differ() -> None:
    before = _shadow_counter_total()
    diverged = record_shadow_divergence_if_needed(
        legacy_decision=DualCoreDecision("execution_first", "legacy", [], []),
        aurora_decision=DualCoreDecision("cognitive_first", "aurora", [], []),
        trigger_point="pre-node-routing",
        enabled=True,
    )
    after = _shadow_counter_total()
    same = record_shadow_divergence_if_needed(
        legacy_decision=DualCoreDecision("execution_first", "legacy", [], []),
        aurora_decision=DualCoreDecision("execution_first", "aurora", [], []),
        trigger_point="pre-node-routing",
        enabled=True,
    )

    assert diverged is True
    assert same is False
    assert after == before + 1


def test_build_shadow_snapshot_includes_behavioral_hints() -> None:
    snapshot = build_shadow_snapshot_from_routing_input(
        _routing_input(
            procrastination_pattern=True,
            cognitive_mode_suggested=True,
            emotional_block_detected=True,
        ),
        user_id="00000000-0000-0000-0000-000000000333",
    )

    summary = str(snapshot.core_signals["routing_summary"])
    assert "拖延回避" in summary
    assert "概念混淆" in summary
    assert "need help regroup" in summary


def test_shadow_hooks_are_flag_gated_and_shadow_only() -> None:
    routing_input = _routing_input(
        current_guidance="先把第一步压缩到 25 分钟",
        session_length_preference=25,
    )
    user_id = "00000000-0000-0000-0000-000000000444"

    with (
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_MODE", False),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE", False),
    ):
        before_hook = _shadow_hook_total("pre-tool-selection", "pre-tool-selection")
        before_response_hook = _shadow_hook_total("pre-response-formatting", "pre-response-formatting")

        assert (
            prepare_shadow_pre_tool_selection_hook(routing_input, user_id=user_id, enabled=True) is None
        )
        assert (
            prepare_shadow_pre_response_formatting_hook(routing_input, user_id=user_id, enabled=True) is None
        )

        after_hook = _shadow_hook_total("pre-tool-selection", "pre-tool-selection")
        after_response_hook = _shadow_hook_total("pre-response-formatting", "pre-response-formatting")

    assert after_hook == before_hook
    assert after_response_hook == before_response_hook

    with (
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_MODE", True),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE", False),
    ):
        before_tool = _shadow_hook_total("pre-tool-selection", "pre-tool-selection")
        before_response = _shadow_hook_total("pre-response-formatting", "pre-response-formatting")

        tool_observation = prepare_shadow_pre_tool_selection_hook(
            routing_input,
            user_id=user_id,
            enabled=True,
        )
        response_observation = prepare_shadow_pre_response_formatting_hook(
            routing_input,
            user_id=user_id,
            enabled=True,
        )

        after_tool = _shadow_hook_total("pre-tool-selection", "pre-tool-selection")
        after_response = _shadow_hook_total("pre-response-formatting", "pre-response-formatting")

    assert tool_observation is not None
    assert tool_observation.hook_point == "pre-tool-selection"
    assert tool_observation.trigger_point == "pre-tool-selection"
    assert response_observation is not None
    assert response_observation.hook_point == "pre-response-formatting"
    assert response_observation.trigger_point == "pre-response-formatting"
    assert after_tool == before_tool + 1
    assert after_response == before_response + 1

    with (
        patch("app.aurora.migration.aurora_flags.AURORA_SHADOW_MODE", True),
        patch("app.aurora.migration.aurora_flags.AURORA_ACTIVE", True),
    ):
        assert prepare_shadow_pre_tool_selection_hook(routing_input, user_id=user_id, enabled=True) is None
        assert prepare_shadow_pre_response_formatting_hook(routing_input, user_id=user_id, enabled=True) is None
