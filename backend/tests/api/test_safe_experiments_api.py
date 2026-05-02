from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.safe_experiments import router
from app.models.user import User


pytestmark = pytest.mark.asyncio


async def test_safe_experiment_create_transition_and_opt_out(db_session):
    user = User(
        username="safe-exp-admin",
        email="safe-exp-admin@example.com",
        hashed_password="hashed",
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    async def override_db():
        yield db_session

    app = FastAPI()
    app.include_router(router, prefix="/safe-experiments")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_superuser] = lambda: user

    payload = {
        "name": "Strategy pacing canary",
        "hypothesis": "Reducing pace improves completion without fatigue.",
        "domain": "exam_sprint",
        "excluded_context": ["D0_exam_day", "fatigue_critical"],
        "policies": [
            {"policy_key": "primary", "risk_level": "low"},
            {"policy_key": "reduce_pace", "risk_level": "low"},
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/safe-experiments/", json=payload)
        assert created.status_code == 200
        experiment_key = created.json()["experiment_key"]

        transitioned = await client.post(
            f"/safe-experiments/{experiment_key}/transition",
            json={"target_status": "shadow", "reason": "validated design"},
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "shadow"

        opt_out = await client.post("/safe-experiments/me/opt-out", json={"opted_out": True})
        assert opt_out.status_code == 200
        assert opt_out.json() == {"opted_out": True}

        opt_out_state = await client.get("/safe-experiments/me/opt-out")
        assert opt_out_state.status_code == 200
        assert opt_out_state.json() == {"opted_out": True}

    app.dependency_overrides.clear()
