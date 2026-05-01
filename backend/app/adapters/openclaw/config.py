"""OpenClaw adapter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class OpenClawConfig:
    enabled: bool = False
    gateway_url: str = ""
    auth_token: str = ""
    default_agent_id: str = ""
    transport: str = "responses_http"
    ws_url: str = ""
    ws_protocol_version: int = 3
    ws_wait_timeout_ms: int = 30000
    ws_allow_insecure_auth: bool = False
    ws_device_token: str = ""
    ws_device_identity_path: str = ""
    ws_client_id: str = "sparkle-backend"
    ws_client_version: str = "0.1.0"
    default_workdir: str = ""
    default_timeout_seconds: int = 300
    max_concurrent_runs: int = 3

    @classmethod
    def from_settings(cls) -> OpenClawConfig:
        return cls(
            enabled=settings.OPENCLAW_ENABLED,
            gateway_url=settings.OPENCLAW_GATEWAY_URL.rstrip("/"),
            auth_token=settings.OPENCLAW_AUTH_TOKEN,
            default_agent_id=settings.OPENCLAW_DEFAULT_AGENT_ID,
            transport=settings.OPENCLAW_TRANSPORT,
            ws_url=settings.OPENCLAW_WS_URL.rstrip("/"),
            ws_protocol_version=settings.OPENCLAW_WS_PROTOCOL_VERSION,
            ws_wait_timeout_ms=settings.OPENCLAW_WS_WAIT_TIMEOUT_MS,
            ws_allow_insecure_auth=settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH,
            ws_device_token=settings.OPENCLAW_WS_DEVICE_TOKEN,
            ws_device_identity_path=settings.OPENCLAW_WS_DEVICE_IDENTITY_PATH,
            ws_client_id=settings.OPENCLAW_WS_CLIENT_ID,
            ws_client_version=settings.APP_VERSION,
            default_workdir=settings.OPENCLAW_DEFAULT_WORKDIR,
            default_timeout_seconds=settings.OPENCLAW_DEFAULT_TIMEOUT_SECONDS,
            max_concurrent_runs=settings.OPENCLAW_MAX_CONCURRENT_RUNS,
        )
