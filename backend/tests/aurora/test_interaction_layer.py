from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.aurora.schemas import (
    AuroraPresenceLevel,
    DecisionBasis,
    DecisionMechanism,
    ImpactClass,
    InitiationType,
    InteractionModelVariant,
    TransitionDecisionRecord,
    UXIntent,
)
from app.aurora.policy_loader import load_policy_version
from app.interaction import load_interaction_model_registry, project_ux_signals, route_interaction_model


def _build_tdr(
    *,
    variant: InteractionModelVariant,
    ux_intent: UXIntent,
    aurora_presence: AuroraPresenceLevel,
) -> TransitionDecisionRecord:
    return TransitionDecisionRecord(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        user_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        created_at=datetime(2026, 4, 17, 9, 0, 0),
        decision_type="stay",
        proposed_transition=None,
        initiation_type=InitiationType.REACTIVE,
        decision_mechanism=DecisionMechanism.DETERMINISTIC,
        decision_basis=DecisionBasis.MIXED,
        input_snapshot_ref="ss_ws5",
        impact_class=ImpactClass.MEDIUM,
        inference_knobs={"temperature": 0.3},
        capability_gate={"enabled": True},
        interaction_model_variant=variant,
        rollback_anchor={
            "prev_focus_contract_version": 3,
            "prev_active_commitment_ids": [],
            "prev_claim_statuses": {},
            "policy_version_at_decision": "aurora_policy@v1.0",
        },
        evidence_refs=["ws5_fixture"],
        policy_version="aurora_policy@v1.0",
        confirmed_by_user=None,
        user_feedback=None,
        ux_intent=ux_intent,
        aurora_presence=aurora_presence,
    )


def test_interaction_registry_loads_four_policy_configs() -> None:
    policy = load_policy_version("v1.0")

    registry = load_interaction_model_registry(policy)

    assert set(registry) == {
        InteractionModelVariant.DEFAULT_CONVERSATION,
        InteractionModelVariant.TASK_EXECUTION,
        InteractionModelVariant.META_REFLECTION,
        InteractionModelVariant.HOLDING_MODE,
    }
    assert registry[InteractionModelVariant.DEFAULT_CONVERSATION].context_budget == 1200
    assert registry[InteractionModelVariant.META_REFLECTION].default_tone == "reflective"


def test_variant_router_uses_explicit_variant_when_present() -> None:
    policy = load_policy_version("v1.0")
    tdr = _build_tdr(
        variant=InteractionModelVariant.TASK_EXECUTION,
        ux_intent=UXIntent.ROUTINE,
        aurora_presence=AuroraPresenceLevel.AMBIENT,
    )

    route = route_interaction_model(tdr, policy, enabled_variants=["task_execution"])

    assert route.selected_variant == InteractionModelVariant.TASK_EXECUTION
    assert route.enabled is True
    assert route.profile.response_shape == "structured"
    assert route.profile.tool_policy == "structured_tooling"


def test_variant_router_derives_meta_reflection_from_context() -> None:
    policy = load_policy_version("v1.0")
    tdr = _build_tdr(
        variant=InteractionModelVariant.DEFAULT_CONVERSATION,
        ux_intent=UXIntent.RECONCILIATION,
        aurora_presence=AuroraPresenceLevel.META_SURFACE,
    )

    route = route_interaction_model(
        tdr,
        policy,
        enabled_variants=["default_conversation", "meta_reflection"],
    )

    assert route.selected_variant == InteractionModelVariant.META_REFLECTION
    assert route.reason == "aurora_presence_meta_surface"
    assert route.enabled is True
    assert route.profile.temperature < 0.3
    assert "reconciliation" in route.profile.system_prompt.lower()


def test_variant_router_maps_holding_intent_to_holding_mode() -> None:
    policy = load_policy_version("v1.0")
    tdr = _build_tdr(
        variant=InteractionModelVariant.DEFAULT_CONVERSATION,
        ux_intent=UXIntent.HOLDING,
        aurora_presence=AuroraPresenceLevel.AMBIENT,
    )

    route = route_interaction_model(tdr, policy, enabled_variants=["holding_mode"])

    assert route.selected_variant == InteractionModelVariant.HOLDING_MODE
    assert route.enabled is True
    assert route.profile.tool_policy == "minimal_support"
    assert route.profile.render_mode == "holding"


def test_variant_router_is_inert_without_feature_gate() -> None:
    policy = load_policy_version("v1.0")
    tdr = _build_tdr(
        variant=InteractionModelVariant.DEFAULT_CONVERSATION,
        ux_intent=UXIntent.ACTIVE_ADJUSTMENT,
        aurora_presence=AuroraPresenceLevel.ACTIVE,
    )

    route = route_interaction_model(tdr, policy, enabled_variants=[])

    assert route.selected_variant == InteractionModelVariant.TASK_EXECUTION
    assert route.enabled is False


def test_ux_renderer_projects_stable_signals_when_enabled() -> None:
    ambient = project_ux_signals(
        AuroraPresenceLevel.AMBIENT,
        UXIntent.ROUTINE,
        enabled=True,
    )
    active = project_ux_signals(
        AuroraPresenceLevel.ACTIVE,
        UXIntent.ACTIVE_ADJUSTMENT,
        enabled=True,
    )
    meta = project_ux_signals(
        AuroraPresenceLevel.META_SURFACE,
        UXIntent.RECONCILIATION,
        enabled=True,
    )

    assert ambient.enabled is True
    assert ambient.conversation_frame == "conversation"
    assert ambient.mirror_bar_pulse is False
    assert active.conversation_frame == "active_update"
    assert active.mirror_bar_pulse is True
    assert active.allow_task_affordance is True
    assert meta.conversation_frame == "meta_dialogue"
    assert meta.allow_reflection_affordance is True
    assert meta.pulse_intensity > active.pulse_intensity


def test_ux_renderer_is_inert_when_feature_gate_is_off() -> None:
    projection = project_ux_signals(
        AuroraPresenceLevel.ACTIVE,
        UXIntent.ACTIVE_ADJUSTMENT,
        enabled=False,
    )

    assert projection.enabled is False
    assert projection.conversation_frame == "legacy"
    assert projection.mirror_bar_pulse is False
    assert projection.pulse_intensity == 0.0
