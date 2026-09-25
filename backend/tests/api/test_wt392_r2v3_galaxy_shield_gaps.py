"""wt392 · 双轮审查第二轮 · WT391-HUNT-R3 F4 —— galaxy_graph 同族失效缺口.

SHIELD-INVAL 同族扫描结论的修复守卫：``GET /galaxy/graph`` 读面有两层
缓存（服务层 Redis ``@cached`` 视图 + API 层 ``_galaxy_graph_shield``
10s TTL 进程内结果缓存）。outcome 吸收面已双层齐清（
``invalidate_galaxy_graph_view_cache``，既有守卫
``test_galaxy_graph_shield_invalidation.py``），但 J-07 同族扫描发现仍有
写面**只清 Redis 层、不宣告 shield**——读面最长 10s 回写前旧值：

1. ``NodeSectorService.invalidate_user_graph_cache``（单点覆盖 4 个调用面：
   ``galaxy_service``×2、``expansion_service``、sector 回填提交后）；
2. ``GalaxyStatsService.spark_node`` 学习解锁路径（裸 ``delete_pattern``）。

契约：这两条写路径提交后，API shield 进程内缓存必须同步失效
（``notify_read_view_invalidated("galaxy_graph", ...)``），立即重读不陈旧。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.deps import get_current_user_id, get_db
from app.api.v1 import galaxy as galaxy_api
from app.core.request_coalescing import EndpointShield
from app.models.galaxy import KnowledgeNode
from app.services.galaxy.stats_service import GalaxyStatsService
from app.services.node_sector_service import NodeSectorService

app = FastAPI()
app.include_router(galaxy_api.router, prefix="/api/v1")


@pytest.fixture
def fresh_shield(monkeypatch):
    """每测替换全新 shield 实例（SHIELD-INVAL 既有守卫同法）。"""
    shield = EndpointShield(name="galaxy_graph", max_concurrency=8, ttl=10.0, wait_timeout=8.0)
    monkeypatch.setattr(galaxy_api, "_galaxy_graph_shield", shield)
    return shield


async def _make_node(db_session) -> KnowledgeNode:
    node = KnowledgeNode(name=f"wt392 F4 节点 {uuid4().hex[:8]}", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


@pytest.mark.asyncio
async def test_sector_invalidate_user_graph_cache_clears_api_shield(db_session, test_user, fresh_shield):
    """sector 失效单点（galaxy_service/expansion/回填共用）必须双层齐清。"""
    await _make_node(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/galaxy/graph")
            assert resp.status_code == 200
            assert fresh_shield.snapshot()["cache_entries"] == 1, "前置：shield 层已 prime"

            await NodeSectorService(db_session).invalidate_user_graph_cache(test_user.id)

            assert fresh_shield.snapshot()["cache_entries"] == 0, (
                "只清 Redis 不宣告 shield：10s TTL 内读面回写前旧值（wt391 F4）"
            )
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_spark_node_write_clears_api_shield(db_session, test_user, fresh_shield):
    """spark_node 学习解锁写面提交后，shield 层必须同步失效。"""
    node = await _make_node(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/galaxy/graph")
            assert resp.status_code == 200
            assert fresh_shield.snapshot()["cache_entries"] == 1, "前置：shield 层已 prime"

            result = await GalaxyStatsService(db_session).spark_node(
                user_id=test_user.id,
                node_id=node.id,
                study_minutes=10,
                trigger_expansion=False,
            )
            assert result is not None, "前置：spark 写面真实执行"

            assert fresh_shield.snapshot()["cache_entries"] == 0, (
                "spark_node 只清 Redis 不宣告 shield：学习解锁后读面 10s 不更新（wt391 F4）"
            )
    finally:
        app.dependency_overrides = {}
