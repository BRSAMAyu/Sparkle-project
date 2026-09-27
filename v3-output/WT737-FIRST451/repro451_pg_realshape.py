"""WT737 权威 RED 驱动：V3-FIX-451 真实 schema 形态——user_streak_stats 的
PK=(user_id,id) 复合主键（\\d 实测），id 为 BaseModel 缺省随机 uuid4。

修复前引擎形态：absent 行时 `SELECT ... FOR UPDATE`（对不存在行不持锁，两事务
同见 0 行）→ 各自 `UserStreakStats(user_id=...)` INSERT（id=随机 uuid4）。
双方复合主键 (user_id,id) 因 id 随机而互不相同——互不阻塞、互不冲突、双双提交
落库为重复行。此后引擎 `scalar_one_or_none()` 读到 2 行恒抛 MultipleResultsFound：
该用户后续每个触达连胜统计的事件持续 500，非台账原记「IntegrityError 一次 500
重试自愈」而是持久损坏面（登记单失败模式修正依据）。

预期断言面（RED，真实形态）：
  step2: A/B 的 FOR UPDATE SELECT 均见 0 行
  step3: B 的 INSERT 立即完成（无任何阻塞/冲突——与假设形态对照的差异点）
  step4: A/B 均提交成功，表内该用户 2 行（重复行落地）
  step5: 修复前引擎读形态（scalar_one_or_none 同型取单行）见 2 行 → 必然
         MultipleResultsFound → RED
  串行对照 GREEN 排除非竞态解释。sqlite 写锁天然串行无法构造该并发窗，以真 PG 为准。
"""
import asyncio
import sys
import uuid

import asyncpg

DSN = "postgresql://wt737_scratch:wt737scratch@localhost:5432/wt737_race"
U1 = uuid.uuid5(uuid.NAMESPACE_URL, "wt737-realshape-u1")  # 测试用户 uuid


def p(msg):
    print(msg, flush=True)


async def reset(conn):
    await conn.execute("DROP TABLE IF EXISTS wt737_streak_stats")
    # 真实表形（\\d user_streak_stats）竞态相关列的最小镜像：复合主键+随机 uuid4 id
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


async def firstrace() -> bool:
    a, b = await asyncpg.connect(DSN), await asyncpg.connect(DSN)
    await reset(a)

    # ── A：首个核心活动事件先到（420 修后引擎形态）──
    await a.execute("BEGIN")
    rows_a = await a.fetch("SELECT user_id FROM wt737_streak_stats WHERE user_id=$1 FOR UPDATE", U1)
    p(f"[realshape] step2 A FOR UPDATE SELECT on absent row -> {len(rows_a)} row(s)")
    assert len(rows_a) == 0, "expected absent row for A"
    id_a = uuid.uuid4()  # BaseModel id 缺省 uuid.uuid4 的同型随机值
    await a.execute(
        "INSERT INTO wt737_streak_stats (user_id, id, current_streak, freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, id_a, 0, 1,
    )

    # ── B：同用户首个事件并发到达。absent 行不持锁 → B 同见 0 行同走 INSERT；
    #    id 随机 → 复合主键不同 → 无阻塞无冲突 ──
    await b.execute("BEGIN")
    rows_b = await b.fetch("SELECT user_id FROM wt737_streak_stats WHERE user_id=$1 FOR UPDATE", U1)
    p(f"[realshape] step2 B FOR UPDATE SELECT on absent row -> {len(rows_b)} row(s)")
    assert len(rows_b) == 0, "expected absent row for B"
    id_b = uuid.uuid4()
    assert id_a != id_b, "uuid4 collision (astronomically unlikely)"
    t_ins = asyncio.create_task(
        b.execute(
            "INSERT INTO wt737_streak_stats (user_id, id, current_streak, freeze_charges) VALUES ($1,$2,$3,$4)",
            U1, id_b, 0, 1,
        )
    )
    await asyncio.sleep(0.4)
    p(f"[realshape] step3 B INSERT (distinct random id) completed without blocking: done={t_ins.done()} "
      "—— 双方复合主键互不冲突，无 IntegrityError 可言")
    await t_ins

    await a.execute("COMMIT")
    await b.execute("COMMIT")

    cnt = await a.fetchval("SELECT count(*) FROM wt737_streak_stats WHERE user_id=$1", U1)
    ids = [str(r["id"])[:8] for r in await a.fetch("SELECT id FROM wt737_streak_stats WHERE user_id=$1", U1)]
    p(f"[realshape] step4 both committed, rows for user = {cnt} (ids {ids}) —— 重复行落地")
    if cnt != 2:
        p("[realshape] step4 UNEXPECTED: expected 2 duplicate rows")
        await a.close()
        await b.close()
        return False

    # ── 修复前引擎读形态：scalar_one_or_none 同型（单行期望）读到 2 行 →
    #    SQLAlchemy MultipleResultsFound（此处以行数直接断言同事实）──
    readback = await a.fetch("SELECT id FROM wt737_streak_stats WHERE user_id=$1", U1)
    multi = len(readback) > 1
    p(f"[realshape] step5 engine single-row read sees {len(readback)} row(s) -> "
      f"{'MultipleResultsFound every后续事件 —— RED（持久 500，非自愈）' if multi else 'single row (unexpected)'}")

    # ── 串行对照：A 提交后 B 才 get-or-create → SELECT 命中，不 INSERT ──
    await reset(a)
    await a.execute(
        "INSERT INTO wt737_streak_stats (user_id, id, current_streak, freeze_charges) VALUES ($1,$2,$3,$4)",
        U1, uuid.uuid4(), 0, 1,
    )
    hit = await b.fetch("SELECT user_id FROM wt737_streak_stats WHERE user_id=$1 FOR UPDATE", U1)
    serial_ok = len(hit) == 1
    p(f"[realshape] [serial-control] second arrival sees exactly 1 row: {'GREEN' if serial_ok else 'RED'}")

    await a.close()
    await b.close()
    return multi and serial_ok


if __name__ == "__main__":
    # 修前驱动：真实形态 RED（重复行+多行读失败）+ 串行对照 GREEN → 退出码 0。
    raced_red = asyncio.run(firstrace())
    sys.exit(0 if raced_red else 3)  # 3 = 竞态未如预期复现
