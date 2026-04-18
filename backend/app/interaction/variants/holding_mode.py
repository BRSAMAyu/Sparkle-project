"""Holding-mode interaction variant."""

from __future__ import annotations

from app.aurora.schemas import InteractionModelConfig

from ..profiles import InteractionVariantProfile, build_interaction_variant_profile


def build_profile(config: InteractionModelConfig) -> InteractionVariantProfile:
    return build_interaction_variant_profile(
        config,
        system_prompt=(
            "Prioritize containment, steadiness, and emotional support. "
            "Avoid task pressure, optimization language, or achievement pushes."
        ),
        render_mode="holding",
        response_shape="supportive",
        temperature=0.12,
        max_output_tokens=560,
        tool_policy="minimal_support",
        render_hints={
            "suppress_task_push": True,
            "show_pause_language": True,
            "prefer_validation": True,
        },
    )
