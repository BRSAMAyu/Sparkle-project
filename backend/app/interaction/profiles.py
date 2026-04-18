"""Variant prompt/render profiles for the interaction layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.aurora.schemas import InteractionModelConfig, InteractionModelVariant


@dataclass(frozen=True)
class InteractionVariantProfile:
    """Runtime profile for a single interaction model variant."""

    variant: InteractionModelVariant
    policy_variant: str
    context_budget: int
    allowed_tools_base: tuple[str, ...]
    default_tone: str
    default_proactivity: float
    writable_policy_scope: tuple[str, ...]
    system_prompt: str
    render_mode: str
    response_shape: str
    temperature: float
    max_output_tokens: int
    tool_policy: str
    render_hints: dict[str, Any] = field(default_factory=dict)

    def prompt_block(self, *, user_message: str | None = None) -> str:
        """Return the prompt block the variant would inject into the LLM context."""

        lines = [
            self.system_prompt.strip(),
            f"tone={self.default_tone}",
            f"render_mode={self.render_mode}",
            f"response_shape={self.response_shape}",
            f"context_budget={self.context_budget}",
        ]
        if user_message:
            lines.append(f"user_message={user_message.strip()}")
        return "\n".join(line for line in lines if line)


def build_interaction_variant_profile(
    config: InteractionModelConfig,
    *,
    system_prompt: str,
    render_mode: str,
    response_shape: str,
    temperature: float,
    max_output_tokens: int,
    tool_policy: str,
    render_hints: dict[str, Any] | None = None,
) -> InteractionVariantProfile:
    """Create a runtime variant profile from a frozen policy config."""

    return InteractionVariantProfile(
        variant=config.variant,
        policy_variant=config.variant.value,
        context_budget=config.context_budget,
        allowed_tools_base=tuple(config.allowed_tools_base),
        default_tone=config.default_tone,
        default_proactivity=config.default_proactivity,
        writable_policy_scope=tuple(config.writable_policy_scope),
        system_prompt=system_prompt.strip(),
        render_mode=render_mode,
        response_shape=response_shape,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        tool_policy=tool_policy,
        render_hints=dict(render_hints or {}),
    )
