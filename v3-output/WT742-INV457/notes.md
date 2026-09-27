# WT742 — V3-FIX-457 实施记录（inventory STREAK_FREEZE 发货路径并发修复）

- 分支 `agent/node-b/wt742/inv457`（base 6fdbc258 = main），修复 commit **78eb25af**
- 先例学习：`git show 8c195be1`（wt737 V3-FIX-451，main）——确定性 uuid5 + ON CONFLICT
  DO NOTHING + FOR UPDATE 收敛读三件套全形态照学，本批同构复刻并补跨路径仲裁关键约束。

## 1. schema 实证（登记单教训执行：先 \d 不轻信登记）

`docker exec sparkle_db psql -U postgres -d sparkle -c "\d user_streak_stats"`（PG 16）：

- PK = `user_streak_stats_pkey PRIMARY KEY (user_id, id)` **复合主键**
- `id uuid NOT NULL` **无库端缺省**（BaseModel Python 侧 `default=uuid.uuid4`，app/models/base.py:150）
- `user_id` **无独立唯一约束**（仅 FK → users ON DELETE CASCADE；指名 ON CONFLICT (user_id) 会 42P10）
- 其余索引：last_activity_date / deleted_at，与竞态无关

结论：与 451 登记的修正后形态完全一致——登记单原记「无锁 SELECT+裸 INSERT」成立，
且无锁读改写丢更新（457 特有 face②）在真 PG 复现成立（下节）。

## 2. 真 PG 红→绿（三层证据，docker sparkle_db 一次性库 wt742_race + 角色 wt742_scratch）

复现件全部在本目录，log 为 tee 原样输出：

| 件 | 形态 | 结论 |
|---|---|---|
| `repro457_pg_prefix.py` + `.log.txt` | raw asyncpg 双连接，修前语句形态 | **RED**：face① 首建并发双 INSERT 无阻塞双落 2 行（随机 id 复合键互不冲突）→ scalar_one_or_none 同型读恒 MultipleResultsFound 持久 500；face② 行已存在时无锁读算写，A 未提交窗内 B 同读 0、双方各写 1 → final=1（两卡只计一份丢更新）；串行对照 2/单行 GREEN |
| `repro457_pg_postfix.py` + `.log.txt` | raw asyncpg 双连接，修后语句形态 | **GREEN**：跨路径 face①——engine(451 确定性 id) × inventory(457 同源 id) 并发首建，B INSERT 阻塞 0.4s（done=False）→ A 提交后仲裁 INSERT 0 0 静默跳过 → 锁读同一行，单行收敛且 id=确定性值；face②——双方 FOR UPDATE，B 阻塞在计算之前，读 A 已提交值再算 → final=2=如实计账 |
| `repro457_service_pg_prefix.py` + `.log.txt` | **真修前代码**（PYTHONPATH 指 main 仓 backend）并发跑 `InventoryService._apply_consumable_effect` | **RED**：rows=2 + scalar_one 读抛 MultipleResultsFound |
| `repro457_service_pg.py` + `.log.txt` | **真修后代码**（worktree）两会话并发发货 + engine 交叉读 | **GREEN**：rows=1、freeze_charges=3（列 ORM 缺省 1「默认送1个」+ 发货 2，两笔都如实计账；log 可见 B before=2=读 A 已提交值）；`AchievementEngine._get_or_create_streak_stats` 交叉读同一行不另建 |

说明：sqlite 写锁天然串行测不出该并发窗（与 451 同判），并发证据以真 PG 为准；
pytest 单元面对行为/收敛钉子。一次性角色库 `wt742_scratch`/`wt742_race` 本验证新建，
未触 sparkle 业务库数据。

## 3. 修法（451 三件套同构 + 行锁，P4 最小面）

`backend/app/services/inventory_service.py` STREAK_FREEZE 分支：

1. 读改写加 `with_for_update()`（achievement_engine :2253 的 420 先例；锁由调用方
   `use_consumable` 的 commit 释放，覆盖读-算-写全程，face② 闭合）
2. 首建 INSERT id 改 **与 451 完全同源** `uuid5(NAMESPACE_URL, f"achievement-streak-stats:{user_id}")`
   ——复合主键 (user_id,id) 依赖两侧 id 相等才能仲裁 inventory↔engine 跨路径并发首建
   （457 登记点③），**两处字符串必须同步变更**，代码内已加耦合警示注释
3. 方言分派目标无关 ON CONFLICT DO NOTHING（pg/sqlite 直写；其余方言 begin_nested+
   IntegrityError 兜底，同 451 形态）后重走 FOR UPDATE 收敛读；末尾防御回退保持非 None 契约
4. 不选 UNIQUE(user_id) 迁移：迁移+schema 快照导出+存量去重超 P4 卡面（与 451 同判）

## 4. 测试面（零回退）

- `tests/unit/test_inventory_consumable_effect_wiring.py`：**6 passed** = 4 既有
  + 2 新增（`firstbuild_id_deterministic_shared_with_engine`：单行+id==engine 派生值；
  `firstbuild_then_engine_reads_same_row`：engine 交叉读单行、累加不产生第二行）
- 回归全绿（SECRET_KEY 一次性 env + 隔离 worktree 无 .env，演示库守卫三选一之 2）：
  streak 族 5 文件+accountability 时区+guest seed 清理 **38 passed**；
  shop/inventory 邻域 **9 passed, 3 skipped**；achievement 族 14 文件+api+e2e
  **89 passed**；state aggregator/narrative/contract **43 passed** ——合计 **176+ 用例全绿**
- 既有基线（非本批引入）：`tests/integration/test_shop_acceptance.py`(15)、
  `test_achievement_progress_context.py`(1)、`test_north_star_journey.py`(10) 的
  fixture ERROR 为 demo 库守卫拒绝（集成夹具需专属真库），**main 上逐字同型复跑证实**
- 新增 2 测试在修前代码上亦 RED（PG 服务级 prefix 已证同路径机制；单元钉子在 sqlite
  不可并发构造，并发面由上述真 PG 三件承担）

## 5. mypy / ruff

- mypy app：**worktree 133 = main 133**，逐条归一化 diff **零漂移**，触达文件 0 错
  （登记单写「132」为写卡时旧值；main 当前基线即 133，wt737 批亦记 133=133）
- ruff check 触达两文件 **All checks passed**；`ruff format --check` 漂移 hunks
  **28 = 28** 与 main 既有集合零新增（既有漂移不重排纪律；本批新增代码零格式偏差——
  初稿 2 处新漂移已按 format 口径修正后复验）

## 6. 台账动作

- **V3-FIX-457 → FIXED@78eb25af**（本批实证补全登记原记「未运行级复现」缺项：
  两 face 均真 PG 运行级红→绿）
- **新发现 V3-FIX-467**（P4，OPEN）：`guest_seed_service.py:844-888`
  `_ensure_user_streak_stats`（调用点 :2641）同表第三入口——同族首建并发
  （随机 id 双行→持久 MultipleResultsFound）+行已存在分支全字段覆盖写；
  触发面窄（guest→formal 升级单流一次性）故 P4 留档不阻塞，修法方向同三件套
  但种子覆盖语义需产品先裁。467/468 全文 grep 0 命中后占用
- `scripts/devtools/ledger_union_merge.py --verify`：零 FAIL（结果见提交记录）

## 铁律自检

- 未伪造：四份 log 均本机真 PG 16.15 实跑 tee 原样；服务级 RED 直接跑 main 修前
  真代码（main 只读未动，PYTHONPATH 指向运行）。
- 路径先 find/grep 亲证；未 push；main 仓未提交脏状态未触碰。
- 一次性 PG 角色库仅本验证自建，演示库守卫按其指引通过。
