# INTAKE-IDX：intake 同目标并发窗口根治报告

- 卡：**INTAKE-IDX**（INTAKE 卡申报残留：同目标并发 intake 仍有查询-创建竞态窗口，根治 = 部分唯一索引）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt111`（基线 main@5d1df370）
- 交付物：`v3-output/INTAKE-IDX/changes.patch`（5 文件：2 改 + 3 新，+716/-11）+ 本报告
- 状态：完成，未 commit / 未 push；已验证 patch 在干净 HEAD（5d1df370）上 `git apply --check` 通过

## ① 索引定义（一句）

```sql
CREATE UNIQUE INDEX uq_plans_user_sprint_goal_active
    ON plans (user_id, subject, target_date)
    WHERE type = 'SPRINT' AND is_active AND deleted_at IS NULL;
```

键与谓词**精确对齐** INTAKE 卡幂等语义的同目标同一性 `(user, SPRINT, subject, exam_date, is_active, 未软删)`（即 `ExamSprintIntakeService._find_reusable_sprint_plan` 的查询条件）：

- `'SPRINT'` 是 `Enum(PlanType)` 的**成员名**——基线迁移与 gateway `schema.sql` 均为 `plantype AS ENUM ('SPRINT','GROWTH')`（无 values_callable 时 SQLAlchemy 持久化成员名），PG 与 SQLite 字面量一致；
- **GROWTH 被谓词排除**（intake 幂等语义只定义在 SPRINT 上，收敛半径最小化）；`subject`/`target_date` 为 NULL 的行不参与（PG/SQLite 唯一索引中 NULL 互异）——224 个活跃冲刺计划中 209 个键列含 NULL（历史种子/测试用户），零影响；
- 模型侧 `app/models/plan.py` 以**同一谓词**声明 `postgresql_where` + `sqlite_where`（SQLite 测试基座 create_all 后语义一致，不再依赖 sr8r2g2 时代"NULL 互异退化等价"的间接论证），模型元数据与迁移一字不差。

## ② 存量现状与清理策略

### 现状计数（2026-09-22 执行前只读查询，真实 DB 未做任何写操作）

违反组判定查询（PG/SQLite 通用，与迁移内 `_count_duplicate_groups` 同源）：

```sql
SELECT user_id, subject, target_date, COUNT(*) AS active_dup
FROM plans
WHERE type = 'SPRINT' AND is_active AND deleted_at IS NULL
  AND subject IS NOT NULL AND target_date IS NOT NULL
GROUP BY user_id, subject, target_date
HAVING COUNT(*) > 1;
```

结果：**恰好 1 组违反**（LOOP1 时代双计划，与 INTAKE 卡残留描述吻合）：

| 保留裁决 | plan_id | name | created_at | tasks |
|---|---|---|---|---|
| **保留（最新）** | `866061a3-8098-414d-a114-131d615c889d` | 7天计网冲刺 | 2026-09-20 04:34:49 | 1 |
| 收敛（停用） | `358f50d5-b2a5-48bd-9c91-3ae9878956a1` | 7天计网冲刺 | 2026-09-19 06:27:24 | 1 |

- user：`ccd264a5-3dc0-4002-9def-40a6d77d0efe`，subject=计算机网络，target_date=2026-05-02
- 盘面：活跃冲刺计划 224 条（其中 209 条键列含 NULL，不受约束）；inactive/软删冲刺 5 条

### 清理策略：**保留最新**（裁决理由）

- 与服务层复用语义一致：`_find_reusable_sprint_plan` 即 `ORDER BY created_at DESC LIMIT 1`——幂等复用永远指向最新，收敛后该用户复跑 intake 得到的 plan 不变；
- 收敛动作是**非破坏性**的：旧者仅置 `is_active = false`（不删行、不改内容、不占配额——与配额语义天然一致），可随时人工恢复。

### 清理 SQL 上报段（**只上报，未执行**，主会话裁决）

迁移 `intakeidx_20260922` 的 `upgrade()` **已内置自动收敛**（先 SELECT 计数→UPDATE 收敛→再建索引，两套方言各有关现：PG 用 `DISTINCT ON`，SQLite 用 EXISTS 相关子查询），正常 `alembic upgrade head` 即安全通过。若主会话希望**在升级前人工预收敛**（效果与迁移内置收敛等价，可提前审计），可执行：

```sql
-- 预收敛（保留每组最新 active，旧者停用；幂等，可重复执行）
UPDATE plans
SET is_active = FALSE, updated_at = timezone('utc', now())
WHERE type = 'SPRINT' AND is_active AND deleted_at IS NULL
  AND subject IS NOT NULL AND target_date IS NOT NULL
  AND id NOT IN (
      SELECT DISTINCT ON (user_id, subject, target_date) id
      FROM plans
      WHERE type = 'SPRINT' AND is_active AND deleted_at IS NULL
        AND subject IS NOT NULL AND target_date IS NOT NULL
      ORDER BY user_id, subject, target_date, created_at DESC, id DESC
  );
-- 本库当前预期影响行数：1（即 358f50d5-b2a5-48bd-9c91-3ae9878956a1）
```

## ③ 服务层适配（闭环）

`exam_sprint_intake_service.py` 生成路径外包一层 try/except（**未触碰** INTAKE 刚合入的复用/生成主逻辑，纯增量适配）：

```
复用查询命中 → 复用（原 BP-7 顺序重放语义，不变）
复用查询落空 → 创建
                 └─ IntegrityError（撞 uq_plans_user_sprint_goal_active）
                      → rollback 清残渣 → 回查复用既有计划
                      → 回查为空（他因唯一冲突）→ 原样 raise 不吞错
```

- 失败点恒在 `PlanService.create` 的 commit（任务在建 plan 之后逐个创建，败者到不了任务步骤，无半成品残渣——`TaskService.create` 每任务独立 commit）；
- PG 侧与 `PlanService.create` 既有配额 advisory 锁正交互补：锁串行化配额检查，索引封死同目标重复，各管一段。

## ④ 红→绿 + 回归统计

### 本卡新测试（5 个，全绿；先红后绿）

| 测试 | 断言 | 结果 |
|---|---|---|
| `test_intakeidx_plans_sprint_goal_unique_migration_sqlite.py::…converges_and_enforces…` | 迁移在 sqlite 基座重放：存量双计划收敛保留最新、谓词边界行（inactive/软删/GROWTH/NULL 键/他用户）零误伤、索引落上后同目标双活跃行被拒、inactive 形态可共存、downgrade 后索引移除恢复可插 | PASS |
| `…::…noop_on_clean_data…` | 无存量违反时收敛零操作、索引照常生效 | PASS |
| `test_exam_sprint_intake_concurrency.py::test_plans_sprint_goal_partial_index_blocks_duplicates` | 模型元数据级索引语义：同目标活跃双行拒、停用/软删后可再建、GROWTH/NULL 键共存（8 行终态断言） | PASS |
| `…::test_intake_falls_back_to_reuse_when_concurrent_plan_wins` | 确定性冲突注入（竞态败者视角）：创建撞索引 → 回查复用赢家 plan、零残渣（plan=1、task=0）、无 500 | PASS |
| `…::test_concurrent_intake_same_goal_creates_exactly_one_plan` | **N=6 路完整 intake（真实创建路径）齐步竞态**：栅栏保证全部通过复用查询（全查空）后才放行创建；断言 DB 恰 1 个 sprint plan、6 路全拿同一 plan_id、上报任务 id 无幻影且归属该 plan | PASS（连跑 3 次稳定） |

开发中红→绿实证：栅栏版竞态测试首轮曾红（Day-1 包不一致 `{(task,), ()}`——败者在任务落库中途回查复用），证明竞态窗口被真实复现且索引+回退生效；plan 先提交/任务逐个提交属既有创建路径的提交粒度，plan 身份才是本卡不变量，断言据此校准。

### 回归（pytest 全绝对路径，SECRET_KEY 内联注入，未落任何 .env；解释器只读借用 wt108 venv）

| 套件 | 结果 |
|---|---|
| exam_sprint 全家（intake 3 + **本卡并发 3** + review 11 + diagnose_api 1 + diagnostic_service 8 + policy 3 + api 7 + dashboard 2） | **38 passed**（INTAKE 基线 35 零回退 + 新 3） |
| 迁移 sqlite 重放全家（x07/d03/understanding_depth/action_plan + 本卡 intakeidx） | 全 passed |
| C2 intent 唯一（plan_execution_record，同型先例） | passed |
| plan/task/north_star/dashboard 重度用例（progress_update/task_service/task_tools/north_star_metrics 等） | 142 passed |
| 计划种子风险面扫描（16 个会 seed SPRINT+subject+target_date 的 unit 文件） | 147 passed |
| sprint 命名套件（pack_loader/pack_registry/galaxy_mastery） | 47 passed |
| plan_progress_update 补充批 | 9 passed |
| integration/aurora/e2e 批（8F/34P/3E）与 theater/stage33/stage35 批（3F/50P） | **与基线克隆（干净 HEAD 5d1df370）逐批比对完全一致**——存量失败，与本卡零关 |
| 风格 | ruff check、black --check(120) 双绿（本卡 5 文件） |

### 红线面

- **`alembic heads` 单头** ✅：`intakeidx_20260922 (head)`（守卫 DB-HEAD 亦报 `✅ alembic 单头`）；链 `x07_20260921 → intakeidx_20260922`，upgrade/downgrade 在测试库跑通（见迁移重放测试）。
- **exam_sprint 套件零回退** ✅（38 passed）。
- **intake 主逻辑零改动** ✅：`_find_reusable_sprint_plan`/`_bundle_from_existing_plan`/生成路径原样，仅外层增 try/except（+37 行含注释）。
- API 契约零变化：`ExamSprintIntakeResponse/LaunchPayload` schema 未动；并发败者的 launch 载荷形状不变（plan_id 指向同一 UUID）。

## 冲突面 / 待主会话事项

1. **gateway `schema.sql` 将暂时落后**：索引已进迁移与模型元数据，但 schema.sql 是自动导出快照（硬规则：手改无效），需主会话合入后跑 `make sync-db` 刷新导出与 SQLC。本卡无 Docker dump 管线权限，未动。
2. **存量清理裁决**：迁移内置自动收敛（升级即生效）；若需预收敛/人工复核，用上方上报 SQL（预期影响 1 行）。
3. **Day-1 包瞬时可见性**（非阻塞，既有粒度）：并发败者回查复用时可能拿到空/部分 Day-1 任务列表（plan 先提交、任务逐个提交）。plan 身份不变，北极星 intake 指标按 plan_id 去重不受影响；如需彻底闭合可在后续卡把"plan+Day1 任务"改为单事务提交。
4. **两处存量问题复证**（与本卡无关，clone 基线法证明）：integration/aurora/e2e 批与 theater/stage35 批在干净 HEAD 上失败形态完全一致；BG 守卫（proto 跨语言生成物缺失）在 fresh worktree 恒红，同样基线复现 exit=1。
5. `Makefile` 的 `db-migrate` heads 计数正则 `^[0-9a-f]` 不匹配现头 `x07_*`（'x' 非十六进制字符）——本卡新头 `intakeidx_*` 恰好匹配；该正则脆弱性建议另行立卡。

## ⑤ 收工核查

- [x] worktree 内无构建产物入库：未产生 `mobile/build`、`.dart_tool`、venv、node_modules；`backend/app/gen`（gitignored 测试基座生成物，自主仓只读 rsync，3 个自引用 symlink 已换真实文件副本）不入库
- [x] `/tmp` 自清：`/tmp/wt111-intakeidx-baseline`（基线克隆）、`/tmp/intakeidx_debug.db`、`/tmp/bg_out.txt` 已删除
- [x] 未起模拟器 / Gradle / 浏览器实例，无 HEAVY 任务；pytest 串行跑完即退，无遗留进程
- [x] 未创建任何 `.env`（SECRET_KEY 全部内联 env 注入）
- [x] 主仓只读未动：仅 rsync 读出 `backend/app/gen`；真实 DB 仅只读 SELECT（清理 SQL 未执行）
- [x] git status 干净度：仅 2 个预期修改文件 + 3 个新文件 + `v3-output/INTAKE-IDX/`（本卡产物）
- [x] 未 commit / 未 push
