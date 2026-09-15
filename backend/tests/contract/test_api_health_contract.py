from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser
from app.api.v1.health_production import router as health_router
from app.core.cache import cache_service
from app.db.session import get_db


@pytest.fixture
def health_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_router, prefix="/api/v1")

    async def override_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_superuser] = lambda: SimpleNamespace(
        id="admin-user",
        is_superuser=True,
    )
    return app


@pytest.mark.asyncio
async def test_health_endpoint_contract_includes_checks_and_details(health_app: FastAPI):
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=object())
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)
    health_app.dependency_overrides[get_db] = lambda: db

    with patch.object(cache_service, "redis", redis_client):
        async with AsyncClient(
            transport=ASGITransport(app=health_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/health?detailed=true")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["system"]["app_name"]
    assert data["system"]["version"]
    assert "timestamp" in data["system"]
    assert data["checks"]["database"]["status"] == "ok"
    assert data["checks"]["redis"]["status"] == "ok"
    assert data["details"]["features"]["circuit_breaker"] is True
    assert "grpc_port" in data["details"]["config"]


@pytest.mark.asyncio
async def test_health_detailed_exposes_queue_metrics_when_redis_is_available(health_app: FastAPI):
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=object())
    redis_client = MagicMock()
    redis_client.ping = AsyncMock(return_value=True)
    redis_client.llen = AsyncMock(return_value=7)
    health_app.dependency_overrides[get_db] = lambda: db

    with patch.object(cache_service, "redis", redis_client), patch(
        "app.api.v1.health_production.health_check",
        AsyncMock(
            return_value={
                "status": "healthy",
                "system": {"app_name": "Sparkle", "version": "test"},
                "checks": {"database": {"status": "ok"}},
                "details": {"features": {"circuit_breaker": True}},
            }
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=health_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/health/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["summarization_queue_length"] == 7
    assert data["metrics"]["queue_healthy"] is True


@pytest.mark.asyncio
async def test_readiness_returns_503_with_stable_error_detail_when_dependency_fails(health_app: FastAPI):
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=RuntimeError("db unavailable"))
    health_app.dependency_overrides[get_db] = lambda: db

    with patch.object(cache_service, "redis", None):
        async with AsyncClient(
            transport=ASGITransport(app=health_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["detail"]["status"] == "not_ready"
    assert "db unavailable" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_liveness_contract_is_minimal_and_timestamped(health_app: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=health_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert isinstance(data["timestamp"], str)
