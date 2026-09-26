"""V3-FIX-182：visual-elements LABS 孤儿链发布闸两态回归。

背景：U-07 摘除「我的」页入口后 /visual-elements 全组（8 条路由）0 应用内
入边、可深链直达且后端无闸（证伪实录：带鉴权深链 4 路 200）。

本闸挂在 api/v1/router.py 的 visual-elements 组注册级依赖上，唯一权威=
``settings.RELEASE_ENABLE_VISUAL_ELEMENTS``（wt483 卡 A 五旗权威，
V3-FIX-231 起与 /release-flags 契约同源，原独立开关 ENABLE_VISUAL_ELEMENTS
已删——双权威脑裂禁绝）：
- 关（默认）：组内全部路由 403 FEATURE_DISABLED，且先于端点鉴权依赖生效；
- 开：深链可达 200；
- 闸只作用于本组（T36 教训：router 前缀级旗子会误杀同 router 合法子面，
  如 leaderboards/self-anchor）——关闭态下其他组不受影响。
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
    "/api/v1/visual-elements",
    "/api/v1/visual-elements/config",
    "/api/v1/visual-elements/defaults",
    "/api/v1/visual-elements/unlocked",
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
    """关（默认）：深链 403 FEATURE_DISABLED，且先于鉴权依赖生效。

    不覆盖 get_current_user：若闸缺失，请求会先撞鉴权得 401 而非 403。
    """
    monkeypatch.setattr(settings, "RELEASE_ENABLE_VISUAL_ELEMENTS", False)
    with TestClient(gate_app, raise_server_exceptions=False) as client:
        for path in DISABLED_PATHS:
            response = client.get(path)
            assert response.status_code == 403, f"{path} -> {response.status_code}"
            assert response.json()["detail"] == "FEATURE_DISABLED"
        # POST 面同样被组闸拦截（unlock 为 POST 端点）
        unlock = client.post("/api/v1/visual-elements/unlock")
        assert unlock.status_code == 403
        assert unlock.json()["detail"] == "FEATURE_DISABLED"


@pytest.mark.asyncio
async def test_gate_on_deep_link_reachable(gate_app, db_session, monkeypatch):
    """开：深链可达 200（组闸放行后走端点自身鉴权/业务逻辑）。"""
    monkeypatch.setattr(settings, "RELEASE_ENABLE_VISUAL_ELEMENTS", True)
    user = User(username="wt482_gate_on", email="wt482_gate_on@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    async def _override_get_current_user():
        return user

    gate_app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(gate_app) as client:
        response = client.get("/api/v1/visual-elements")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["items"] == []


@pytest.mark.asyncio
async def test_gate_scoped_to_visual_elements_group_only(gate_app, db_session, monkeypatch):
    """T36 教训守卫：关闭态不得波及同 api_router 的其他组。

    leaderboards/self-anchor 是 D-COMM-1 唯一在册产品面；若此闸被误做成
    router 级/前缀级一刀切，此用例即红。
    """
    monkeypatch.setattr(settings, "RELEASE_ENABLE_VISUAL_ELEMENTS", False)
    user = User(username="wt482_gate_scope", email="wt482_gate_scope@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.commit()

    async def _override_get_current_user():
        return user

    gate_app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(gate_app, raise_server_exceptions=False) as client:
        # 本组：仍然拒绝
        visual = client.get("/api/v1/visual-elements")
        assert visual.status_code == 403
        assert visual.json()["detail"] == "FEATURE_DISABLED"
        # 邻组：leaderboards/self-anchor 正常可达（诚实空态 200），非 403
        self_anchor = client.get("/api/v1/leaderboards/self-anchor")
        assert self_anchor.status_code != 403, self_anchor.text
        assert self_anchor.status_code == 200
        assert self_anchor.json()["success"] is True
