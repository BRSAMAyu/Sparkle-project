"""WT766 服务级真 PG RED 驱动：并发执行修前真实
guest_seed_service._ensure_user_streak_stats（467/479 目标函数，本件运行于
实现前的 worktree 代码）——

两独立 AsyncSession（独立 PG 连接）+ asyncio.Barrier 同时到达，模拟 479 收敛
后的触发面：两个访客并发登录，各自重播同一批共享演示 friend 行的 streak 种子。

RED 期望（修前代码）：
  双方无锁 SELECT 同见 0 行 → 各自裸 INSERT 随机 uuid4 id → 复合主键互不
  冲突双落 2 行；其后 scalar_one_or_none 同型读（seed 自身+451/457 修后
  engine/inventory）恒 MultipleResultsFound。

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


async def seed_worker(user_id, barrier: asyncio.Barrier):
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
                # 修前真代码：nora friend 行种子值（调用点 :2641 同型参数）
                return await _ensure_user_streak_stats(
                    session,
                    user_id=user_id,
                    current_streak=15,
                    max_streak=15,
                    total_checkin_days=40,
                    last_activity_date=datetime.utcnow() - timedelta(hours=2),
                    longest_streak_start=datetime.utcnow() - timedelta(days=19),
                    longest_streak_end=datetime.utcnow() - timedelta(days=4),
                    freeze_charges=1,
                    max_freeze_charges=3,
                )
    finally:
        await engine.dispose()


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

    barrier = asyncio.Barrier(2)
    r1, r2 = await asyncio.gather(
        seed_worker(U1, barrier),
        seed_worker(U1, barrier),
    )
    p(f"[svc-prefix] A row id={r1.id}")
    p(f"[svc-prefix] B row id={r2.id}")
    p(f"[svc-prefix] same row object returned? {r1.id == r2.id}")

    conn = await asyncpg.connect(DSN_SYNC)
    try:
        n = await conn.fetchval("SELECT count(*) FROM user_streak_stats WHERE user_id=$1", U1)
    finally:
        await conn.close()
    p(f"[svc-prefix] rows={n} (RED 期望 2 重复行)")
    RESULTS["rows"] = n
    dup = n == 2

    # scalar_one_or_none 同型读（seed 自身 + 451/457 修后读面）
    engine = create_async_engine(DSN_ASYNC)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        try:
            result = await session.execute(select(UserStreakStats).where(UserStreakStats.user_id == U1))
            result.scalar_one_or_none()
            multi = False
            p("[svc-prefix] single-row read: ok (unexpected for RED)")
        except Exception as e:
            multi = "MultipleResultsFound" in type(e).__name__ or "multiple rows" in str(e).lower()
            p(f"[svc-prefix] single-row read raised {type(e).__name__}: multi={multi}")
    await engine.dispose()
    RESULTS["multi_read"] = multi

    print("\nRESULT_JSON=" + __import__("json").dumps(RESULTS, ensure_ascii=False), flush=True)
    verdict = dup and multi
    print(f"SERVICE PREFIX VERDICT: {'RED (race reproduced on real pre-fix code, real PG)' if verdict else 'NOT REPRODUCED'}", flush=True)
    sys.exit(0 if verdict else 3)


if __name__ == "__main__":
    asyncio.run(main())
