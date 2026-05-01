"""Interaction-layer UX signal projection helpers."""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import AuroraPresenceLevel, UXIntent
from app.config.aurora import aurora_flags


@dataclass(frozen=True)
class AuroraUxProjection:
    """Stable projection of Aurora state into UI-facing signals."""

    enabled: bool
    presence_level: AuroraPresenceLevel
    ux_intent: UXIntent
    mirror_bar_pulse: bool
    pulse_intensity: float
    conversation_frame: str
    aura_message: str
    allow_companion_affordance: bool
    allow_task_affordance: bool
    allow_reflection_affordance: bool


def _projection_for_presence(
    presence_level: AuroraPresenceLevel,
    ux_intent: UXIntent,
) -> tuple[bool, float, str, str, bool, bool, bool]:
    if ux_intent == UXIntent.HOLDING:
        return True, 0.58, "holding", "holding_support", True, False, False
    if presence_level == AuroraPresenceLevel.META_SURFACE:
        return True, 0.92, "meta_dialogue", "meta_surface", True, False, True
    if ux_intent in {UXIntent.META_SURFACE, UXIntent.RECONCILIATION, UXIntent.IDENTITY_MOMENT}:
        return True, 0.78, "meta_dialogue", "meta_reflection", True, False, True
    if ux_intent == UXIntent.ACTIVE_ADJUSTMENT or presence_level == AuroraPresenceLevel.ACTIVE:
        return True, 0.66, "active_update", "active_presence", False, True, False
    return False, 0.18, "conversation", "ambient", False, False, False


def project_ux_signals(
    presence_level: AuroraPresenceLevel,
    ux_intent: UXIntent,
    *,
    enabled: bool | None = None,
) -> AuroraUxProjection:
    """Project Aurora presence into a deterministic UI signal bundle."""

    gate_enabled = enabled if enabled is not None else bool(aurora_flags.INTERACTION_VARIANTS)
    if not gate_enabled:
        return AuroraUxProjection(
            enabled=False,
            presence_level=presence_level,
            ux_intent=ux_intent,
            mirror_bar_pulse=False,
            pulse_intensity=0.0,
            conversation_frame="legacy",
            aura_message="interaction_variants_disabled",
            allow_companion_affordance=False,
            allow_task_affordance=False,
            allow_reflection_affordance=False,
        )

    mirror_bar_pulse, pulse_intensity, conversation_frame, aura_message, allow_companion, allow_task, allow_reflection = (
        _projection_for_presence(presence_level, ux_intent)
    )
    return AuroraUxProjection(
        enabled=True,
        presence_level=presence_level,
        ux_intent=ux_intent,
        mirror_bar_pulse=mirror_bar_pulse,
        pulse_intensity=pulse_intensity,
        conversation_frame=conversation_frame,
        aura_message=aura_message,
        allow_companion_affordance=allow_companion,
        allow_task_affordance=allow_task,
        allow_reflection_affordance=allow_reflection,
    )
