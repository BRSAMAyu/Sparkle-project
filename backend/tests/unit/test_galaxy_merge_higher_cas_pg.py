"""V3-FIX-295 收尾（wt589）: ``GalaxyService.update_node_mastery`` 的
``merge_higher=True`` CAS 在**真 PostgreSQL** 上的实证。

wt583（79383e43）实现的 PG 面谓词——
``ON CONFLICT (user_id, node_id) DO UPDATE SET ... WHERE
user_node_status.mastery_score < EXCLUDED.mastery_score``——只被 sqlite 钉
（``tests/unit/test_galaxy_grpc_conflict_merge_cas.py``）覆盖行为等价性；
``EXCLUDED`` 引用是 PG 方言惟一分支，sqlite 测试无法覆盖其真实执行面。
本文件在真 PG 上钉四条契约：

1. stored < incoming：单语句原子写入 + revision 推进（审计/outbox 照常）；
2. stored >= incoming：DO UPDATE 的 WHERE 求值为假 → 零行更新 → 幂等返回
   且**零物理写**（行版本 ``xmin`` 不变、审计/outbox 零行）；
3. 并发窗口（wt583 修前红场景的 PG 版，真连接真提交按序注入）：冲突 →
   窗口内更高值提交 → 合并腿低值 CAS → 高者保留；
4. 两连接真并发竞争同 (user, node)：胜者恒为高 mastery（ON CONFLICT 行锁
   排队 + WHERE 对最新已提交行求值，max-wins 与调度顺序无关）。

环境定界门与 ``test_galaxy_concurrency.py`` 同构（TEST-DBGUARD 演示库 →
方言 → 探活，整模块 skip）；CI（Backend Tests）的 DATABASE_URL 指向 live
PG ``sparkle_test`` 且 ``test_migrations`` 先行建全 schema，本文件真跑。

测试卫生：种子数据一律带 ``galaxy_merge_cas_test`` 前缀；teardown 按精确
ID 逆序清除 user_node_status / knowledge_nodes / mastery_audit_log /
event_outbox / event_sequence_counters / users，不触碰既有数据。
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

TEST_MARKER = "galaxy_merge_cas_test"

# === 环境定界门（整模块 skip，判据顺序与 tests/_dbguard.py 同纪律：
# === 演示库 > 方言 > 探活）。任一不满足即跳过，绝不静默硬失败。 ===
_DATABASE_URL = settings.DATABASE_URL or ""
if _dbguard.is_demo_db_url(_DATABASE_URL):
    pytest.skip(
        "TEST-DBGUARD: 演示库隔离 "
        + _dbguard.demo_guard_message(_DATABASE_URL, "test_galaxy_merge_higher_cas_pg (module)"),
        allow_module_level=True,
    )
try:
    _backend = make_url(_DATABASE_URL).get_backend_name() if _DATABASE_URL else ""
except Exception:
    _backend = ""
if _backend != "postgresql":
    pytest.skip(
        "test_galaxy_merge_higher_cas_pg 需要 live PostgreSQL：merge_higher CAS 的 "
        f"ON CONFLICT ... WHERE mastery_score < EXCLUDED 谓词是 PG 方言惟一分支"
        f"（当前 DATABASE_URL 后端={_backend or '未配置/不可解析'}）。CI（Backend "
        "Tests）的 DATABASE_URL 指向 sparkle_test 且 test_migrations 先行建表，"
        "不受本门影响。",
        allow_module_level=True,
    )


async def _probe_live_pg() -> None:
    # 同会话多 PG 门控模块防串台：import 期探针若复用上一个探针 loop 留在池里
    # 的 asyncpg 连接，会撞 "attached to a different loop"（各模块探针各自
    # asyncio.run，loop 互异）。先弃池再探活，保证探针永远拿本 loop 新连接。
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))


try:
    asyncio.run(_probe_live_pg())
except Exception as exc:
    pytest.skip(
        "test_galaxy_merge_higher_cas_pg 需要 live PostgreSQL 但连接失败："
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
        ("DELETE FROM mastery_audit_log WHERE node_id = :node_id", {"node_id": node_id}),
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
        description="用于验证 merge_higher CAS 掌握度合并（真 PG 实证，测试自清理）。",
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


async def _row_state(user_id: UUID, node_id: UUID) -> tuple[int, float, int, str]:
    """读 (xmin, mastery_score, revision, updated_at::text)——xmin 断言行版本。"""
    query = text("""
        SELECT xmin::text::bigint, mastery_score, revision, updated_at::text
        FROM user_node_status
        WHERE user_id = :user_id AND node_id = :node_id
    """)
    async with AsyncSessionLocal() as db:
        row = (await db.execute(query, {"user_id": user_id, "node_id": node_id})).fetchone()
    assert row is not None, "user_node_status row should exist"
    return int(row[0]), float(row[1]), int(row[2]), str(row[3])


async def _merge_higher(user_id: UUID, node_id: UUID, new_mastery: float) -> dict:
    """独立连接上的 merge_higher CAS 调用（每个调用自持会话，事务独立）。"""
    async with AsyncSessionLocal() as db:
        service = GalaxyService(db)
        return await service.update_node_mastery(
            user_id=user_id,
            node_id=node_id,
            new_mastery=new_mastery,
            reason=f"{TEST_MARKER}",
            merge_higher=True,
        )


@pytest.mark.asyncio
async def test_cas_writes_atomically_when_stored_lower(seeded_ids):
    """契约 1：stored < incoming 时原子写入 + revision 推进（审计/outbox 照常）。"""
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=40, revision=3)

    result = await _merge_higher(user_id, node_id, 75)

    assert result.get("success") is True
    assert result.get("old_mastery") == 40.0
    assert result.get("new_mastery") == 75.0
    assert result.get("current_revision") == 4, "revision 应从 3 推进到 4"

    _, stored_mastery, stored_revision, _ = await _row_state(user_id, node_id)
    assert stored_mastery == 75.0, f"stored 应为 75.0，实际 {stored_mastery}"
    assert stored_revision == 4, f"revision 应为 4，实际 {stored_revision}"

    async with AsyncSessionLocal() as db:
        audit = (
            await db.execute(
                text(
                    "SELECT old_mastery, new_mastery, revision FROM mastery_audit_log "
                    "WHERE user_id = :user_id AND node_id = :node_id"
                ),
                {"user_id": user_id, "node_id": node_id},
            )
        ).fetchone()
        outbox_count = (
            await db.execute(
                text(
                    "SELECT count(*) FROM event_outbox WHERE aggregate_type = 'galaxy_node_mastery' "
                    "AND aggregate_id = :user_id"
                ),
                {"user_id": user_id},
            )
        ).scalar_one()
    assert audit is not None, "写入腿应留审计行"
    assert int(audit[0]) == 40 and int(audit[1]) == 75 and int(audit[2]) == 4
    assert outbox_count >= 1, "写入腿应外发 mastery outbox 事件"


@pytest.mark.asyncio
async def test_cas_idempotent_zero_write_when_stored_higher(seeded_ids):
    """契约 2：stored >= incoming 时零写幂等——xmin/revision/updated_at 全不变。

    PG 的 ``ON CONFLICT DO UPDATE ... WHERE`` 求值为假时该行不产生新行版本
    （``INSERT 0 0``），``xmin`` 不变是零物理写的强断言（比 revision/值相等
    更硬：任何 UPDATE——哪怕写回同值——都会推进 xmin）。
    """
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=80, revision=5)

    xmin_before, mastery_before, revision_before, updated_at_before = await _row_state(user_id, node_id)

    result = await _merge_higher(user_id, node_id, 50)

    assert result.get("success") is True, "stored >= incoming 应幂等成功而非冲突"
    assert result.get("old_mastery") == 80.0
    assert result.get("new_mastery") == 80.0, "new 应回读库内真值（不被低值覆盖）"
    assert result.get("current_revision") == 5, "revision 不应推进"

    xmin_after, mastery_after, revision_after, updated_at_after = await _row_state(user_id, node_id)
    assert xmin_after == xmin_before, f"xmin 不应变化（零物理写）：before={xmin_before} after={xmin_after}"
    assert mastery_after == 80.0, f"mastery 应保持 80.0，实际 {mastery_after}"
    assert revision_after == 5, f"revision 应保持 5，实际 {revision_after}"
    assert updated_at_after == updated_at_before, "updated_at 不应被幂等腿触碰"

    async with AsyncSessionLocal() as db:
        audit_count = (
            await db.execute(
                text("SELECT count(*) FROM mastery_audit_log WHERE node_id = :node_id"),
                {"node_id": node_id},
            )
        ).scalar_one()
        outbox_count = (
            await db.execute(
                text(
                    "SELECT count(*) FROM event_outbox WHERE aggregate_type = 'galaxy_node_mastery' "
                    "AND aggregate_id = :user_id"
                ),
                {"user_id": user_id},
            )
        ).scalar_one()
    assert audit_count == 0, "幂等腿不应写审计"
    assert outbox_count == 0, "幂等腿不应外发事件"


@pytest.mark.asyncio
async def test_cas_window_interleave_merge_leg_never_overwrites_higher(seeded_ids):
    """契约 3：wt583 修前红场景的真 PG 版（真连接真提交按序注入）。

    序列（wt576 复核按序注入， mastery 值平移至 <80 以绕开成就副作用面）：
        seed: mastery=10, revision=5
        step1 A stale write (revision=3, mastery=30) → conflict
        step2 W window write (revision=5, mastery=75) → success   ← 窗口内并发写
        step3 A merge leg (merge_higher=True, mastery=30) → 零写幂等
    修前盲写终值 30 覆盖 75；CAS 契约要求终值恒为 75。
    """
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=10, revision=5)

    # step1: 连接 A 携过期 revision 盲写（独立会话，真实提交）
    async with AsyncSessionLocal() as db_a:
        stale = await GalaxyService(db_a).update_node_mastery(
            user_id=user_id, node_id=node_id, new_mastery=30, reason=f"{TEST_MARKER}.stale", revision=3
        )
    assert stale.get("success") is False and stale.get("reason") == "conflict"
    assert stale.get("current_revision") == 5

    # step2: 连接 W 在窗口内原子提交更高值
    async with AsyncSessionLocal() as db_w:
        window = await GalaxyService(db_w).update_node_mastery(
            user_id=user_id, node_id=node_id, new_mastery=75, reason=f"{TEST_MARKER}.window", revision=5
        )
    assert window.get("success") is True
    assert window.get("new_mastery") == 75.0 and window.get("current_revision") == 6

    # step3: 连接 A 的合并腿带低值走 CAS（merge_higher=True, 无 revision）
    merged = await _merge_higher(user_id, node_id, 30)
    assert merged.get("success") is True, "CAS 幂等腿应成功返回而非冲突"
    assert merged.get("old_mastery") == 75.0
    assert merged.get("new_mastery") == 75.0, "低值合并腿不得覆盖窗口内高值"
    assert merged.get("current_revision") == 6, "幂等腿不推 revision"

    _, stored_mastery, stored_revision, _ = await _row_state(user_id, node_id)
    assert stored_mastery == 75.0, f"终值应为高者 75.0，实际 {stored_mastery}"
    assert stored_revision == 6, f"revision 应保持 6，实际 {stored_revision}"


@pytest.mark.asyncio
async def test_cas_two_connections_race_max_wins(seeded_ids):
    """契约 4：两连接真并发竞争同 (user, node)，胜者恒为高 mastery。

    ON CONFLICT 行锁使后到者等待先到者提交，且 DO UPDATE 的 WHERE 对**最新
    已提交行**求值——两种调度（30 先提交 / 70 先提交）终值都必须是 70，
    与 wt583 修前"读旧值→盲写"的调度依赖行为（30 可覆盖 70）形成对照。
    """
    user_id = seeded_ids["user_id"]
    node_id = seeded_ids["node_id"]
    await engine.dispose()

    async with AsyncSessionLocal() as db:
        await _seed_user_node_status(db, user_id=user_id, node_id=node_id, mastery_score=10, revision=1)

    results = await asyncio.gather(
        _merge_higher(user_id, node_id, 30),
        _merge_higher(user_id, node_id, 70),
        return_exceptions=True,
    )
    for r in results:
        assert not isinstance(r, Exception), f"CAS 调用不应抛错: {r!r}"
        assert r.get("success") is True, "CAS 竞争双方都应 success（CAS 不产生 conflict）"
        assert r.get("new_mastery") in (30.0, 70.0), f"new 应回读库内真值: {r.get('new_mastery')}"
        assert r.get("new_mastery") >= r.get("old_mastery", 0.0), "CAS 任何一腿都不得把库内值写低"
    assert any(r.get("new_mastery") == 70.0 for r in results), "高值腿必须至少在返回值中体现 70"

    _, stored_mastery, stored_revision, _ = await _row_state(user_id, node_id)
    assert stored_mastery == 70.0, f"无论调度顺序，终值都应为高者 70.0，实际 {stored_mastery}"
    assert stored_revision in (2, 3), f"revision 应为 2（仅 70 写入）或 3（30 先写、70 再写），实际 {stored_revision}"
