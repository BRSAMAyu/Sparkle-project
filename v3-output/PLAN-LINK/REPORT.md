# PLAN-LINK · plan→task 关联链补齐 — 施工报告

> 2026-09-22 · Worker wt119 · 基于 main@2853ef5c · 禁 commit/push，产物仅本 worktree
> 关联：P1-4-DASHBOARD 遗留段（sprint 仪表盘计数错乱的根子）、NORTHSTAR-LOOP1 证据 C1b

---

## 0. 交付物

| 文件 | 说明 |
|---|---|
| `backend/app/services/task_service.py` | 运行时修复：`TaskService.create` 默认关联 + `resolve_default_plan_id` |
| `backend/alembic/versions/planlink_20260922_backfill_manual_task_plan.py` | 存量回填迁移（可逆，挂 463923b1704e） |
| `backend/tests/services/test_task_default_plan_link.py` | 服务面裁决语义红绿测试 ×12 |
| `backend/tests/unit/test_planlink_backfill_migration_sqlite.py` | 迁移 sqlite 隔离重放测试 ×4 |
| `changes.patch` | 以上四文件合并 patch |

---

## 1. 创建路径盘点（摸底结论）

Task 模型 `plan_id` 可空（`app/models/task.py:99`）。全部 `TaskService.create` 调用方与直接 `Task(...)` 构造点逐一核过：

| # | 路径 | 位置 | plan_id 现状 |
|---|---|---|---|
| 1 | intake 计划 day 卡（planning_workflow） | `orchestration/planning_workflow.py:1159` | ✅ `plan.id` |
| 2 | intake 修复任务（repair） | `orchestration/planning_workflow.py:1385` | ✅ `plan.id` |
| 3 | intake（ExamSprintIntakeService） | `services/exam_sprint_intake_service.py:442` | ✅ `plan.id` |
| 4 | goal 分解 milestone 卡 | `api/v1/goals.py:216,238` | ✅ `plan.id`（goal 自动建 plan，SPRINT/GROWTH 按 goal_type） |
| 5 | **手动创建 API（POST /tasks）** | `api/v1/tasks.py:383` | ❌ 仅透传客户端 plan_id（UI 只在 plan 深链时带，日常入口为 NULL）→ **本卡修复** |
| 6 | omnibar 快建 | `services/omnibar_service.py:95` | ❌ 未传 → 本卡修复覆盖 |
| 7 | agent 建任务工具（聊天内 fallback，C1b 本尊） | `tools/task_tools.py:85,264,515` | ❌ 未传 → 本卡修复覆盖 |
| 8 | 错题衍生（模板实例化） | `services/error_pattern_template_service.py:155` | ❌ payload 无 plan_id → 本卡修复覆盖 |
| 9 | 错题专项修复 | `services/error_replan_bridge.py:1253` | ✅ `plan_id` |
| 10 | 复习补强（fail-safe remedial） | `services/task_feedback_service.py:555` | ✅ 继承源任务 plan_id（源 NULL 则 NULL，源头被本卡修复） |
| 11 | 前置复习插入（plan_adjustment） | `services/plan_adjustment_applier.py:360` | ✅ 继承源任务 plan_id |
| 12 | 复盘补强（adaptive_replanner） | `orchestration/adaptive_replanner.py:1021` | ✅ 入参 plan_id |
| 13 | 隐藏聊天控制任务 | `services/execution_service.py:2101` | 显式 None（**正确**——非学习任务，不属缺口） |
| 14 | 群任务→个人任务 | `services/community_service.py:2301` | ✅ 已有「默认关联最新 active SPRINT」先例（本卡裁决对其对齐） |
| 15 | 学习路径子任务 | `api/v1/learning_paths.py:575` | ❌ 未传 → 本卡修复覆盖（父任务 :737 有 plan.id） |
| 16 | theater 推演任务 | `services/theater/prediction_theater_service.py:3380,3407` | ✅ `plan_id` |
| 17 | card_protocol 单卡导入 | `services/card_protocol/card_snapshot_service.py:406` | 显式 `plan_id=None`（导入态语义，本卡保留——见 §2 显式边界） |
| 18 | card_protocol phase 结构导入 | `card_snapshot_service.py:602` | ✅ `new_plan.id` |
| 19 | card_protocol phase design | `phase_design_service.py:62` | ✅ `legacy_plan_id` |
| 20 | guest seed | `services/guest_seed_service.py:395,1944` | 直构 Task 不走 service（395 defaults 传参、1944 带 growth_plan.id） |

**缺口定性**：`plan_id` 缺失的路径全部收敛在 `TaskService.create` 的「未传 plan_id」分支——单点修复（service 层）即同时覆盖 5/6/7/8/15 五条手动族路径，无需逐路径改。orchestration 域仅 planning_workflow（已有 plan_id）与 adaptive_replanner（已有 plan_id），**未触碰 wt115 的面**（其修 orchestration/memory，本卡只动 `services/task_service.py` 数据层，零交叠）。

---

## 2. 关联默认裁决

**裁决依据（创建时上下文）**：用户在 active sprint plan 存续期手动建的学习任务，默认关联该计划；用户显式选择「不关联」可除外。

**UI 现状（已查）**：`mobile/lib/features/task/presentation/screens/task_create_screen.dart` 仅从路由 query param `planId` 取值（plan 详情深链），**无「关联/不关联计划」选择器**。按卡裁决执行「默认关联」并在此注明：**计划选择器/豁免开关属 UI 后续**（届时前端显式传 `plan_id=null` 即走「明确不关联」语义，后端已预留）。

**落地语义**（`TaskService.create` + `resolve_default_plan_id`）：

1. **优先级**：active SPRINT plan → goal plan（`goal_id` 非空的活跃计划）→ 保持 NULL（无计划不强行造）。
2. **多计划并存**：`is_primary` 优先、`created_at` 最新——逐字对齐 `community_service.py` 群任务认领的既有先例，不发明第二套规则。
3. **显式语义边界**：`TaskCreate` 显式传 `plan_id` → 一字尊重（intake/goal/修复类生成路径零影响）；显式传 `plan_id=None`（`model_fields_set` 含 `plan_id`）→ 视为「明确不关联」保持 NULL——card_protocol 单卡导入（盘点 #17）依赖此语义，被测试锁定。
4. **类型边界**：仅学习族（LEARNING/TRAINING/ERROR_FIX/REFLECTION）默认关联；SOCIAL/PLANNING/OCR 不关联（#13 隐藏控制任务的直构路径不受影响）。
5. **失败兜底**：解析异常 warn + 保持 NULL，**不阻断任务创建**（P1-4 教训：兜底正确优先）。
6. 默认关联后既有 `on_task_created` → PlanState 同步自动生效（既有 try/except 包裹），按计划维度的进度聚合对手动任务从此可见——即本卡的根治目标。

**P1-4 口径不变**：`sprint_task_ledger.sprint_ledger_condition` 读用户全域（不按 plan 收窄），回填/默认关联只会让 plan 域视图更准，账本权威源零改动。INTAKE-IDX 唯一索引谓词（plans 表）不涉。

---

## 3. 回填迁移

**文件**：`alembic/versions/planlink_20260922_backfill_manual_task_plan.py`，`revision=planlink_20260922`，`down_revision=463923b1704e`（合流头）。**合入前已验单头**：`alembic heads` → `planlink_20260922 (head)`；`tests/test_migrations_single_head.py` + `test_alembic_chain_linearity.py` 全绿。dev 库 `alembic_version` 实测停在 `463923b1704e`，本迁移可直接落位。

**回填条件（从严，四条全满足）**：
1. `task.plan_id IS NULL` 且任务未软删；
2. 同 user 存在**恰好一个** active、未软删的 SPRINT 计划（多个活跃冲刺并存=归属歧义，宁缺勿错不回填）；
3. 任务创建时间在计划期内：`task.created_at >= plan.created_at`，且 `plan.target_date` 非空时 `created_at::date <= target_date`（过期计划不吸收 target 之后的任务）；
4. 仅 SPRINT 域回填——goal plan 回落只在运行时默认关联生效（迁移侧只做无歧义可精确判定的域）。

**可逆性设计**：窗口条件与 intake day 卡落窗完全重叠，按窗口反推 downgrade 会误伤 intake 原生任务——故 upgrade 在回填行的 `guide_json` 写 `plan_link_backfill` 标记（与 pause_state 等运行时键同级共存），downgrade **只处理带标记的行**且 plan_id 仍等于标记值才清空（防覆盖迁移后重新挂靠），随后剥标记。零 schema 变更，round-trip 后 schema 与数据语义均还原（测试锁定）。逐行 Python 判定 + 绑定参数更新，PG（JSONB 显式 CAST）/SQLite 双方言可移植，重放幂等。

**存量统计（dev 库 sparkle 只读快照，2026-09-22）**：

| 指标 | 值 |
|---|---|
| 全域未删任务 | 1390 |
| NULL plan_id 任务 | 25（全部为学习族类型） |
| 唯一 active SPRINT 的用户 | 193 |
| 多 active SPRINT 的用户 | 15（其 NULL 任务不回填，宁缺勿错） |
| **满足从严回填条件 → 预计回填行数** | **5**（全部落在有 target_date 的窗口内） |

> 注：25 个 NULL 任务中仅 5 行满足全部从严条件——其余属无活跃冲刺/多冲刺歧义/窗口外，按「回填只准不错」原则放弃；这些用户此后新手动任务由运行时默认关联覆盖。

---

## 4. 红→绿统计

| 阶段 | 命令（绝对路径） | 结果 |
|---|---|---|
| 基线（改前） | `pytest tests/api/test_task_*… tests/test_plan_task_*… tests/api/test_plans_api.py tests/test_migrations_single_head.py`（13 文件族） | **166 passed** |
| **红**（临时还原旧行为，单文件粒度变异+还原） | `pytest tests/services/test_task_default_plan_link.py` | **5 failed / 7 passed**（默认关联断言全红，显式/NULL 兼容断言过——与旧行为一致，红得干净） |
| **绿**（修复恢复后全量） | 基线 13 文件 + `test_planlink_backfill_migration_sqlite.py` + `test_alembic_chain_linearity.py` + `test_task_default_plan_link.py` | **185 passed / 0 failed** |
| 风格 | `black --check -l 120` + `ruff check`（4 个改动文件；task_service.py 既有漂移不动，**我的新增 hunk 零新增违规**） | clean |

迁移单测覆盖：窗口内回填+标记、计划前/target 后/多冲刺歧义/goal-only/软删五类不回填、intake 原生行 round-trip 原样存活、幂等重放、零新表。

---

## 5. 冲突面声明

- **wt115（orchestration/memory）**：本卡只动 `services/task_service.py` + 新增迁移/测试；orchestration 域两处创建点（planning_workflow/adaptive_replanner）本就带 plan_id，未改。零交叠。
- **wt118（mobile 设计）**：本卡零 mobile 改动；UI 计划选择器留作后续卡（§2 已注明后端预留语义）。
- **INTAKE-IDX**：谓词在 plans 表，本卡未触 plans schema。
- 迁移链：单头挂在 463923b1704e 之后，单头守卫测试随 patch 交付。

## 6. 收工核查

- [x] 修改仅在自己 worktree（`/Users/brsama/code/GitHub/Sparkle-sysrev/wt119`）；主仓只读未触碰
- [x] 未 commit/push；交付物 = `v3-output/PLAN-LINK/{changes.patch,REPORT.md}` + 4 个工作树内代码/测试文件
- [x] 本地生成的 `backend/app/gen/`（gitignored 构建产物，proto 与基线无漂移用 grpc_tools 本地生成）随 worktree 生命周期回收
- [x] `/tmp/wt119_head_task_service.py` 探针文件已删
- [x] 未起任何独立端口进程/模拟器/浏览器实例（全程 LIGHT：pytest + 只读 psql）；swap 空闲 1.27G、load ~3，纪律内
- [x] dev 库全程只读 SELECT（含 alembic_version 读取），零写入
