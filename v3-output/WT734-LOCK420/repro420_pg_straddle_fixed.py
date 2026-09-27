"""WT734 验证：V3-FIX-420 修复后（_get_or_create_streak_stats 加 with_for_update）
同一 straddle 时序在真 PG 16 READ COMMITTED 下分叉消除。

与 WT719-VERIFY1/repro420_pg_straddle.py 同一三环时序，唯一差异是引擎语句形态：
修复后 B（00:00:01 事件）的 _get_or_create_streak_stats SELECT ... FOR UPDATE 在
A（23:59:59 事件）未提交窗内阻塞在 stats 行锁上（环①被锁前移拦截），A 提交后
才读到已更新的 last_activity_date=D0 → delta=1 走正常连续分支 → S+1、
day0 不被触碰。终态应与串行对照收敛（GREEN）。

预期断言面：
  ring1-fixed: B 的 FOR UPDATE SELECT 阻塞至 A 提交（锁真实生效，非时序巧合）
  场景 1（无卡）：S=7/day0=ACTIVE/charges=0
  场景 2（有卡 1 张）：S=7/day0=ACTIVE/charges=1（卡不被白烧）
  场景 3（串行对照）：S=7/day0=ACTIVE
"""
import asyncio
import datetime as dt
import sys

import asyncpg

DSN = "postgresql://wt719_scratch:wt719scratch@localhost:5432/wt719_race"
D_LAST = dt.date(2026, 9, 24)  # stats.last_activity_date（前日活动日）
D0 = dt.date(2026, 9, 25)      # A 事件本地日（23:59:59）
D1 = dt.date(2026, 9, 26)      # B 事件本地日（00:00:01）
S0 = 5


def p(msg):
    print(msg, flush=True)


async def seed(conn, freeze_charges):
    await conn.execute("DROP TABLE IF EXISTS wt719_streak_stats")
    await conn.execute("DROP TABLE IF EXISTS wt719_streak_days")
    await conn.execute(
        """CREATE TABLE wt719_streak_stats (
             user_id text PRIMARY KEY,
             current_streak int NOT NULL DEFAULT 0,
             last_activity_date date,
             freeze_charges int NOT NULL DEFAULT 0)"""
    )
    await conn.execute(
        """CREATE TABLE wt719_streak_days (
             user_id text NOT NULL,
             day date NOT NULL,
             status text NOT NULL,
             PRIMARY KEY (user_id, day))"""
    )
    await conn.execute(
        "INSERT INTO wt719_streak_stats VALUES ($1, $2, $3, $4)",
        "u1", S0, D_LAST, freeze_charges,
    )


async def race(freeze_charges: int, label: str) -> None:
    a, b = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    await seed(a, freeze_charges)

    # ── A：23:59:59 事件先到，_get_or_create_streak_stats 的
    #    SELECT ... FOR UPDATE 拿到 stats 行锁并进入未提交窗
    #    （process_event 成就逐条评估多 await 窗的压缩态）──
    await a.execute("BEGIN")
    row_a = await a.fetchrow(
        "SELECT last_activity_date, current_streak FROM wt719_streak_stats WHERE user_id='u1' FOR UPDATE"
    )
    last_a, s_a = row_a["last_activity_date"], row_a["current_streak"]
    assert (last_a, s_a) == (D_LAST, S0), (last_a, s_a)

    # ── B：00:00:01 事件后到，同语句形态 SELECT ... FOR UPDATE ——
    #    环①被锁前移拦截：B 阻塞在 A 行锁上，读不到 A 未提交前的旧值 ──
    await b.execute("BEGIN")
    t_sel = asyncio.create_task(
        b.fetchrow("SELECT last_activity_date, current_streak FROM wt719_streak_stats WHERE user_id='u1' FOR UPDATE")
    )
    await asyncio.sleep(0.4)
    p(f"[{label}] ring1-fixed B FOR UPDATE SELECT blocked under A uncommitted window: done={t_sel.done()}")
    assert not t_sel.done(), "ring1-fixed failed: B FOR UPDATE SELECT did not block on A lock"

    # ── A：写 stats + day0 ACTIVE，提交（未提交窗闭合）──
    await a.execute(
        "UPDATE wt719_streak_stats SET current_streak=$1, last_activity_date=$2 WHERE user_id='u1'",
        s_a + 1, D0,
    )
    await a.execute("INSERT INTO wt719_streak_days VALUES ($1, $2, $3)", "u1", D0, "ACTIVE")
    await a.execute("COMMIT")

    # ── B 解锁后读到的是 A 提交后的新值 → delta=1 正常连续分支 ──
    row = await t_sel
    last_b, s_b = row["last_activity_date"], row["current_streak"]
    delta = (D1 - last_b).days
    p(f"[{label}] ring1-fixed B resumed after A commit: last={last_b} S={s_b} → delta={delta}")
    assert (last_b, s_b) == (D0, S0 + 1), (last_b, s_b)
    assert delta == 1, f"stale read survived: delta={delta}"

    # B 正常连续分支：S+1，last=D1，day(D1) ACTIVE；day0 不触碰
    await b.execute(
        "UPDATE wt719_streak_stats SET current_streak=$1, last_activity_date=$2 WHERE user_id='u1'",
        s_b + 1, D1,
    )
    await b.execute("INSERT INTO wt719_streak_days VALUES ($1, $2, $3)", "u1", D1, "ACTIVE")
    await b.execute("COMMIT")

    fin_s = await a.fetchval("SELECT current_streak FROM wt719_streak_stats WHERE user_id='u1'")
    fin_last = await a.fetchval("SELECT last_activity_date FROM wt719_streak_stats WHERE user_id='u1'")
    fin_charges = await a.fetchval("SELECT freeze_charges FROM wt719_streak_stats WHERE user_id='u1'")
    fin_day0 = await a.fetchval("SELECT status FROM wt719_streak_days WHERE user_id='u1' AND day=$1", D0)

    correct_s, correct_day0 = S0 + 2, "ACTIVE"
    p(f"[{label}] FINAL: S={fin_s}(correct {correct_s}) last={fin_last}(correct {D1}) "
      f"charges={fin_charges}(before {freeze_charges}) day0={fin_day0}(correct {correct_day0})")
    if fin_s != correct_s or fin_day0 != correct_day0 or fin_charges != freeze_charges:
        p(f"[{label}] RED: straddle race diverged from serialized outcome")
        ok = False
    else:
        p(f"[{label}] GREEN: converged with serialized outcome")
        ok = True
    await a.close()
    await b.close()
    return ok


async def main() -> bool:
    ok1 = await race(freeze_charges=0, label="scenario1 no-freeze-card")
    ok2 = await race(freeze_charges=1, label="scenario2 with-freeze-card")

    # ── 场景 3 对照：完全串行（B 在 A 提交后重读）→ 收敛 ──
    a, b = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    await seed(a, 0)
    await a.execute("BEGIN")
    await a.execute(
        "UPDATE wt719_streak_stats SET current_streak=$1, last_activity_date=$2 WHERE user_id='u1'",
        S0 + 1, D0,
    )
    await a.execute("INSERT INTO wt719_streak_days VALUES ($1,$2,$3)", "u1", D0, "ACTIVE")
    await a.execute("COMMIT")
    await b.execute("BEGIN")
    last_b = await b.fetchval("SELECT last_activity_date FROM wt719_streak_stats WHERE user_id='u1'")
    s_b = await b.fetchval("SELECT current_streak FROM wt719_streak_stats WHERE user_id='u1'")
    delta = (D1 - last_b).days
    assert delta == 1, delta
    await b.execute(
        "UPDATE wt719_streak_stats SET current_streak=$1, last_activity_date=$2 WHERE user_id='u1'",
        s_b + 1, D1,
    )
    await b.execute("INSERT INTO wt719_streak_days VALUES ($1,$2,$3)", "u1", D1, "ACTIVE")
    await b.execute("COMMIT")
    fin_s = await a.fetchval("SELECT current_streak FROM wt719_streak_stats WHERE user_id='u1'")
    fin_day0 = await a.fetchval("SELECT status FROM wt719_streak_days WHERE user_id='u1' AND day=$1", D0)
    ok3 = fin_s == S0 + 2 and fin_day0 == "ACTIVE"
    p(f"[scenario3 serialized-control] FINAL: S={fin_s} day0={fin_day0} → "
      f"{'GREEN (correct)' if ok3 else 'RED'}")
    await a.close()
    await b.close()
    return ok1 and ok2 and ok3


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
