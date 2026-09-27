"""WT719 补充实验：V3-FIX-420 连胜 straddle 竞态 —— 真 PG 16 READ COMMITTED 运行级复现.

不动主线：在 dev PG（sparkle_db）一次性库 wt719_race 里建最小两张表（同型
user_streak_stats / user_streak_days，PK (user_id,day)），两条独立连接按
achievement_engine._update_streak_stats 的语句形态驱动 wt713 推理链三环：

  ① B 的 SELECT 在 A 未提交时读旧 last_activity_date（READ COMMITTED 语句级快照）
  ② B 的 stats UPDATE（ORM 预计算 stale SET 值）阻塞在 A 行锁上，
    A 提交后 EvalPlanQual 重查 WHERE 主键仍命中 → stale 值照写（丢更新）
  ③ day0 行：B 的定位 SELECT 在 A 提交后执行 → 见 ACTIVE → 覆写 MISSED/FROZEN

时序（A 先持锁进入未提交窗 = process_event 成就评估多 await 窗）：
  A: BEGIN; SELECT stats; UPDATE stats; INSERT day0 ACTIVE   [未提交窗]
  B: BEGIN; SELECT stats(旧); UPDATE stats(stale) → 阻塞     [环①②]
  A: COMMIT                                                  [窗闭合]
  B: UPDATE 落应用; SELECT day0→ACTIVE→UPDATE MISSED; COMMIT  [环②③]

场景 1（无卡）：正确串行终态 S=7/day0=ACTIVE；竞态终态 S=1/day0=MISSED。
场景 2（有卡 1 张）：白烧 1 张、S 只 +1、day0=FROZEN。
场景 3（对照，串行）：S=7/day0=ACTIVE —— 排除非竞态解释。
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

    # ── A：23:59:59 事件开事务读 stats（delta=1 正常路径，未提交窗开启）──
    await a.execute("BEGIN")
    last_a = await a.fetchval("SELECT last_activity_date FROM wt719_streak_stats WHERE user_id='u1'")
    s_a = await a.fetchval("SELECT current_streak FROM wt719_streak_stats WHERE user_id='u1'")
    assert (last_a, s_a) == (D_LAST, S0), (last_a, s_a)

    # ── B：00:00:01 事件开事务读 stats —— 环①：A 未提交 → 读旧值 ──
    await b.execute("BEGIN")
    last_b = await b.fetchval("SELECT last_activity_date FROM wt719_streak_stats WHERE user_id='u1'")
    s_b = await b.fetchval("SELECT current_streak FROM wt719_streak_stats WHERE user_id='u1'")
    stale_delta = (D1 - last_b).days
    p(f"[{label}] ring1 B stale read under A uncommitted: last={last_b} S={s_b} → delta={stale_delta}")
    assert (last_b, s_b) == (D_LAST, S0), "ring1 failed: B did not read stale value"
    assert stale_delta == 2, stale_delta

    # B 按断签/冻结分支预计算终值（_update_streak_stats else 分支语义）
    days_missed = stale_delta - 1
    use_freeze = freeze_charges >= days_missed
    if use_freeze:
        b_new_s, b_new_charges, b_day0 = S0 + 1, freeze_charges - days_missed, "FROZEN"
    else:
        b_new_s, b_new_charges, b_day0 = 1, freeze_charges, "MISSED"  # 断签归 1
    b_new_last = D1

    # ── A：写 + 保持未提交（成就评估多 await 窗的压缩态）──
    await a.execute(
        "UPDATE wt719_streak_stats SET current_streak=$1, last_activity_date=$2 WHERE user_id='u1'",
        s_a + 1, D0,
    )
    await a.execute("INSERT INTO wt719_streak_days VALUES ($1, $2, $3)", "u1", D0, "ACTIVE")

    # ── 环②：B 的 stale stats UPDATE 先发 → 阻塞在 A 行锁 ──
    t = asyncio.create_task(
        b.execute(
            "UPDATE wt719_streak_stats SET current_streak=$1, last_activity_date=$2, "
            "freeze_charges=$3 WHERE user_id='u1'",
            b_new_s, b_new_last, b_new_charges,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[{label}] ring2 B stale stats UPDATE blocked on A row lock: done={t.done()}")
    assert not t.done(), "ring2 failed: B UPDATE did not block on A lock"

    # ── A 提交（未提交窗闭合）→ B 的 stale UPDATE 落应用 ──
    await a.execute("COMMIT")
    await t
    p(f"[{label}] ring2 B stale UPDATE applied after A commit (EvalPlanQual pk re-check pass)")

    # ── 环③：B 的 day0 定位 SELECT 在 A 提交后执行 → 见 ACTIVE → 覆写 ──
    day0 = await b.fetchval("SELECT status FROM wt719_streak_days WHERE user_id='u1' AND day=$1", D0)
    if day0 is not None:
        await b.execute(
            "UPDATE wt719_streak_days SET status=$2 WHERE user_id='u1' AND day=$1", D0, b_day0
        )
        p(f"[{label}] ring3 day0 located: {day0} → overwrite {b_day0}")
    else:
        await b.execute("INSERT INTO wt719_streak_days VALUES ($1,$2,$3)", "u1", D0, b_day0)
        p(f"[{label}] ring3 day0 insert path (A-uncommitted index-collision branch, not this timing)")
    await b.execute("COMMIT")

    fin_s = await a.fetchval("SELECT current_streak FROM wt719_streak_stats WHERE user_id='u1'")
    fin_last = await a.fetchval("SELECT last_activity_date FROM wt719_streak_stats WHERE user_id='u1'")
    fin_charges = await a.fetchval("SELECT freeze_charges FROM wt719_streak_stats WHERE user_id='u1'")
    fin_day0 = await a.fetchval("SELECT status FROM wt719_streak_days WHERE user_id='u1' AND day=$1", D0)

    correct_s, correct_day0 = S0 + 2, "ACTIVE"
    p(f"[{label}] FINAL: S={fin_s}(correct {correct_s}) last={fin_last}(correct {D1}) "
      f"charges={fin_charges}(before {freeze_charges}) day0={fin_day0}(correct {correct_day0})")
    if fin_s != correct_s or fin_day0 != correct_day0:
        p(f"[{label}] RED: straddle race diverged from serialized outcome")
    else:
        p(f"[{label}] GREEN: converged with serialized outcome")
    await a.close()
    await b.close()


async def main():
    await race(freeze_charges=0, label="scenario1 no-freeze-card")
    await race(freeze_charges=1, label="scenario2 with-freeze-card")

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
    ok = fin_s == S0 + 2 and fin_day0 == "ACTIVE"
    p(f"[scenario3 serialized-control] FINAL: S={fin_s} day0={fin_day0} → "
      f"{'GREEN (correct)' if ok else 'RED'}")
    await a.close()
    await b.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
