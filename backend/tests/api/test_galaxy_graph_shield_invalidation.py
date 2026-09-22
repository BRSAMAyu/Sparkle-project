"""SHIELD-INVAL · 星图读面双层缓存失效收口（API 层 shield 失效面）.

背景（LOOP4 CP-00 活栈实证）：``GET /galaxy/graph`` 有两层缓存——

1. 服务层 ``GalaxyService.get_galaxy_graph`` 的 ``@cached(ttl=600)`` 视图，
   NBP-4 已挂失效（``invalidate_galaxy_graph_view_cache`` /
   ``update_node_mastery`` 提交后删 Redis 键）；
2. API 层 ``_galaxy_graph_shield``（single-flight + 10s TTL + 并发钳制），
   修复前**没有任何失效面**：prime → 评分 → 立即取图，Redis 键已删但
   shield 仍回 prime 时的旧快照（mastery 全 null），星图读面最长 10s
   不更新。

本文件在 TestClient 级钉死：**写路径提交后，两层同时失效，API 立即读
不陈旧**。覆盖三条真实写路径——REST mastery 更新、服务层失效 helper
（outcome 吸收面）、诊断评分写（``_write_mastery_value``）。

shield 语义红线：single-flight / 并发钳制行为不因失效面受损（单测见
``tests/core/test_request_coalescing.py``）。
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.api.deps import get_current_user_id, get_db
from app.api.v1 import galaxy as galaxy_api
from app.core.cache import cache_service
from app.core.request_coalescing import EndpointShield
from app.models.galaxy import KnowledgeNode
from app.services.exam_sprint_diagnostic_service import ExamSprintDiagnosticService
from app.services.galaxy.outcome_absorption_service import invalidate_galaxy_graph_view_cache

app = FastAPI()
app.include_router(galaxy_api.router, prefix="/api/v1")


@pytest.fixture
def fresh_shield(monkeypatch):
    """每测替换全新 shield 实例（隔离进程全局缓存 + 事件循环绑定）.

    ``_invalidate_galaxy_graph_shield`` 回调在调用时解析模块全局，因此
    monkeypatch 后服务层失效会精确打在本测的 shield 上。
    """
    shield = EndpointShield(name="galaxy_graph", max_concurrency=8, ttl=10.0, wait_timeout=8.0)
    monkeypatch.setattr(galaxy_api, "_galaxy_graph_shield", shield)
    return shield


async def _make_node(db_session) -> KnowledgeNode:
    node = KnowledgeNode(name=f"SHIELD-INVAL 节点 {uuid4().hex[:8]}", importance_level=3, is_seed=True)
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


def _node_view(graph_json: dict, node_id) -> dict:
    for view in graph_json["nodes"]:
        if view["id"] == str(node_id):
            return view
    raise AssertionError(f"node {node_id} missing from galaxy graph response")


def _service_cache_keys(user_id, prefix: str = "view:get_galaxy_graph") -> list[str]:
    return [k for k in cache_service._local_cache if f":{prefix}:{user_id}:" in k]


async def _prime_both_layers(ac: httpx.AsyncClient, user_id) -> dict:
    """取图一次：API shield 与服务层视图缓存同时建立（两层 prime）。"""
    resp = await ac.get("/api/v1/galaxy/graph")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_mastery_update_visible_on_graph_immediately_despite_shield(
    db_session, test_user, fresh_shield, monkeypatch
):
    """红线复现（修复前红）：prime → REST mastery 更新 → 立即取图必须见新值.

    修复前第二次 GET 命中 shield 的 10s TTL 旧快照，user_status 仍为 null；
    修复后写路径失效两层，读面立即可见。
    """
    node = await _make_node(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            before = await _prime_both_layers(ac, test_user.id)
            assert _node_view(before, node.id)["user_status"] is None, "前置：图上尚无个人状态"
            assert fresh_shield.snapshot()["cache_entries"] == 1, "前置：API shield 层必须已 prime"
            if not cache_service.redis:
                assert _service_cache_keys(test_user.id), "前置：服务层视图缓存必须已 prime"

            mastery_resp = await ac.post(
                f"/api/v1/galaxy/nodes/{node.id}/mastery",
                json={"mastery": 42, "reason": "shield_inval_regression"},
            )
            assert mastery_resp.status_code == 200, mastery_resp.text

            # 立即重读（零 sleep）：不得回 shield 旧快照
            after = await _prime_both_layers(ac, test_user.id)
            view = _node_view(after, node.id)
            assert view["user_status"] is not None, "mastery 更新后图上必须出现个人状态"
            assert view["user_status"]["mastery_score"] == pytest.approx(42.0)
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_service_invalidation_helper_clears_api_shield(db_session, test_user, fresh_shield):
    """服务层失效 helper（outcome 吸收面）必须同时清 API shield 层."""
    node = await _make_node(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            await _prime_both_layers(ac, test_user.id)
            assert fresh_shield.snapshot()["cache_entries"] == 1, "前置：shield 层已 prime"

            deleted = await invalidate_galaxy_graph_view_cache(test_user.id)

            assert fresh_shield.snapshot()["cache_entries"] == 0, "服务层失效必须同步清掉 shield 层"
            if not cache_service.redis:
                assert _service_cache_keys(test_user.id) == [], "服务层 Redis/兜底键必须同时被清"
            # 失效后重算：节点仍在图中（行为面不因失效受损）
            after = await _prime_both_layers(ac, test_user.id)
            assert _node_view(after, node.id)["id"] == str(node.id)
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_diagnostic_mastery_write_visible_immediately(db_session, test_user, fresh_shield):
    """诊断评分路径（``_write_mastery_value``）写后立即取图不陈旧.

    sqlite 方言走直写分支（PG 主路径经 update_node_mastery，同获失效）；
    修复前直写分支零失效，shield 旧快照吞掉评分结果。
    """
    node = await _make_node(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: str(test_user.id)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            before = await _prime_both_layers(ac, test_user.id)
            assert _node_view(before, node.id)["user_status"] is None
            assert fresh_shield.snapshot()["cache_entries"] == 1

            await ExamSprintDiagnosticService(db_session)._write_mastery_value(
                user_id=test_user.id, node_id=node.id, mastery=55.0
            )

            after = await _prime_both_layers(ac, test_user.id)
            view = _node_view(after, node.id)
            assert view["user_status"] is not None, "诊断评分后图上必须出现个人状态"
            assert view["user_status"]["mastery_score"] == pytest.approx(55.0)
    finally:
        app.dependency_overrides = {}
