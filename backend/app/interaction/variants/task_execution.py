"""Task execution interaction variant."""

from __future__ import annotations

from app.aurora.schemas import InteractionModelConfig

from ..profiles import InteractionVariantProfile, build_interaction_variant_profile


def build_profile(config: InteractionModelConfig) -> InteractionVariantProfile:
    return build_interaction_variant_profile(
        config,
        system_prompt=(
            "Use a structured task frame. Keep the response concise, actionable, "
            "and optimized for execution over reflection."
        ),
        render_mode="task",
        response_shape="structured",
        temperature=0.15,
        max_output_tokens=650,
        tool_policy="structured_tooling",
        render_hints={
            "show_checklist": True,
            "show_deadlines": True,
            "prefer_bullets": True,
        },
    )
