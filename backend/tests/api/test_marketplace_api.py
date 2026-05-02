from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.marketplace import router as marketplace_router
from app.models.marketplace import MarketplaceSkill, PackAdoptionHistory, UserSkillAdoption  # noqa: F401
from app.models.user import User
from app.signals.marketplace import MarketplacePersistenceService, SkillCard


@pytest.fixture
def marketplace_client(db_session):
    app = FastAPI()
    app.include_router(marketplace_router)
    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_current_active_superuser] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


async def _user(db_session, username: str, *, is_superuser: bool = False) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _listed_skill(db_session) -> MarketplaceSkill:
    service = MarketplacePersistenceService(db_session)
    return await service.register_skill_card(
        SkillCard(
            card_id="sk_api_marketplace",
            name="API listed skill",
            description="Preview and adopt through API.",
            author_id="00000000-0000-0000-0000-000000000002",
            goal_type="exam",
            domain="math",
            trigger_condition="stuck_on_transfer",
            action_template="use one worked example first",
            expected_outcome="task_started_and_completed",
            evidence_grade=3,
            evidence_summary="stable outcome-backed skill",
            episode_count=10,
            success_rate=0.8,
            context_signatures=[{"domain": "math"}],
            status="active",
        )
    )


@pytest.mark.asyncio
async def test_marketplace_api_preview_and_confirmed_adoption(db_session, marketplace_client) -> None:
    client, state = marketplace_client
    user = await _user(db_session, "marketplace_api_user")
    skill = await _listed_skill(db_session)
    state["current_user"] = user

    preview = client.get(f"/marketplace/skills/{skill.skill_id}/preview")
    assert preview.status_code == 200
    assert preview.json()["requires_explicit_confirm"] is True

    rejected = client.post(f"/marketplace/skills/{skill.skill_id}/adopt", json={"confirm": False})
    assert rejected.status_code == 422

    adopted = client.post(
        f"/marketplace/skills/{skill.skill_id}/adopt",
        json={"confirm": True, "trace_id": "trace-api-adopt"},
    )
    assert adopted.status_code == 201
    assert adopted.json()["asset_id"] == skill.skill_id
    assert adopted.json()["explicit_confirm"] is True


@pytest.mark.asyncio
async def test_marketplace_admin_registration_rejects_pii(db_session, marketplace_client) -> None:
    client, state = marketplace_client
    admin = await _user(db_session, "marketplace_admin", is_superuser=True)
    state["current_user"] = admin

    response = client.post(
        "/marketplace/admin/skills",
        json={
            "skill_id": "sk_admin_pii",
            "name": "Unsafe listing",
            "description": "Call me at 13800138000",
            "evidence_grade": 3,
            "episode_count": 8,
            "success_rate": 0.75,
            "status": "active",
        },
    )

    assert response.status_code == 422
    assert "pii_detected" in response.json()["detail"]
