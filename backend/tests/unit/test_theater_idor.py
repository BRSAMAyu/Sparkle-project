from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user_id, get_db
from app.api.v1.theater import router as theater_router
from app.main import sparkle_exception_handler
from app.core.exceptions import SparkleException
from app.models.theater_candidate_bundle import TheaterCandidateBundle
from app.models.theater_prediction import TheaterPrediction
from app.models.user import User


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(theater_router, prefix="/api/v1")
    app.add_exception_handler(SparkleException, sparkle_exception_handler)
    return app


@pytest.fixture
async def theater_idor_client(db_session):
    app = _build_test_app()
    current_user = {"id": ""}

    async def _override_get_db():
        yield db_session

    async def _override_get_current_user_id():
        return current_user["id"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user_id] = _override_get_current_user_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, current_user

    app.dependency_overrides.clear()


@pytest.fixture
async def theater_idor_seed(db_session):
    user_a = User(username="theater_a", email="theater_a@example.com", hashed_password="hashed")
    user_b = User(username="theater_b", email="theater_b@example.com", hashed_password="hashed")
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    bundle = TheaterCandidateBundle(
        user_id=user_a.id,
        prediction_id="prediction-a",
        topic="热力学第二章",
        target_name="熵增方向判断",
        target_resolution_mode="topic",
        status="ready",
        nodes_payload=[{"id": "node-1", "name": "熵增方向判断"}],
        edges_payload=[],
        semantic_matches=[],
        source_metadata={},
    )
    db_session.add(bundle)
    await db_session.flush()

    prediction = TheaterPrediction(
        prediction_id="prediction-a",
        user_id=user_a.id,
        topic="热力学第二章",
        target_name="熵增方向判断",
        target_resolution_mode="topic",
        horizon_days=14,
        preview_mode=False,
        generated_at=datetime.utcnow(),
        candidate_bundle_id=bundle.id,
        paths=[{"id": "route-a", "title": "稳态补链", "steps": [{"node_id": "node-1", "node_name": "熵增方向判断"}]}],
        discussion_turns=[],
        timeline=[],
        accuracy_tracking={},
        routing_notes={},
    )
    db_session.add(prediction)
    await db_session.commit()
    await db_session.refresh(prediction)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "prediction": prediction,
    }


@pytest.mark.asyncio
async def test_theater_idor_read_denies_cross_user_access(theater_idor_client, theater_idor_seed, monkeypatch):
    client, current_user = theater_idor_client
    current_user["id"] = str(theater_idor_seed["user_b"].id)

    published: list[tuple[str, dict[str, str]]] = []

    async def _fake_publish(event_type: str, payload: dict[str, str]) -> None:
        published.append((event_type, payload))

    monkeypatch.setattr("app.services.theater.prediction_theater_service.event_bus_reliable.publish", _fake_publish)

    response = await client.get(f"/api/v1/theater/predictions/{theater_idor_seed['prediction'].prediction_id}")

    assert response.status_code == 403
    body = response.json()
    assert body["message"] == "resource access denied"
    assert published[0][0] == "theater.access_denied"
    assert published[0][1]["requester_id"] == str(theater_idor_seed["user_b"].id)


@pytest.mark.asyncio
async def test_theater_idor_write_denies_cross_user_mutation(theater_idor_client, theater_idor_seed, monkeypatch):
    client, current_user = theater_idor_client
    current_user["id"] = str(theater_idor_seed["user_b"].id)

    published: list[tuple[str, dict[str, str]]] = []

    async def _fake_publish(event_type: str, payload: dict[str, str]) -> None:
        published.append((event_type, payload))

    monkeypatch.setattr("app.services.theater.prediction_theater_service.event_bus_reliable.publish", _fake_publish)

    response = await client.post(
        f"/api/v1/theater/predictions/{theater_idor_seed['prediction'].prediction_id}/actuals",
        json={"actual_completion_rate": 0.4, "actual_mastery": 55.0},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["message"] == "resource access denied"
    assert published[0][0] == "theater.access_denied"
    assert published[0][1]["target_resource_id"] == theater_idor_seed["prediction"].prediction_id


@pytest.mark.asyncio
async def test_theater_owner_can_read_own_prediction(theater_idor_client, theater_idor_seed):
    client, current_user = theater_idor_client
    current_user["id"] = str(theater_idor_seed["user_a"].id)

    response = await client.get(f"/api/v1/theater/predictions/{theater_idor_seed['prediction'].prediction_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["prediction_id"] == theater_idor_seed["prediction"].prediction_id
    assert body["user_id"] == str(theater_idor_seed["user_a"].id)
