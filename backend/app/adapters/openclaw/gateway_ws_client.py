"""OpenClaw Gateway WebSocket client for Phase 2 lifecycle control."""

from __future__ import annotations

import asyncio
import base64
import inspect
import json
import platform
import random
from pathlib import Path
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from time import monotonic, time
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse, urlunparse
import unicodedata

import websockets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from loguru import logger

from app.adapters.openclaw.config import OpenClawConfig
from app.adapters.openclaw.client import (
    OpenClawConfigurationError,
    OpenClawError,
    OpenClawExecutionError,
    OpenClawTimeout,
)

EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
_ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def _coerce_ws_url(config: OpenClawConfig) -> str:
    if config.ws_url:
        return config.ws_url
    raw_url = config.gateway_url
    if not raw_url:
        return ""

    parsed = urlparse(raw_url)
    scheme = parsed.scheme.lower()
    if scheme in {"ws", "wss"}:
        return raw_url
    if scheme == "https":
        parsed = parsed._replace(scheme="wss")
    else:
        parsed = parsed._replace(scheme="ws")
    return urlunparse(parsed)


@dataclass
class _GatewayRunCapture:
    run_id: str
    session_key: str
    output_parts: list[str] = field(default_factory=list)
    tool_calls_count: int = 0
    usage: dict[str, Any] | None = None
    approval: dict[str, Any] | None = None
    lifecycle_phase: str | None = None
    error_message: str | None = None

    def observe(self, frame: dict[str, Any]) -> None:
        event_name = frame.get("event")
        payload = frame.get("payload") or {}

        if event_name == "agent":
            self._observe_agent_event(payload)
            return

        if event_name == "exec.approval.requested":
            approval_id = payload.get("approvalId") or payload.get("id")
            if approval_id:
                self.approval = {
                    "id": approval_id,
                    "host": payload.get("host"),
                    "agent_id": payload.get("agentId"),
                    "command": payload.get("command")
                    or payload.get("rawCommand")
                    or (payload.get("systemRunPlan") or {}).get("rawCommand"),
                    "cwd": payload.get("cwd") or (payload.get("systemRunPlan") or {}).get("cwd"),
                    "metadata": payload,
                }
            return

        if event_name == "chat":
            text = self._extract_text(payload)
            if text:
                self.output_parts.append(text)

    def build_result(
        self,
        *,
        wait_payload: dict[str, Any] | None = None,
        status_override: str | None = None,
    ) -> dict[str, Any]:
        wait_payload = wait_payload or {}
        wait_status = str(wait_payload.get("status") or "").lower()
        response_status = status_override or self._resolve_status(wait_status)
        output_text = "\n".join(part for part in self.output_parts if part).strip()

        result: dict[str, Any] = {
            "id": self.run_id,
            "status": response_status,
            "output": [],
            "usage": wait_payload.get("usage") or self.usage,
            "session_key": self.session_key,
            "transport": "gateway_ws",
        }
        if output_text:
            result["output"] = [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": output_text,
                        }
                    ],
                }
            ]

        if self.approval:
            result["approval"] = self.approval
            result["required_action"] = {
                "type": "approval",
                "approval_id": self.approval["id"],
            }

        error_message = wait_payload.get("error") or self.error_message
        if isinstance(error_message, dict):
            error_message = error_message.get("message") or json.dumps(error_message, ensure_ascii=False)
        if error_message:
            result["error"] = {"message": str(error_message)}

        return result

    def observe_final_response(self, payload: dict[str, Any]) -> None:
        status = str(payload.get("status") or "").lower()
        if status == "error":
            summary = payload.get("summary")
            if isinstance(summary, str) and summary.strip():
                self.error_message = summary.strip()

        result = payload.get("result")
        if not isinstance(result, dict):
            return

        final_texts: list[str] = []
        for item in result.get("payloads") or []:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                final_texts.append(text.strip())
        if final_texts:
            self.output_parts = final_texts

        meta = result.get("meta") or {}
        if isinstance(meta, dict):
            agent_meta = meta.get("agentMeta") or {}
            if isinstance(agent_meta, dict):
                usage = agent_meta.get("lastCallUsage") or agent_meta.get("usage")
                if isinstance(usage, dict):
                    self.usage = usage

    def _resolve_status(self, wait_status: str) -> str:
        if self.approval:
            return "requires_action"
        if wait_status == "ok":
            return "completed"
        if wait_status == "timeout":
            return "timed_out"
        if self.lifecycle_phase == "error" or wait_status == "error":
            return "failed"
        return "completed" if self.output_parts else "failed"

    def _observe_agent_event(self, payload: dict[str, Any]) -> None:
        stream_type = payload.get("stream")
        usage = payload.get("usage")
        if isinstance(usage, dict):
            self.usage = usage

        if stream_type == "assistant":
            text = self._extract_text(payload)
            if text:
                self.output_parts.append(text)
            return

        if stream_type == "tool":
            event_type = str(payload.get("event") or payload.get("phase") or "").lower()
            if event_type in {"start", "call", "end", "result"}:
                self.tool_calls_count += 1 if event_type in {"start", "call"} else 0
            return

        if stream_type == "lifecycle":
            self.lifecycle_phase = payload.get("phase")
            error = payload.get("error")
            if isinstance(error, dict):
                self.error_message = error.get("message")
            elif error:
                self.error_message = str(error)

    def _extract_text(self, payload: dict[str, Any]) -> str:
        for key in ("delta", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        message = payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                parts: list[str] = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    text = block.get("text") or block.get("delta")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
                if parts:
                    return "\n".join(parts)
        return ""


class OpenClawGatewayWebSocketClient:
    """Gateway control-plane client for `agent` lifecycle orchestration."""

    def __init__(self, config: OpenClawConfig):
        self._config = config
        self._ws_url = _coerce_ws_url(config)
        self._request_counter = 0

    async def execute(
        self,
        request_body: dict[str, Any],
        *,
        timeout_seconds: int,
        event_callback: EventCallback | None = None,
    ) -> dict[str, Any]:
        async with self._connect() as websocket:
            await self._handshake(websocket)

            buffered_events: list[dict[str, Any]] = []
            request_id = await self._send_request(websocket, method="agent", params=request_body)
            capture: _GatewayRunCapture | None = None
            deadline = monotonic() + max(float(timeout_seconds), 1.0)

            while monotonic() < deadline:
                remaining = max(deadline - monotonic(), 0.1)
                try:
                    frame = await self._recv_json(websocket, timeout_seconds=min(1.0, remaining))
                except asyncio.TimeoutError:
                    continue

                frame_type = frame.get("type")
                if frame_type == "event":
                    buffered_events.append(frame)
                    if capture is not None:
                        capture.observe(frame)
                        await self._dispatch_event_callback(event_callback, frame)
                        if capture.approval:
                            return capture.build_result(status_override="requires_action")
                    continue

                if frame_type != "res" or frame.get("id") != request_id:
                    continue
                if not frame.get("ok", False):
                    raise OpenClawExecutionError(self._extract_gateway_error(frame))

                payload = frame.get("payload")
                payload = payload if isinstance(payload, dict) else {}
                payload_status = str(payload.get("status") or "").lower()
                if payload_status == "accepted":
                    run_id = str(payload.get("runId") or request_body.get("idempotencyKey") or "").strip()
                    if not run_id:
                        raise OpenClawExecutionError("Gateway `agent` did not return a runId")
                    session_key = str(payload.get("sessionKey") or request_body.get("sessionKey") or "").strip()
                    capture = _GatewayRunCapture(run_id=run_id, session_key=session_key)
                    for buffered in buffered_events:
                        capture.observe(buffered)
                        await self._dispatch_event_callback(event_callback, buffered)
                    if capture.approval:
                        return capture.build_result(status_override="requires_action")
                    continue

                if capture is None:
                    run_id = str(payload.get("runId") or request_body.get("idempotencyKey") or "").strip()
                    session_key = str(payload.get("sessionKey") or request_body.get("sessionKey") or "").strip()
                    capture = _GatewayRunCapture(run_id=run_id or "gateway-run", session_key=session_key)
                    for buffered in buffered_events:
                        capture.observe(buffered)
                        await self._dispatch_event_callback(event_callback, buffered)

                capture.observe_final_response(payload)
                status_override = "completed" if payload_status == "ok" else "failed"
                return capture.build_result(status_override=status_override)

        raise OpenClawTimeout(f"OpenClaw execution timed out after {timeout_seconds}s")

    async def resolve_approval(
        self,
        *,
        approval_id: str,
        decision: str,
        run_id: str,
        session_key: str,
        timeout_seconds: int,
        event_callback: EventCallback | None = None,
    ) -> dict[str, Any]:
        async with self._connect() as websocket:
            await self._handshake(websocket)
            capture = _GatewayRunCapture(run_id=run_id, session_key=session_key)

            await self._rpc(
                websocket,
                method="exec.approval.resolve",
                params={
                    "approvalId": approval_id,
                    "decision": decision,
                },
                on_event=lambda frame: self._observe_capture_and_callback(capture, frame, event_callback),
            )

            if decision == "deny":
                capture.error_message = "Execution denied by user"
                return capture.build_result(status_override="failed")

            await self._await_run_state(
                websocket,
                capture=capture,
                timeout_seconds=timeout_seconds,
                event_callback=event_callback,
                stop_on_approval=True,
            )
            if capture.approval:
                return capture.build_result(status_override="requires_action")

        wait_payload = await self._wait_for_run_completion(
            run_id=run_id,
            timeout_seconds=timeout_seconds,
        )
        return capture.build_result(wait_payload=wait_payload)

    async def cancel_run(
        self,
        *,
        session_key: str,
        run_id: str | None = None,
    ) -> None:
        async with self._connect() as websocket:
            await self._handshake(websocket)
            params: dict[str, Any] = {"sessionKey": session_key}
            if run_id:
                params["runId"] = run_id
            await self._rpc(websocket, method="chat.abort", params=params)

    async def health_check(self) -> bool:
        if not self._ws_url:
            return False
        try:
            async with self._connect() as websocket:
                await self._handshake(websocket)
                payload = await self._rpc(websocket, method="health", params={})
                return bool(payload.get("ok", True))
        except Exception:
            return False

    async def list_nodes(
        self,
        *,
        connected_only: bool = True,
        last_connected: str | None = None,
    ) -> dict[str, Any]:
        async with self._connect() as websocket:
            await self._handshake(websocket)
            payload = await self._rpc(websocket, method="node.list", params={})
            if not connected_only and not last_connected:
                return payload
            items = payload.get("items") or payload.get("nodes") or payload.get("paired") or []
            filtered: list[Any] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                if connected_only and not bool(item.get("connected", item.get("isConnected", False))):
                    continue
                filtered.append(item)
            return {"items": filtered}

    async def invoke_node(
        self,
        *,
        node_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        invoke_timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        async with self._connect() as websocket:
            await self._handshake(websocket)
            payload: dict[str, Any] = {
                "nodeId": node_id,
                "command": command,
                "params": params or {},
            }
            if invoke_timeout_ms is not None:
                payload["timeoutMs"] = invoke_timeout_ms
            if idempotency_key:
                payload["idempotencyKey"] = idempotency_key
            return await self._rpc(websocket, method="node.invoke", params=payload)

    async def _send_request(
        self,
        websocket,
        *,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        self._request_counter += 1
        request_id = f"sparkle-{self._request_counter}"
        await websocket.send(
            json.dumps(
                {
                    "type": "req",
                    "id": request_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )
        return request_id

    async def _wait_for_run_completion(
        self,
        *,
        run_id: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        async with self._connect() as websocket:
            await self._handshake(websocket)
            return await self._rpc(
                websocket,
                method="agent.wait",
                params={
                    "runId": run_id,
                    "timeoutMs": self._effective_wait_timeout_ms(timeout_seconds),
                },
            )

    async def _await_run_state(
        self,
        websocket,
        *,
        capture: _GatewayRunCapture,
        timeout_seconds: int,
        event_callback: EventCallback | None,
        stop_on_approval: bool,
    ) -> bool:
        deadline = monotonic() + max(float(timeout_seconds), 1.0)
        while monotonic() < deadline:
            remaining = max(deadline - monotonic(), 0.1)
            try:
                frame = await self._recv_json(websocket, timeout_seconds=min(1.0, remaining))
            except asyncio.TimeoutError:
                continue

            if frame.get("type") != "event":
                continue

            capture.observe(frame)
            await self._dispatch_event_callback(event_callback, frame)

            if stop_on_approval and capture.approval:
                return False
            if capture.lifecycle_phase in {"end", "error"}:
                return True
        return False

    async def _handshake(self, websocket) -> None:
        if not self._config.ws_allow_insecure_auth and not self._config.ws_device_token:
            raise OpenClawConfigurationError(
                "Gateway WS transport requires OPENCLAW_WS_ALLOW_INSECURE_AUTH=true or OPENCLAW_WS_DEVICE_TOKEN"
            )

        nonce = None
        try:
            frame = await self._recv_json(websocket, timeout_seconds=5.0)
            if frame.get("type") == "event" and frame.get("event") == "connect.challenge":
                payload = frame.get("payload") or {}
                nonce = payload.get("nonce")
        except asyncio.TimeoutError:
            logger.debug("OpenClaw gateway did not send connect.challenge before timeout; continuing with connect")

        auth_payload: dict[str, Any] = {}
        if self._config.auth_token:
            auth_payload["token"] = self._config.auth_token
        if self._config.ws_device_token:
            auth_payload["deviceToken"] = self._config.ws_device_token

        platform_name = self._resolve_platform_name()
        device_family = self._resolve_device_family(platform_name)

        params: dict[str, Any] = {
            "minProtocol": self._config.ws_protocol_version,
            "maxProtocol": self._config.ws_protocol_version,
            "client": {
                "id": "gateway-client",
                "displayName": self._config.ws_client_id or "Sparkle Backend",
                "version": self._config.ws_client_version,
                "platform": platform_name,
                "deviceFamily": device_family,
                "mode": "backend",
                "instanceId": self._config.ws_client_id or "sparkle-backend",
            },
            "role": "operator",
            "scopes": ["operator.read", "operator.write", "operator.approvals"],
            "caps": [],
            "commands": [],
            "permissions": {},
            "auth": auth_payload,
            "locale": "zh-CN",
            "userAgent": f"{self._config.ws_client_id}/{self._config.ws_client_version}",
        }
        if nonce and self._config.ws_device_token:
            params["device"] = self._build_device_payload(
                nonce=nonce,
                client_id=str(params["client"]["id"]),
                client_mode=str(params["client"]["mode"]),
                platform_name=platform_name,
                device_family=device_family,
                scopes=list(params["scopes"]),
            )

        await self._rpc(websocket, method="connect", params=params)

    def _build_device_payload(
        self,
        *,
        nonce: str,
        client_id: str,
        client_mode: str,
        platform_name: str,
        device_family: str,
        scopes: list[str],
    ) -> dict[str, Any]:
        identity = self._load_device_identity()
        signed_at_ms = int(time() * 1000)
        signature_token = self._config.auth_token or self._config.ws_device_token
        payload = self._build_device_auth_payload_v3(
            device_id=identity["device_id"],
            client_id=client_id,
            client_mode=client_mode,
            scopes=scopes,
            signed_at_ms=signed_at_ms,
            signature_token=signature_token,
            nonce=nonce,
            platform_name=platform_name,
            device_family=device_family,
        )
        signature = identity["private_key"].sign(payload.encode("utf-8"))
        return {
            "id": identity["device_id"],
            "publicKey": identity["public_key_base64url"],
            "signature": self._base64url_encode(signature),
            "signedAt": signed_at_ms,
            "nonce": nonce,
        }

    def _load_device_identity(self) -> dict[str, Any]:
        raw_path = (self._config.ws_device_identity_path or "").strip()
        if not raw_path:
            raise OpenClawConfigurationError(
                "Gateway WS transport requires OPENCLAW_WS_DEVICE_IDENTITY_PATH when OPENCLAW_WS_DEVICE_TOKEN is set"
            )
        path = Path(raw_path).expanduser()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise OpenClawConfigurationError(f"OpenClaw WS device identity file does not exist: {path}") from exc
        except json.JSONDecodeError as exc:
            raise OpenClawConfigurationError(f"OpenClaw WS device identity file is invalid JSON: {path}") from exc

        if not isinstance(payload, dict):
            raise OpenClawConfigurationError(f"OpenClaw WS device identity file is invalid: {path}")
        device_id = str(payload.get("deviceId") or "").strip()
        public_key_pem = str(payload.get("publicKeyPem") or "").strip()
        private_key_pem = str(payload.get("privateKeyPem") or "").strip()
        if not device_id or not public_key_pem or not private_key_pem:
            raise OpenClawConfigurationError(f"OpenClaw WS device identity file is incomplete: {path}")

        try:
            private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
            public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        except ValueError as exc:
            raise OpenClawConfigurationError(f"OpenClaw WS device identity file contains invalid PEM keys: {path}") from exc
        if not isinstance(private_key, Ed25519PrivateKey):
            raise OpenClawConfigurationError(f"OpenClaw WS device identity must use an Ed25519 private key: {path}")

        public_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        public_raw = public_der[len(_ED25519_SPKI_PREFIX) :] if public_der.startswith(_ED25519_SPKI_PREFIX) else public_der
        return {
            "device_id": device_id,
            "public_key_base64url": self._base64url_encode(public_raw),
            "private_key": private_key,
        }

    def _build_device_auth_payload_v3(
        self,
        *,
        device_id: str,
        client_id: str,
        client_mode: str,
        scopes: list[str],
        signed_at_ms: int,
        signature_token: str | None,
        nonce: str,
        platform_name: str,
        device_family: str,
    ) -> str:
        return "|".join(
            [
                "v3",
                device_id,
                client_id,
                client_mode,
                "operator",
                ",".join(scopes),
                str(signed_at_ms),
                signature_token or "",
                nonce,
                self._normalize_device_metadata(platform_name),
                self._normalize_device_metadata(device_family),
            ]
        )

    @staticmethod
    def _normalize_device_metadata(value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            return ""
        return "".join(
            ch for ch in unicodedata.normalize("NFKD", trimmed) if not unicodedata.combining(ch)
        ).lower()

    @staticmethod
    def _resolve_platform_name() -> str:
        system_name = platform.system().lower()
        if system_name == "darwin":
            return "darwin"
        if system_name == "windows":
            return "windows"
        return system_name or "linux"

    @staticmethod
    def _resolve_device_family(platform_name: str) -> str:
        if platform_name == "darwin":
            return "Mac"
        if platform_name == "windows":
            return "PC"
        return "Linux"

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

    async def _rpc(
        self,
        websocket,
        *,
        method: str,
        params: dict[str, Any] | None = None,
        on_event: EventCallback | None = None,
    ) -> dict[str, Any]:
        request_id = await self._send_request(websocket, method=method, params=params)

        while True:
            frame = await self._recv_json(websocket, timeout_seconds=max(self._config.default_timeout_seconds, 30))
            frame_type = frame.get("type")
            if frame_type == "event":
                if on_event:
                    await self._dispatch_event_callback(on_event, frame)
                continue
            if frame_type != "res" or frame.get("id") != request_id:
                continue
            if not frame.get("ok", False):
                raise OpenClawExecutionError(self._extract_gateway_error(frame))
            payload = frame.get("payload")
            return payload if isinstance(payload, dict) else {}

    async def _observe_capture_and_callback(
        self,
        capture: _GatewayRunCapture,
        frame: dict[str, Any],
        event_callback: EventCallback | None,
    ) -> None:
        capture.observe(frame)
        await self._dispatch_event_callback(event_callback, frame)

    async def _dispatch_event_callback(
        self,
        callback: EventCallback | None,
        frame: dict[str, Any],
    ) -> None:
        if callback is None:
            return
        result = callback(frame)
        if inspect.isawaitable(result):
            await result

    async def _recv_json(self, websocket, *, timeout_seconds: float) -> dict[str, Any]:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
        except websockets.exceptions.ConnectionClosed as exc:
            raise OpenClawError(f"Gateway connection closed: {exc.code}") from exc
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        try:
            decoded = json.loads(message)
        except json.JSONDecodeError as exc:
            raise OpenClawExecutionError("Gateway returned non-JSON frame") from exc
        if not isinstance(decoded, dict):
            raise OpenClawExecutionError("Gateway returned invalid frame payload")
        return decoded

    def _effective_wait_timeout_ms(self, timeout_seconds: int) -> int:
        return max(self._config.ws_wait_timeout_ms, int(max(timeout_seconds, 1) * 1000))

    def _extract_gateway_error(self, frame: dict[str, Any]) -> str:
        error = frame.get("error") or {}
        if isinstance(error, dict):
            message = error.get("message") or error.get("code") or "Gateway request failed"
            return str(message)
        return str(error) if error else "Gateway request failed"

    @asynccontextmanager
    async def _connect(self):
        if not self._ws_url:
            raise OpenClawConfigurationError("OpenClaw Gateway WS URL is not configured")
        connection = None
        websocket = None
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                connection = websockets.connect(
                    self._ws_url,
                    ping_interval=15,
                    ping_timeout=30,
                    close_timeout=5,
                    max_size=2**22,
                )
                websocket = await connection.__aenter__()
                break
            except Exception as exc:
                last_error = exc
                if attempt >= 4:
                    raise
                base_delay = min(30.0, float(2**attempt))
                delay = max(0.25, base_delay * random.uniform(0.8, 1.2))
                logger.warning(
                    "OpenClaw Gateway WS connect attempt {}/5 failed: {}. Retrying in {:.2f}s",
                    attempt + 1,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

        if websocket is None or connection is None:
            raise OpenClawConfigurationError(str(last_error or "OpenClaw Gateway WS connection failed"))

        try:
            yield websocket
        finally:
            await connection.__aexit__(None, None, None)
