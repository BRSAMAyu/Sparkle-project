from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.core.metrics import KILL_SWITCH_MODE


TRI_STATE_MODES = frozenset({"off", "shadow", "live"})
_MODE_ALIASES = {
    "0": "off",
    "1": "live",
    "false": "off",
    "no": "off",
    "off": "off",
    "on": "live",
    "shadow": "shadow",
    "true": "live",
    "yes": "live",
    "live": "live",
    "live_canary": "live",
}


@dataclass(frozen=True)
class KillSwitchBinding:
    stage: str
    feature: str
    redis_key: str
    settings_attr: str | None = None
    legacy_bool_attr: str | None = None
    fallback_mode: str = "off"
    enabled_mode: str = "live"
    allowed_modes: frozenset[str] = TRI_STATE_MODES
    enabled_legacy_modes: frozenset[str] = frozenset({"shadow", "live"})


def normalize_mode(
    value: Any,
    *,
    allowed_modes: frozenset[str] = TRI_STATE_MODES,
    fallback: str = "off",
) -> str:
    normalized = str(value if value is not None else fallback).strip().lower()
    normalized = _MODE_ALIASES.get(normalized, normalized)
    if normalized not in allowed_modes:
        return fallback
    return normalized


def mode_value(mode: str) -> int:
    normalized = normalize_mode(mode)
    if normalized == "live":
        return 2
    if normalized == "shadow":
        return 1
    return 0


def is_enabled_mode(mode: str) -> bool:
    return normalize_mode(mode) in {"shadow", "live"}


def is_live_mode(mode: str) -> bool:
    return normalize_mode(mode) == "live"


def record_mode_gauge(stage: str, feature: str, mode: str) -> None:
    KILL_SWITCH_MODE.labels(stage=stage, feature=feature).set(mode_value(mode))


def resolve_settings_mode(binding: KillSwitchBinding) -> str:
    if binding.settings_attr:
        raw_setting = getattr(settings, binding.settings_attr, None)
        configured = normalize_mode(
            raw_setting,
            allowed_modes=binding.allowed_modes,
            fallback=binding.fallback_mode,
        )
        if binding.legacy_bool_attr and configured == binding.fallback_mode:
            if bool(getattr(settings, binding.legacy_bool_attr, False)):
                return binding.enabled_mode
        if configured in binding.allowed_modes:
            return configured

    if binding.legacy_bool_attr:
        if bool(getattr(settings, binding.legacy_bool_attr, False)):
            return binding.enabled_mode
        return "off"

    return binding.fallback_mode


async def read_mode(
    *,
    redis_client,
    prefix: str,
    binding: KillSwitchBinding,
    record_gauge: bool = True,
) -> str:
    mode = resolve_settings_mode(binding)
    if redis_client is not None:
        raw = await redis_client.get(f"{prefix}{binding.redis_key}")
        if raw is not None:
            mode = normalize_mode(
                raw,
                allowed_modes=binding.allowed_modes,
                fallback=binding.fallback_mode,
            )
    if record_gauge:
        record_mode_gauge(binding.stage, binding.feature, mode)
    return mode


async def write_mode(
    *,
    redis_client,
    prefix: str,
    binding: KillSwitchBinding,
    mode: Any,
    record_gauge: bool = True,
) -> str:
    normalized = normalize_mode(
        mode,
        allowed_modes=binding.allowed_modes,
        fallback=binding.fallback_mode,
    )
    if redis_client is None:
        if binding.settings_attr:
            setattr(settings, binding.settings_attr, normalized)
        if binding.legacy_bool_attr:
            setattr(settings, binding.legacy_bool_attr, normalized in binding.enabled_legacy_modes)
    else:
        await redis_client.set(f"{prefix}{binding.redis_key}", normalized)

    if record_gauge:
        record_mode_gauge(binding.stage, binding.feature, normalized)
    return normalized
