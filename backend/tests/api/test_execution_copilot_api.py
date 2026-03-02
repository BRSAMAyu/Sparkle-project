from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.execution_copilot import router as execution_copilot_router
from app.db.session import get_db


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(execution_copilot_router)

    async def _override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
    return TestClient(app)


def test_execution_copilot_routes(monkeypatch):
    plan_id = str(uuid4())

    async def _fake_build_copilot(self, *, user_id, plan_id, limit=3):
        return {
            "plan_id": str(plan_id),
            "today_actions": [],
            "blockers": [],
            "repair_suggestions": [],
            "execution_copilot_hint": "ok",
            "checkpoint_summary": {
                "due": 1,
                "done": 1,
                "skipped": 0,
                "done_rate": 1.0,
                "skip_rate": 0.0,
                "due_completion_rate": 1.0,
                "last_status": "done",
            },
            "risk_level": "low",
            "adoptable_actions": [],
        }

    async def _fake_record(self, *, user_id, plan_id, status, task_id=None, note=None):
        return {"success": True, "event_type": f"checkpoint_{status}"}

    async def _fake_timeline(self, *, user_id, plan_id, days=7):
        return {
            "plan_id": str(plan_id),
            "timeline_days": days,
            "timeline": [],
            "checkpoint_summary": {
                "due": 0,
                "done": 0,
                "skipped": 0,
                "done_rate": 0.0,
                "skip_rate": 0.0,
                "due_completion_rate": 0.0,
                "last_status": "none",
            },
            "top_blockers": [],
        }

    monkeypatch.setattr(
        "app.api.v1.execution_copilot.ExecutionCopilotService.build_copilot",
        _fake_build_copilot,
    )
    monkeypatch.setattr(
        "app.api.v1.execution_copilot.ExecutionCopilotService.record_checkpoint_event",
        _fake_record,
    )
    monkeypatch.setattr(
        "app.api.v1.execution_copilot.ExecutionCopilotService.build_timeline",
        _fake_timeline,
    )

    client = _build_client()

    get_resp = client.get(f"/execution/copilot/{plan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["success"] is True
    assert "checkpoint_summary" in get_resp.json()["data"]

    checkpoint_resp = client.post(
        f"/execution/copilot/{plan_id}/checkpoint",
        json={"status": "done", "task_id": "task-1"},
    )
    assert checkpoint_resp.status_code == 200
    assert checkpoint_resp.json()["data"]["success"] is True

    timeline_resp = client.get(f"/execution/copilot/{plan_id}/timeline?days=14")
    assert timeline_resp.status_code == 200
    assert timeline_resp.json()["data"]["timeline_days"] == 14
