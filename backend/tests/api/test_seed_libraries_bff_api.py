from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.seed_libraries import router as seed_libraries_router
from app.db.session import get_db


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(seed_libraries_router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), is_superuser=False)

    async def _override_db():
        mock_db = AsyncMock(spec=AsyncSession)
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def test_seed_libraries_list_can_bridge_from_template_packs(monkeypatch):
    monkeypatch.setattr("app.api.v1.seed_libraries.settings.ENABLE_SEED_LIBRARY_TEMPLATE_BFF", True)
    monkeypatch.setattr("app.api.v1.seed_libraries.settings.ENABLE_SEED_TEMPLATE_PACKS_V1", True)
    monkeypatch.setattr("app.api.v1.seed_libraries.service.list_libraries", lambda *args, **kwargs: ([], 0))

    pack = SimpleNamespace(
        id=uuid4(),
        scenario_type="study_plan",
        name="学习规划包",
        description="用于学习规划的模板包",
        owner_id=uuid4(),
        visibility="public",
        status="published",
        language="zh",
        tags=["study", "plan"],
        quality_score=0.92,
        adoption_score=0.33,
        created_at=_now(),
        updated_at=_now(),
    )

    async def _mock_list_packs(*args, **kwargs):
        return [pack]

    monkeypatch.setattr("app.api.v1.seed_libraries.template_service.list_packs", _mock_list_packs)

    client = _build_client()
    with client:
        resp = client.get("/seed-libraries?source=templates")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "学习规划包"
    assert body["data"][0]["category"] == "teaching_content"
    assert body["meta"]["total"] == 1


def test_seed_libraries_subscribe_can_bridge_to_template(monkeypatch):
    monkeypatch.setattr("app.api.v1.seed_libraries.settings.ENABLE_SEED_LIBRARY_TEMPLATE_BFF", True)
    monkeypatch.setattr("app.api.v1.seed_libraries.settings.ENABLE_SEED_TEMPLATE_PACKS_V1", True)

    template_id = uuid4()
    user_id = uuid4()

    template = SimpleNamespace(
        id=template_id,
        name="写作模板",
        pack_id=uuid4(),
    )
    subscription = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        is_enabled=True,
        priority=3,
        created_at=_now(),
    )

    async def _mock_get_template(*args, **kwargs):
        return template

    async def _mock_subscribe(*args, **kwargs):
        return subscription

    monkeypatch.setattr("app.api.v1.seed_libraries.template_service.get_template", _mock_get_template)
    monkeypatch.setattr("app.api.v1.seed_libraries.template_service.subscribe", _mock_subscribe)

    client = _build_client()
    with client:
        client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, is_superuser=False)
        resp = client.post(f"/seed-libraries/subscribe/{template_id}", json={"priority": 3})

    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["library_id"] == str(template_id)
    assert body["data"]["library_name"] == "写作模板"
