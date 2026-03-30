from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router


def test_api_root_contract_exposes_stable_endpoint_index():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    with TestClient(app) as client:
        response = client.get("/api/v1/")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v1"
    assert data["status"] == "active"
    assert "/health" in data["endpoints"]
    assert "/chat" in data["endpoints"]
    assert "/tasks" in data["endpoints"]


def test_openapi_contains_critical_v1_paths():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/" in paths
    assert "/api/v1/health/health/live" in paths
    assert "/api/v1/health/health/ready" in paths
    assert "/api/v1/chat/chat" in paths
    assert "/api/v1/tasks" in paths


def test_openapi_marks_health_live_with_get_operation():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    schema = app.openapi()
    operation = schema["paths"]["/api/v1/health/health/live"]["get"]

    assert operation["summary"]
    assert "responses" in operation
    assert "200" in operation["responses"]
