# WT737-FIRST451 — V3-FIX-451 连胜统计首建并发去重

- 日期：2026-09-27
- 分支：`agent/node-b/wt737/first451`（base `2ae4495d`）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt737-first451`
- fix commit：`023b2205`（单文件 `backend/app/services/achievement_engine.py`，净 +44/-4）
- 任务：修 V3-FIX-451（P4，wt734 于 420 收口顺审登记）——
  `_get_or_create_streak_stats` 的 `FOR UPDATE` 对不存在行不持锁，用户首个
  核心活动事件并发双 INSERT 的首建竞态。

## 登记失败模式修正（本卡最重要发现）

台账原记（wt734）：「后提交方 flush 撞 **user_id 主键 IntegrityError** → 500，
**重试自愈**」。真实 schema 下该失败模式**不成立**：

- 真 PG `\d user_streak_stats`（docker sparkle_db 实测）：PK = **(user_id, id)
  复合主键**；`id` 继承自 BaseModel、缺省**随机 uuid4**；user_id **无独立唯一
  约束**（alembic 全链仅 pkey+两个普通索引，无 UNIQUE(user_id)）。
- 故并发首建双方复合键互不相同 → **互不阻塞、互不冲突、双双提交落库为重复行**
  （实证 2 行落地）；此后引擎 `scalar_one_or_none()` 读到多行恒抛
  **MultipleResultsFound → 持久 500，非自愈**（比登记原记更差：不是一次性
  500，而是该用户后续所有触达连胜统计的事件持续失败，需人工清重）。
- 台账原记 IntegrityError 形态仅在「user_id 唯一」假设下成立——附假设形态
  对照复现（claimshape）双留档，修正依据可验。

## 修法（P4 最小面，确定性 id + ON CONFLICT DO NOTHING 收敛读）

首建 INSERT 的 `id` 改 **uuid5(NAMESPACE_URL, "achievement-streak-stats:{user_id}")**
确定性派生（先例：`orchestration/routing_engine.py:2563` stage4-routing；仓内
uuid5 派生键多处：learning/seed_bridge、task_reflection_service）——复合主键
(user_id, id) 随之成为每用户天然去重键；方言分派（先例：同文件
`_record_session_completion` :294-318）：

- postgresql / sqlite：`pg_insert/sqlite_insert(...).values(user_id, id).on_conflict_do_nothing()`
  **目标无关**（user_id 无唯一约束，指名 `(user_id)` 会 42P10；pkey 仲裁），
  然后重走原 `SELECT ... FOR UPDATE` **收敛读**；
- 其他方言（理论分支）：`begin_nested` + flush + `except IntegrityError` 回退
  （同先例三段式的尾段）。

语义：后到方 INSERT 阻塞在先到方未提交 pkey 元组上 → 先到方提交后其 INSERT
被静默跳过（INSERT 0 0）→ 收敛读锁到先到方的同一行，双方返回同值；先到方
自插自读不变；420 的 straddle 行锁语义原样保留（收敛读即原 FOR UPDATE 语句）。
读面尾部加防御回退（理论上不可达，仅保非 None 返回契约）。
**否决案**：UNIQUE(user_id) 迁移（迁移+gateway schema 快照导出+存量重去重，
超 P4 卡面）；per-user 分布式/advisory 锁（面更宽）。

## 真 PG 红绿对照（docker sparkle_db，PostgreSQL 16.15；一次性角色/库
`wt737_scratch`@`wt737_race`，`docker exec psql` 创建仅本验证用）

三份驱动 + tee 原样 log，全部本机实跑：

| 驱动 | 形态 | 结果 |
| --- | --- | --- |
| `repro451_pg_claimshape.py` + `repro451_pg_claimshape_prefix.log.txt` | 登记原记假设形态（user_id 单列唯一） | **RED**：A/B 锁读均 0 行→B 的 INSERT 阻塞 A 未提交元组（0.4s done=False）→A 提交后 B 撞 pkey UniqueViolationError；串行对照 GREEN |
| `repro451_pg_realshape.py` + `repro451_pg_realshape_prefix.log.txt` | **真实 schema 形态**（复合 pkey+随机 uuid4） | **RED**：A/B 锁读均 0 行→B 的 INSERT **无阻塞无冲突立即完成**（done=True，与假设形态的关键差异）→双双提交 **2 行重复落地**→引擎单行读形态见 2 行=MultipleResultsFound 持久化；串行对照 GREEN |
| `repro451_pg_realshape_fixed.py` + `repro451_pg_realshape_postfix.log.txt` | 修复后引擎语句形态（确定性 uuid5 id+ON CONFLICT DO NOTHING+收敛读） | **GREEN**：B 同 id INSERT 阻塞 A 未提交元组（0.4s done=False，锁真实生效）→A 提交后 B status=`INSERT 0 0` 静默跳过→收敛读 1 行与 A 同 id→终态单行；后续事件路径/串行对照（两次首建仍单行同 id）全 GREEN |

sqlite 说明：sqlite 写锁天然串行（单写者）无法构造首建并发窗，本竞态只能以
真 PG 验证（如实注明）；测试面 sqlite 全绿证明方言分支形态无损。

## 测试面（find 先行，全部绿，153 = 420 批基线零回退）

- streak 核心 31：`test_streak_engine_local_day_freeze_max.py`、
  `test_streak_quality_local_today.py`、`test_streak_quality_service.py`、
  `test_streak_weak_persistence.py`、`test_growth_streak_local_clock.py`
- achievement 族 72：`test_achievement_engine_regression.py`、
  `test_achievement_engine_phase3.py`、`test_achievement_contract_weekend.py`、
  `test_achievement_system_alignment.py`、
  `test_v3_fix260_achievement_type_wire_parity.py`、
  `test_accountability_achievement_service_timezone.py`、
  `test_achievement_event_consumer.py`、`test_achievement_event_publishers.py`、
  `test_achievement_engine_aliases.py`
- e2e/api 14：`test_achievement_unlock_e2e.py`、`test_achievement_api.py`
- 邻域 36：`test_accountability_system_api.py`、
  `test_dashboard_flame_card_local_day.py`、
  `test_statistics_local_timezone_boundary.py`、leaderboard 三件
- 运行方式：隔离 worktree 无 .env（演示库守卫 `tests/_dbguard` 三选一之 2）+
  一次性 `SECRET_KEY` 环境变量（settings 强制非空，测试专用不入库）。

## mypy / ruff

- mypy `app`（venv mypy，`--cache-dir /tmp` 双侧隔离）：worktree **133 = main
  133**，`sed 's/:[0-9]*:/:/'` 归一 sort diff **零差异**；触达文件
  achievement_engine.py **0 错**。中途自检捕获过 +2 新增（复用 `stmt` 变量的
  Insert 类型合并、收敛读 None 收窄），已按先例拆 `stmt_sqlite` + 防御回退
  归零——最终零回涨（任务卡引 132 为 wt734 期间历史口径，本环境 main=133，
  与 wt734 记录一致）。
- ruff：`check` 触达文件 All checks passed；`format --diff` 漂移 hunks
  8 处 = main 既有集合整体位移（:197/:636/:1876+:2865 起 5 处），**零新增**
  （中途新增的 1 处已按 120 列折叠归位）；未顺手动既有漂移行。

## 台账

- V3-FIX-451 → **FIXED@023b2205**（状态格含登记失败模式修正与全部证据指针）。
- 新发现 **V3-FIX-457**（P4，OPEN）：`inventory_service.py:433-440`
  STREAK_FREEZE 发货路径——同表 UserStreakStats **无锁 SELECT（连 FOR UPDATE
  都没有）+ absent 行裸 INSERT**：①首建并发与 451 同型（复合 pkey 随机 id
  不冲突→重复行→持久 MultipleResultsFound，451 复现件已实证同表机制）；②
  `freeze_charges` 读-算-写无锁丢更新（并发发货白花光子）。457 号 grep 复核
  空闲（0 命中）、458 备用未占用。修法方向已留：with_for_update（420 先例）
  + 与 451 相同的确定性 id upsert 收敛读。
- `ledger_union_merge.py --verify`：**316 行、8 裸管形态、零 FAIL、无重号**
  （verify 通过）。

## 铁律自检

- 未伪造：三份 RED/GREEN 均本机真 PG 16.15 实跑，log 为 tee 原样输出；登记
  原记失败模式与真实 schema 不符时**如实修正并双形态留档**，未迁就原记叙述。
- 一次性 PG 角色库 `wt737_scratch`/`wt737_race` 本验证新建（docker exec psql），
  未触 sparkle 业务库数据；演示库守卫按其指引以隔离 worktree+无 .env 通过。
- 路径先 find（函数/模型/migration/测试/verify 工具/uuid5 先例均先探后用）；
  gen 产物按先例主仓 `cp -RL` 不入库（git status 恒净）；未 push；主仓只读
  未动（mypy 对照 `--cache-dir /tmp`，测试在 worktree 内跑）。
- 最小面：fix 单文件单函数（+44/-4 含注释）；无迁移、无 schema 快照变化、
  无新依赖。

## 产出

- fix commit `023b2205`（`agent/node-b/wt737/first451`）
- `repro451_pg_claimshape.py` + `_prefix.log.txt`（假设形态 RED 对照）
- `repro451_pg_realshape.py` + `_prefix.log.txt`（真实形态权威 RED）
- `repro451_pg_realshape_fixed.py` + `_postfix.log.txt`（修后 GREEN）
- 本 notes.md；台账 451 FIXED + 457 登记（docs commit）
