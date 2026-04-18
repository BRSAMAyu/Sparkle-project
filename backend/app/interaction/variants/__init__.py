"""Variant-specific prompt/render profile builders."""

from __future__ import annotations

from app.aurora.schemas import InteractionModelConfig, InteractionModelVariant

from ..profiles import InteractionVariantProfile
from .default_conversation import build_profile as build_default_conversation_profile
from .holding_mode import build_profile as build_holding_mode_profile
from .meta_reflection import build_profile as build_meta_reflection_profile
from .task_execution import build_profile as build_task_execution_profile

PROFILE_BUILDERS = {
    InteractionModelVariant.DEFAULT_CONVERSATION: build_default_conversation_profile,
    InteractionModelVariant.TASK_EXECUTION: build_task_execution_profile,
    InteractionModelVariant.META_REFLECTION: build_meta_reflection_profile,
    InteractionModelVariant.HOLDING_MODE: build_holding_mode_profile,
}


def load_variant_profile(
    variant: InteractionModelVariant,
    config: InteractionModelConfig,
) -> InteractionVariantProfile:
    """Load the runtime profile for a given interaction variant."""

    try:
        builder = PROFILE_BUILDERS[variant]
    except KeyError as exc:
        raise ValueError(f"Unsupported interaction variant: {variant.value}") from exc
    return builder(config)
