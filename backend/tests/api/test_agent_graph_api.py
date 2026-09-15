from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.v2.agent_graph as agent_graph_module
from app.api.deps import get_current_user
from app.api.v2.agent_graph import router as agent_graph_router


def test_agent_graph_chat_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(agent_graph_router, prefix="/agent")

    with TestClient(app) as client:
        response = client.post("/agent/chat", json={"message": "hello", "stream": False})

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_agent_graph_chat_uses_current_user_id(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(agent_graph_router, prefix="/agent")
    user_id = uuid4()

    async def _override_user():
        return SimpleNamespace(id=user_id)

    calls = {}

    async def _ainvoke(inputs, config):
        calls["inputs"] = inputs
        calls["config"] = config
        return {"messages": [SimpleNamespace(content="response")]}

    app.dependency_overrides[get_current_user] = _override_user
    monkeypatch.setattr(agent_graph_module.sparkle_graph, "ainvoke", _ainvoke)

    with TestClient(app) as client:
        response = client.post("/agent/chat", json={"message": "hello", "stream": False})

    assert response.status_code == 200
    assert response.json()["response"] == "response"
    assert calls["inputs"]["user_id"] == str(user_id)
    assert calls["inputs"]["session_id"] == response.json()["session_id"]
