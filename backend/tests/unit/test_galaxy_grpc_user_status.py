"""GRAPH-GRPC-SHAPE: gRPC GetUserGalaxy must carry per-node user_status.

Breakage this pins (2026-09-23 终审实证，同一账号同一时刻）：
- GET :8000/api/v1/galaxy/graph（引擎 REST 直连）→ 节点带 user_status
  （mastery_score=25.0, is_unlocked=True, ...）
- GET :8080/api/v1/galaxy/graph（经网关，gRPC-first）→ 节点 user_status=null

Root cause: proto ``GalaxyNode``（proto/galaxy_service.proto）只有
node_id/label/node_type/mastery(int32)/tags —— per-user 状态结构
（backend/app/schemas/galaxy.py UserStatusInfo）在 proto 上没有承载位，
servicer 无从填充，网关映射出的响应自然丢掉整个 user_status。移动端
（mobile/lib/shared/entities/galaxy_model.dart GalaxyNodeModel.fromJson）
从 user_status 读 10 个字段并静默取默认值——已解锁节点被渲染成锁定、
复习紧迫度信号全部归零。这是星图 mastery/解锁态对真实用户（全部走网关）
可见性的终点断点。

本文件固化 servicer 层契约：GetUserGalaxy 的每个节点必须把
``node.user_status``（缓存命中 rehydrate 出来的 UserStatusInfo）完整映射进
proto ``GalaxyNode.user_status``（GalaxyNodeUserStatus），移动端消费的
10 个字段一一对应；mastery_score 走 double（int32 ``mastery`` 会截断小数）。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.galaxy import (
    GalaxyGraphResponse,
    GalaxyUserStats,
    NodeWithStatus,
    UserStatusInfo,
)
from tests.unit.test_galaxy_grpc_cached_graph import (
    USER_ID,
    _cache_roundtrip,
    _FakeContext,
    _make_servicer_with,
)

MASTERY_LAST_UPDATED_AT = datetime(2026, 9, 19, 12, 30)
FIRST_UNLOCK_AT = datetime(2026, 9, 10, 8, 0)


def _build_user_status(**overrides) -> UserStatusInfo:
    """UserStatusInfo with every mobile-consumed field non-default."""
    payload: dict = {
        # 非整数：int32 mastery 截断为 25，double 必须保住 .5
        "mastery_score": 25.5,
        "total_study_minutes": 42,
        "study_count": 7,
        "is_unlocked": True,
        "is_collapsed": False,
        "is_favorite": False,
        "decay_paused": False,
        "status": "glimmer",
        "brightness": 0.25,
        "recent_error_count": 2,
        "review_urgency_score": 0.75,
        "is_review_recommended": True,
        "review_urgency_reason": "3 days since last mastery update",
        "days_since_mastery_update": 3.5,
        "mastery_last_updated_at": MASTERY_LAST_UPDATED_AT,
        "first_unlock_at": FIRST_UNLOCK_AT,
    }
    payload.update(overrides)
    return UserStatusInfo(**payload)


def _build_graph_response(user_status: UserStatusInfo | None) -> GalaxyGraphResponse:
    node = NodeWithStatus(
        id=uuid4(),
        name="命题逻辑",
        importance_level=3,
        sector_code="TECH",
        is_seed=True,
        keywords=["propositional_logic"],
        position_angle=0.0,
        position_radius=0.0,
        position_x=0.0,
        position_y=0.0,
        user_status=user_status,
    )
    return GalaxyGraphResponse(
        nodes=[node],
        relations=[],
        edges=[],
        user_stats=GalaxyUserStats(total_nodes=1, unlocked_count=1),
        user_flame_intensity=1.0,
    )


async def _get_user_galaxy(monkeypatch: pytest.MonkeyPatch, graph: object):
    """Run the servicer on a cache-round-tripped payload (the production path)."""
    cached_payload = _cache_roundtrip(graph)
    servicer = _make_servicer_with(monkeypatch, cached_payload)
    context = _FakeContext({"user-id": USER_ID})
    response = await servicer.GetUserGalaxy(
        SimpleNamespace(user_id=USER_ID),
        context,
    )
    assert context.code is None, f"GetUserGalaxy failed: code={context.code} details={context.details!r}"
    return response


@pytest.mark.asyncio
async def test_get_user_galaxy_carries_user_status_on_grpc_nodes(monkeypatch: pytest.MonkeyPatch):
    """Servicer contract: node.user_status maps field-for-field into proto."""
    response = await _get_user_galaxy(monkeypatch, _build_graph_response(_build_user_status()))

    assert len(response.nodes) == 1
    node = response.nodes[0]
    # proto3 message presence: the status block must actually be set.
    assert node.HasField("user_status"), (
        "gRPC GalaxyNode carries no user_status — proto shape loses the "
        "REST face's per-node user block (mobile then defaults is_unlocked=false)"
    )
    us = node.user_status
    # Mobile consumption set (mobile/lib/shared/entities/galaxy_model.dart),
    # one assertion per field mobile reads out of user_status.
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
    # legacy int32 mastery still filled (back-compat for existing consumers)
    assert node.mastery == 25


@pytest.mark.asyncio
async def test_get_user_galaxy_null_status_stays_absent_not_zero(monkeypatch: pytest.MonkeyPatch):
    """REST emits user_status=null for status-less nodes; proto must mirror
    with absence (HasField false), never a zeroed status block (a zeroed
    block would read as "unlocked=false but exists" instead of "no signal")."""
    response = await _get_user_galaxy(monkeypatch, _build_graph_response(None))

    node = response.nodes[0]
    assert not node.HasField("user_status")
    assert node.mastery == 0
