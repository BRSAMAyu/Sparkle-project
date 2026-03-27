"""OpenClaw HTTP client for `/v1/responses`."""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.adapters.openclaw.config import OpenClawConfig

DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_WRITE_TIMEOUT = 10.0
DEFAULT_POOL_TIMEOUT = 5.0


class OpenClawClient:
    """OpenClaw transport facade for HTTP and Gateway WS."""

    def __init__(self, config: OpenClawConfig):
        self._config = config
        self._base_url = config.gateway_url
        self._ws_client = None
        if config.transport == "gateway_ws":
            from app.adapters.openclaw.gateway_ws_client import OpenClawGatewayWebSocketClient

            self._ws_client = OpenClawGatewayWebSocketClient(config)

    async def execute(
        self,
        request_body: dict[str, Any],
        *,
        timeout_seconds: int | None = None,
        event_callback=None,
    ) -> dict[str, Any]:
        if self._config.transport == "gateway_ws":
            if not self._ws_client:
                raise OpenClawConfigurationError("OpenClaw Gateway WS transport is not initialized")
            return await self._ws_client.execute(
                request_body,
                timeout_seconds=timeout_seconds or self._config.default_timeout_seconds,
                event_callback=event_callback,
            )

        if not self._config.enabled:
            raise OpenClawError("OpenClaw integration is disabled")
        if not self._base_url:
            raise OpenClawError("OpenClaw gateway URL is not configured")

        read_timeout = float(timeout_seconds or self._config.default_timeout_seconds)
        timeout = httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=read_timeout + 30.0,
            write=DEFAULT_WRITE_TIMEOUT,
            pool=DEFAULT_POOL_TIMEOUT,
        )
        headers = {
            "Content-Type": "application/json",
        }
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"

        url = f"{self._base_url}/v1/responses"
        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                response = await http.post(url, json=request_body, headers=headers)

            if response.status_code == 401:
                raise OpenClawError("Authentication failed - check OPENCLAW_AUTH_TOKEN")
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise OpenClawRateLimited(f"Rate limited, retry after {retry_after}s")
            if response.status_code >= 500:
                raise OpenClawError(f"OpenClaw server error: {response.status_code}")
            if response.status_code >= 400:
                error_body = response.json() if response.content else {}
                error_message = error_body.get("error", {}).get("message", response.text)
                raise OpenClawExecutionError(f"Request failed: {error_message}")

            return response.json()
        except httpx.TimeoutException as exc:
            raise OpenClawTimeout(f"OpenClaw execution timed out after {read_timeout}s") from exc
        except httpx.ConnectError as exc:
            raise OpenClawError(f"Cannot connect to OpenClaw at {self._base_url}") from exc

    async def resolve_approval(
        self,
        *,
        approval_id: str,
        decision: str,
        run_id: str,
        session_key: str,
        timeout_seconds: int | None = None,
        event_callback=None,
    ) -> dict[str, Any]:
        if self._config.transport != "gateway_ws" or not self._ws_client:
            raise OpenClawConfigurationError("Approval resolution requires Gateway WS transport")
        return await self._ws_client.resolve_approval(
            approval_id=approval_id,
            decision=decision,
            run_id=run_id,
            session_key=session_key,
            timeout_seconds=timeout_seconds or self._config.default_timeout_seconds,
            event_callback=event_callback,
        )

    async def cancel_run(self, *, session_key: str, run_id: str | None = None) -> None:
        if self._config.transport != "gateway_ws" or not self._ws_client:
            logger.debug("Skipping remote cancel because Gateway WS transport is not active")
            return
        await self._ws_client.cancel_run(session_key=session_key, run_id=run_id)

    async def health_check(self) -> bool:
        if self._config.transport == "gateway_ws":
            if not self._ws_client:
                return False
            return await self._ws_client.health_check()
        if not self._config.enabled or not self._base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as http:
                response = await http.get(f"{self._base_url}/v1/models")
            return response.status_code == 200
        except Exception:
            return False

    async def list_nodes(
        self,
        *,
        connected_only: bool = True,
        last_connected: str | None = None,
    ) -> dict[str, Any]:
        if self._config.transport != "gateway_ws" or not self._ws_client:
            return {"items": []}
        return await self._ws_client.list_nodes(
            connected_only=connected_only,
            last_connected=last_connected,
        )

    async def invoke_node(
        self,
        *,
        node_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        invoke_timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if self._config.transport != "gateway_ws" or not self._ws_client:
            raise OpenClawConfigurationError("Node invocation requires Gateway WS transport")
        return await self._ws_client.invoke_node(
            node_id=node_id,
            command=command,
            params=params or {},
            invoke_timeout_ms=invoke_timeout_ms,
            idempotency_key=idempotency_key,
        )


class OpenClawError(Exception):
    """Base OpenClaw adapter error."""


class OpenClawTimeout(OpenClawError):
    """OpenClaw execution timed out."""


class OpenClawRateLimited(OpenClawError):
    """OpenClaw request hit rate limits."""


class OpenClawExecutionError(OpenClawError):
    """OpenClaw returned a non-successful execution response."""


class OpenClawConfigurationError(OpenClawError):
    """OpenClaw transport configuration is invalid."""
