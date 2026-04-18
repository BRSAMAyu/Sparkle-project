"""Meta-reflection interaction variant."""

from __future__ import annotations

from app.aurora.schemas import InteractionModelConfig

from ..profiles import InteractionVariantProfile, build_interaction_variant_profile


def build_profile(config: InteractionModelConfig) -> InteractionVariantProfile:
    return build_interaction_variant_profile(
        config,
        system_prompt=(
            "Use a deeper reflective frame. Surface reconciliation, identity, "
            "and narrative coherence before moving toward action."
        ),
        render_mode="meta",
        response_shape="reflective",
        temperature=0.2,
        max_output_tokens=1100,
        tool_policy="deep_reflection",
        render_hints={
            "show_identity_prompt": True,
            "show_reason_chain": True,
            "invite_reconciliation": True,
        },
    )
