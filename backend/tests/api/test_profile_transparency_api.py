from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.profile_transparency import router as profile_router
from app.db.session import get_db


@pytest.fixture
def profile_client(db_session):
    app = FastAPI()
    app.include_router(profile_router)

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


def test_override_inferred_rejects_non_adjustable_key(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.post(
        "/profile/override-inferred",
        json={"key": "community_engagement_level", "value": "high"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "key is not adjustable"


def test_reset_override_requires_key(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.post("/profile/reset-override", json={"key": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "key required"


def test_inferred_preferences_returns_behavioral_baseline_for_sparse_user(profile_client):
    client, state = profile_client
    state["current_user"] = type("UserStub", (), {"id": uuid4()})()

    response = client.get("/profile/inferred-preferences")

    assert response.status_code == 200
    payload = response.json()
    keys = {item["key"] for item in payload}
    assert "avg_question_complexity" in keys
    assert "community_engagement_level" in keys
    assert "social_learning_preference" in keys
