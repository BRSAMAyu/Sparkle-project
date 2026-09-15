"""User-scoped OpenClaw connection profile storage and config resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import UUID

from app.adapters.openclaw.config import OpenClawConfig
from app.services.personalization.preference_service import PreferenceService

OPENCLAW_CONNECTION_PROFILE_KEY = "openclaw.connection.profile"
_SUPPORTED_TRANSPORTS = {"responses_http", "gateway_ws"}


def _normalize_url(value: str | None) -> str:
    return (value or "").strip().rstrip("/")


def _coerce_transport(value: str | None, *, default: str) -> str:
    transport = (value or "").strip() or default
    return transport if transport in _SUPPORTED_TRANSPORTS else default


def _coerce_http_url(gateway_url: str, ws_url: str) -> str:
    raw_url = _normalize_url(gateway_url) or _normalize_url(ws_url)
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower()
    if scheme == "ws":
        parsed = parsed._replace(scheme="http")
    elif scheme == "wss":
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed).rstrip("/")


def _coerce_ws_url(ws_url: str, gateway_url: str) -> str:
    raw_url = _normalize_url(ws_url) or _normalize_url(gateway_url)
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower()
    if scheme == "http":
        parsed = parsed._replace(scheme="ws")
    elif scheme == "https":
        parsed = parsed._replace(scheme="wss")
    return urlunparse(parsed).rstrip("/")


@dataclass(frozen=True)
class OpenClawConnectionProfile:
    gateway_url: str = ""
    auth_token: str = ""
    device_token: str = ""
    transport: str = "responses_http"
    ws_url: str = ""
    paired_at: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.gateway_url or self.ws_url)

    def to_payload(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "gateway_url": self.gateway_url,
            "auth_token": self.auth_token or None,
            "device_token": self.device_token or None,
            "transport": self.transport,
            "ws_url": self.ws_url or None,
            "paired_at": self.paired_at,
        }

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any] | None,
        *,
        default_transport: str = "responses_http",
    ) -> OpenClawConnectionProfile:
        payload = payload or {}
        gateway_url = _coerce_http_url(
            str(payload.get("gateway_url") or ""),
            str(payload.get("ws_url") or ""),
        )
        ws_url = _coerce_ws_url(
            str(payload.get("ws_url") or ""),
            str(payload.get("gateway_url") or ""),
        )
        return cls(
            gateway_url=gateway_url,
            auth_token=str(payload.get("auth_token") or "").strip(),
            device_token=str(payload.get("device_token") or "").strip(),
            transport=_coerce_transport(payload.get("transport"), default=default_transport),
            ws_url=ws_url,
            paired_at=(str(payload.get("paired_at") or "").strip() or None),
        )


class OpenClawConnectionProfileService:
    """Persist and resolve per-user OpenClaw connection profiles."""

    def __init__(self, db, redis=None):
        self._preference_service = PreferenceService(db, redis)

    async def get_profile(self, *, user_id: UUID) -> OpenClawConnectionProfile | None:
        prefs = await self._preference_service.get_preferences(user_id)
        explicit = dict(prefs.explicit or {})
        payload = explicit.get(OPENCLAW_CONNECTION_PROFILE_KEY)
        if not isinstance(payload, dict):
            return None
        profile = OpenClawConnectionProfile.from_payload(payload)
        return profile if profile.configured else None

    async def save_profile(
        self,
        *,
        user_id: UUID,
        payload: dict[str, Any],
    ) -> OpenClawConnectionProfile:
        profile = OpenClawConnectionProfile.from_payload(payload)
        await self._preference_service.update_explicit(
            user_id,
            {
                OPENCLAW_CONNECTION_PROFILE_KEY: profile.to_payload(),
            },
        )
        return profile

    async def clear_profile(self, *, user_id: UUID) -> None:
        await self._preference_service.delete_explicit_key(user_id, OPENCLAW_CONNECTION_PROFILE_KEY)

    async def resolve_config(
        self,
        *,
        user_id: UUID | None,
        fallback_config: OpenClawConfig,
    ) -> tuple[OpenClawConfig, str]:
        if user_id is None:
            return fallback_config, "global"

        profile = await self.get_profile(user_id=user_id)
        if profile is None:
            return fallback_config, "global"

        use_fallback_credentials = not profile.auth_token and not profile.device_token
        resolved = OpenClawConfig(
            enabled=True,
            gateway_url=profile.gateway_url or fallback_config.gateway_url,
            auth_token=profile.auth_token or (fallback_config.auth_token if use_fallback_credentials else ""),
            default_agent_id=fallback_config.default_agent_id,
            transport=profile.transport or fallback_config.transport,
            ws_url=profile.ws_url or _coerce_ws_url("", profile.gateway_url) or fallback_config.ws_url,
            ws_protocol_version=fallback_config.ws_protocol_version,
            ws_wait_timeout_ms=fallback_config.ws_wait_timeout_ms,
            ws_allow_insecure_auth=fallback_config.ws_allow_insecure_auth or bool(profile.auth_token),
            ws_device_token=profile.device_token or (fallback_config.ws_device_token if use_fallback_credentials else ""),
            ws_device_identity_path=fallback_config.ws_device_identity_path,
            ws_client_id=fallback_config.ws_client_id,
            ws_client_version=fallback_config.ws_client_version,
            default_workdir=fallback_config.default_workdir,
            default_timeout_seconds=fallback_config.default_timeout_seconds,
            max_concurrent_runs=fallback_config.max_concurrent_runs,
        )
        return resolved, "user_profile"
