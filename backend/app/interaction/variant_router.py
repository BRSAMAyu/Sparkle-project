"""Pure interaction variant routing."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.aurora.schemas import (
    AuroraPolicyVersion,
    AuroraPresenceLevel,
    InteractionModelConfig,
    InteractionModelVariant,
    TransitionDecisionRecord,
    UXIntent,
)
from app.config.aurora import aurora_flags

from .config import (
    InteractionVariantFeatureGate,
    load_interaction_model_config,
    normalize_variant_names,
)
from .profiles import InteractionVariantProfile
from .variants import load_variant_profile


@dataclass(frozen=True)
class InteractionRoute:
    """Resolved interaction route derived from a TransitionDecisionRecord."""

    selected_variant: InteractionModelVariant
    config: InteractionModelConfig
    profile: InteractionVariantProfile
    enabled: bool
    reason: str


def _feature_gate(enabled_variants: Iterable[str] | None = None) -> InteractionVariantFeatureGate:
    if enabled_variants is None:
        enabled_variants = aurora_flags.INTERACTION_VARIANTS
    return InteractionVariantFeatureGate(normalize_variant_names(enabled_variants))


def _derive_variant_from_context(
    ux_intent: UXIntent,
    aurora_presence: AuroraPresenceLevel,
) -> tuple[InteractionModelVariant, str]:
    if ux_intent == UXIntent.HOLDING:
        return InteractionModelVariant.HOLDING_MODE, "ux_intent_holding"
    if aurora_presence == AuroraPresenceLevel.META_SURFACE:
        return InteractionModelVariant.META_REFLECTION, "aurora_presence_meta_surface"
    if ux_intent in {UXIntent.META_SURFACE, UXIntent.RECONCILIATION, UXIntent.IDENTITY_MOMENT}:
        return InteractionModelVariant.META_REFLECTION, f"ux_intent_{ux_intent.value}"
    if ux_intent == UXIntent.ACTIVE_ADJUSTMENT or aurora_presence == AuroraPresenceLevel.ACTIVE:
        return InteractionModelVariant.TASK_EXECUTION, "active_adjustment_or_active_presence"
    return InteractionModelVariant.DEFAULT_CONVERSATION, "routine_default"


def select_interaction_variant(
    tdr: TransitionDecisionRecord,
    *,
    ux_intent: UXIntent | None = None,
    aurora_presence: AuroraPresenceLevel | None = None,
) -> tuple[InteractionModelVariant, str]:
    """Choose a variant from TDR inputs with context-aware fallback rules."""

    context_ux_intent = ux_intent or tdr.ux_intent
    context_presence = aurora_presence or tdr.aurora_presence

    if tdr.interaction_model_variant != InteractionModelVariant.DEFAULT_CONVERSATION:
        return tdr.interaction_model_variant, "explicit_tdr_variant"

    return _derive_variant_from_context(context_ux_intent, context_presence)


def route_interaction_model(
    tdr: TransitionDecisionRecord,
    policy_version: AuroraPolicyVersion,
    *,
    ux_intent: UXIntent | None = None,
    aurora_presence: AuroraPresenceLevel | None = None,
    enabled_variants: Iterable[str] | None = None,
) -> InteractionRoute:
    """Resolve the runtime profile for a TDR without mutating orchestrator state."""

    selected_variant, reason = select_interaction_variant(
        tdr,
        ux_intent=ux_intent,
        aurora_presence=aurora_presence,
    )
    config = load_interaction_model_config(policy_version, selected_variant)
    profile = load_variant_profile(selected_variant, config)
    gate = _feature_gate(enabled_variants)
    return InteractionRoute(
        selected_variant=selected_variant,
        config=config,
        profile=profile,
        enabled=gate.allows(selected_variant),
        reason=reason,
    )
