# WT734-LOCK420 — V3-FIX-420 连胜统计读-算-写补行锁

- 日期：2026-09-27
- 分支：`agent/node-b/wt734/lock420`（base `dfc19e63`）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt734-lock420`
- 任务：复核 CONFIRMED@wt719 且已补真 PG 运行级复现的 V3-FIX-420（P3）——
  `achievement_engine._update_streak_stats` 对 `UserStreakStats` 读-算-写无行锁，
  跨本地日 straddle 并发下 stale 覆写。修法按复核指明：`_get_or_create_streak_stats`
  SELECT 加 `with_for_update`（同文件 `:1470`/`:1478` 成就解锁路径先例）。

## 改动（fix commit `423c7b06`）

`backend/app/services/achievement_engine.py` `_get_or_create_streak_stats`：
`select(UserStreakStats).where(user_id == user_id)` → 追加 `.with_for_update()`，
附 V3-FIX-420 注释（成因/复现件指引/先例/sqlite no-op 说明）。净 +8/-1 行，单文件。

## 真 PG 红绿对照（docker sparkle_db，PostgreSQL 16.15）

一次性角色/库：`wt719_scratch`@`wt719_race`（`docker exec sparkle_db psql` 创建，
仅本验证用）。语句形态驱动（同 wt713 推理链三环，与引擎 `_update_streak_stats`
语义同型：A=23:59:59 事件 delta=1 正常路径、B=00:00:01 事件按 stale/fresh delta 分支）。

### 修前 RED —— `repro420_pg_straddle.py` + `repro420_pg_straddle_prefix.log.txt`

与 WT719-VERIFY1 原件同语句形态（B 无锁读+预计算 stale UPDATE），本机复跑：

- 场景 1（无卡）：环① stale 读 delta=2 → 环② stale UPDATE 阻塞 A 行锁、A 提交后
  EvalPlanQual 照写 → 环③ day0 ACTIVE→MISSED。终态 S=1（正确 7）、day0=MISSED —— RED。
- 场景 2（有卡 1 张）：同三环，白烧 1 张（charges 1→0）、S=6（正确 7）、day0=FROZEN —— RED。
- 场景 3（串行对照）：S=7、day0=ACTIVE —— GREEN，排除非竞态解释。

### 修后 GREEN —— `repro420_pg_straddle_fixed.py` + `repro420_pg_straddle_postfix.log.txt`

唯一差异=语句形态对准修复后引擎：A/B 首读均为 `SELECT ... FOR UPDATE`
（`_get_or_create_streak_stats` 新形态），其余时序不变：

- ring1-fixed：B 的 FOR UPDATE SELECT 在 A 未提交窗内阻塞（0.4s 时点 `done=False`
  实证锁真实生效，非时序巧合），A 提交后恢复，读到 last=D0/S=6 → delta=1 正常连续分支。
- 场景 1（无卡）：S=7、day0=ACTIVE、charges=0 —— GREEN。
- 场景 2（有卡）：S=7、day0=ACTIVE、charges=1（卡不烧）—— GREEN。
- 场景 3（串行对照）：GREEN。

分叉消除：加锁后 B 不可能在 A 未提交窗读到旧 `last_activity_date`，stale delta
分支不可达，终态恒与串行对照收敛。

## freeze 分支 stale 覆写面顺审（复核要求项）

裁决：随行锁自然闭合。`_update_streak_stats` 全部分支的读-算-写
（`freeze_charges >= days_missed` 判定、`-= days_missed` 扣卡、
`last_activity_date` 推进）都发生在持锁 SELECT 之后、同事务 flush 之前；
后到事务在先到提交前无法进入计算段，`freeze_charges`/`last_activity_date`
读值恒为已提交新鲜值。`_upsert_streak_day` 全部 7 个调用点
（:2080/:2093/:2112/:2141/:2155/:2163/:2202）均在 `_update_streak_stats`
锁窗内，day 行写入随 stats 行锁每用户串行，无锁外 day 行写者
（全仓 `UserStreakDay(` 直构仅 engine 一处）。场景 2 的 charges=1 保持即为运行级佐证。

## 测试面（find 先行，全部绿）

- streak 核心：`test_streak_engine_local_day_freeze_max.py`（293/294 直钉）、
  `test_streak_quality_local_today.py`、`test_streak_quality_service.py`、
  `test_streak_weak_persistence.py`、`test_growth_streak_local_clock.py` —— 31 passed。
- achievement 族：`test_achievement_engine_regression.py`、
  `test_achievement_engine_phase3.py`、`test_achievement_contract_weekend.py`、
  `test_achievement_system_alignment.py`、`test_v3_fix260_achievement_type_wire_parity.py`、
  `test_accountability_achievement_service_timezone.py`、
  `test_achievement_event_consumer.py`、`test_achievement_event_publishers.py`、
  `test_achievement_engine_aliases.py` —— 72 passed。
- e2e/api：`test_achievement_unlock_e2e.py`、`test_achievement_api.py` —— 14 passed。
- 邻域（streak 消费面）：`test_accountability_system_api.py`、
  `test_dashboard_flame_card_local_day.py`、`test_statistics_local_timezone_boundary.py`、
  leaderboard 三件 —— 36 passed。
- 合计 153 passed，0 failed。sqlite 无行锁语义，`with_for_update` 在该方言为
  no-op（SQLAlchemy 编译期忽略），上述 sqlite 面全绿即 no-op 实证。

## mypy / ruff

- mypy `app`：本 worktree 133 错 = 主仓 main（同版本 mypy 1.20.2、临时 cache）
  逐条 diff **IDENTICAL**（`sed 's/:[0-9]*:/:/'` 归一后 sort diff 零差异）；
  台账引 132 为历史口径差（main 近两提交/工具版本漂移，与本改动无关），
  触达文件 `achievement_engine.py` 0 错——零回涨。
- ruff：`check app/services/achievement_engine.py` All checks passed；
  `format --check` 报既有漂移，主仓 main 同判，漂移 hunks
  （:197/:636/:1876 附近）与本改动（:2249 起）零重叠，未顺手动既有行。

## 台账

- V3-FIX-420 → **FIXED@423c7b06**（状态格引用本目录证据与 153 用例/mypy/ruff 面）。
- 新发现 **V3-FIX-451**（P4，OPEN）：`_get_or_create_streak_stats` 首建并发
  IntegrityError 面——`FOR UPDATE` 对不存在的行不持锁，同一用户首次核心活动事件
  并发时双方同走 INSERT、后提交方撞 `user_id` 主键 500，重试自愈；触发窗口为
  user_streak_stats 首行诞生前的一次性窄窗，与 420（行已存在场景）正交。
  修法方向：INSERT ... ON CONFLICT DO NOTHING + 重读，或 per-user 分布式锁
  （srl/FIX-193 先例）；建议并入下一批触达 achievement_engine 的卡顺带处理。
- `ledger_union_merge.py --verify`：登行前 313 行通过 → 登行后
  **314 行、裸管 8 形态、零 FAIL、无重号**（枚举合法）。

## 铁律自检

- 未伪造：RED/GREEN 均本机真 PG 实跑，log 为 tee 原样输出；fixed 复现件首版
  曾因 A 未持锁即发 B 锁读导致断言失败（脚本时序错，非 PG 事实），修正为
  A/B 均按修复后形态 FOR UPDATE 后重跑，失败版未留档不入证据链。
- 一次性 PG 角色库 `wt719_scratch`/`wt719_race` 为本验证新建（docker exec psql），
  未触 sparkle 业务库数据。
- 路径先 find（测试/台账/verify 工具均先探后用）；gen 产物按先例主仓
  `cp -RL` 不入库（`git status` 恒净）；未 push。
- 主仓只读未动（mypy 对照跑主仓使用 `--cache-dir /tmp`，零写入主仓工作区）。

## 产出

- `repro420_pg_straddle.py`（修前驱动，沿 WT719-VERIFY1）+ `repro420_pg_straddle_prefix.log.txt`（RED）
- `repro420_pg_straddle_fixed.py`（修后形态驱动）+ `repro420_pg_straddle_postfix.log.txt`（GREEN）
- 本 notes.md
- commits：`423c7b06`（fix）+ docs（台账 420 FIXED/451 登记 + 本目录入册）
