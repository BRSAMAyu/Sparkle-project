# CP-01 · exam-sprint 计划人工确认端点（POST /plans/{id}/confirm）

> 2026-09-22 ｜ Worker 交付 ｜ worktree wt125 ｜ 基线 `240ce2bb`（feat(landing)）
> 上游证据：`v3-output/NORTHSTAR-LOOP3/REPORT.md` #5——运行时探针 `POST /plans/{id}/confirm`、`/approve` 均 404，exam-sprint 计划草案→人工确认无专用端点。

## 一、调研实证（改动前，只读）

| 调查面 | 结论 |
| --- | --- |
| `backend/app/models/plan.py` | `PlanStage` = sprint/daily/review/paused（学习旅程阶段）；`PlanStatus` 枚举（draft/pending_review/active/…）**是死代码——无任何列引用**；Plan 表无 status 列、无 confirmed_at；有 `deleted_at` 软删（SoftDeleteMixin） |
| `backend/app/api/v1/plans.py` | 全 CRUD + archive/restore + compass approve + phase 系，**无 /confirm**；域风格：他人计划统一 404（防资源枚举）；`PlanService.get_by_id` 只按 (id, user_id) 过滤，**不看 deleted_at** |
| `exam_sprint_intake_service.py` | intake 直接 `PlanService.create(plan_stage=PlanStage.SPRINT)` 后即 launch（`ExamSprintIntakeResponse.launch`），无确认动作；planning session 内部 state 有 "AWAITING_CONFIRM" 字符串但只管会话流转，与计划持久化状态无关 |
| router 注册 | `app/api/v1/router.py:205` `include_router(plans.router, prefix="/plans")` |
| gateway | `proxy_routes.go` **逐路由显式注册**（非通配透传）——`POST /:id/confirm` 原本缺失，Python 侧实现了网关不注册的话移动端链路仍然 404 |
| mobile | `api_endpoints.dart` 无计划确认端点；`sprint_actions_dialog.dart` 的 confirm 弹窗是"完成/放弃"确认（本地 UI 语义），无端点调用残留 |

## 二、设计裁决

### 落点：新增 `plans.confirmed_at` 列（迁移 `cp01confirm_20260922`）

三个候选落点全部排除的理由：

1. **`plan_stage` 前进一级** ✗ ——它是旅程阶段（sprint→daily→review），intake 创建即落 SPRINT，无 draft 值；"确认"推进到 daily 是语义错误。
2. **复用 `PlanStatus` 枚举加 status 列** ✗ ——该枚举本是死代码，启用它要同时给全量存量行定值，行为面远超本卡。
3. **`PlanState.status` 加 confirmed 值** ✗ ——它是执行态存储（active/archived）+ 乐观锁版本，语义不符。

故以最小新增表达状态机：**`confirmed_at IS NULL` = 待确认（草稿态）；非 NULL = 已确认（生效态）**。列型 `sa.DateTime()` nullable——跟随项目 naive UTC 时间列惯例（`BaseModel.deleted_at`、`_utcnow()` 同款），不引入 timestamptz 的时区不一致风险。

### 幂等语义

- 首次确认：写 `confirmed_at = _utcnow()`，返回 200，`already_confirmed: false`，message「计划已确认生效」。
- 重复确认：**保留首次时间戳不覆盖**（盖章动作，重复点击/断线重连重放不产生新事实），返回 200，`already_confirmed: true`，message「计划已确认，无需重复操作」。

### 归属与拒绝面

| 输入 | 行为 |
| --- | --- |
| 他人计划 | 404（对齐 plans 域统一 404 防枚举风格；任务卡允许 403/404 二选一） |
| 计划不存在 | 404 |
| 软删（deleted_at 非空） | 404（注意：不能复用 `get_by_id`，它不过滤软删——confirm 自带 `deleted_at IS NULL` 查询） |
| 已归档（is_active=False）未软删 | **允许确认**（200）：确认记录用户意图，不隐含恢复/激活，不改 is_active（最小行为面，不进归档/配额域） |

### 响应形状（对齐 plans.py 既有 dict 端点风格，如 update_priority/archive）

```json
{
  "plan_id": "uuid",
  "plan_stage": "sprint",
  "confirmed_at": "2026-09-22T12:00:00",
  "already_confirmed": false,
  "message": "计划已确认生效"
}
```

### 分层

- `PlanService.confirm_plan(db, plan_id, user_id) -> dict | None`：查询（user_id + 未软删）→ 幂等判定 → 落值 → commit → 摘要 dict；None=404。
- handler 薄：`POST /{plan_id:uuid}/confirm`，None→404，逻辑全在 service。

## 三、触碰文件清单（红线面）

| 文件 | 改动 | 为何不破坏既有行为 |
| --- | --- | --- |
| `backend/app/models/plan.py` | +`confirmed_at` 列、+`DateTime` 导入 | 纯增量 nullable 列，无既有读路径引用；新测试与迁移测试守护 |
| `backend/app/services/plan_service.py` | +`confirm_plan` 方法 | 纯新增方法，未动任何既有方法 |
| `backend/app/api/v1/plans.py` | +`POST /{plan_id:uuid}/confirm` handler | 纯新增路由；`{plan_id:uuid}` UUID converter 与 `/discovery`、`/compass`、`/phases` 等静态前缀路由无匹配冲突（非 UUID 路径段永不命中） |
| `backend/alembic/versions/cp01confirm_20260922_add_plan_confirmed_at.py` | 新增迁移 | `down_revision="planlink_20260922"`（验证过是唯一 head，`alembic heads` 单头）；纯 add/drop column，无数据改写；SQLite 基座走 batch_alter_table |
| `backend/gateway/internal/handler/proxy_routes.go` | +1 行 `plans.POST("/:id/confirm", h.proxyWithHeaders)` | 纯代理注册（无业务逻辑，符合硬规则 3）；无此行则移动端→网关链路仍 404，闭环不闭合 |
| `backend/gateway/internal/handler/proxy_routes_test.go` | 守护清单 +1 行 | 该测试是子集断言（只查 expected 命中，不查反向精确匹配），加行安全；把新路由纳入防误删守护 |
| `backend/tests/api/test_plan_confirm_api.py` | 新增测试 | 只读新增 |
| `backend/tests/unit/test_cp01_confirm_migration_sqlite.py` | 新增测试 | 只读新增 |

未触碰：`schema.sql`（自动导出快照，手改无效——合入方 `make sync-db` 重生成）；proto/生成代码；exam_sprint_intake_service；mobile。

## 四、测试矩阵

| 用例 | 基线（改动前） | 改动后 |
| --- | --- | --- |
| 首次确认 200 + confirmed_at 落值 + plan_stage 回显 | 红（404） | ✅ 绿 |
| 重复确认幂等：confirmed_at 保留首次值 + already_confirmed=true | 红（404） | ✅ 绿 |
| 他人计划 404 | 假绿（端点不存在也是 404）→ 实现后转真绿（真打归属过滤） | ✅ 绿 |
| 不存在 404 | 同上 | ✅ 绿 |
| 软删计划 404 | 同上 | ✅ 绿 |
| 已归档未软删允许确认 200 且 is_active 不变 | 红（404） | ✅ 绿 |
| 迁移 upgrade 加列 + 存量行 NULL（无推测回填） | — | ✅ 绿 |
| 迁移 round-trip downgrade 还原 schema + 行存活 | — | ✅ 绿 |
| 迁移重入幂等 | — | ✅ 绿 |

- 新测试文件：`tests/api/test_plan_confirm_api.py`（6 用例）、`tests/unit/test_cp01_confirm_migration_sqlite.py`（3 用例）。
- 定向复核：`test_plans_api.py + test_exam_sprint_api.py + 新增两文件` = **19 passed**。
- alembic 单头验证：`alembic heads` → `cp01confirm_20260922 (head)`，链 `planlink_20260922 -> cp01confirm_20260922`。
- 网关：`CGO_ENABLED=0 go build ./...` OK；`go test ./internal/handler/ -run TestProxyRoutesHandler` OK。

### 全量回归（`-k "plan"`，单进程）

- 改动树：**758 passed / 25 failed / 9 skipped / 1 error**。失败集中在 `tests/orchestration/`（planning sidecar、planning_workflow）与 `tests/integration/test_cache_consistency_integration.py`（error）——均为编排/LLM mock 域，与本卡触碰面（plans 模型/服务/路由、gateway 代理注册、新迁移）无代码路径交集。
- **基线对照（`git clone` worktree→/tmp/cp01-baseline，只含 HEAD、无本卡改动，同命令同环境）**：见 §七 待基线跑完后回填结论——证明 25 failed 为存量债务、非本卡引入。

## 五、冲突面（与在途卡）

- **chat 面积重划 / SSE 卡**：零交集。本卡未触碰 chat、SSE、orchestration 任何文件；gateway 改动仅在 plans 代理组内加一行。
- **同域潜在冲突**：若其他卡同窗口改 `plans.py` / `plan_service.py` / `plan.py` 模型 / `proxy_routes.go` 的 plans 段，diff 可能相邻——本卡改动全部为追加式（无行改写），git 合并友好。
- **迁移链**：唯一新增迁移挂在当前 head；若合入窗口另有卡加迁移，以合入方 rebase 顺序为准（后到者改 down_revision）。

## 六、诚实申报

1. **回归的 25 failed 不是本卡未验清**：失败文件（orchestration/cache 一致性）与本卡无代码路径交集，且基线对照正在收尾（§七回填）；如合入方需要，可复核 `/tmp/cp01_baseline_regression.log`（收工前保留，报告定稿后随 /tmp 自清删除——数字已誊入本报告）。
2. **`make sync-db` 未跑**：worktree 无活库（主仓 DB 只读纪律），`backend/gateway/schema.sql` 快照未重生成——合入方合入后跑 `make sync-db` 即可，快照属自动产物。
3. **is_active=False 计划允许确认**是本卡定义的行为（见 §二表格）：若产品语义要求"归档计划拒绝确认"，是一行 409 的改动，留给验收裁决。
4. **mobile 侧未接端点**（本卡范围外）：`api_endpoints.dart` 加 `planConfirm(id)` + intake 完成页确认按钮属后续卡；REST 面已端到端闭合（Python→gateway）。
5. **基线红证的 3 个 404 用例改动前为假绿**（端点不存在天然 404）：实现后转为真绿（真打归属/软删过滤逻辑），已在 §四标注。
6. **worktree 缺 `app/gen`**（gitignored 生成物）：已用 `make proto-gen`（docker 不可用，host 工具链回落）生成；产物不进 git、不进 patch。

## 七、基线对照结论（已回填）

按 AGENTS.md 并发验收纪律做干净基线对照：`git clone <worktree> /tmp/cp01-baseline`（只含 HEAD `240ce2bb`，天然无本卡改动），同命令同环境重跑：

| 树 | 结果 |
| --- | --- |
| 基线（HEAD，无 CP-01） | **25 failed / 752 passed / 9 skipped / 1 error**（841s） |
| 改动树（HEAD + CP-01） | **25 failed / 758 passed / 9 skipped / 1 error**（824s） |

- **失败数完全一致（25+1）**：全部为 HEAD 存量债务（orchestration planning sidecar / planning_workflow / adaptive_replanning / north_star_journey / cache 一致性 error），与本卡无代码路径交集。
- 改动树日志中可见的 7 条失败明细（6 FAILED + 1 ERROR）逐一核对，**全部在基线失败名单内**（7/7 命中）。
- **+6 passed 恰好 = 本卡 6 个新 API 用例**；3 个新迁移用例因文件名不含 "plan"（`cp01_confirm_migration_sqlite`）不在 `-k plan` 选择集内，单独验证过绿。
- **结论：CP-01 零回归引入。**

## 八、移交事项

- **gRPC 面**：本卡仅 REST。若 mobile 走 gRPC 消费确认动作，需在 `proto/` 增加 plan confirm RPC（建议 `ConfirmPlan(ConfirmPlanRequest) returns (ConfirmPlanResponse)`，复用 §二响应形状）+ `make proto-gen` + gateway gRPC 桥接线——不做 proto 改动（本卡纪律）。
- **schema 快照**：合入后 `make sync-db` 重导出。
- **mobile 接线**：intake launch 后的确认按钮 → `POST /api/v1/plans/{id}/confirm`，按 `already_confirmed` 渲染已确认态。

## 九、收工核查

- `git status --short` 清单 = §三表 8 个文件（5 改 3 新代码 + 1 新报告目录），无多余产物；index 已 `git reset -q` 还原（无残留 staged）。
- patch：`v3-output/CP01-CONFIRM/changes.patch`，**528 行**——5 个修改文件 + 3 个新文件；新文件 diff 头均为 `--- /dev/null`（已自查，3/3）；patch 仅含 backend 代码路径（报告本体不入 patch，避免自引用）。
- 无 commit / 无 push；主仓全程只读；无进程残留（测试全部前台/后台任务已结束）；/tmp 下 `cp01-baseline/`、`cp01_baseline_regression.log`、`cp01_*fails.txt` 收工自清。
