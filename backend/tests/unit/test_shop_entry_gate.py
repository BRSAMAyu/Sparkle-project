"""V3-FIX-05：shop 空目录/入口暴露收口两态回归（wt483 PLAN §2.2，卡 C shop 提前量）。

背景：shop_items/shop_purchases 目录 0 行（B-01 HIDDEN 判定 + Reviewer 确认），
后端 /shop + /inventory 组注册无任何发布闸——证伪实录（修前 96f02a2b）：
RELEASE_ENABLE_SHOP 默认 False 下带鉴权深链 GET /shop/items、/shop/purchases、
/inventory 全部 200（诚实空列表但面在场），无鉴权深链 401 而非 403（闸缺席，
先撞鉴权）；移动端 streak_details_screen.dart:427 context.push('/shop') 是唯一
应用内入口。本卡 = 入口移除（移动端，另 commit）+ 旗兜底深链（后端本文件钉）。

形制参照 test_visual_elements_gate.py（V3-FIX-182 先例）：
- 关（默认）：shop/inventory 两组全部路由 403 FEATURE_DISABLED，且先于端点
  鉴权依赖生效；
- 开：深链可达 200；
- 闸只作用于 shop/inventory 两组（T36 教训：前缀级旗子会误杀同 router 合法
  子面，如 leaderboards/self-anchor）——关闭态下其他组不受影响。

未来 D-MONETIZE §3-4 重启商城：翻 RELEASE_ENABLE_SHOP=True 即恢复（旗的
「降级/重启」开关语义，PLAN §2.2 裁决）。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.router import api_router
from app.config import settings
from app.db.session import get_db
from app.models.user import User

DISABLED_PATHS = (
    "/api/v1/shop/items",
    "/api/v1/shop/purchases",
    "/api/v1/inventory",
    "/api/v1/inventory/owned",
)


@pytest.fixture
def gate_app(db_session: AsyncSession) -> FastAPI:
    """真实 api_router 全量挂载（等价 main.py 的 /api/v1 形态）+ db 覆盖。"""

    async def _override_get_db():
        yield db_session

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.mark.asyncio
async def test_gate_off_returns_403_feature_disabled_before_auth(gate_app, monkeypatch):
    """关（默认 RELEASE_ENABLE_SHOP=False）：深链 403 FEATURE_DISABLED，先于鉴权。

    不覆盖 get_current_user：若闸缺失，请求会先撞鉴权得 401 而非 403
    （修前实录即 401——本用例是闸在场的判别器）。
    """
    monkeypatch.setattr(settings, "RELEASE_ENABLE_SHOP", False)
    with TestClient(gate_app, raise_server_exceptions=False) as client:
        for path in DISABLED_PATHS:
            response = client.get(path)
            assert response.status_code == 403, f"{path} -> {response.status_code}"
            assert response.json()["detail"] == "FEATURE_DISABLED"
        # 写面同样被组闸拦截（purchase/equip 为 POST 端点）
        purchase = client.post("/api/v1/shop/purchase", json={})
        assert purchase.status_code == 403
        assert purchase.json()["detail"] == "FEATURE_DISABLED"
        equip = client.post("/api/v1/inventory/equip", json={})
        assert equip.status_code == 403
        assert equip.json()["detail"] == "FEATURE_DISABLED"


@pytest.mark.asyncio
async def test_gate_off_rejects_even_with_valid_auth(gate_app, db_session, monkeypatch):
    """关 + 带鉴权：仍 403（修前实录此面 200 空列表——本卡收口的暴露本体）。"""
    monkeypatch.setattr(settings, "RELEASE_ENABLE_SHOP", False)
    user = User(username="wt489_gate_off_auth", email="wt489_gate_off_auth@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    async def _override_get_current_user():
        return user

    gate_app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(gate_app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/shop/items")
        assert response.status_code == 403, f"shop items -> {response.status_code}: {response.text}"
        assert response.json()["detail"] == "FEATURE_DISABLED"
        inventory = client.get("/api/v1/inventory")
        assert inventory.status_code == 403, f"inventory -> {inventory.status_code}"
        assert inventory.json()["detail"] == "FEATURE_DISABLED"


@pytest.mark.asyncio
async def test_gate_on_deep_link_reachable(gate_app, db_session, monkeypatch):
    """开（D-MONETIZE 重启语义）：深链可达 200（组闸放行后走端点自身鉴权/业务）。"""
    monkeypatch.setattr(settings, "RELEASE_ENABLE_SHOP", True)
    user = User(username="wt489_gate_on", email="wt489_gate_on@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    async def _override_get_current_user():
        return user

    gate_app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(gate_app) as client:
        response = client.get("/api/v1/shop/items")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["success"] is True
        assert body["data"] == []


@pytest.mark.asyncio
async def test_gate_scoped_to_shop_inventory_groups_only(gate_app, db_session, monkeypatch):
    """T36 教训守卫：关闭态不得波及同 api_router 的其他组。

    leaderboards/self-anchor 是 D-COMM-1 唯一在册产品面；/release-flags 是
    契约读面。若此闸被误做成 router 级/前缀级一刀切，此用例即红。
    """
    monkeypatch.setattr(settings, "RELEASE_ENABLE_SHOP", False)
    user = User(username="wt489_gate_scope", email="wt489_gate_scope@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    async def _override_get_current_user():
        return user

    gate_app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(gate_app, raise_server_exceptions=False) as client:
        # 本组：仍然拒绝
        shop = client.get("/api/v1/shop/items")
        assert shop.status_code == 403, shop.text
        assert shop.json()["detail"] == "FEATURE_DISABLED"
        # 邻组：leaderboards/self-anchor 正常可达（诚实空态 200），非 403
        self_anchor = client.get("/api/v1/leaderboards/self-anchor")
        assert self_anchor.status_code != 403, self_anchor.text
        assert self_anchor.status_code == 200
        assert self_anchor.json()["success"] is True
        # 契约读面：不受本闸影响且如实上报 shop=False
        flags = client.get("/api/v1/release-flags")
        assert flags.status_code == 200
        assert flags.json()["shop"] is False
