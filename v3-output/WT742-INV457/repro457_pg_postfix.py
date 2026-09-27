"""WT742 权威 GREEN 驱动：V3-FIX-457 修复后形态（451 三件套同构）——

  face①-fixed 首建并发：A=achievement_engine 451 修后形态（确定性 id
         uuid5("achievement-streak-stats:{u}") INSERT）；B=inventory 修复后
         形态（FOR UPDATE SELECT absent → 同源确定性 id INSERT ...
         ON CONFLICT DO NOTHING → 重走 FOR UPDATE 收敛读）。跨路径同源 id
         使复合主键 (user_id,id) 成仲裁键：B 的 INSERT 阻塞在 A 未提交元组
         上，A 提交后静默跳过（INSERT 0 0）并锁读同一行——单行收敛、无
         MultipleResultsFound 面。
  face②-fixed 无锁读改写闭合：A/B 都走 SELECT ... FOR UPDATE——B 阻塞在
         计算之前，A 提交后 B 读到已提交的 charges=1 再算 min(1+1,3)=2，
         终值 2=两次发货如实计账。
  serial 对照不变 GREEN。
"""

import asyncio
import json
import uuid

import asyncpg

DSN = "postgresql://wt742_scratch:wt742scratch@localhost:5432/wt742_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt742-inv457-u1")
TABLE = "wt742_streak_stats"

# 451 与 457 修复共享的确定性派生（两处代码同一字符串，跨路径仲裁的承载点）
def stats_id_for(user_id):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"achievement-streak-stats:{user_id}")

RESULTS: dict[str, object] = {}


def p(msg):
    print(msg, flush=True)


async def reset(conn):
    await conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
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


async def face1_crosspath_firstbuild(conn_a, conn_b):
    """face①-fixed：engine(451修后) × inventory(457修后) 跨路径并发首建。"""
    a, b = conn_a, conn_b
    await reset(a)
    sid = stats_id_for(U1)

    # ── A：engine 451 修后形态——FOR UPDATE absent（无锁）+ 确定性 id INSERT ──
    await a.execute("BEGIN")
    rows_a = await a.fetch(f"SELECT user_id FROM {TABLE} WHERE user_id=$1 FOR UPDATE", U1)
    p(f"[f1f] A(engine) FOR UPDATE on absent row -> {len(rows_a)} row(s)")
    assert len(rows_a) == 0
    await a.execute(
        f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, sid, 1, 3,
    )

    # ── B：inventory 457 修后形态——FOR UPDATE SELECT → 同源 id
    #      ON CONFLICT DO NOTHING → 收敛读 ──
    await b.execute("BEGIN")
    rows_b = await b.fetch(f"SELECT user_id FROM {TABLE} WHERE user_id=$1 FOR UPDATE", U1)
    assert len(rows_b) == 0
    t_ins = asyncio.create_task(
        b.execute(
            f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) "
            "VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
            U1, sid, 1, 3,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[f1f] B ON CONFLICT DO NOTHING blocked on A uncommitted tuple: done={t_ins.done()}")
    assert not t_ins.done(), "B must block on A's speculative insertion (same pkey)"
    await a.execute("COMMIT")
    status = await t_ins
    await b.execute("COMMIT")
    p(f"[f1f] A committed; B INSERT arbitrated by pkey -> {status} (INSERT 0 0 = silently skipped)")

    n = await a.fetchval(f"SELECT count(*) FROM {TABLE} WHERE user_id=$1", U1)
    ids = await a.fetch(f"SELECT id FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[f1f] rows for user: {n}, ids={ [str(r['id']) for r in ids] }  (单行收敛 = GREEN)")
    assert n == 1 and str(ids[0]["id"]) == str(sid)
    RESULTS["face1_fixed_rows"] = n
    RESULTS["face1_fixed_id_is_deterministic"] = str(ids[0]["id"]) == str(sid)


async def face2_locked_readmodifywrite(conn_a, conn_b):
    """face②-fixed：读算写全程行锁（420 先例），B 阻塞在计算之前。"""
    a, b = conn_a, conn_b
    await reset(a)
    await a.execute(
        f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, stats_id_for(U1), 0, 3,
    )

    # ── A：FOR UPDATE 读 0 → 算 1 → UPDATE（未提交，持行锁）──
    await a.execute("BEGIN")
    row_a = await a.fetchrow(
        f"SELECT freeze_charges, max_freeze_charges FROM {TABLE} WHERE user_id=$1 FOR UPDATE", U1
    )
    calc_a = min(int(row_a["freeze_charges"] or 0) + 1, int(row_a["max_freeze_charges"] or 0))
    await a.execute(
        f"UPDATE {TABLE} SET freeze_charges=$2, updated_at=now() WHERE user_id=$1", U1, calc_a
    )
    p(f"[f2f] A locked-read charges={row_a['freeze_charges']} -> computed {calc_a} (uncommitted)")

    # ── B：FOR UPDATE 阻塞在 A 提交前——计算尚未发生 ──
    await b.execute("BEGIN")
    t_sel = asyncio.create_task(
        b.fetchrow(f"SELECT freeze_charges, max_freeze_charges FROM {TABLE} WHERE user_id=$1 FOR UPDATE", U1)
    )
    await asyncio.sleep(0.4)
    p(f"[f2f] B FOR UPDATE blocked before compute: done={t_sel.done()}")
    assert not t_sel.done(), "B must block before reading"
    await a.execute("COMMIT")
    row_b = await t_sel
    p(f"[f2f] A committed; B locked-read charges={row_b['freeze_charges']} (committed value)")
    calc_b = min(int(row_b["freeze_charges"] or 0) + 1, int(row_b["max_freeze_charges"] or 0))
    await b.execute(
        f"UPDATE {TABLE} SET freeze_charges=$2, updated_at=now() WHERE user_id=$1", U1, calc_b
    )
    await b.execute("COMMIT")

    final = await a.fetchval(f"SELECT freeze_charges FROM {TABLE} WHERE user_id=$1", U1)
    n = await a.fetchval(f"SELECT count(*) FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[f2f] final freeze_charges={final} rows={n}  (两次发货=2，丢更新闭合 = GREEN)")
    assert final == 2 and n == 1
    RESULTS["face2_fixed_final_charges"] = final


async def serial_control(conn_a):
    a = conn_a
    await reset(a)
    await a.execute(
        f"INSERT INTO {TABLE} (user_id, id, freeze_charges, max_freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, stats_id_for(U1), 0, 3,
    )
    for _ in range(2):
        row = await a.fetchrow(
            f"SELECT freeze_charges, max_freeze_charges FROM {TABLE} WHERE user_id=$1 FOR UPDATE", U1
        )
        calc = min(int(row["freeze_charges"] or 0) + 1, int(row["max_freeze_charges"] or 0))
        await a.execute(
            f"UPDATE {TABLE} SET freeze_charges=$2, updated_at=now() WHERE user_id=$1", U1, calc
        )
    final = await a.fetchval(f"SELECT freeze_charges FROM {TABLE} WHERE user_id=$1", U1)
    p(f"[serial] charges={final}  (对照 GREEN)")
    assert final == 2
    RESULTS["serial_charges"] = final


async def main():
    ca, cb = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    try:
        await serial_control(ca)
        await face1_crosspath_firstbuild(ca, cb)
        await face2_locked_readmodifywrite(ca, cb)
    finally:
        await ca.close()
        await cb.close()
    print("\nRESULT_JSON=" + json.dumps(RESULTS, ensure_ascii=False), flush=True)
    print("POSTFIX VERDICT: GREEN confirmed (single-row convergence + no lost update)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
