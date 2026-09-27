"""WT742 服务级真 PG 竞态驱动（RED 对照版）：同一并发脚本跑修复前代码
（PYTHONPATH 指向 main 仓 backend，inventory STREAK_FREEZE 分支为修复前形态：
裸 SELECT + 随机 id 裸 INSERT + 无锁读算写）。

RED 期望：两会话并发首建发货 → 双行落地（复合键随机 id 互不冲突）→
单行读形态 scalar_one 抛 MultipleResultsFound。
"""

import asyncio
import json
import os
import uuid
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "wt742_test_only_secret")

import asyncpg  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

DSN_SYNC = "postgresql://wt742_scratch:wt742scratch@localhost:5432/wt742_race"
DSN_ASYNC = "postgresql+asyncpg://wt742_scratch:wt742scratch@localhost:5432/wt742_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt742-svc-race-u1")

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


async def delivery_worker(user_id: str, quantity: int, barrier: asyncio.Barrier):
    from app.models.shop import ConsumableEffectType
    from app.services.inventory_service import InventoryService
    from sqlalchemy.ext.asyncio import async_sessionmaker

    engine = create_async_engine(DSN_ASYNC)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            stub = SimpleNamespace(
                effect_type=ConsumableEffectType.STREAK_FREEZE,
                consumable_item=None,
            )
            async with session.begin():
                await barrier.wait()
                svc = InventoryService(session)
                return await svc._apply_consumable_effect(user_id, stub, quantity)
    finally:
        await engine.dispose()


async def main():
    await reset_schema()

    from app.models.achievement import UserStreakStats
    from app.models.base import Base
    from app.models.user import User
    from sqlalchemy.ext.asyncio import async_sessionmaker

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
                    username="wt742u",
                    email="wt742u@test.local",
                    hashed_password="x",
                )
            )
    await engine.dispose()

    uid = str(U1)
    barrier = asyncio.Barrier(2)
    r1, r2 = await asyncio.gather(
        delivery_worker(uid, 1, barrier),
        delivery_worker(uid, 1, barrier),
    )
    p(f"[svc-prefix] A={r1}")
    p(f"[svc-prefix] B={r2}")

    conn = await asyncpg.connect(DSN_SYNC)
    try:
        row = await conn.fetchrow(
            "SELECT count(*) AS n FROM user_streak_stats WHERE user_id=$1", U1
        )
    finally:
        await conn.close()
    n = row["n"]
    p(f"[svc-prefix] rows={n}  (修复前：随机 id 双行落地 = RED)")
    assert n == 2, f"expected duplicate rows on pre-fix code, got {n}"
    RESULTS["service_rows"] = n

    # 修复前引擎/服务后续单行读形态 → MultipleResultsFound（持久 500 面）
    from sqlalchemy import select

    engine = create_async_engine(DSN_ASYNC)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    read_outcome = "no-error"
    async with maker() as session:
        try:
            result = await session.execute(
                select(UserStreakStats).where(UserStreakStats.user_id == uid)
            )
            result.scalar_one()
        except Exception as exc:
            read_outcome = type(exc).__name__
    await engine.dispose()
    p(f"[svc-prefix] scalar_one read outcome: {read_outcome} (期望 MultipleResultsFound = RED)")
    assert read_outcome == "MultipleResultsFound"
    RESULTS["scalar_read"] = read_outcome
    print("\nRESULT_JSON=" + json.dumps(RESULTS, ensure_ascii=False), flush=True)
    print("SERVICE PREFIX VERDICT: RED confirmed (real pre-fix code on real PG)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
