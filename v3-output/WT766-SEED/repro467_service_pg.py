"""WT766 服务级真 PG GREEN 驱动：并发执行修复后的
guest_seed_service._ensure_user_streak_stats（与 repro467_service_pg_prefix
同并发脚本形态，跑修后代码）——

  GREEN 期望：
  ①两会话并发首建（共享 friend 行，479 跨访客触发面同构）→ 单行收敛
    （确定性 uuid5 id=451/457 同源串）+ 双方返回同一行；
  ②并发覆盖重播（行已存在，两事务同时全字段覆写）→ 行锁下 last-write-wins，
    终态=种子集、无丢行无异常；
  ③engine（451 修后）交叉读同一行不另建。

结构：users + user_streak_stats 两表按 ORM metadata 建表（最小依赖集）。
"""

import asyncio
import os
import sys
import uuid

os.environ.setdefault("SECRET_KEY", "wt766_test_only_secret")

BACKEND = "/Users/brsama/code/GitHub/Sparkle-sysrev/wt766-seed/backend"
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(BACKEND, "app"))
sys.path.insert(0, os.path.join(BACKEND, "app", "gen"))

import asyncpg  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

DSN_SYNC = "postgresql://wt766_scratch:wt766scratch@localhost:5432/wt766_race"
DSN_ASYNC = "postgresql+asyncpg://wt766_scratch:wt766scratch@localhost:5432/wt766_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt766-svc-race-u1")

RESULTS: dict[str, object] = {}


def p(msg):
    print(msg, flush=True)


async def reset_schema():
    conn = await asyncpg.connect(DSN_SYNC)
    try:
        await conn.execute("DROP TABLE IF EXISTS user_streak_stats")
        await conn.execute("DROP TABLE IF EXISTS users")
    finally:
        await conn.close()


async def seed_worker(user_id, barrier: asyncio.Barrier, streak: int):
    from datetime import datetime, timedelta

    from app.services.guest_seed_service import _ensure_user_streak_stats

    engine = create_async_engine(DSN_ASYNC)
    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            async with session.begin():
                await barrier.wait()
                return await _ensure_user_streak_stats(
                    session,
                    user_id=user_id,
                    current_streak=streak,
                    max_streak=streak,
                    total_checkin_days=40,
                    last_activity_date=datetime.utcnow() - timedelta(hours=2),
                    longest_streak_start=datetime.utcnow() - timedelta(days=19),
                    longest_streak_end=datetime.utcnow() - timedelta(days=4),
                    freeze_charges=1,
                    max_freeze_charges=3,
                )
    finally:
        await engine.dispose()


async def row_count() -> int:
    conn = await asyncpg.connect(DSN_SYNC)
    try:
        return await conn.fetchval("SELECT count(*) FROM user_streak_stats WHERE user_id=$1", U1)
    finally:
        await conn.close()


async def main():
    await reset_schema()

    from app.models.achievement import UserStreakStats
    from app.models.base import Base
    from app.models.user import User

    engine = create_async_engine(DSN_ASYNC)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync: Base.metadata.create_all(
                sync, tables=[User.__table__, UserStreakStats.__table__]
            )
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            session.add(
                User(
                    id=U1,
                    username="wt766u",
                    email="wt766u@test.local",
                    hashed_password="x",
                )
            )
    await engine.dispose()

    # ── ①并发首建：两访客同时重播共享 friend 行种子 ──
    barrier = asyncio.Barrier(2)
    r1, r2 = await asyncio.gather(
        seed_worker(U1, barrier, 15),
        seed_worker(U1, barrier, 15),
    )
    p(f"[svc] A id={r1.id} B id={r2.id} same={r1.id == r2.id}")
    n = await row_count()
    p(f"[svc] firstbuild rows={n} (期望 1 = GREEN 单行收敛)")
    assert n == 1, f"duplicate rows: {n}"
    assert r1.id == r2.id, "两会话各得一行"
    from uuid import NAMESPACE_URL, uuid5

    expected_id = uuid5(NAMESPACE_URL, f"achievement-streak-stats:{str(U1)}")
    assert str(r1.id) == str(expected_id), f"id 异源: {r1.id} != {expected_id}"
    p(f"[svc] id == uuid5('achievement-streak-stats:<uid>') 与 451/457 同源 OK")
    RESULTS["firstbuild_rows"] = n

    # ── ②并发覆盖重播：行已存在，两事务同时全字段覆写（升级重放收敛面）──
    barrier2 = asyncio.Barrier(2)
    o1, o2 = await asyncio.gather(
        seed_worker(U1, barrier2, 9),
        seed_worker(U1, barrier2, 9),
    )
    n2 = await row_count()
    p(f"[svc] replay rows={n2} streak={o1.current_streak}/{o2.current_streak} (期望 1 行=9 = GREEN)")
    assert n2 == 1, f"replay duplicate rows: {n2}"
    assert int(o1.current_streak) == 9 and int(o2.current_streak) == 9, "覆盖重播终态未收敛"
    RESULTS["replay_rows"] = n2

    # ── ③engine 交叉读同一行，不另建 ──
    from app.services.achievement_engine import AchievementEngine

    engine = create_async_engine(DSN_ASYNC)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            eng = AchievementEngine(session)
            stats = await eng._get_or_create_streak_stats(str(U1))
            assert int(stats.freeze_charges or 0) == 1
    await engine.dispose()
    n3 = await row_count()
    p(f"[svc] engine cross-read rows={n3} (期望 1 = GREEN)")
    assert n3 == 1
    RESULTS["engine_cross_rows"] = n3

    print("\nRESULT_JSON=" + __import__("json").dumps(RESULTS, ensure_ascii=False), flush=True)
    print("SERVICE VERDICT: GREEN (fixed real code path on real PG)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
