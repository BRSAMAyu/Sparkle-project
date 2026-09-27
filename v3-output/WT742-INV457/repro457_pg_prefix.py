"""WT742 权威 RED 驱动：V3-FIX-457 inventory STREAK_FREEZE 发货路径——

修复前 services/inventory_service.py:431-444 语句形态（真 PG \d user_streak_stats
镜像：PK=(user_id,id) 复合主键、id 无库端缺省=BaseModel 随机 uuid4、user_id 无
独立唯一约束）：

  face① 首建并发：裸 SELECT（连 FOR UPDATE 都没有）对 absent 行同见 0 行 →
         各自 INSERT（id=随机 uuid4）→ 复合键互不冲突双双落库 2 行 →
         此后 scalar_one_or_none 同型读恒 MultipleResultsFound（持久 500，
         与 451 真实形态同机制；且本路径可与 achievement_engine 事件并发——
         引擎侧即便已 451 修复，本路径随机 id 照样与其确定性 id 互异落双行）。
  face② 无锁读改写：行已存在时裸 SELECT 读 freeze_charges → Python 算
         min(before+quantity, max) → flush 盲 UPDATE 覆写。READ COMMITTED 下
         B 在 A 未提交窗内同读旧值，双方同写 +quantity 只生效一份 → 丢更新，
         用户白花光子。

预期断言面（RED，真实形态）：
  face①: A/B 裸 SELECT 均见 0 行；B INSERT 无阻塞无冲突；双双提交后表内 2 行；
         单行读形态抛 MultipleResultsFound（simulated：fetch 全行 count=2）
  face②: A/B 裸 SELECT 同读 charges=0；B UPDATE 阻塞至 A 提交后覆写；
         终值 charges=1 != 期望 2（两次发货只计一次）
  serial 对照 GREEN：同操作串行两次 → charges=2 且 1 行（排除非竞态解释）。
sqlite 写锁天然串行无法构造该并发窗，以真 PG 16 为准（451 同判）。
"""

import asyncio
import json
import uuid

import asyncpg

DSN = "postgresql://wt742_scratch:wt742scratch@localhost:5432/wt742_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt742-inv457-u1")
TABLE = "wt742_streak_stats"

RESULTS: dict[str, object] = {}


def p(msg):
    print(msg, flush=True)


async def reset(conn):
    await conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
    # 真实表形（\d user_streak_stats @ sparkle@postgres 16）竞态相关列最小镜像
    await conn.execute(
        f"""CREATE TABLE {TABLE} (
             user_id uuid NOT NULL,
             id uuid NOT NULL,
             freeze_charges int,
             max_freeze_charges int,
             created_at timestamp NOT NULL DEFAULT now(),
             updated_at timestamp NOT NULL DEFAULT now(),
             CONSTRAINT wt742_streak_stats_pkey PRIMARY KEY (user_id, id))"""
    )


async def seed_row(conn, charges=0, max_charges=3):
    """预置单行（face② 的已存在行场景，等价于用户已有连胜统计）。"""
    await conn.execute(
        f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, uuid.uuid5(uuid.NAMESPACE_URL, "wt742-seed"), charges, max_charges,
    )


async def face1_firstbuild(conn_a, conn_b):
    """face①：首建并发（inventory 修复前形态：裸 SELECT + 随机 id INSERT）。"""
    a, b = conn_a, conn_b
    await reset(a)

    # ── A：STREAK_FREEZE 发货，stats 不存在分支 ──
    await a.execute("BEGIN")
    rows_a = await a.fetch(f"SELECT user_id FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[f1] A plain SELECT on absent row -> {len(rows_a)} row(s) (no lock taken)")
    assert len(rows_a) == 0
    await a.execute(
        f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, uuid.uuid4(), 1, 3,  # BaseModel id 缺省=随机 uuid4
    )

    # ── B：同用户并发购买同卡发货 ──
    await b.execute("BEGIN")
    rows_b = await b.fetch(f"SELECT user_id FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[f1] B plain SELECT on absent row -> {len(rows_b)} row(s)")
    assert len(rows_b) == 0
    id_b = uuid.uuid4()
    t_ins = asyncio.create_task(
        b.execute(
            f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) VALUES ($1,$2,$3,$4)",
            U1, id_b, 1, 3,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[f1] B INSERT (distinct random id) completed without blocking: done={t_ins.done()}")
    await t_ins

    await a.execute("COMMIT")
    await b.execute("COMMIT")

    n = await a.fetchval(f"SELECT count(*) FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[f1] rows landed for user: {n}  (期望 1，重复行落地 = RED)")
    assert n == 2, f"expected duplicate rows, got {n}"
    RESULTS["face1_rows"] = n
    # 单行读形态（engine _get_or_create_streak_stats / guest_seed 同型
    # scalar_one_or_none）→ 2 行必抛 MultipleResultsFound
    RESULTS["face1_scalar_read"] = "MultipleResultsFound"


async def face2_lostupdate(conn_a, conn_b):
    """face②：无锁读改写丢更新（发货前已有 stats 行）。"""
    a, b = conn_a, conn_b
    await reset(a)
    await seed_row(a, charges=0, max_charges=3)

    # ── A：裸 SELECT 读 charges=0 → 算 min(0+1,3)=1 → UPDATE（未提交）──
    await a.execute("BEGIN")
    row_a = await a.fetchrow(
        f"SELECT freeze_charges, max_freeze_charges FROM {TABLE} WHERE user_id=$1", U1
    )
    calc_a = min(int(row_a["freeze_charges"] or 0) + 1, int(row_a["max_freeze_charges"] or 0))
    p(f"[f2] A read charges={row_a['freeze_charges']} -> computed {calc_a}")

    # ── B：A 未提交窗内并发发货，裸 SELECT 同读 0 ──
    await b.execute("BEGIN")
    row_b = await b.fetchrow(
        f"SELECT freeze_charges, max_freeze_charges FROM {TABLE} WHERE user_id=$1", U1
    )
    calc_b = min(int(row_b["freeze_charges"] or 0) + 1, int(row_b["max_freeze_charges"] or 0))
    p(f"[f2] B read charges={row_b['freeze_charges']} (stale, A uncommitted) -> computed {calc_b}")
    assert calc_a == 1 and calc_b == 1, "both must read stale 0 and compute 1"

    await a.execute(
        f"UPDATE {TABLE} SET freeze_charges=$2, updated_at=now() WHERE user_id=$1", U1, calc_a
    )
    t_b = asyncio.create_task(
        b.execute(
            f"UPDATE {TABLE} SET freeze_charges=$2, updated_at=now() WHERE user_id=$1", U1, calc_b
        )
    )
    await asyncio.sleep(0.3)
    p(f"[f2] B UPDATE blocked on A uncommitted tuple: done={t_b.done()}")
    await a.execute("COMMIT")
    await t_b
    await b.execute("COMMIT")

    final = await a.fetchval(f"SELECT freeze_charges FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[f2] final freeze_charges={final}  (两次发货期望 2，丢更新 = RED)")
    assert final == 1, f"lost update expected final=1, got {final}"
    RESULTS["face2_final_charges"] = final


async def serial_control(conn_a):
    """串行对照：同操作串行两次 → 2（证明期望行为本身成立，排除非竞态解释）。"""
    a = conn_a
    await reset(a)
    await seed_row(a, charges=0, max_charges=3)
    for _ in range(2):
        row = await a.fetchrow(
            f"SELECT freeze_charges, max_freeze_charges FROM {TABLE} WHERE user_id=$1", U1
        )
        calc = min(int(row["freeze_charges"] or 0) + 1, int(row["max_freeze_charges"] or 0))
        await a.execute(
            f"UPDATE {TABLE} SET freeze_charges=$2, updated_at=now() WHERE user_id=$1", U1, calc
        )
    final = await a.fetchval(f"SELECT freeze_charges FROM {TABLE} WHERE user_id=$1", U1)
    n = await a.fetchval(f"SELECT count(*) FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[serial] charges={final} rows={n}  (对照 GREEN)")
    assert final == 2 and n == 1
    RESULTS["serial_charges"] = final
    RESULTS["serial_rows"] = n


async def main():
    ca, cb = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    try:
        await serial_control(ca)
        await face1_firstbuild(ca, cb)
        await face2_lostupdate(ca, cb)
    finally:
        await ca.close()
        await cb.close()
    print("\nRESULT_JSON=" + json.dumps(RESULTS, ensure_ascii=False), flush=True)
    print("PREFIX VERDICT: RED confirmed (face1 duplicate rows + face2 lost update)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
