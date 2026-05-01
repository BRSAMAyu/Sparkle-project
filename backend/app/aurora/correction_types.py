"""Unified Aurora correction payload contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


_DEFAULT_SURFACE = "chat"
_DEFAULT_SOURCE = "predicted_chip"


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _infer_surface(raw: Mapping[str, Any]) -> str:
    surface = _as_str(raw.get("surface"))
    if surface:
        return surface

    context_source = _as_str(raw.get("context_source") or raw.get("band_status"))
    lower_source = context_source.lower()
    if "dashboard" in lower_source or "home" in lower_source:
        return "dashboard"
    if "status_band" in lower_source or "band" in lower_source:
        return "status_band"
    if "push" in lower_source:
        return "push"
    if "core_session" in lower_source:
        return "core_session"
    return _DEFAULT_SURFACE


def _infer_source(raw: Mapping[str, Any]) -> str:
    source = _as_str(raw.get("source"))
    if source:
        return source

    legacy_type = _as_str(raw.get("type")).lower()
    is_freeform = _as_bool(raw.get("is_freeform"), default=legacy_type == "freeform")
    if is_freeform:
        return "freeform_input"
    if legacy_type in {"cooldown_override", "calibration_override"}:
        return "calibration_override"
    if legacy_type == "chip" or raw.get("chip_id"):
        return "predicted_chip"

    context_source = _as_str(raw.get("context_source"))
    return context_source or _DEFAULT_SOURCE


@dataclass(frozen=True)
class AuroraCorrectionPayload:
    """Normalized correction payload shared by dashboard, chat, status band, and push."""

    surface: str = _DEFAULT_SURFACE
    source: str = _DEFAULT_SOURCE
    semantic_value: str = "freeform_correction"
    label: str = ""
    freeform_text: str = ""
    is_freeform: bool = False
    is_disconfirming: bool = False
    band_status: str = ""
    telemetry_id: str = ""
    group_id: str = ""
    conversation_id: str = ""
    message_id: str = ""

    @classmethod
    def normalize(
        cls,
        raw: Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> "AuroraCorrectionPayload":
        """Build a complete payload from canonical or legacy correction fields."""
        data: dict[str, Any] = {}
        if raw:
            data.update(dict(raw))
        data.update({key: value for key, value in overrides.items() if value is not None})

        legacy_type = _as_str(data.get("type")).lower()
        freeform_text = _as_str(data.get("freeform_text"))
        is_freeform = _as_bool(data.get("is_freeform"), default=legacy_type == "freeform" or bool(freeform_text))
        semantic_value = _as_str(data.get("semantic_value")) or ("freeform_correction" if is_freeform else "unknown")

        return cls(
            surface=_infer_surface(data),
            source=_infer_source({**data, "is_freeform": is_freeform}),
            semantic_value=semantic_value,
            label=_as_str(data.get("label")),
            freeform_text=freeform_text,
            is_freeform=is_freeform,
            is_disconfirming=_as_bool(data.get("is_disconfirming"), default=is_freeform),
            band_status=_as_str(data.get("band_status")),
            telemetry_id=_as_str(data.get("telemetry_id")),
            group_id=_as_str(data.get("group_id")),
            conversation_id=_as_str(data.get("conversation_id") or data.get("session_id")),
            message_id=_as_str(data.get("message_id")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "source": self.source,
            "semantic_value": self.semantic_value,
            "label": self.label,
            "freeform_text": self.freeform_text,
            "is_freeform": self.is_freeform,
            "is_disconfirming": self.is_disconfirming,
            "band_status": self.band_status,
            "telemetry_id": self.telemetry_id,
            "group_id": self.group_id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
        }
