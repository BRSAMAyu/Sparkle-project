from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
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
                headers={"Idempotency-Key": "test-adjust-1"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["balance"] == 60
    mock_service.grant_photons.assert_awaited_once()
    mock_service.record_transaction.assert_awaited_once()


def test_adjust_requires_idempotency_key_after_superuser_auth():
    app = _build_app()

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    async def _override_superuser():
        return SimpleNamespace(id=uuid4(), is_superuser=True)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_superuser] = _override_superuser

    with TestClient(app) as client:
        response = client.post(
            "/photons/adjust",
            json={
                "user_id": str(uuid4()),
                "amount": 50,
                "reason": "manual correction",
                "transaction_type": "admin_adjustment",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Idempotency-Key header is required"


def test_transfer_returns_real_transfer_id():
    app = _build_app()
    transfer_id = str(uuid4())
    mock_service = SimpleNamespace(
        transfer_photons=AsyncMock(
            return_value={
                "from_user_id": str(uuid4()),
                "to_user_id": str(uuid4()),
                "amount": 25,
                "from_balance": 75,
                "to_balance": 25,
                "reason": "gift",
                "transfer_id": transfer_id,
            }
        ),
    )

    async def _override_get_db():
        db = MagicMock(spec=AsyncSession)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "receiver"
        db.execute = AsyncMock(return_value=execute_result)
        yield db

    async def _override_user():
        return SimpleNamespace(id=uuid4(), username="sender")

    from app.api.deps import get_current_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user

    with patch("app.api.v1.photons.get_photon_service", return_value=mock_service):
        with TestClient(app) as client:
            response = client.post(
                "/photons/transfer",
                json={
                    "recipient_id": str(uuid4()),
                    "amount": 25,
                    "message": "gift",
                },
                headers={"Idempotency-Key": "transfer-1"},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transfer_id"] == transfer_id


def _guest_user_override(request: Request):
    """Dependency that mimics deps.get_current_user_id's token_payload contract.

    get_current_user_id stores the decoded JWT on request.state.token_payload;
    the transfer guard must read the is_guest claim from there instead of
    comparing against a legacy demo constant.
    """
    request.state.token_payload = {"sub": str(uuid4()), "is_guest": True}
    return SimpleNamespace(id=uuid4(), username="guest_probe")


def _full_account_user_override(request: Request):
    request.state.token_payload = {"sub": str(uuid4())}
    return SimpleNamespace(id=uuid4(), username="regular_user")


def test_transfer_forbidden_for_guest_jwt_claim():
    """Guest JWT (is_guest claim) must get 403 on /photons/transfer.

    Regression for gamification-eval P1-4: the old guard only compared the
    legacy constant GUEST_USER_ID="guest_sparkle_demo_visitor", so any real
    guest (UUID id, guest_* username) could transfer photons.
    """
    app = _build_app()
    mock_service = SimpleNamespace(transfer_photons=AsyncMock())

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _guest_user_override

    with patch("app.api.v1.photons.get_photon_service", return_value=mock_service):
        with TestClient(app) as client:
            response = client.post(
                "/photons/transfer",
                json={"recipient_id": str(uuid4()), "amount": 10, "message": "probe"},
                headers={"Idempotency-Key": "guest-transfer-1"},
            )

    assert response.status_code == 403
    assert "Guest users cannot transfer" in response.json()["detail"]
    mock_service.transfer_photons.assert_not_awaited()


def test_transfer_allowed_for_full_account_token():
    """Non-guest token (no is_guest claim) still transfers normally."""
    app = _build_app()
    transfer_id = uuid4()
    mock_service = SimpleNamespace(
        transfer_photons=AsyncMock(
            return_value={
                "from_user_id": str(uuid4()),
                "to_user_id": str(uuid4()),
                "amount": 25,
                "from_balance": 75,
                "to_balance": 25,
                "reason": "gift",
                "transfer_id": transfer_id,
            }
        ),
    )

    async def _override_get_db():
        db = MagicMock(spec=AsyncSession)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = "receiver"
        db.execute = AsyncMock(return_value=execute_result)
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _full_account_user_override

    with patch("app.api.v1.photons.get_photon_service", return_value=mock_service):
        with TestClient(app) as client:
            response = client.post(
                "/photons/transfer",
                json={"recipient_id": str(uuid4()), "amount": 25, "message": "gift"},
                headers={"Idempotency-Key": "full-transfer-1"},
            )

    assert response.status_code == 200
    assert response.json()["transfer_id"] == str(transfer_id)
