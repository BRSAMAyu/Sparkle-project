"""Interaction model configuration loading helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.aurora.schemas import AuroraPolicyVersion, InteractionModelConfig, InteractionModelVariant


class InteractionModelConfigLoadError(RuntimeError):
    """Raised when a requested interaction model config cannot be resolved."""


def load_interaction_model_registry(
    policy_version: AuroraPolicyVersion,
) -> dict[InteractionModelVariant, InteractionModelConfig]:
    """Return the interaction registry keyed by variant."""

    registry: dict[InteractionModelVariant, InteractionModelConfig] = {}
    for config in policy_version.interaction_model_registry:
        if config.variant in registry:
            raise InteractionModelConfigLoadError(
                f"Duplicate interaction model registry entry for {config.variant.value}"
            )
        registry[config.variant] = config
    return registry


def load_interaction_model_config(
    policy_version: AuroraPolicyVersion,
    variant: InteractionModelVariant,
) -> InteractionModelConfig:
    """Resolve a single interaction model config from the frozen policy registry."""

    registry = load_interaction_model_registry(policy_version)
    try:
        return registry[variant]
    except KeyError as exc:
        raise InteractionModelConfigLoadError(
            f"Interaction model config not found for variant {variant.value}"
        ) from exc


def normalize_variant_names(values: Iterable[str] | None) -> frozenset[str]:
    """Normalize feature flag values into a case-insensitive variant allowlist."""

    if values is None:
        return frozenset()
    return frozenset(item.strip().lower() for item in values if str(item).strip())


@dataclass(frozen=True)
class InteractionVariantFeatureGate:
    """Snapshot of the interaction variant allowlist."""

    enabled_variants: frozenset[str]

    @property
    def enabled(self) -> bool:
        return bool(self.enabled_variants)

    def allows(self, variant: InteractionModelVariant | str) -> bool:
        token = variant.value if isinstance(variant, InteractionModelVariant) else str(variant)
        return token.strip().lower() in self.enabled_variants
