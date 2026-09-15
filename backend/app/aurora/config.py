"""Aurora runtime configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import aurora_flags


@dataclass(frozen=True)
class AuroraRuntimeConfig:
    """Frozen configuration snapshot for Aurora runtime helpers."""

    shadow_mode: bool = aurora_flags.AURORA_SHADOW_MODE
    active: bool = aurora_flags.AURORA_ACTIVE
    interaction_variants: tuple[str, ...] = tuple(aurora_flags.INTERACTION_VARIANTS)
    policy_directory: Path = Path(__file__).resolve().parent / "policies"
    default_policy_version: str = "v1.0"
    soft_timeout_ms: int = 250
    hard_timeout_ms: int = 900

    @property
    def any_enabled(self) -> bool:
        return self.shadow_mode or self.active

    @property
    def mode(self) -> str:
        if self.active:
            return "active"
        if self.shadow_mode:
            return "shadow"
        return "disabled"


DEFAULT_AURORA_CONFIG = AuroraRuntimeConfig()

