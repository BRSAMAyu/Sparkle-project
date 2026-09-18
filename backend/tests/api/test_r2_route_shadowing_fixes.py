"""R2-EI-13 / R2-EI-14 回归：字面量路由必须先于同形参数化路由声明。

修复前：
- ``DELETE /notification-center/notifications/clear-read`` 声明在
  ``DELETE /notifications/{notification_id}`` 之后，请求被参数化路由捕获，
  ``notification_id="clear-read"`` 未通过 UUID 校验 → 恒 422（R2-EI-13，P1，
  移动端 notification_center_repository.dart:309 活跃调用）。
- ``GET /seed-libraries/my-subscriptions`` 声明在 ``GET /seed-libraries/{library_id}``
  之后，同理恒 422（R2-EI-14，P2，Go 网关 proxy_routes.go 亦暴露该路径）。

红-绿证明：TestClient 实际 dispatch，修复前这两个行为断言为 422（红），
重排声明顺序后为 200（绿）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.notification_center as notification_center_module
import app.api.v1.seed_libraries as seed_libraries_module
from app.api.deps import get_current_user
from app.db.session import get_db


class _FakeNotificationCenterService:
    """替换真实服务，隔离 DB；返回可辨识的固定值以证明 dispatch 目标。"""

    def __init__(self, db):
        self.db = db

    async def clear_read_notifications(self, user_id):
        return 3

    async def delete_notification(self, user_id, notification_id, notification_type):
        return True


@pytest.fixture
def shadow_client(monkeypatch):
    monkeypatch.setattr(
        notification_center_module, "NotificationCenterService", _FakeNotificationCenterService
    )

    async def _fake_get_subscriptions(db, user_id, is_enabled):
        return []

    monkeypatch.setattr(
        seed_libraries_module.service, "get_subscriptions", _fake_get_subscriptions
    )

    app = FastAPI()
    app.include_router(notification_center_module.router)
    app.include_router(seed_libraries_module.router)

    async def _override_get_db():
        yield MagicMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    with TestClient(app) as test_client:
        yield test_client


# ---------- R2-EI-13: notification_center clear-read ----------


def test_clear_read_dispatches_to_literal_handler(shadow_client):
    """修复前红：恒 422（被 {notification_id} 捕获且 UUID 校验失败）。"""
    resp = shadow_client.delete("/notification-center/notifications/clear-read")
    assert resp.status_code != 422, (
        "R2-EI-13: DELETE /notifications/clear-read is shadowed by "
        "DELETE /notifications/{notification_id} and always 422s"
    )
    assert resp.status_code == 200
    # count == 3 证明确实进入了字面量 handler（fake 服务返回值），
    # 而非某个参数化 handler 碰巧放行。
    assert resp.json() == {"message": "Cleared 3 read notifications", "count": 3}


def test_notification_center_literal_route_declared_before_parameterized():
    """声明顺序守卫：字面量 /clear-read 必须先于 /{notification_id} 注册。"""
    delete_paths = [
        r.path
        for r in notification_center_module.router.routes
        if isinstance(r, APIRoute)
        and "DELETE" in (r.methods or set())
        and r.path
        in (
            "/notification-center/notifications/clear-read",
            "/notification-center/notifications/{notification_id}",
        )
    ]
    assert delete_paths == [
        "/notification-center/notifications/clear-read",
        "/notification-center/notifications/{notification_id}",
    ], f"Literal DELETE route must be declared first, got order: {delete_paths}"


def test_single_notification_delete_still_works(shadow_client):
    """重排不得破坏参数化路由本身的功能。"""
    resp = shadow_client.delete(
        f"/notification-center/notifications/{uuid4()}",
        params={"notification_type": "system"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Notification deleted"}


# ---------- R2-EI-14: seed_libraries my-subscriptions alias ----------


def test_my_subscriptions_alias_dispatches_to_literal_handler(shadow_client):
    """修复前红：恒 422（被 {library_id} 捕获且 UUID 校验失败）。"""
    resp = shadow_client.get("/seed-libraries/my-subscriptions")
    assert resp.status_code != 422, (
        "R2-EI-14: GET /seed-libraries/my-subscriptions is shadowed by "
        "GET /seed-libraries/{library_id} and always 422s"
    )
    assert resp.status_code == 200
    # 空列表 payload 证明进入 get_my_subscriptions（fake 服务返回值），
    # 而非 get_library 的 LibraryResponse 形状（后者 data 是库详情对象）。
    body = resp.json()
    assert body["data"] == []
    assert body["success"] is True


def test_seed_libraries_literal_route_declared_before_parameterized():
    """声明顺序守卫：字面量 /my-subscriptions 必须先于 /{library_id} 注册。"""
    get_paths = [
        r.path
        for r in seed_libraries_module.router.routes
        if isinstance(r, APIRoute)
        and "GET" in (r.methods or set())
        and r.path in ("/seed-libraries/my-subscriptions", "/seed-libraries/{library_id}")
    ]
    assert get_paths == [
        "/seed-libraries/my-subscriptions",
        "/seed-libraries/{library_id}",
    ], f"Literal GET route must be declared first, got order: {get_paths}"


def test_seed_library_detail_still_works(shadow_client, monkeypatch):
    """重排不得破坏 {library_id} 参数化路由本身的功能。"""

    async def _fake_get_library_for_user(db, library_id, user_id, include_items=True):
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=library_id,
            name="lib",
            description="",
            category="few_shot",
            visibility="private",
            language="zh",
            tags=[],
            is_official=False,
            is_featured=False,
            quality_score=None,
            owner_id=user_id,
            created_at=now,
            updated_at=now,
        )

    async def _fake_get_library_stats(db, library_id):
        return {"item_count": 0, "subscriber_count": 0}

    async def _fake_get_rating_summary(db, library_id, user_id):
        return {
            "user_rating_avg": None,
            "user_rating_count": 0,
            "current_user_rating": None,
        }

    async def _fake_get_library_adoption_actions(db, library):
        return []

    monkeypatch.setattr(
        seed_libraries_module.service, "get_library_for_user", _fake_get_library_for_user
    )
    monkeypatch.setattr(seed_libraries_module.service, "get_library_stats", _fake_get_library_stats)
    monkeypatch.setattr(
        seed_libraries_module.service, "get_rating_summary", _fake_get_rating_summary
    )
    monkeypatch.setattr(
        seed_libraries_module.service,
        "get_library_adoption_actions",
        _fake_get_library_adoption_actions,
    )
    monkeypatch.setattr(
        seed_libraries_module.service,
        "_blend_quality_score",
        lambda base, avg, count: base,
    )

    resp = shadow_client.get(f"/seed-libraries/{uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "lib"
