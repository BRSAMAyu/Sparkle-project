"""SERVICER-BACKFILL (GRAPH-GRPC-SHAPE follow-up): SearchNodes /
GetRecommendedNodes must carry per-node user_status, same contract as
GetUserGalaxy.

背景：wt149 给 GetUserGalaxy 补了 proto GalaxyNodeUserStatus 后，两个同样构造
GalaxyNode 的 servicer 仍在出 null——网关 gRPC-first 分支把 REST 面的
results[].user_status 丢成 null，mobile
(mobile/lib/shared/entities/galaxy_model.dart GalaxySearchResult.fromJson)
把 user_status 展平进节点模型，null 时静默默认 is_unlocked=false + mastery 0。

本文件固化三个契约：
1. SearchNodes：semantic_search 已为每个结果 rehydrate 完整 UserStatusInfo
   （retrieval.get_user_node_status → SearchResultItem.user_status），servicer
   必须整块映射进 proto（mobile 消费的 10 个字段一一对应）；
2. GetRecommendedNodes：predict_next_node 返回 NodeWithStatus，其 user_status
   与 REST 面同源（NodeWithStatus.from_models），同样必须整块映射；
3. null 镜像：无状态节点必须保持 user_status 缺省（proto3 message presence，
   HasField=false），与 REST 的 user_status=null 对齐——绝不能落一个全零块
   （全零块读起来是「未解锁但存在信号」而非「无信号」）。

附带的回归钉（同一行块上的前置缺陷）：semantic_search 产出的 node 是 NodeBase
——没有 source_type / keywords 属性；补填前 servicer 直接访问
``r.node.source_type``，任何非空生产搜索都会 AttributeError → INTERNAL →
网关被迫回落 REST（gRPC 搜索分支从未成功返回过）。修复后按 REST 语义降级
"unknown"，且本文件所有 SearchNodes 用例都走真实 SearchResultItem/NodeBase
生产形状，防止该缺陷以任何形式复发。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from app.gen.galaxy.v1 import galaxy_service_pb2
from app.schemas.galaxy import NodeBase, NodeWithStatus, SearchResultItem
from app.services import galaxy_grpc_service as grpc_module
from tests.unit.test_galaxy_grpc_cached_graph import USER_ID, _FakeContext
from tests.unit.test_galaxy_grpc_user_status import (
    FIRST_UNLOCK_AT,
    MASTERY_LAST_UPDATED_AT,
    _build_user_status,
)


# --- fakes（production shapes only：SearchResultItem.node = NodeBase）--------


def _build_search_result(user_status) -> SearchResultItem:
    node = NodeBase(
        id=uuid4(),
        name="传输层拥塞控制",
        importance_level=4,
        sector_code="TECH",
        is_seed=True,
        tags=["tcp", "congestion_control"],
    )
    return SearchResultItem(node=node, similarity=0.87, user_status=user_status)


def _build_predicted(user_status) -> NodeWithStatus:
    """predict_next_node 的真实返回类型与构造路径（NodeWithStatus.from_models）。"""
    return NodeWithStatus(
        id=uuid4(),
        name="滑动窗口协议",
        importance_level=4,
        sector_code="TECH",
        is_seed=True,
        position_angle=0.0,
        position_radius=0.0,
        position_x=0.0,
        position_y=0.0,
        user_status=user_status,
    )


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DB:
    def __init__(self, rows=()):
        self._rows = rows

    async def execute(self, stmt):
        return _Rows(self._rows)


def _make_servicer(monkeypatch: pytest.MonkeyPatch, *, search_results=None, predicted=None, db_rows=()):
    class _FakeGalaxyService:
        def __init__(self, db):
            self.db = db

        async def semantic_search(self, *, user_id, query, subject_id, limit):
            return search_results

        async def predict_next_node(self, user_id):
            return predicted

    @asynccontextmanager
    async def fake_session_factory():
        yield _DB(db_rows)

    monkeypatch.setattr(grpc_module, "GalaxyService", _FakeGalaxyService)
    return grpc_module.GalaxyGrpcServiceImpl(db_session_factory=fake_session_factory)


# --- SearchNodes -------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_nodes_carries_user_status_on_grpc_nodes(monkeypatch: pytest.MonkeyPatch):
    """每个搜索结果的 user_status 必须整块进 proto；int32 mastery 通道照旧。"""
    result = _build_search_result(_build_user_status())
    servicer = _make_servicer(
        monkeypatch,
        search_results=[result],
        db_rows=[(result.node.id, 88)],  # 批量回查喂 int32 mastery 字段
    )
    context = _FakeContext({"user-id": USER_ID})

    response = await servicer.SearchNodes(
        galaxy_service_pb2.SearchNodesRequest(query="拥塞控制", limit=5), context
    )

    assert context.code is None, f"SearchNodes failed: code={context.code} details={context.details!r}"
    assert response.total_found == 1
    node = response.nodes[0]
    assert node.HasField("user_status"), (
        "gRPC search nodes carry no user_status — gateway gRPC branch serves "
        "null and mobile defaults is_unlocked=false on every search hit"
    )
    us = node.user_status
    # mobile 消费集（GalaxySearchResult.fromJson 展平 → GalaxyNodeModel），逐字段断言
    assert us.mastery_score == 25.5, "mastery_score must survive as double (int32 mastery truncates)"
    assert us.is_unlocked is True
    assert us.study_count == 7
    assert us.recent_error_count == 2
    assert us.review_urgency_score == pytest.approx(0.75)
    assert us.is_review_recommended is True
    assert us.review_urgency_reason == "3 days since last mastery update"
    assert us.days_since_mastery_update == pytest.approx(3.5)
    assert us.mastery_last_updated_at.ToDatetime() == MASTERY_LAST_UPDATED_AT
    assert us.first_unlock_at.ToDatetime() == FIRST_UNLOCK_AT
    # 旧 int32 mastery 通道仍由批量回查填充（既有消费方 back-compat）
    assert node.mastery == 88
    # 生产形状（NodeBase 无 source_type/keywords）按 REST 语义降级，不得抛
    assert node.node_type == "unknown"


@pytest.mark.asyncio
async def test_search_nodes_null_status_stays_absent_not_zero(monkeypatch: pytest.MonkeyPatch):
    """REST 面对无状态节点出 user_status=null；proto 必须镜像为缺省（非全零块）。"""
    servicer = _make_servicer(monkeypatch, search_results=[_build_search_result(None)])
    context = _FakeContext({"user-id": USER_ID})

    response = await servicer.SearchNodes(
        galaxy_service_pb2.SearchNodesRequest(query="拥塞控制", limit=5), context
    )

    assert context.code is None
    node = response.nodes[0]
    assert not node.HasField("user_status")
    assert node.mastery == 0


# --- GetRecommendedNodes -----------------------------------------------------


@pytest.mark.asyncio
async def test_recommended_nodes_carries_user_status_on_grpc_nodes(monkeypatch: pytest.MonkeyPatch):
    """predict_next_node 的 NodeWithStatus.user_status 必须整块进 proto。"""
    servicer = _make_servicer(monkeypatch, predicted=_build_predicted(_build_user_status()))
    context = _FakeContext({"user-id": USER_ID})

    response = await servicer.GetRecommendedNodes(galaxy_service_pb2.GetRecommendedNodesRequest(), context)

    assert context.code is None, f"GetRecommendedNodes failed: code={context.code} details={context.details!r}"
    assert len(response.nodes) == 1
    assert len(response.reasons) == 1
    node = response.nodes[0]
    assert node.HasField("user_status"), (
        "gRPC recommended nodes carry no user_status — same shape loss as the "
        "graph face fixed by GRAPH-GRPC-SHAPE"
    )
    us = node.user_status
    assert us.mastery_score == 25.5
    assert us.is_unlocked is True
    assert us.study_count == 7
    assert us.recent_error_count == 2
    assert us.review_urgency_score == pytest.approx(0.75)
    assert us.is_review_recommended is True
    assert us.mastery_last_updated_at.ToDatetime() == MASTERY_LAST_UPDATED_AT
    assert us.first_unlock_at.ToDatetime() == FIRST_UNLOCK_AT
    # 旧 int32 mastery 字段照旧由同一 user_status 截断填充
    assert node.mastery == 25


@pytest.mark.asyncio
async def test_recommended_nodes_null_status_stays_absent_not_zero(monkeypatch: pytest.MonkeyPatch):
    """无状态推荐节点：user_status 缺省镜像 REST null，int32 mastery 归 0。"""
    servicer = _make_servicer(monkeypatch, predicted=_build_predicted(None))
    context = _FakeContext({"user-id": USER_ID})

    response = await servicer.GetRecommendedNodes(galaxy_service_pb2.GetRecommendedNodesRequest(), context)

    assert context.code is None
    node = response.nodes[0]
    assert not node.HasField("user_status")
    assert node.mastery == 0
