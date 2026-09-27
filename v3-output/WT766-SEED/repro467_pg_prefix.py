"""WT766 RED 驱动（真 PG 形态层）：V3-FIX-467/479 修前 guest 种子路径
_ensure_user_streak_stats 语句形态——无锁 SELECT（连 FOR UPDATE 都没有）+
absent 行裸 INSERT（id=BaseModel 缺省随机 uuid4）。

表形为 dev 库 \\d user_streak_stats 实测镜像：PK=(user_id,id) 复合主键、
id 无库级缺省（随机值来自 ORM uuid4）、user_id 无独立唯一约束。

竞态语义（451/457 同机制同表第三入口）：
  step2: A/B 两事务先后/并发各走无锁 SELECT → 同见 0 行
  step3: 各自 INSERT 随机 uuid4 id → 复合主键互不相同 → 无阻塞无冲突
  step4: 双双提交 → 2 重复行落地
  step5: scalar_one_or_none 同型读恒 MultipleResultsFound → 持久损坏面 RED
  串行对照 GREEN 排除非竞态解释。sqlite 写锁天然串行无法构造该并发窗，
  以真 PG 为准（PG 16.15，docker sparkle_db 一次性库 wt766_race，建后即删）。
"""
import asyncio
import sys
import uuid

import asyncpg

DSN = "postgresql://wt766_scratch:wt766scratch@localhost:5432/wt766_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt766-shape-u1")  # 演示 friend 行同型 uuid 主键


def p(msg):
    print(msg, flush=True)


async def reset(conn):
    await conn.execute("DROP TABLE IF EXISTS wt766_streak_stats")
    await conn.execute(
        """CREATE TABLE wt766_streak_stats (
             user_id uuid NOT NULL,
             id uuid NOT NULL,
             current_streak int,
             freeze_charges int,
             created_at timestamp NOT NULL DEFAULT now(),
             updated_at timestamp NOT NULL DEFAULT now(),
             CONSTRAINT wt766_streak_stats_pkey PRIMARY KEY (user_id, id))"""
    )


async def firstrace() -> bool:
    a, b = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    await reset(a)

    # ── A：访客登录重播种子，为共享 friend 行建 streak（修前语句形态）──
    await a.execute("BEGIN")
    rows_a = await a.fetch("SELECT user_id FROM wt766_streak_stats WHERE user_id=$1", U1)
    p(f"[prefix] step2 A plain SELECT (no lock) on absent row -> {len(rows_a)} row(s)")
    assert len(rows_a) == 0, "expected absent row for A"
    id_a = uuid.uuid4()  # BaseModel id 缺省 uuid.uuid4 同型随机值
    await a.execute(
        "INSERT INTO wt766_streak_stats (user_id, id, current_streak, freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, id_a, 15, 1,
    )

    # ── B：另一访客并发登录重播同一 friend 行。无锁 SELECT 同见 0 行 → 同走
    #    INSERT；id 随机 → 复合主键不同 → 无阻塞无冲突 ──
    await b.execute("BEGIN")
    rows_b = await b.fetch("SELECT user_id FROM wt766_streak_stats WHERE user_id=$1", U1)
    p(f"[prefix] step2 B plain SELECT (no lock) on absent row -> {len(rows_b)} row(s)")
    assert len(rows_b) == 0, "expected absent row for B"
    id_b = uuid.uuid4()
    assert id_a != id_b, "uuid4 collision (astronomically unlikely)"
    t_ins = asyncio.create_task(
        b.execute(
            "INSERT INTO wt766_streak_stats (user_id, id, current_streak, freeze_charges) VALUES ($1,$2,$3,$4)",
            U1, id_b, 15, 1,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[prefix] step3 B INSERT (distinct random id) completed without blocking: done={t_ins.done()} "
      "—— 双方复合主键互不冲突，无 IntegrityError 可言")
    await t_ins

    await a.execute("COMMIT")
    await b.execute("COMMIT")

    cnt = await a.fetchval("SELECT count(*) FROM wt766_streak_stats WHERE user_id=$1", U1)
    ids = [str(r["id"])[:8] for r in await a.fetch("SELECT id FROM wt766_streak_stats WHERE user_id=$1", U1)]
    p(f"[prefix] step4 both committed, rows for friend user = {cnt} (ids {ids}) —— 重复行落地")
    if cnt != 2:
        p("[prefix] step4 UNEXPECTED: expected 2 duplicate rows")
        await a.close()
        await b.close()
        return False

    # ── scalar_one_or_none 同型读（seed 自身 :857 + 451/457 修后 engine/inventory
    #    读面）见 2 行 → MultipleResultsFound，此后每次访客登录种子 SAVEPOINT
    #    回滚、seed_status 恒 failed（auth.py 非致命语义）——RED ──
    readback = await a.fetch("SELECT id FROM wt766_streak_stats WHERE user_id=$1", U1)
    multi = len(readback) > 1
    p(f"[prefix] step5 single-row read sees {len(readback)} row(s) -> "
      f"{'MultipleResultsFound on every后续读—— RED（持久损坏面）' if multi else 'single row (unexpected)'}")

    # ── 串行对照：A 提交后 B 才到达 → SELECT 命中既有行，走覆盖写分支不 INSERT ──
    await reset(a)
    await a.execute(
        "INSERT INTO wt766_streak_stats (user_id, id, current_streak, freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, uuid.uuid4(), 15, 1,
    )
    hit = await b.fetch("SELECT user_id FROM wt766_streak_stats WHERE user_id=$1", U1)
    serial_ok = len(hit) == 1
    p(f"[prefix] [serial-control] second arrival sees exactly 1 row: {'GREEN' if serial_ok else 'RED'}")

    await a.close()
    await b.close()
    return multi and serial_ok


if __name__ == "__main__":
    raced_red = asyncio.run(firstrace())
    sys.exit(0 if raced_red else 3)  # 3 = 竞态未如预期复现
