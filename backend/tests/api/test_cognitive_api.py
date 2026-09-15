from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1 import cognitive as cognitive_module
from app.api.v1.cognitive import router as cognitive_router
from app.db.session import get_db


class _SingleAccessUser:
    def __init__(self, user_id):
        self._user_id = user_id
        self._reads = 0

    @property
    def id(self):
        self._reads += 1
        if self._reads > 1:
            raise RuntimeError("id should only be read once")
        return self._user_id


@pytest.fixture
def cognitive_client(db_session):
    app = FastAPI()
    app.include_router(cognitive_router, prefix="/cognitive")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_create_fragment_reads_current_user_id_once(
    cognitive_client,
    monkeypatch,
):
    client, state = cognitive_client
    user_id = uuid4()
    fragment_id = uuid4()
    state["current_user"] = _SingleAccessUser(user_id)

    async def _mock_create_fragment(self, **kwargs):
        del self
        assert kwargs["user_id"] == user_id
        return SimpleNamespace(
            id=fragment_id,
            user_id=user_id,
            content=kwargs["content"],
            source_type=kwargs["source_type"],
            resource_type=kwargs["resource_type"],
            resource_url=None,
            context_tags=kwargs["context_tags"],
            error_tags=kwargs["error_tags"],
            severity=kwargs["severity"],
            sentiment=None,
            analysis_status="pending",
            error_message=None,
            task_id=None,
            source_event_id=kwargs["source_event_id"],
            persona_version=kwargs["persona_version"],
            created_at="2026-03-19T00:00:00",
        )

    monkeypatch.setattr(
        cognitive_module.CognitiveService,
        "create_fragment",
        _mock_create_fragment,
    )
    monkeypatch.setattr(
        cognitive_module,
        "_analyze_fragment_task",
        lambda *args, **kwargs: None,
    )

    response = client.post(
        "/cognitive/fragments",
        json={
            "content": "debug fragment",
            "source_type": "behavior",
            "resource_type": "text",
            "context_tags": {"scene": "test"},
            "error_tags": ["procrastination"],
            "severity": 3,
            "source_event_id": "test-source-event",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(user_id)
    assert payload["id"] == str(fragment_id)
