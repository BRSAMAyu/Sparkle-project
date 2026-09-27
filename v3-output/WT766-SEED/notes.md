# WT766 — V3-FIX-467 + FIX-479 合卡实施记录（guest 种子路径 UserStreakStats 首建并发收敛 + 覆盖写语义）

- 分支 `agent/node-b/wt766/seed`（base 5f00b4e8 = main），修复 commit **见 git log（本文件随修复 commit 同提交）**
- 先例学习：451（wt737，achievement_engine:2274）/457（wt742，inventory_service:459）
  三件套全形态照学；协调方裁决照执行——种子语义=幂等重放收敛，覆盖写语义保留
  （last-write-wins 行锁下安全），不选 UNIQUE(user_id) 迁移（超卡面）。

## 1. schema 实证（先 \d 不轻信登记）

`docker exec sparkle_db psql -U postgres -d sparkle -c "\d user_streak_stats"`（PG 16，只读）：

- PK = `user_streak_stats_pkey PRIMARY KEY (user_id, id)` **复合主键**
- `id uuid NOT NULL` **无库端缺省**（BaseModel Python 侧 `default=uuid.uuid4`）
- `user_id` **无独立唯一约束**（仅 FK → users ON DELETE CASCADE；指名 ON CONFLICT (user_id) 会 42P10）

与 451/457 登记形态逐项一致，467 机制成立前提全部亲证。

## 2. 真 PG 红→绿（docker sparkle_db 一次性库 wt766_race + 角色 wt766_scratch，建后即删）

复现件全部在本目录，log 为 tee 原样输出：

| 件 | 形态 | 结论 |
|---|---|---|
| `repro467_pg_prefix.py` + `.log.txt` | raw asyncpg 双连接，修前语句形态（无锁 SELECT+随机 uuid4 裸 INSERT） | **RED**：双事务同见 0 行→各自 INSERT 复合键互不冲突无阻塞→双落 2 行→scalar_one_or_none 同型读恒 MultipleResultsFound 持久损坏；串行对照单行 GREEN |
| `repro467_service_pg_prefix.py` + `.log.txt` | **真修前代码**（sys.path 指 worktree 实现前快照）两会话+barrier 并发跑 `_ensure_user_streak_stats` | **RED**：rows=2（两会话各得随机 id 行）+ 单行读抛 `MultipleResultsFound` |
| `repro467_service_pg.py` + `.log.txt` | **真修后代码**（worktree）三层：①并发首建 ②并发覆盖重播 ③engine 交叉读 | **GREEN**：①rows=1 且两会话返回同一行、id==uuid5 与 451/457 同源；②行已存在双事务同时全字段覆写，rows=1 终态收敛（streak=9/9，行锁下 last-write-wins 无异常）；③engine `_get_or_create_streak_stats` 交叉读同一行不另建 |

触发面按 479 收敛口径构造：操作对象=跨访客共享的演示 friend 行（`friend.id`），
两会话并发模拟两个访客同时登录重播种子——无需同用户双端重放。

**sqlite 面的精确化（对 wt737「sqlite 测不出」判例的补充）**：行锁语义 sqlite 确实
无法构造（with_for_update 为方言 no-op），但「双会话共享 StaticPool 单连接 + barrier
同步双方首读」的并发形态在 sqlite 上**可复现修前双行**（两会话首读都先于任一 INSERT
落库）——故本批服务级并发收敛形态测试可入库常态化（RED/GREEN 双向实证），行锁机制
本体仍以真 PG 复现件为准。

## 3. 修法（451/457 三件套同构 + 覆盖写加锁，P4 最小面）

`backend/app/services/guest_seed_service.py` `_ensure_user_streak_stats`（:843-930 附近，调用点 :2641 不变）：

1. 读加 `with_for_update()`（420/451/457 先例；sqlite 方言 no-op）——**首建与行已存在
   分支统一被此锁读覆盖**（裁决点：覆盖写分支同样加锁=首读即锁读）
2. 首建 INSERT id 改确定性 uuid5——与 achievement_engine:2274 / inventory_service:459
   **逐字符同源**（python re 亲证三处表达式完全一致），代码内加**三入口耦合警示注释**
   （复合主键 (user_id,id) 依赖三侧 id 相等仲裁跨路径并发首建，改字符串即重开双行竞态）
3. 方言分派目标无关 ON CONFLICT DO NOTHING（pg/sqlite 直写；其余方言 begin_nested+
   IntegrityError 兜底，同 451/457 形态）后重走 FOR UPDATE 收敛读；防御回退保持非 None
   契约（挂起实例带确定性 id）
4. **覆盖写语义保留**：首建与既有行统一走全字段种子覆写（重播=同种子集收敛），
   行锁使后到覆写基于先到已提交值执行
5. 不选 UNIQUE(user_id) 迁移：迁移+schema 快照导出+存量去重超 P4 卡面（与 451/457 同判）

## 4. 测试面（零回退）

- 新增 `tests/unit/test_guest_seed_streak_wiring.py` **3 passed**：
  ①`firstbuild_id_deterministic_shared_with_engine`（确定性 id + engine 交叉读单行）
  ②`replay_overwrites_converging_values`（覆盖写语义保留钉子，修前亦 GREEN=语义未变）
  ③`concurrent_firstbuild_single_row_convergence`（两会话 barrier 并发形态，**修前 RED
  双行、修后 GREEN 单行**——本机对修前代码实跑复证）
- 回归全绿（SECRET_KEY 一次性 env + 隔离 worktree 无 .env，演示库守卫三选一之 2）：
  - guest_seed+streak unit **46 passed**（含新 3）
  - achievement+inventory+shop unit **70 passed**
  - services 层 guest_seed+achievement **38 passed**
  - tests/e2e **35 passed**
  - guest/邻域 api+auth **33 passed**
  - 合计 **222 passed 全绿**
- 既有基线（非本批引入）：`tests/integration/` shop/achievement 四文件在隔离 worktree
  为 TEST-DBGUARD 夹具守卫 ERROR（集成夹具按 conftest 自述需 **Alembic 迁移后真库**，
  "assume they already exist from migrations"）；指到一次性库 wt766_race 复跑为
  UndefinedTableError（push_preferences 等迁移面表缺失）——main 上该面因演示库会话门
  整体拒绝运行，属环境前置缺口，与本卡改动无关（改动文件未被这些测试导入）

## 5. mypy / ruff

- mypy app：**worktree 91 = main 91**（error 明细逐条 sort 后 diff **完全一致**），
  与卡面基线 91 吻合；触达文件 `guest_seed_service.py` 转递闭包错误集与 main 逐字节
  相同、自身 0 错
- ruff check 触达两文件 **All checks passed**；`ruff format --check` 漂移 hunks
  **27 = main 28 − 1**（本函数重写消去既有漂移 hunk 1 个，新增代码零格式偏差——
  初稿 3 处新漂移已按 format 口径修正后复验；既有漂移不重排纪律遵守）

## 6. 台账动作

- **V3-FIX-467 → FIXED@<修复 commit>**（运行级实证补全：真 PG 三层红→绿，
  覆盖写语义按协调方裁决保留并加锁）
- **V3-FIX-479 → FIXED@<修复 commit>**（触发面收敛修正随行保留；409 残留以本行修后
  口径收敛——触发面=跨访客共享 friend 行每次登录重播，非「同用户双端重放」）
- 新发现：**零登记**（498/499 grep 复核空闲不虚占——本批顺审发现的 integration
  夹具需迁移库前置缺口属已知环境基线，非产品缺陷，不占号）
- `scripts/devtools/ledger_union_merge.py --verify`：零 FAIL（结果见提交记录）

## 铁律自检

- 未伪造：三份 log 均本机真 PG 16.15 实跑 tee 原样；服务级 prefix RED 跑的是实现前
  的真实代码（worktree 编辑前快照，非 mock 非 stub）。
- 一次性 PG 角色/库 `wt766_scratch`/`wt766_race` 本验证自建，验证完成后 DROP，未触
  sparkle 业务库数据；未动运行栈/.env；main 仓未提交脏状态未触碰。
- 路径先 find/grep 亲证；未 push。
