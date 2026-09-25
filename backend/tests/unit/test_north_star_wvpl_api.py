"""WT352 · G7 WVPL 北极星只读暴露端点 API 测试（愿景差距 G7 验收）。

覆盖三面（卡面验收）：
1. 认证沿同族 admin 端点惯例：非 superuser 被拒（superuser 依赖链生效）；
2. 空/未初始化态诚实返回：空库 → 零计数 + None 比率 + 空 samples，
   schema/caliber 仍为 frozen 值（不造假数据、不编造比率）；
3. happy path：固定 fixture（与 golden 共享单份事实源）下，端点响应与
   ``NorthStarWvplService.build_fact`` 的 frozen 口径逐字段一致（响应形状 =
   frozen schema，handler 零后处理），且 seed/guest cohort 不混入生产数字。
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_active_superuser, get_db
from app.api.v1.north_star_wvpl import router
from app.core.north_star_wvpl import WVPL_CALIBER_VERSION, WVPL_FACT_SCHEMA
from app.models.user import User
from app.services.north_star_wvpl_service import NorthStarWvplService
from tests.golden.north_star_wvpl_fixture import AS_OF, build_standard_fixture

app = FastAPI()
app.include_router(router, prefix="/api/v1")


def _override_db(db_session):
    async def override_get_db():
        yield db_session

    return override_get_db


@pytest.mark.asyncio
async def test_wvpl_fact_requires_superuser(db_session):
    """认证/权限沿同族 admin 端点惯例：superuser 依赖拒绝即 403。"""

    def override_superuser_forbidden():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_active_superuser] = override_superuser_forbidden
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/admin/north-star/wvpl-fact")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_wvpl_fact_empty_db_honest_state(db_session):
    """空库/未初始化态：零计数 + None 比率 + 空 samples，frozen 标识在位（不造假）。"""

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_active_superuser] = lambda: User(
        username="admin", email="admin@example.com", hashed_password="x", is_superuser=True
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/admin/north-star/wvpl-fact")
        assert resp.status_code == 200
        payload = resp.json()

        # frozen schema/caliber 标识（响应形状 = frozen schema）
        assert payload["schema"] == WVPL_FACT_SCHEMA
        assert payload["caliber_version"] == WVPL_CALIBER_VERSION

        # 分母/分子诚实为零，比率 None（分母 0 不伪造比率 = frozen 口径）
        north_star = payload["north_star"]
        assert north_star["active_users"] == 0
        assert north_star["wvpl_users"] == 0
        assert north_star["loops_total"] == 0
        assert north_star["wvpl_ratio"] is None
        assert north_star["loops_per_wvpl_user"] is None

        # 无事件溯源样本、无截断、cohort 排除为零
        assert payload["loops"]["samples"] == []
        assert payload["loops"]["all_time_bounded"]["truncated"] is False
        assert payload["cohort"]["excluded_users"] == 0

        # 可审计三件套随空态同样在位（口径注释 + 源查询登记）
        assert payload["definitions"]["loop"]
        assert payload["provenance"]["source_queries"]
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_wvpl_fact_happy_path_matches_frozen_service(db_session):
    """happy path：端点响应 == frozen 口径服务产出（同 as_of + 同 generated_at 逐字段一致）。"""

    await build_standard_fixture(db_session)

    app.dependency_overrides[get_db] = _override_db(db_session)
    app.dependency_overrides[get_current_active_superuser] = lambda: User(
        username="admin", email="admin@example.com", hashed_password="x", is_superuser=True
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/admin/north-star/wvpl-fact", params={"as_of": AS_OF.isoformat()})
        assert resp.status_code == 200
        payload = resp.json()

        # 权威比对：注入响应自带的 generated_at，服务必须逐字段复现同一事实 JSON
        expected = await NorthStarWvplService(db_session).build_fact(
            as_of=AS_OF, generated_at=AS_OF.fromisoformat(payload["provenance"]["generated_at"])
        )
        assert payload == expected

        # frozen 标识 + 生产数字非平凡 + cohort 分离（seed loop 不进生产数字）
        assert payload["schema"] == WVPL_FACT_SCHEMA
        assert payload["caliber_version"] == WVPL_CALIBER_VERSION
        assert payload["north_star"]["loops_total"] == 2  # alice×2；seed 的 demo loop 被排除
        assert payload["north_star"]["active_users"] >= payload["north_star"]["wvpl_users"] > 0
        assert payload["north_star"]["wvpl_ratio"] is not None
        assert payload["cohort"]["excluded_users"] > 0  # seed/guest 被单列，不混入生产分母
    finally:
        app.dependency_overrides = {}
