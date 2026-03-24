from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser
from app.api.v1.photons import router as photons_router
from app.db.session import get_db


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(photons_router, prefix="/photons")
    return app


def test_adjust_requires_superuser():
    app = _build_app()

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    async def _forbidden_superuser():
        raise HTTPException(status_code=403, detail="Not enough permissions")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_superuser] = _forbidden_superuser

    with TestClient(app) as client:
        response = client.post(
            "/photons/adjust",
            json={
                "user_id": str(uuid4()),
                "amount": 50,
                "reason": "test",
                "transaction_type": "admin_adjustment",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


def test_adjust_allows_superuser_and_records_transaction():
    app = _build_app()
    mock_service = SimpleNamespace(
        grant_photons=AsyncMock(
            return_value={
                "user_id": str(uuid4()),
                "old_balance": 10,
                "new_balance": 60,
            }
        ),
        deduct_photons=AsyncMock(),
        record_transaction=AsyncMock(),
    )

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    async def _override_superuser():
        return SimpleNamespace(id=uuid4(), is_superuser=True)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_superuser] = _override_superuser

    with patch("app.api.v1.photons.get_photon_service", return_value=mock_service):
        with TestClient(app) as client:
            response = client.post(
                "/photons/adjust",
                json={
                    "user_id": str(uuid4()),
                    "amount": 50,
                    "reason": "manual correction",
                    "transaction_type": "admin_adjustment",
                    "extra_data": {"source": "api-test"},
                },
            )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["balance"] == 60
    mock_service.grant_photons.assert_awaited_once()
    mock_service.record_transaction.assert_awaited_once()
