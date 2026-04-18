"""Aurora feature flag configuration."""

from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.settings import backend_env_path, repo_env_path, service_env_path


class AuroraFlags(BaseSettings):
    """Default-safe Aurora feature flags."""

    model_config = SettingsConfigDict(
        env_file=[repo_env_path, service_env_path, backend_env_path],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    AURORA_SHADOW_MODE: bool = Field(
        default=False,
        validation_alias=AliasChoices("AURORA_SHADOW_MODE"),
    )
    AURORA_ACTIVE: bool = Field(
        default=False,
        validation_alias=AliasChoices("AURORA_ACTIVE"),
    )
    INTERACTION_VARIANTS: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("INTERACTION_VARIANTS"),
    )

    @field_validator("INTERACTION_VARIANTS", mode="before")
    @classmethod
    def _parse_variants(cls, value):
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return value

    @property
    def any_aurora_enabled(self) -> bool:
        return self.AURORA_SHADOW_MODE or self.AURORA_ACTIVE

    def interaction_variant_enabled(self, variant: str) -> bool:
        normalized = variant.strip().lower()
        return normalized in {item.strip().lower() for item in self.INTERACTION_VARIANTS}


aurora_flags = AuroraFlags()
