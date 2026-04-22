from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.shop import router as shop_router
from app.db.session import get_db


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(shop_router, prefix="/shop")
    return app


def test_purchase_requires_idempotency_header():
    app = _build_app()

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    async def _override_user():
        return SimpleNamespace(id=uuid4())

    mock_service = SimpleNamespace(purchase_item=AsyncMock())
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch("app.api.v1.shop.get_shop_service", return_value=mock_service):
        with TestClient(app) as client:
            response = client.post("/shop/purchase", json={"item_id": "item-1"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Idempotency-Key header is required"
    mock_service.purchase_item.assert_not_called()


def test_purchase_passes_idempotency_header_to_service():
    app = _build_app()

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    async def _override_user():
        return SimpleNamespace(id=uuid4())

    mock_service = SimpleNamespace(
        purchase_item=AsyncMock(
            return_value={
                "success": True,
                "purchase_id": str(uuid4()),
                "item_id": "item-1",
                "item_name": "Item 1",
                "price_paid": 100,
                "balance_before": 500,
                "balance_after": 400,
                "item_type": "consumable",
                "rarity": "common",
                "replayed": False,
            }
        )
    )
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch("app.api.v1.shop.get_shop_service", return_value=mock_service):
        with TestClient(app) as client:
            response = client.post(
                "/shop/purchase",
                json={"item_id": "item-1"},
                headers={"Idempotency-Key": "purchase-key-1"},
            )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert mock_service.purchase_item.await_args.kwargs["idempotency_key"] == "purchase-key-1"
