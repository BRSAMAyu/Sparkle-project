"""GAP-3: HTTP-level tests for executions.py API endpoints.

Tests the 5 core execution operations:
  1. GET /health — health check (unauthenticated)
  2. POST /tasks/{task_id}/handoff — start task execution
  3. POST /{intent_id}/cancel — cancel an active intent
  4. POST /{intent_id}/handback — hand back a completed execution
  5. GET /{intent_id} — fetch intent by ID
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user
from app.api.v1.executions import router as executions_router
from app.db.session import get_db
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus
from app.models.user import User


def _make_user():
    return SimpleNamespace(id=uuid4())


def _make_intent(user_id=None, status=ExecutionIntentStatus.pending):
    intent = MagicMock(spec=ExecutionIntent)
    intent.id = uuid4()
    intent.user_id = user_id or uuid4()
    intent.task_id = uuid4()
    intent.status = status
    intent.node_id = None
    intent.openclaw_session_id = None
    intent.template_id = None
    intent.user_note = None
    intent.priority = 0
    intent.created_at = None
    intent.updated_at = None
    intent.started_at = None
    intent.completed_at = None
    intent.error_message = None
    intent.retry_count = 0
    intent.metadata_ = {}
    return intent


@pytest.fixture
def executions_client():
    app = FastAPI()
    app.include_router(executions_router, prefix="/executions")

    db_mock = MagicMock(spec=AsyncSession)

    async def _get_db():
        yield db_mock

    user = _make_user()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_current_user] = lambda: user

    with TestClient(app, raise_server_exceptions=False) as client:
        client._test_user = user
        client._db_mock = db_mock
        yield client


def test_execution_health_returns_200(executions_client):
    """GET /executions/health — should return 200 with status field."""
    with patch("app.api.v1.executions.ExecutionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.get_health.return_value = {
            "openclaw_enabled": False,
            "reachable": False,
            "message": "OpenClaw not configured",
        }
        mock_svc_cls.return_value = mock_svc

        resp = executions_client.get("/executions/health")

    assert resp.status_code == 200


def test_get_intent_by_id(executions_client):
    """GET /executions/{intent_id} — returns 200 with intent data."""
    user = executions_client._test_user
    intent = _make_intent(user_id=user.id)

    with patch("app.api.v1.executions.ExecutionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.get_intent.return_value = intent
        mock_svc_cls.return_value = mock_svc

        resp = executions_client.get(f"/executions/{intent.id}")

    assert resp.status_code == 200


def test_cancel_intent_returns_200(executions_client):
    """POST /executions/{intent_id}/cancel — returns 200."""
    user = executions_client._test_user
    intent = _make_intent(user_id=user.id, status=ExecutionIntentStatus.active)
    intent.status = ExecutionIntentStatus.cancelled

    with patch("app.api.v1.executions.ExecutionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.cancel_intent.return_value = intent
        mock_svc_cls.return_value = mock_svc

        resp = executions_client.post(f"/executions/{intent.id}/cancel")

    assert resp.status_code == 200


def test_handback_intent_returns_200(executions_client):
    """POST /executions/{intent_id}/handback — returns 200."""
    user = executions_client._test_user
    intent = _make_intent(user_id=user.id, status=ExecutionIntentStatus.completed)

    with patch("app.api.v1.executions.ExecutionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.handback_intent.return_value = intent
        mock_svc_cls.return_value = mock_svc

        resp = executions_client.post(f"/executions/{intent.id}/handback")

    assert resp.status_code == 200


def test_handoff_task_requires_task_id(executions_client):
    """POST /executions/tasks/{task_id}/handoff — missing task returns 404 or 422."""
    with patch("app.api.v1.executions.ExecutionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        from fastapi import HTTPException
        mock_svc.handoff_task.side_effect = HTTPException(status_code=404, detail="task_not_found")
        mock_svc_cls.return_value = mock_svc

        resp = executions_client.post(f"/executions/tasks/{uuid4()}/handoff")

    assert resp.status_code in (404, 422)
