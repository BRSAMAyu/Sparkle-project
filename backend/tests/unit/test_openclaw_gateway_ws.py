from __future__ import annotations

import json

import pytest

from app.adapters.openclaw.config import OpenClawConfig
from app.adapters.openclaw.gateway_ws_client import OpenClawGatewayWebSocketClient


class _FakeWebSocket:
    def __init__(self, frames: list[dict]):
        self._frames = [json.dumps(frame) for frame in frames]
        self.sent: list[dict] = []

    async def recv(self):
        if not self._frames:
            raise AssertionError("No more frames queued for FakeWebSocket.recv()")
        return self._frames.pop(0)

    async def send(self, message: str):
        self.sent.append(json.loads(message))


class _FakeConnect:
    def __init__(self, websocket: _FakeWebSocket):
        self._websocket = websocket

    async def __aenter__(self):
        return self._websocket

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_config() -> OpenClawConfig:
    return OpenClawConfig(
        enabled=True,
        gateway_url="http://openclaw.local",
        auth_token="token",
        default_agent_id="main",
        transport="gateway_ws",
        ws_url="ws://openclaw.local",
        ws_allow_insecure_auth=True,
        ws_client_id="sparkle-backend",
        ws_client_version="0.1.0",
    )


@pytest.mark.asyncio
async def test_gateway_ws_execute_returns_approval_result(monkeypatch) -> None:
    websocket = _FakeWebSocket(
        [
            {"type": "event", "event": "connect.challenge", "payload": {"nonce": "nonce-1", "ts": 1}},
            {"type": "res", "id": "sparkle-1", "ok": True, "payload": {"type": "hello-ok", "protocol": 3}},
            {
                "type": "res",
                "id": "sparkle-2",
                "ok": True,
                "payload": {
                    "runId": "run-1",
                    "status": "accepted",
                    "acceptedAt": "2026-03-27T00:00:00Z",
                    "sessionKey": "sparkle:main:user:task",
                },
            },
            {
                "type": "event",
                "event": "exec.approval.requested",
                "payload": {
                    "approvalId": "approval-1",
                    "systemRunPlan": {"rawCommand": "rg -n TODO", "cwd": "/tmp"},
                },
            },
        ]
    )
    monkeypatch.setattr(
        "app.adapters.openclaw.gateway_ws_client.websockets.connect",
        lambda *args, **kwargs: _FakeConnect(websocket),
    )

    client = OpenClawGatewayWebSocketClient(_make_config())
    response = await client.execute(
        {
            "agentId": "main",
            "sessionKey": "sparkle:main:user:task",
            "message": "hello",
            "idempotencyKey": "idempotency-1",
        },
        timeout_seconds=30,
    )

    assert response["status"] == "requires_action"
    assert response["approval"]["id"] == "approval-1"
    assert response["required_action"]["approval_id"] == "approval-1"
    assert websocket.sent[0]["method"] == "connect"
    assert websocket.sent[0]["params"]["client"]["id"] == "gateway-client"
    assert websocket.sent[0]["params"]["client"]["mode"] == "backend"
    assert websocket.sent[1]["method"] == "agent"


@pytest.mark.asyncio
async def test_gateway_ws_execute_collects_output_and_waits_for_completion(monkeypatch) -> None:
    websocket = _FakeWebSocket(
        [
            {"type": "event", "event": "connect.challenge", "payload": {"nonce": "nonce-1", "ts": 1}},
            {"type": "res", "id": "sparkle-1", "ok": True, "payload": {"type": "hello-ok", "protocol": 3}},
            {
                "type": "res",
                "id": "sparkle-2",
                "ok": True,
                "payload": {
                    "runId": "run-2",
                    "status": "accepted",
                    "acceptedAt": "2026-03-27T00:00:00Z",
                    "sessionKey": "sparkle:main:user:task",
                },
            },
            {
                "type": "event",
                "event": "agent",
                "payload": {"stream": "assistant", "delta": '{"summary":"done"}'},
            },
            {
                "type": "event",
                "event": "agent",
                "payload": {"stream": "lifecycle", "phase": "end"},
            },
            {
                "type": "res",
                "id": "sparkle-2",
                "ok": True,
                "payload": {
                    "runId": "run-2",
                    "status": "ok",
                    "result": {
                        "payloads": [{"text": '{"summary":"done"}'}],
                        "meta": {"agentMeta": {"lastCallUsage": {"input": 1, "output": 1}}},
                    },
                },
            },
        ]
    )
    monkeypatch.setattr(
        "app.adapters.openclaw.gateway_ws_client.websockets.connect",
        lambda *args, **kwargs: _FakeConnect(websocket),
    )

    client = OpenClawGatewayWebSocketClient(_make_config())
    response = await client.execute(
        {
            "agentId": "main",
            "sessionKey": "sparkle:main:user:task",
            "message": "hello",
            "idempotencyKey": "idempotency-2",
        },
        timeout_seconds=30,
    )

    assert response["status"] == "completed"
    assert response["output"][0]["content"][0]["text"] == '{"summary":"done"}'
    assert websocket.sent[1]["method"] == "agent"


@pytest.mark.asyncio
async def test_gateway_ws_resolve_approval_resumes_run(monkeypatch) -> None:
    resolve_socket = _FakeWebSocket(
        [
            {"type": "event", "event": "connect.challenge", "payload": {"nonce": "nonce-1", "ts": 1}},
            {"type": "res", "id": "sparkle-1", "ok": True, "payload": {"type": "hello-ok", "protocol": 3}},
            {"type": "res", "id": "sparkle-2", "ok": True, "payload": {"status": "accepted"}},
            {
                "type": "event",
                "event": "agent",
                "payload": {"stream": "assistant", "delta": '{"summary":"approved"}'},
            },
            {
                "type": "event",
                "event": "agent",
                "payload": {"stream": "lifecycle", "phase": "end"},
            },
        ]
    )
    wait_socket = _FakeWebSocket(
        [
            {"type": "event", "event": "connect.challenge", "payload": {"nonce": "nonce-2", "ts": 2}},
            {"type": "res", "id": "sparkle-3", "ok": True, "payload": {"type": "hello-ok", "protocol": 3}},
            {"type": "res", "id": "sparkle-4", "ok": True, "payload": {"status": "ok"}},
        ]
    )
    connections = iter([_FakeConnect(resolve_socket), _FakeConnect(wait_socket)])
    monkeypatch.setattr(
        "app.adapters.openclaw.gateway_ws_client.websockets.connect",
        lambda *args, **kwargs: next(connections),
    )

    client = OpenClawGatewayWebSocketClient(_make_config())
    response = await client.resolve_approval(
        approval_id="approval-1",
        decision="allow-once",
        run_id="run-3",
        session_key="sparkle:main:user:task",
        timeout_seconds=30,
    )

    assert response["status"] == "completed"
    assert response["output"][0]["content"][0]["text"] == '{"summary":"approved"}'
    assert resolve_socket.sent[1]["method"] == "exec.approval.resolve"
    assert wait_socket.sent[1]["method"] == "agent.wait"


@pytest.mark.asyncio
async def test_gateway_ws_list_nodes_and_invoke(monkeypatch) -> None:
    list_socket = _FakeWebSocket(
        [
            {"type": "event", "event": "connect.challenge", "payload": {"nonce": "nonce-1", "ts": 1}},
            {"type": "res", "id": "sparkle-1", "ok": True, "payload": {"type": "hello-ok", "protocol": 3}},
            {
                "type": "res",
                "id": "sparkle-2",
                "ok": True,
                "payload": {
                    "items": [
                        {
                            "nodeId": "node-1",
                            "name": "MacBook",
                            "platform": "macos",
                            "connected": True,
                            "commands": ["system.run"],
                        }
                    ]
                },
            },
        ]
    )
    invoke_socket = _FakeWebSocket(
        [
            {"type": "event", "event": "connect.challenge", "payload": {"nonce": "nonce-2", "ts": 2}},
            {"type": "res", "id": "sparkle-3", "ok": True, "payload": {"type": "hello-ok", "protocol": 3}},
            {
                "type": "res",
                "id": "sparkle-4",
                "ok": True,
                "payload": {"ok": True, "result": {"stdout": "clean"}},
            },
        ]
    )
    connections = iter([_FakeConnect(list_socket), _FakeConnect(invoke_socket)])
    monkeypatch.setattr(
        "app.adapters.openclaw.gateway_ws_client.websockets.connect",
        lambda *args, **kwargs: next(connections),
    )

    client = OpenClawGatewayWebSocketClient(_make_config())
    nodes = await client.list_nodes()
    result = await client.invoke_node(
        node_id="node-1",
        command="system.run",
        params={"raw": "git status"},
        invoke_timeout_ms=15000,
        idempotency_key="node-invoke-1",
    )

    assert nodes["items"][0]["nodeId"] == "node-1"
    assert result["ok"] is True
    assert list_socket.sent[1]["method"] == "node.list"
    assert invoke_socket.sent[1]["method"] == "node.invoke"
