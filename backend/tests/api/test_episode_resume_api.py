"""V4-I01 · ``GET /episode-resume/tasks/{task_id}`` REST 入口守卫。

覆盖：
- 组成直通：服务层视图原样出（HTTP 200 + view）；
- 对象不存在 / 跨用户 → 404（不泄露存在性，house runs.py 先例）；
- 无 receipt ref / scheme 不符 → 200 + 类型化 ``context_receipt_missing``
  （不造伪 receipt、不出半真视图）；
- goal 终态 → 200 + ``goal_changed_requires_calibration``（旧计划不强推）。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.episode_resume import router as episode_resume_router
from app.db.session import get_db
from app.services.episode_resume_service import EpisodeResumeService

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 9, 28, 8, 55, 0)
_RECEIPT = "context_selection://csr_i01_api"


@pytest.fixture(name="api")
def _api(db_session):
    app = FastAPI()
    app.include_router(episode_resume_router)

    async def _override_get_db():
        yield db_session

    caller = SimpleNamespace(id=None)  # 由各用例置为真实 user id

    def _override_user():
        return caller

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    with TestClient(app) as test_client:
        test_client.caller = caller  # type: ignore[attr-defined]
        yield test_client


async def test_endpoint_returns_view(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["schema_version"] == "episode_resume_view.v1"
    assert body["view"]["task_ref"] == f"task://{task.id}"
    assert body["reason_code"] is None


async def test_endpoint_404_on_missing_and_cross_user(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    owner = await _make_user(db_session, suffix="o")
    outsider = await _make_user(db_session, suffix="x")
    _, task = await _make_episode(db_session, owner)

    # 不存在
    api.caller.id = owner.id
    resp = api.get(f"/episode-resume/tasks/{uuid4()}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 404
    # 跨用户（不泄露存在性）
    api.caller.id = outsider.id
    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 404


async def test_endpoint_missing_receipt_is_typed_not_fatal(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"] is None
    assert body["reason_code"] == "context_receipt_missing"


async def test_endpoint_goal_closed_returns_calibration(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user, goal_status="cancelled")
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"] is None
    assert body["reason_code"] == "goal_changed_requires_calibration"


async def test_service_is_read_only_surface():
    """读模型纪律锚：服务类不暴露任何写方法名（防漂移为第二真值写面）。"""
    write_forbidden = ("save", "create", "update", "delete", "insert", "commit", "upsert", "write")
    methods = [name for name in dir(EpisodeResumeService) if not name.startswith("_")]
    assert methods == ["build_resume_view"]
    assert not any(any(w in name.lower() for w in write_forbidden) for name in methods)
