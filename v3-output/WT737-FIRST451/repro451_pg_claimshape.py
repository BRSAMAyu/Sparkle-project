"""WT737 附加验证（登记原记形态）：V3-FIX-451 台账原记「后提交方 flush 撞
user_id 主键 IntegrityError→重试自愈」的语句形态（user_id 单列唯一）。

注意：真实 user_streak_stats 表 PK=(user_id,id) 复合主键、user_id 无独立唯一
约束（\\d 实测+alembic 全链无 UNIQUE(user_id)），故本形态为假设形态而非真实
schema 行为——保留作对照：若 user_id 唯一，并发首建确实表现为台账所记的
IntegrityError。真实形态见 repro451_pg_realshape.py（重复行落库→持久
MultipleResultsFound，非自愈型）。

预期断言面（RED，假设形态）：
  step2: A/B 的 FOR UPDATE SELECT 均见 0 行（absent-row 无锁可取）
  step4: B 的 INSERT 阻塞在 A 未提交元组上（0.4s 时点 done=False）
  step5: A 提交后 B INSERT 抛 UniqueViolationError
  串行对照 GREEN 排除非竞态解释。sqlite 写锁天然串行无法构造该并发窗，以真 PG 为准。
"""
import asyncio
import sys

import asyncpg

DSN = "postgresql://wt737_scratch:wt737scratch@localhost:5432/wt737_race"


def p(msg):
    print(msg, flush=True)


async def reset(conn):
    await conn.execute("DROP TABLE IF EXISTS wt737_streak_stats")
    await conn.execute(
        """CREATE TABLE wt737_streak_stats (
             user_id text PRIMARY KEY,
             current_streak int NOT NULL DEFAULT 0,
             freeze_charges int NOT NULL DEFAULT 1)"""
    )


async def firstrace() -> bool:
    a, b = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    await reset(a)

    # ── A：首个核心活动事件先到。420 修后形态：SELECT ... FOR UPDATE（absent
    #    行 → 0 行，无锁可取），走 INSERT 分支，进入未提交窗（process_event
    #    成就评估 await 窗的压缩态）──
    await a.execute("BEGIN")
    rows_a = await a.fetch(
        "SELECT user_id FROM wt737_streak_stats WHERE user_id='u1' FOR UPDATE"
    )
    p(f"[claimshape] step2 A FOR UPDATE SELECT on absent row -> {len(rows_a)} row(s)")
    assert len(rows_a) == 0, "expected absent row for A"

    await a.execute(
        "INSERT INTO wt737_streak_stats (user_id, current_streak, freeze_charges) VALUES ($1,$2,$3)",
        "u1", 0, 1,
    )

    # ── B：同用户首个事件并发到达。同形态 SELECT ... FOR UPDATE——absent 行
    #    不持锁，B 同样见 0 行、同样走 INSERT 分支（451 竞态窗本体）──
    await b.execute("BEGIN")
    rows_b = await b.fetch(
        "SELECT user_id FROM wt737_streak_stats WHERE user_id='u1' FOR UPDATE"
    )
    p(f"[claimshape] step2 B FOR UPDATE SELECT on absent row -> {len(rows_b)} row(s)")
    assert len(rows_b) == 0, "expected absent row for B (FOR UPDATE does not lock absent rows)"

    t_ins = asyncio.create_task(
        b.execute(
            "INSERT INTO wt737_streak_stats (user_id, current_streak, freeze_charges) VALUES ($1,$2,$3)",
            "u1", 0, 1,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[claimshape] step4 B plain INSERT blocked on A in-flight tuple: done={t_ins.done()}")
    assert not t_ins.done(), "B INSERT did not block on A uncommitted row (no overlap?)"

    # ── A 提交：未提交窗闭合 ──
    await a.execute("COMMIT")

    # ── B 的 INSERT 恢复 → 撞 user_id 主键 unique_violation（500/回滚）──
    try:
        await t_ins
        p("[claimshape] step5 B INSERT survived — no IntegrityError (unexpected)")
        await b.execute("ROLLBACK")
        ok = False
    except asyncpg.UniqueViolationError as exc:
        p(f"[claimshape] step5 B INSERT raised UniqueViolationError: {str(exc).splitlines()[0]} "
          "-> process_event 事务回滚，事件 500（重试自愈）—— RED")
        await b.execute("ROLLBACK")
        ok = False

    fin = await a.fetchrow("SELECT user_id, current_streak, freeze_charges FROM wt737_streak_stats WHERE user_id='u1'")
    p(f"[claimshape] step6 FINAL: row={dict(fin) if fin else None}（仅 A 存活；B 事件丢失待重试）")

    # ── 串行对照：B 在 A 提交后 get-or-create → SELECT 命中，不 INSERT ──
    await reset(a)
    await a.execute("BEGIN")
    await a.execute(
        "INSERT INTO wt737_streak_stats (user_id, current_streak, freeze_charges) VALUES ($1,$2,$3)",
        "u1", 0, 1,
    )
    await a.execute("COMMIT")
    await b.execute("BEGIN")
    hit = await b.fetchrow("SELECT user_id FROM wt737_streak_stats WHERE user_id='u1' FOR UPDATE")
    serial_ok = hit is not None
    await b.execute("ROLLBACK")
    p(f"[claimshape] [serial-control] second arrival sees row (no INSERT needed): {'GREEN' if serial_ok else 'RED'}")

    await a.close()
    await b.close()
    return ok and serial_ok


if __name__ == "__main__":
    # 本驱动为修前形态：并发场景预期 RED（B 撞主键），串行对照预期 GREEN。
    # firstrace 返回 False（并发 RED）属预期；程序退出码 0 仅在 RED 如期出现时。
    raced_green = asyncio.run(firstrace())
    sys.exit(0 if not raced_green else 3)  # 3 = 并发场景意外 GREEN（修复提前生效）
