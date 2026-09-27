"""V3-FIX-467/479 · guest 种子路径 UserStreakStats 首建并发收敛 + 覆盖写语义。

467：guest_seed_service._ensure_user_streak_stats 修前对 UserStreakStats 无锁
SELECT+absent 行裸 INSERT（id=BaseModel 随机 uuid4 缺省）——同用户并发到达双
事务同见 None 各自 INSERT，PK=(user_id,id) 复合主键随机 id 互不冲突双落重复行
→scalar_one_or_none 读面恒 MultipleResultsFound 持久损坏（451/457 同机制同表
第三入口；真 PG 16.15 复现件 v3-output/WT766-SEED/）。
479：触发面收敛修正——操作对象是跨所有访客共享的演示 friend 行，每次访客登
录都重播种子，跨访客并发即竞态，无需同用户双端重放。

修法（451/457 三件套同构）：确定性 uuid5 同源 id（与 achievement_engine/
inventory_service 同一字符串，复合主键成为每用户去重键+跨路径仲裁面）+方言化
ON CONFLICT DO NOTHING+FOR UPDATE 收敛读；覆盖写语义保留（升级重放=同种子集
收敛，last-write-wins 在行锁下安全）。

sqlite 无行锁语义且写锁天然串行——并发窗无法在 sqlite 构造，并发收敛测试以
「服务级并发形态」断言（两会话同时 _ensure 单行收敛），竞态机制本体由真 PG
复现件钉死；with_for_update 在 sqlite 方言下为 no-op，不影响本文件断言面。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.achievement import UserStreakStats
from app.services.guest_seed_service import _ensure_user_streak_stats


def _seed_kwargs(user_id, streak: int = 15):
    """调用点 guest_seed_service:2641 friend 行种子的同型参数面。"""
    return {
        "user_id": user_id,
        "current_streak": streak,
        "max_streak": streak,
        "total_checkin_days": 40,
        "last_activity_date": datetime(2026, 9, 27, 8, 0, 0),
        "longest_streak_start": datetime(2026, 9, 8, 8, 0, 0),
        "longest_streak_end": datetime(2026, 9, 23, 8, 0, 0),
        "freeze_charges": 1,
        "max_freeze_charges": 3,
    }


@pytest.mark.asyncio
async def test_seed_firstbuild_id_deterministic_shared_with_engine(db_session, test_user):
    """首建 id=uuid5 确定性派生（与 achievement_engine 451/inventory 457 同一
    字符串），engine 交叉读命中同一行不另建——跨路径仲裁面单行收敛。"""
    from app.services.achievement_engine import AchievementEngine

    stats = await _ensure_user_streak_stats(db_session, **_seed_kwargs(test_user.id))
    expected_id = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{str(test_user.id)}")
    assert stats.id == expected_id

    engine = AchievementEngine(db_session)
    cross = await engine._get_or_create_streak_stats(str(test_user.id))
    assert cross.id == expected_id

    rows = (
        (await db_session.execute(select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1, f"engine 交叉读后行数 {len(rows)} != 1"


@pytest.mark.asyncio
async def test_seed_replay_overwrites_converging_values(db_session, test_user):
    """覆盖写语义保留：重播（下次登录 reseeded 路径）以种子值整体覆写既有行
    （last-write-wins），不另建行——升级重放=同种子集收敛。"""
    first = await _ensure_user_streak_stats(db_session, **_seed_kwargs(test_user.id, streak=15))
    await db_session.commit()

    replay = await _ensure_user_streak_stats(db_session, **_seed_kwargs(test_user.id, streak=9))
    await db_session.commit()

    assert replay.id == first.id
    assert replay.current_streak == 9
    assert replay.freeze_charges == 1

    count = (
        await db_session.execute(
            select(func.count()).select_from(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
        )
    ).scalar_one()
    assert count == 1

    reread = (
        await db_session.execute(select(UserStreakStats).where(UserStreakStats.user_id == test_user.id))
    ).scalar_one()
    assert reread.current_streak == 9
    assert reread.max_streak == 9


@pytest.mark.asyncio
async def test_seed_concurrent_firstbuild_single_row_convergence():
    """服务级并发形态：两会话同时 _ensure（barrier 同步首读），断言单行收敛
    （修前双裸 INSERT 落 2 行——真 PG 复现件 v3-output/WT766-SEED/；sqlite 写
    锁串行下面形态测试即并发收敛的最强可达断言）。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        from app.models.base import Base
        from app.models.user import User

        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as setup:
        from uuid import uuid4

        setup.add(
            User(
                id=uuid4(),
                username="wt766_seed_race",
                email="wt766_seed_race@probe.local",
                hashed_password="x",
            )
        )
        await setup.commit()
        await setup.refresh(setup_user := (await setup.execute(select(User))).scalar_one())
        user_id = setup_user.id

    barrier = asyncio.Barrier(2)

    async def worker(session: AsyncSession):
        await barrier.wait()
        return await _ensure_user_streak_stats(session, **_seed_kwargs(user_id))

    session_a = maker()
    session_b = maker()
    try:
        stats_a, stats_b = await asyncio.gather(worker(session_a), worker(session_b))
        await session_a.commit()
        await session_b.commit()
    finally:
        await session_a.close()
        await session_b.close()

    assert stats_a.id == stats_b.id, f"两会话各得一行: {stats_a.id} vs {stats_b.id}"

    async with maker() as check:
        count = (
            await check.execute(
                select(func.count()).select_from(UserStreakStats).where(UserStreakStats.user_id == user_id)
            )
        ).scalar_one()
        assert count == 1, f"并发首建后行数 {count} != 1（重复行落地）"
        row = (await check.execute(select(UserStreakStats).where(UserStreakStats.user_id == user_id))).scalar_one()
        assert row.current_streak == 15

    await engine.dispose()
