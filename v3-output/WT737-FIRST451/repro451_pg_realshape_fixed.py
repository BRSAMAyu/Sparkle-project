"""WT737 修后 GREEN 驱动：V3-FIX-451 修复后引擎语句形态——

_get_or_create_streak_stats 首建分支改为：id=uuid5(NAMESPACE_URL,
"achievement-streak-stats:{user_id}") 确定性派生（routing_engine stage4-routing
同型先例），INSERT ... ON CONFLICT DO NOTHING（目标无关，pkey 仲裁），随后重走
SELECT ... FOR UPDATE 收敛读。

同一用户首个事件并发达达：A/B 复合主键 (user_id, 同一 uuid5) 相同——B 的 INSERT
阻塞在 A 未提交元组上，A 提交后 B 的 INSERT 被静默跳过（INSERT 0 0），B 的
收敛读锁到 A 的同一行。终态单行、双方同值，与串行对照收敛（GREEN）。
"""
import asyncio
import sys
import uuid

import asyncpg

DSN = "postgresql://wt737_scratch:wt737scratch@localhost:5432/wt737_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt737-fixed-u1")
ID_U1 = uuid.uuid5(uuid.NAMESPACE_URL, f"achievement-streak-stats:{U1}")  # 引擎修复后同型派生


def p(msg):
    print(msg, flush=True)


async def reset(conn):
    await conn.execute("DROP TABLE IF EXISTS wt737_streak_stats")
    await conn.execute(
        """CREATE TABLE wt737_streak_stats (
             user_id uuid NOT NULL,
             id uuid NOT NULL,
             current_streak int,
             freeze_charges int,
             created_at timestamp NOT NULL DEFAULT now(),
             updated_at timestamp NOT NULL DEFAULT now(),
             CONSTRAINT wt737_streak_stats_pkey PRIMARY KEY (user_id, id))"""
    )


async def engine_get_or_create(conn, user_id: uuid.UUID) -> list:
    """修复后引擎语句形态：锁读 → absent 则确定性 id upsert → 重锁读收敛。"""
    rows = await conn.fetch("SELECT id FROM wt737_streak_stats WHERE user_id=$1 FOR UPDATE", user_id)
    if rows:
        return rows
    det_id = uuid.uuid5(uuid.NAMESPACE_URL, f"achievement-streak-stats:{user_id}")
    await conn.execute(
        """INSERT INTO wt737_streak_stats (user_id, id, current_streak, freeze_charges)
           VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING""",
        user_id, det_id, 0, 1,
    )
    return await conn.fetch("SELECT id FROM wt737_streak_stats WHERE user_id=$1 FOR UPDATE", user_id)


async def fixedrace() -> bool:
    a, b = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    await reset(a)

    # ── A：首事件先到——锁读 0 行 → 确定性 id INSERT（未提交窗=process_event
    #    成就评估窗压缩态）──
    await a.execute("BEGIN")
    got_a = await engine_get_or_create(a, U1)
    assert len(got_a) == 1 and got_a[0]["id"] == ID_U1, got_a
    p(f"[fixedrace] step1 A first-create INSERT landed (uncommitted), id={str(ID_U1)[:8]}")

    # ── B：并发到达——锁读 0 行（absent 无锁）→ 同一确定性 id INSERT 阻塞在
    #    A 未提交元组上（pkey 仲裁等待）──
    await b.execute("BEGIN")
    rows_b = await b.fetch("SELECT id FROM wt737_streak_stats WHERE user_id=$1 FOR UPDATE", U1)
    assert len(rows_b) == 0, rows_b
    t_ins = asyncio.create_task(
        b.execute(
            """INSERT INTO wt737_streak_stats (user_id, id, current_streak, freeze_charges)
               VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING""",
            U1, ID_U1, 0, 1,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[fixedrace] step2 B same-deterministic-id INSERT blocked on A in-flight tuple: done={t_ins.done()}")
    assert not t_ins.done(), "B INSERT did not block on A uncommitted row (no overlap?)"

    # ── A 提交（模拟 process_event 完成）──
    await a.execute("COMMIT")

    # ── B 恢复：INSERT 被静默跳过（status INSERT 0 0）→ 收敛读锁到 A 的行 ──
    status = await t_ins
    p(f"[fixedrace] step3 B INSERT resumed after A commit: status={status.strip()} —— 冲突跳过，无 IntegrityError")
    got_b = await engine_get_or_create(b, U1)
    assert len(got_b) == 1 and got_b[0]["id"] == ID_U1, got_b
    p(f"[fixedrace] step4 B converged read: 1 row, same id as A —— 双方同值")

    await b.execute("COMMIT")

    cnt = await a.fetchval("SELECT count(*) FROM wt737_streak_stats WHERE user_id=$1", U1)
    single_ok = cnt == 1
    p(f"[fixedrace] FINAL: rows for user = {cnt} (correct 1) -> {'GREEN' if single_ok else 'RED'}")

    # ── 场景 2：后续事件（行已在）——纯锁读命中，不 INSERT ──
    got2 = await engine_get_or_create(a, U1)
    later_ok = len(got2) == 1 and got2[0]["id"] == ID_U1
    p(f"[fixedrace] [later-event] existing-row path returns single row: {'GREEN' if later_ok else 'RED'}")

    # ── 场景 3：串行对照——首建完全串行两次调用，仍单行 ──
    await reset(a)
    await a.execute("BEGIN")
    g1 = await engine_get_or_create(a, U1)
    await a.execute("COMMIT")
    await b.execute("BEGIN")
    g2 = await engine_get_or_create(b, U1)
    await b.execute("COMMIT")
    cnt3 = await a.fetchval("SELECT count(*) FROM wt737_streak_stats WHERE user_id=$1", U1)
    serial_ok = len(g1) == 1 and len(g2) == 1 and cnt3 == 1 and g1[0]["id"] == g2[0]["id"]
    p(f"[fixedrace] [serial-control] two sequential first-creates -> {cnt3} row, same id: "
      f"{'GREEN' if serial_ok else 'RED'}")

    await a.close()
    await b.close()
    return single_ok and later_ok and serial_ok


if __name__ == "__main__":
    ok = asyncio.run(fixedrace())
    sys.exit(0 if ok else 1)