from __future__ import annotations

import pytest

from app.adapters.openclaw.client import OpenClawError
from app.models.user import User
from app.services.openclaw_connection_profile_service import OpenClawConnectionProfileService
from app.services.execution_service import ExecutionService


@pytest.fixture
def openclaw_gateway_ws_settings():
    from app.config import settings

    original = {
        "OPENCLAW_ENABLED": settings.OPENCLAW_ENABLED,
        "OPENCLAW_GATEWAY_URL": settings.OPENCLAW_GATEWAY_URL,
        "OPENCLAW_AUTH_TOKEN": settings.OPENCLAW_AUTH_TOKEN,
        "OPENCLAW_DEFAULT_AGENT_ID": settings.OPENCLAW_DEFAULT_AGENT_ID,
        "OPENCLAW_TRANSPORT": settings.OPENCLAW_TRANSPORT,
        "OPENCLAW_WS_URL": settings.OPENCLAW_WS_URL,
        "OPENCLAW_WS_ALLOW_INSECURE_AUTH": settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH,
    }
    settings.OPENCLAW_ENABLED = True
    settings.OPENCLAW_GATEWAY_URL = "http://openclaw.local"
    settings.OPENCLAW_AUTH_TOKEN = "token"
    settings.OPENCLAW_DEFAULT_AGENT_ID = "default"
    settings.OPENCLAW_TRANSPORT = "gateway_ws"
    settings.OPENCLAW_WS_URL = "ws://openclaw.local"
    settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH = True
    try:
        yield settings
    finally:
        settings.OPENCLAW_ENABLED = original["OPENCLAW_ENABLED"]
        settings.OPENCLAW_GATEWAY_URL = original["OPENCLAW_GATEWAY_URL"]
        settings.OPENCLAW_AUTH_TOKEN = original["OPENCLAW_AUTH_TOKEN"]
        settings.OPENCLAW_DEFAULT_AGENT_ID = original["OPENCLAW_DEFAULT_AGENT_ID"]
        settings.OPENCLAW_TRANSPORT = original["OPENCLAW_TRANSPORT"]
        settings.OPENCLAW_WS_URL = original["OPENCLAW_WS_URL"]
        settings.OPENCLAW_WS_ALLOW_INSECURE_AUTH = original["OPENCLAW_WS_ALLOW_INSECURE_AUTH"]


@pytest.mark.asyncio
async def test_get_health_returns_pairing_error_without_raising(
    db_session,
    openclaw_gateway_ws_settings,
    monkeypatch,
) -> None:
    user = User(username="healthcheck", email="healthcheck@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()

    async def _health_snapshot(self):
        return {
            "reachable": False,
            "transport": "gateway_ws",
            "message": "Gateway WS health check failed",
            "capabilities": [],
        }

    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        raise OpenClawError("pairing required")

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.health_snapshot", _health_snapshot)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    service = ExecutionService(db=db_session)
    health = await service.get_health()

    assert health["reachable"] is False
    assert health["message"] == "pairing required"
    assert health["connected_nodes"] == 0
    assert health["supports_nodes"] is True


@pytest.mark.asyncio
async def test_get_health_prefers_user_profile_over_global_settings(
    db_session,
    monkeypatch,
) -> None:
    from app.config import settings

    original = {
        "OPENCLAW_ENABLED": settings.OPENCLAW_ENABLED,
        "OPENCLAW_GATEWAY_URL": settings.OPENCLAW_GATEWAY_URL,
        "OPENCLAW_TRANSPORT": settings.OPENCLAW_TRANSPORT,
        "OPENCLAW_WS_URL": settings.OPENCLAW_WS_URL,
    }
    settings.OPENCLAW_ENABLED = False
    settings.OPENCLAW_GATEWAY_URL = ""
    settings.OPENCLAW_TRANSPORT = "responses_http"
    settings.OPENCLAW_WS_URL = ""

    user = User(username="healthprofile", email="healthprofile@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await OpenClawConnectionProfileService(db_session).save_profile(
        user_id=user.id,
        payload={
            "gateway_url": "https://user.openclaw.example",
            "auth_token": "user-token",
            "transport": "gateway_ws",
        },
    )

    async def _health_snapshot(self):
        assert self._config.gateway_url == "https://user.openclaw.example"
        assert self._config.ws_url == "wss://user.openclaw.example"
        return {
            "reachable": True,
            "transport": "gateway_ws",
            "message": "gateway_ws",
            "capabilities": ["节点调用"],
        }

    async def _list_nodes(self, *, connected_only=True, last_connected=None):
        return {
            "items": [
                {
                    "nodeId": "node-1",
                    "name": "Remote Node",
                    "platform": "macos",
                    "connected": True,
                    "commands": ["system.run"],
                    "caps": ["system.run"],
                }
            ]
        }

    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.health_snapshot", _health_snapshot)
    monkeypatch.setattr("app.adapters.openclaw.client.OpenClawClient.list_nodes", _list_nodes)

    service = ExecutionService(db=db_session)
    health = await service.get_health(user_id=user.id)

    assert health["openclaw_enabled"] is True
    assert health["gateway_url"] == "https://user.openclaw.example"
    assert health["ws_url"] == "wss://user.openclaw.example"
    assert health["connection_source"] == "user_profile"
    assert health["connected_nodes"] == 1
    assert health["reachable"] is True

    settings.OPENCLAW_ENABLED = original["OPENCLAW_ENABLED"]
    settings.OPENCLAW_GATEWAY_URL = original["OPENCLAW_GATEWAY_URL"]
    settings.OPENCLAW_TRANSPORT = original["OPENCLAW_TRANSPORT"]
    settings.OPENCLAW_WS_URL = original["OPENCLAW_WS_URL"]
