"""Default conversational interaction variant."""

from __future__ import annotations

from app.aurora.schemas import InteractionModelConfig

from ..profiles import InteractionVariantProfile, build_interaction_variant_profile


def build_profile(config: InteractionModelConfig) -> InteractionVariantProfile:
    return build_interaction_variant_profile(
        config,
        system_prompt=(
            "Stay warm, direct, and conversational. "
            "Reflect Aurora context only when it helps the user move forward."
        ),
        render_mode="chat",
        response_shape="conversational",
        temperature=0.45,
        max_output_tokens=900,
        tool_policy="gentle_guidance",
        render_hints={
            "show_aurora_presence": True,
            "show_context_injection": True,
            "supports_short_back_and_forth": True,
        },
    )
