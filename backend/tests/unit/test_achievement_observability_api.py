from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_superuser
from app.api.v1 import observability
from app.models.user import User

app = FastAPI()
app.include_router(observability.router, prefix="/api/v1")


@pytest.mark.asyncio
async def test_achievement_compensation_observability_requires_superuser():
    def override_superuser_forbidden():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_current_active_superuser] = override_superuser_forbidden

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/admin/observability/achievement-photon-compensations")

    assert resp.status_code == 403
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_achievement_compensation_observability_returns_dashboard(monkeypatch):
    admin_user = User(
        id=uuid4(),
        username="reward_admin",
        email="reward_admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
    )

    async def override_superuser():
        return admin_user

    async def fake_dashboard(*, limit: int = 20):
        return {
            "summary": {"tracked_events": 4, "open_alert_count": 1},
            "open_alerts": [{"achievement_id": "ach-1", "status": "retry_failed"}],
            "events": [{"achievement_id": "ach-1", "status": "scheduled"}],
        }

    monkeypatch.setattr(
        "app.api.v1.observability.AchievementRewardObservability.get_dashboard_payload",
        fake_dashboard,
    )
    app.dependency_overrides[get_current_active_superuser] = override_superuser

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/api/v1/admin/observability/achievement-photon-compensations?limit=5")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["summary"]["tracked_events"] == 4
    assert payload["summary"]["open_alert_count"] == 1
    assert payload["open_alerts"][0]["achievement_id"] == "ach-1"
    app.dependency_overrides = {}
