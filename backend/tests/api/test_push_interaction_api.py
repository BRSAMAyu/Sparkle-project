"""V3-FIX-337 引擎侧锚点：POST /api/v1/push/interaction 端点行为。

该端点是推送交互回执（opened/dismissed/...）的唯一写方面（mobile
notification_service._reportPushInteraction）。网关缺 /push 代理组曾使全链
404（修复面在网关），引擎侧本测试钉住三件事，防止端点本身漂移再次造成
engine-mounted-but-changed 断链：

1. 路由形状：完整路径恰为 ``/push/interaction``（mobile
   ApiEndpoints.pushInteraction 与网关代理面都按它拼）；
2. 合法 action 透传 PushFeedbackService.process_interaction（user_id 来自
   当前用户，timestamp 缺省落服务端 now）；
3. 非法 action 返回 400 并记录 push_judgment/invalid，不触达 service。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.push_interaction import router as push_interaction_router
from app.db.session import get_db


def _build_client(monkeypatch, captured: list[dict]):
    app = FastAPI()
    app.include_router(push_interaction_router)

    async def _override_get_db():
        yield None  # service 被桩替代，db 不触达

    user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    async def _fake_process_interaction(self, *, user_id, push_id, action, timestamp):
        captured.append(
            {
                "user_id": user_id,
                "push_id": push_id,
                "action": action,
                "timestamp": timestamp,
            }
        )

    monkeypatch.setattr(
        "app.services.push_feedback_service.PushFeedbackService.process_interaction",
        _fake_process_interaction,
    )

    return TestClient(app), user


def test_push_interaction_route_shape_matches_mobile_contract():
    """路径必须恰为 /push/interaction——mobile api_endpoints.dart:591 的值。"""
    paths = {
        tuple(sorted(route.methods)) + (route.path,)
        for route in push_interaction_router.routes
        if getattr(route, "path", None) == "/push/interaction"
    }
    assert paths == {("POST", "/push/interaction")}, (
        "engine route shape drifted; gateway proxy group and mobile "
        "ApiEndpoints.pushInteraction both pin /push/interaction"
    )


def test_push_interaction_valid_action_delegates_to_service(monkeypatch):
    captured: list[dict] = []
    client, user = _build_client(monkeypatch, captured)
    push_id = uuid4()

    resp = client.post(
        "/push/interaction",
        json={"push_id": str(push_id), "action": "Opened"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert len(captured) == 1
    call = captured[0]
    assert call["user_id"] == user.id
    assert call["push_id"] == push_id
    assert call["action"] == "opened"  # 端点侧归一化小写
    assert isinstance(call["timestamp"], datetime)


def test_push_interaction_invalid_action_returns_400(monkeypatch):
    captured: list[dict] = []
    client, _ = _build_client(monkeypatch, captured)

    resp = client.post(
        "/push/interaction",
        json={"push_id": str(uuid4()), "action": "not-a-real-action"},
    )

    assert resp.status_code == 400
    assert captured == []  # 非法 action 不得触达 service
