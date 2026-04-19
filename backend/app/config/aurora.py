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
    AURORA_SHADOW_USER_IDS: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("AURORA_SHADOW_USER_IDS"),
    )
    AURORA_ACTIVE_USER_IDS: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("AURORA_ACTIVE_USER_IDS"),
    )
    AURORA_SHADOW_COHORT_PERCENT: int = Field(
        default=0,
        validation_alias=AliasChoices("AURORA_SHADOW_COHORT_PERCENT"),
    )
    AURORA_ACTIVE_COHORT_PERCENT: int = Field(
        default=0,
        validation_alias=AliasChoices("AURORA_ACTIVE_COHORT_PERCENT"),
    )
    INTERACTION_VARIANTS: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("INTERACTION_VARIANTS"),
    )
    AURORA_ROUTING_MODE_ENABLED: bool = Field(
        default=False,
        validation_alias=AliasChoices("AURORA_ROUTING_MODE_ENABLED"),
    )
    TASK_ASSISTANT_DORMANT_MODE: bool = Field(
        default=False,
        validation_alias=AliasChoices("TASK_ASSISTANT_DORMANT_MODE"),
    )

    @field_validator(
        "INTERACTION_VARIANTS",
        "AURORA_SHADOW_USER_IDS",
        "AURORA_ACTIVE_USER_IDS",
        mode="before",
    )
    @classmethod
    def _parse_variants(cls, value):
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        return value

    @field_validator("AURORA_SHADOW_COHORT_PERCENT", "AURORA_ACTIVE_COHORT_PERCENT", mode="after")
    @classmethod
    def _clamp_percentage(cls, value: int) -> int:
        return max(0, min(100, int(value)))

    @property
    def any_aurora_enabled(self) -> bool:
        return self.AURORA_SHADOW_MODE or self.AURORA_ACTIVE

    def interaction_variant_enabled(self, variant: str) -> bool:
        normalized = variant.strip().lower()
        return normalized in {item.strip().lower() for item in self.INTERACTION_VARIANTS}


aurora_flags = AuroraFlags()
