"""SECTOR-BACKFILL-Dedup · 星域回填去重与降级回归（COLDSTART 双可靠性项之一）.

活栈根因（2026-09 实证：glm_batch 恒满 200/200、VOID 29/129）：
- ``get_galaxy_graph`` 每次取图调 ``ensure_backfill_for_user``，无在途去重时
  同一批 pending/VOID 节点被反复 enqueue（同一用户 0.7s 两次 node_count=24）；
- completed-VOID 节点（演示库 27 个）被 ``dominant_sector_code == VOID`` 无
  status 门槛地永久重选 → 重复任务灌满队列 → 背压丢新节点回填。

本文件双向钉死：
- 选择面：completed（含 completed-VOID）不再被 ``find_nodes_needing_backfill``
  与 ``ensure_backfill_for_user`` 选中；pending/failed/未分类仍被选中；
- 入队面：在途去重命中 → 不重复入队；投递成功 → 写在途标记；
  背压丢弃/投递失败 → 显式 WARNING 留痕（不静默）、不写标记（下轮自然重试）、
  节点保持 pending；
- 有界降级：Redis 去重探测自身故障 → 放行入队（背压硬顶仍在）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.galaxy import KnowledgeNode
from app.services.node_sector_service import NodeSectorService


@pytest_asyncio.fixture
async def sector_env(tmp_path):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(
        f"sqlite+aiosqlite:////{tmp_path / 'sector_dedup.db'}",
        connect_args={"timeout": 15.0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        nodes = {
            "unclassified": KnowledgeNode(name="Unclassified", description="d"),
            "pending": KnowledgeNode(name="Pending", description="d"),
            "failed": KnowledgeNode(name="Failed", description="d"),
            "completed_void": KnowledgeNode(name="CompletedVoid", description="d"),
            "completed_tech": KnowledgeNode(name="CompletedTech", description="d"),
        }
        for node in nodes.values():
            session.add(node)
        await session.flush()

        nodes["pending"].sector_classification_status = "pending"
        nodes["failed"].sector_classification_status = "failed"
        nodes["completed_void"].sector_classification_status = "completed"
        nodes["completed_void"].dominant_sector_code = "VOID"
        nodes["completed_void"].sector_weights = {"VOID": 100}
        nodes["completed_tech"].sector_classification_status = "completed"
        nodes["completed_tech"].dominant_sector_code = "TECH"
        nodes["completed_tech"].sector_weights = {"TECH": 100}
        await session.commit()

        yield session, nodes

    await engine.dispose()


@pytest.mark.asyncio
async def test_find_nodes_excludes_completed_void(sector_env):
    """completed-VOID / completed 非_VOID 不再被重选（重复入队根因钉死）。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    found = await service.find_nodes_needing_backfill(user_id=uuid4())
    found_set = set(found)
    assert nodes["unclassified"].id in found_set
    assert nodes["pending"].id in found_set
    assert nodes["failed"].id in found_set
    # 修复核心：completed 节点（无论是否 VOID）不进热路径
    assert nodes["completed_void"].id not in found_set
    assert nodes["completed_tech"].id not in found_set


@pytest.mark.asyncio
async def test_candidate_filter_excludes_completed(sector_env):
    """candidate_nodes 路径与 DB 查询路径同语义：completed 被过滤。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    with patch(
        "app.services.node_sector_service.NodeSectorService.enqueue_backfill_for_nodes",
        new=AsyncMock(return_value=True),
    ) as enqueue:
        await service.ensure_backfill_for_user(
            user_id=uuid4(),
            candidate_nodes=list(nodes.values()),
        )
    selected = enqueue.call_args.kwargs["node_ids"]
    selected_set = set(selected)
    assert nodes["completed_void"].id not in selected_set
    assert nodes["completed_tech"].id not in selected_set
    assert nodes["unclassified"].id in selected_set
    assert nodes["pending"].id in selected_set
    assert nodes["failed"].id in selected_set


def _patch_cache(get_return=None, get_exc=None):
    cache_mock = type("CacheMock", (), {})()
    if get_exc is not None:
        cache_mock.get = AsyncMock(side_effect=get_exc)
    else:
        cache_mock.get = AsyncMock(return_value=get_return)
    cache_mock.set = AsyncMock(return_value=True)
    return cache_mock


@pytest.mark.asyncio
async def test_enqueue_skipped_when_batch_inflight(sector_env):
    """在途去重命中：不重复入队（同一批节点不被反复灌进 glm_batch）。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    cache = _patch_cache(get_return="1")
    with (
        patch("app.services.node_sector_service.cache_service", cache),
        patch(
            "app.services.glm_batch_service.glm_batch_service.enqueue_node_sector_backfill",
            new=AsyncMock(return_value=True),
        ) as enqueue,
    ):
        dispatched = await service.enqueue_backfill_for_nodes(
            user_id=uuid4(),
            node_ids=[nodes["pending"].id],
        )
    assert dispatched is False
    enqueue.assert_not_awaited()
    cache.set.assert_not_awaited()
    # 未进入 mark_nodes_pending：pending 状态不被无谓改写
    await session.refresh(nodes["pending"])
    assert nodes["pending"].sector_classification_status == "pending"


@pytest.mark.asyncio
async def test_enqueue_success_sets_inflight_marker(sector_env):
    """投递成功 → 写在途标记 + 节点标记 pending。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    cache = _patch_cache(get_return=None)
    with (
        patch("app.services.node_sector_service.cache_service", cache),
        patch(
            "app.services.glm_batch_service.glm_batch_service.enqueue_node_sector_backfill",
            new=AsyncMock(return_value=True),
        ) as enqueue,
    ):
        dispatched = await service.enqueue_backfill_for_nodes(
            user_id=uuid4(),
            node_ids=[nodes["unclassified"].id],
        )
    assert dispatched is True
    enqueue.assert_awaited_once()
    cache.set.assert_awaited_once()
    await session.refresh(nodes["unclassified"])
    assert nodes["unclassified"].sector_classification_status == "pending"


@pytest.mark.asyncio
async def test_enqueue_drop_degrades_loudly_not_silently(sector_env, tmp_path):
    """背压丢弃（dispatch 返回 False）：显式 WARNING 留痕、不写标记、节点保持
    pending 供下轮重试——丢弃不再无声。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    cache = _patch_cache(get_return=None)

    logs: list[str] = []
    sink_id = None
    from loguru import logger

    try:
        sink_id = logger.add(lambda message: logs.append(str(message)), level="WARNING")
        with (
            patch("app.services.node_sector_service.cache_service", cache),
            patch(
                "app.services.glm_batch_service.glm_batch_service.enqueue_node_sector_backfill",
                new=AsyncMock(return_value=False),
            ),
        ):
            dispatched = await service.enqueue_backfill_for_nodes(
                user_id=uuid4(),
                node_ids=[nodes["unclassified"].id],
            )
    finally:
        if sink_id is not None:
            logger.remove(sink_id)

    assert dispatched is False
    cache.set.assert_not_awaited()  # 丢弃不写在途标记 → 下轮取图自然重试
    await session.refresh(nodes["unclassified"])
    assert nodes["unclassified"].sector_classification_status == "pending"
    assert any("dispatch dropped or failed" in line for line in logs), logs


@pytest.mark.asyncio
async def test_enqueue_probe_failure_degrades_bounded(sector_env):
    """Redis 去重面自身故障 → 放行入队（有界降级；背压硬顶仍在）。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    cache = _patch_cache(get_exc=ConnectionError("redis down"))
    with (
        patch("app.services.node_sector_service.cache_service", cache),
        patch(
            "app.services.glm_batch_service.glm_batch_service.enqueue_node_sector_backfill",
            new=AsyncMock(return_value=True),
        ) as enqueue,
    ):
        dispatched = await service.enqueue_backfill_for_nodes(
            user_id=uuid4(),
            node_ids=[nodes["pending"].id],
        )
    assert dispatched is True
    enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_updates_node_and_leaves_pool(sector_env):
    """端到端语义：分类成功后节点离开回填池（不再被重选）。"""
    session, nodes = sector_env
    service = NodeSectorService(session)
    node = nodes["unclassified"]
    node.sector_weights = {"TECH": 100}
    node.dominant_sector_code = "TECH"
    node.sector_classification_status = "completed"
    await session.commit()

    found = await service.find_nodes_needing_backfill(user_id=uuid4())
    assert node.id not in set(found)
    rows = (await session.execute(select(KnowledgeNode.id))).all()
    assert len(rows) == 5
