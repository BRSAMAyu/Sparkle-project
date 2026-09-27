"""WT742 服务级真 PG 竞态驱动：直接并发执行修复后的
InventoryService._apply_consumable_effect（STREAK_FREEZE 分支）——

与 raw asyncpg 镜像（repro457_pg_prefix/postfix）互补，本件走真实 SQLAlchemy
AsyncSession + 真实服务代码 + 真实 PG（wt742_race 一次性库）：

  GREEN 期望：两会话并发首建发货 → 单行收敛（确定性 id）+ freeze_charges=2
  （行锁串行化读算写，无丢更新）；引擎 _get_or_create_streak_stats 交叉读同
  一行不另建。

结构：users + user_streak_stats 两表按 ORM metadata 建表（最小依赖集）。
"""

import asyncio
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

    engine = create_async_engine(DSN_ASYNC)
    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        from sqlalchemy.ext.asyncio import async_sessionmaker

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

    engine = create_async_engine(DSN_ASYNC)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync: Base.metadata.create_all(
                sync, tables=[User.__table__, UserStreakStats.__table__]
            )
        )
    # 造用户
    from sqlalchemy.ext.asyncio import async_sessionmaker

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
    p(f"[svc] A={r1}")
    p(f"[svc] B={r2}")
    assert r1["effect"] == "streak_freeze" and r2["effect"] == "streak_freeze"
    assert r1["charges_added"] == 1 and r2["charges_added"] == 1, "两笔发货都必须如实计账"

    conn = await asyncpg.connect(DSN_SYNC)
    try:
        row = await conn.fetchrow(
            "SELECT count(*) AS n, max(freeze_charges) AS charges FROM user_streak_stats WHERE user_id=$1", U1
        )
    finally:
        await conn.close()
    p(f"[svc] rows={row['n']} freeze_charges={row['charges']} (期望 1 行；charges=默认1+发货2=3 = GREEN)")
    assert row["n"] == 1, f"duplicate rows: {row['n']}"
    # freeze_charges 列 ORM 缺省=1（「默认送1个」），首建行自带 1，两笔发货各 +1
    assert row["charges"] == 3, f"lost update: {row['charges']}"
    RESULTS["service_rows"] = row["n"]
    RESULTS["service_charges"] = row["charges"]

    # 引擎交叉读同一行，不另建
    from app.services.achievement_engine import AchievementEngine

    engine = create_async_engine(DSN_ASYNC)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        async with session.begin():
            eng = AchievementEngine(session)
            stats = await eng._get_or_create_streak_stats(uid)
            assert int(stats.freeze_charges or 0) == 3
    await engine.dispose()
    conn = await asyncpg.connect(DSN_SYNC)
    try:
        n = await conn.fetchval("SELECT count(*) FROM user_streak_stats WHERE user_id=$1", U1)
    finally:
        await conn.close()
    p(f"[svc] engine cross-read rows={n} (期望 1 = GREEN)")
    assert n == 1
    RESULTS["engine_cross_rows"] = n
    print("\nRESULT_JSON=" + json.dumps(RESULTS, ensure_ascii=False), flush=True)
    print("SERVICE VERDICT: GREEN (fixed real code path on real PG)", flush=True)


if __name__ == "__main__":
    import json

    asyncio.run(main())
