from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.experiments import router as experiments_router
from app.models.experiment import ABExperiment, ExperimentStatus
from app.models.user import User


@pytest.fixture
def experiments_client(db_session):
    app = FastAPI()
    app.include_router(experiments_router, prefix="/experiments")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


async def _create_user(db_session, username: str, *, is_superuser: bool = False) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _create_experiment(db_session, owner: User) -> ABExperiment:
    experiment = ABExperiment(
        name="Owner experiment",
        hypothesis="Owner scoped access",
        status=ExperimentStatus.CREATED.value,
        created_by=owner.id,
    )
    db_session.add(experiment)
    await db_session.commit()
    await db_session.refresh(experiment)
    return experiment


@pytest.mark.asyncio
async def test_get_experiment_rejects_non_owner(db_session, experiments_client) -> None:
    client, state = experiments_client
    owner = await _create_user(db_session, "experiment_owner")
    requester = await _create_user(db_session, "experiment_requester")
    experiment = await _create_experiment(db_session, owner)
    state["current_user"] = requester

    response = client.get(f"/experiments/{experiment.id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_experiment_allows_superuser(db_session, experiments_client) -> None:
    client, state = experiments_client
    owner = await _create_user(db_session, "experiment_owner_super")
    superuser = await _create_user(db_session, "experiment_superuser", is_superuser=True)
    experiment = await _create_experiment(db_session, owner)
    state["current_user"] = superuser

    response = client.get(f"/experiments/{experiment.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(experiment.id)


@pytest.mark.asyncio
async def test_start_experiment_rejects_non_owner_before_framework(db_session, experiments_client) -> None:
    client, state = experiments_client
    owner = await _create_user(db_session, "experiment_start_owner")
    requester = await _create_user(db_session, "experiment_start_requester")
    experiment = await _create_experiment(db_session, owner)
    state["current_user"] = requester

    response = client.post(f"/experiments/{experiment.id}/start")

    assert response.status_code == 404
