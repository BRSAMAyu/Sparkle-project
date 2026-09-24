"""
Test Galaxy Service concurrent mastery update (C1 fix verification)
Tests atomic UPDATE with optimistic locking prevents race conditions

测试卫生（批1-A · TRIAGE §2 表5）：本文件历史上直接写业务库且无任何
cleanup——「并发测试节点-5c2d9cff」等测试节点永久留存并被真实星图查询命中
（数据自相矛盾的污染源之一）。现改为：
- 独立前缀：用户名/邮箱/节点名一律带 ``galaxy_concurrency_test`` 前缀，
  任何未来泄漏都可被唯一识别；
- teardown 清理：fixture 收尾按精确 ID 逆序删除 user_node_status /
  knowledge_node / user，以及 mastery outbox 事件（event_outbox +
  event_sequence_counters，aggregate_type='galaxy_node_mastery'）。
  不触碰任何既有数据。
本测试必须连 PostgreSQL（C1 原子 UPDATE 依赖 FOR UPDATE/RETURNING 的
行锁语义，SQLite 无此保证）。

环境定界（wt342 · 2026-09-25，CI 日志 + 本地独立库实证）：本文件直连应用侧
``AsyncSessionLocal/engine``（不经过 conftest 的 sqlite ``db_session`` fixture），
历史上在 worktree/sqlite 环境呈 3F+3E 硬失败假信号（各卡报告归因不一：
``no such table`` / asyncpg 认证失败 / sqlite 方言）。CI 实况：Backend Tests 的
DATABASE_URL 指向 live PG（sparkle_test），同会话收集序更早的
``tests/test_migrations.py`` 先行 ``alembic upgrade head`` 建全 schema
（run 36015155771 日志 25% 处 test_migrations 全 PASSED 为证），本文件真跑且
3/3 passed（本地同构独立测试库复现一致）——CI 不会红。现按
test_db_partitioning / test_document_retrieval_isolation 先例加整模块 skip 门：
演示库形状 → TEST-DBGUARD 跳过；非 PostgreSQL 方言 → 跳过；PG 探活失败 →
跳过。CI 路径（postgres 方言 + 可达 + 非演示库名）不受影响。
"""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.user import User
from app.services.galaxy_service import GalaxyService
from tests import _dbguard

pytestmark = [pytest.mark.asyncio, pytest.mark.postgres]

TEST_MARKER = "galaxy_concurrency_test"

# === 环境定界门（整模块 skip，先于任何业务建连；判据顺序与 tests/_dbguard.py
# === 同纪律：演示库 > 方言 > 探活）。任一不满足即跳过，绝不静默硬失败。 ===
_DATABASE_URL = settings.DATABASE_URL or ""
if _dbguard.is_demo_db_url(_DATABASE_URL):
    pytest.skip(
        "TEST-DBGUARD: 演示库隔离 " + _dbguard.demo_guard_message(_DATABASE_URL, "test_galaxy_concurrency (module)"),
        allow_module_level=True,
    )
try:
    _backend = make_url(_DATABASE_URL).get_backend_name() if _DATABASE_URL else ""
except Exception:
    _backend = ""
if _backend != "postgresql":
    pytest.skip(
        "test_galaxy_concurrency 需要 live PostgreSQL：C1 原子 UPDATE 依赖 "
        f"FOR UPDATE/RETURNING 行锁语义，SQLite 无此保证（当前 DATABASE_URL "
        f"后端={_backend or '未配置/不可解析'}）。CI（Backend Tests）的 DATABASE_URL "
        "指向 sparkle_test 且 test_migrations 先行建表，不受本门影响。",
        allow_module_level=True,
    )


async def _probe_live_pg() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))


try:
    asyncio.run(_probe_live_pg())
except Exception as exc:
    pytest.skip(
        "test_galaxy_concurrency 需要 live PostgreSQL 但连接失败："
        f"{type(exc).__name__}: {exc}。指路：DATABASE_URL 指向约定命名的 "
        "*_test 库并先行建 schema（CI 内由 tests/test_migrations.py 负责）。",
        allow_module_level=True,
    )


async def _cleanup(db, *, user_id: UUID, node_id: UUID) -> None:
    """按精确 ID 清除本测试产生的全部行（逆 FK 顺序，不触碰既有数据）。"""
    for stmt, params in (
        (
            "DELETE FROM user_node_status WHERE user_id = :user_id AND node_id = :node_id",
            {"user_id": user_id, "node_id": node_id},
        ),
        ("DELETE FROM knowledge_nodes WHERE id = :node_id", {"node_id": node_id}),
        (
            "DELETE FROM event_outbox WHERE aggregate_type = 'galaxy_node_mastery' AND aggregate_id = :user_id",
            {"user_id": user_id},
        ),
        (
            "DELETE FROM event_sequence_counters WHERE aggregate_type = 'galaxy_node_mastery' AND aggregate_id = :user_id",
            {"user_id": user_id},
        ),
        ("DELETE FROM users WHERE id = :user_id", {"user_id": user_id}),
    ):
        await db.execute(text(stmt), params)
    await db.commit()


@pytest.fixture()
async def seeded_ids():
    """生成唯一的测试实体 ID；测试结束后精确清除本测试写入的所有行。"""
    user_id = uuid4()
    node_id = uuid4()
    yield {"user_id": user_id, "node_id": node_id}

    async with AsyncSessionLocal() as db:
        await _cleanup(db, user_id=user_id, node_id=node_id)


async def _seed_user_node_status(db, *, user_id: UUID, node_id: UUID, mastery_score: float, revision: int) -> None:
    """种子数据全部带 TEST_MARKER 前缀，泄漏可识别、teardown 可精确删除。"""
    user = User(
        id=user_id,
        username=f"{TEST_MARKER}_{user_id.hex[:12]}",
        email=f"{TEST_MARKER}.{user_id.hex[:12]}@example.invalid",
        hashed_password="hashed",
    )
    node = KnowledgeNode(
        id=node_id,
        name=f"{TEST_MARKER}-{node_id.hex[:8]}",
        description="用于验证知识星图掌握度并发更新（测试自清理）。",
        importance_level=1,
        source_type="user_created",
        dominant_sector_code="VOID",
        sector_classification_status="pending",
    )
    status = UserNodeStatus(
        user_id=user_id,
        node_id=node_id,
        mastery_score=mastery_score,
        bkt_mastery_prob=max(0.0, min(float(mastery_score) / 100.0, 1.0)),
        revision=revision,
        is_unlocked=True,
    )
    db.add_all([user, node, status])
    await db.commit()


@pytest.mark.asyncio
async def test_concurrent_mastery_update_with_revision(seeded_ids):
    """
    C1 Fix Verification: Concurrent updates with same revision should result in only one success.
    This tests the atomic UPDATE with WHERE revision = expected_revision.
    """
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    # Create initial node status
    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=50, revision=1)

    # Simulate two concurrent updates with the same expected revision (1)
    async def update_mastery(new_score: int):
        async with AsyncSessionLocal() as db:
            service = GalaxyService(db)
            return await service.update_node_mastery(
                user_id=user_id,
                node_id=node_id,
                new_mastery=new_score,
                reason="test",
                revision=1,  # Both expect revision=1
            )

    # Run both updates concurrently
    results = await asyncio.gather(update_mastery(60), update_mastery(70), return_exceptions=True)

    # Analyze results
    success_count = 0
    conflict_count = 0
    for r in results:
        if isinstance(r, dict):
            if r.get("success"):
                success_count += 1
            elif r.get("reason") == "conflict":
                conflict_count += 1

    # Assertions
    assert success_count == 1, f"Expected exactly 1 success, got {success_count}"
    assert conflict_count == 1, f"Expected exactly 1 conflict, got {conflict_count}"

    # Verify final state in database
    async with AsyncSessionLocal() as db:
        verify_query = text("""
            SELECT mastery_score, revision FROM user_node_status
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await db.execute(verify_query, {"user_id": user_id, "node_id": node_id})
        row = result.fetchone()

        assert row is not None, "Record should exist"
        mastery, revision = row
        # One of the two values (60 or 70) should have won
        assert mastery in (60, 70), f"Expected mastery to be 60 or 70, got {mastery}"
        # Revision should have incremented once
        assert revision == 2, f"Expected revision to be 2, got {revision}"


@pytest.mark.asyncio
async def test_sequential_mastery_update_with_revision(seeded_ids):
    """
    C1 Fix Verification: Sequential updates with incrementing revisions should all succeed.
    """
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=40, revision=1)

    # Sequential updates with correct revision numbers
    for expected_rev, new_score in [(1, 50), (2, 60), (3, 70)]:
        async with AsyncSessionLocal() as db:
            service = GalaxyService(db)
            result = await service.update_node_mastery(
                user_id=user_id, node_id=node_id, new_mastery=new_score, reason="test", revision=expected_rev
            )
            assert result.get("success"), f"Update with revision {expected_rev} should succeed"

    # Verify final state
    async with AsyncSessionLocal() as db:
        verify_query = text("""
            SELECT mastery_score, revision FROM user_node_status
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await db.execute(verify_query, {"user_id": user_id, "node_id": node_id})
        row = result.fetchone()

        assert row is not None, "Record should exist"
        mastery, revision = row
        assert mastery == 70, f"Expected mastery to be 70, got {mastery}"
        assert revision == 4, f"Expected revision to be 4, got {revision}"


@pytest.mark.asyncio
async def test_stale_revision_rejected(seeded_ids):
    """
    C1 Fix Verification: Update with stale revision should be rejected.
    """
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=80, revision=5)

    # Try to update with stale revision=3
    async with AsyncSessionLocal() as db:
        service = GalaxyService(db)
        result = await service.update_node_mastery(
            user_id=user_id, node_id=node_id, new_mastery=90, reason="test", revision=3  # Stale revision
        )

    assert result.get("success") is False, "Stale update should fail"
    assert result.get("reason") == "conflict", "Should return conflict reason"
    assert result.get("current_revision") == 5, "Should return current revision"

    # Verify record was not modified
    async with AsyncSessionLocal() as db:
        verify_query = text("""
            SELECT mastery_score, revision FROM user_node_status
            WHERE user_id = :user_id AND node_id = :node_id
        """)
        result = await db.execute(verify_query, {"user_id": user_id, "node_id": node_id})
        row = result.fetchone()

        assert row is not None
        mastery, revision = row
        assert mastery == 80, "Mastery should not change"
        assert revision == 5, "Revision should not change"
