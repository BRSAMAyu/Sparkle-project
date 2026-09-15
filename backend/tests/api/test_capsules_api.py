from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1 import capsules as capsules_module
from app.api.v1.capsules import router as capsules_router
from app.db.session import get_db
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.user import User
from app.services.personalization.preference_service import PreferenceService


@pytest.fixture
def capsules_client(db_session):
    app = FastAPI()
    app.include_router(capsules_router, prefix="/capsules")

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
async def test_generate_batch_falls_back_to_sync_when_celery_unavailable(
    db_session,
    capsules_client,
    monkeypatch,
):
    client, state = capsules_client
    user = User(
        username="capsule_sync_user",
        email="capsule_sync_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    async def _mock_generate_batch(**kwargs):
        del kwargs
        return SimpleNamespace(
            id=uuid4(),
            status="completed",
            actual_count=2,
        )

    monkeypatch.setattr(
        capsules_module,
        "get_celery_status",
        lambda: {"status": "unhealthy", "active_workers": 0},
    )
    monkeypatch.setattr(
        capsules_module.curiosity_capsule_service,
        "generate_batch",
        _mock_generate_batch,
    )

    response = client.post(
        "/capsules/generate/batch",
        json={
            "depth_preference": 0.7,
            "curiosity_preference": 0.8,
            "requested_count": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "completed"
    assert payload["actual_count"] == 2
    assert payload["message"] == "胶囊已生成（同步降级）"


@pytest.mark.asyncio
async def test_submit_feedback_persists_inferred_preferences(
    db_session,
    capsules_client,
):
    client, state = capsules_client
    user = User(
        username="capsule_feedback_user",
        email="capsule_feedback_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    state["current_user"] = user

    capsule = CuriosityCapsule(
        user_id=user.id,
        title="Need deeper insight",
        content="capsule content",
    )
    db_session.add(capsule)
    await db_session.commit()
    await db_session.refresh(capsule)

    response = client.post(
        f"/capsules/{capsule.id}/feedback",
        json={
            "rating": 5,
            "helpful": True,
            "category": "too_short",
            "comment": "请更深入一些",
        },
    )

    assert response.status_code == 200

    prefs = await PreferenceService(db_session).get_preferences(user.id)
    inferred = prefs.inferred or {}
    assert inferred.get("depth_preference") == pytest.approx(0.51, rel=1e-3)
    assert inferred.get("curiosity_preference") == pytest.approx(0.505, rel=1e-3)


@pytest.mark.asyncio
async def test_mark_capsule_read_rejects_non_owner(
    db_session,
    capsules_client,
):
    client, state = capsules_client
    requester = User(
        username="capsule_read_requester",
        email="capsule_read_requester@example.com",
        hashed_password="hashed",
    )
    owner = User(
        username="capsule_read_owner",
        email="capsule_read_owner@example.com",
        hashed_password="hashed",
    )
    db_session.add_all([requester, owner])
    await db_session.flush()
    capsule = CuriosityCapsule(
        user_id=owner.id,
        title="Owner-only capsule",
        content="private capsule",
    )
    db_session.add(capsule)
    await db_session.commit()
    await db_session.refresh(capsule)
    state["current_user"] = requester

    response = client.post(f"/capsules/{capsule.id}/read")

    assert response.status_code == 404
    await db_session.refresh(capsule)
    assert capsule.is_read is False
