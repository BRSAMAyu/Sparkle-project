# V4-I01｜目标Episode接续读模型（`episode_resume_view.v1`）· diff_or_evidence_only

执行：wtI01（分支 `agent/v4/i01`，自 main@`1a53b8c3` 开出）· 2026-09-28 · 纯 backend 读模型，零 HEAVY，零模型调用，无 UI。

## 1. 一句话

**接续视图 = goal/task/run/outcome 既有权威行的只读投影**：目标+任务上「上次到哪（last_confirmed_step）、下一步（pending_human_step）、为什么是现在（why_now，对接 `action_plan.v1.1` 字段位）、最近可信成果（last_valid_outcome，D-02 TruthClass 全 5 值 1:1）、在途 run（run_ref）」的版本化聚合，带 `expires_at` 过期语义（过期只许说明不确定性、不强行接续）与 `freshness`（钉 context receipt ref + memory epoch，epoch 变即 stale 重算）——**零新表、零写路径、零第二任务真值**。

## 2. 交付物（真实路径）

| 文件 | 角色 |
|---|---|
| `backend/app/core/episode_resume_view.py` | 契约层（stdlib+既有权威 import）：`EPISODE_RESUME_VIEW_SCHEMA_VERSION="episode_resume_view.v1"`、封闭词表（`RESUME_DEGRADE_REASONS` 5 值 / `WHY_NOW_CONFIDENCE_BANDS` 4 值 / `STEP_REF_SCHEMES` / `TRUTH_CLASS_VALUES`=D-02 全 5 值复用）、`normalize_why_now`（§4.1 字段级降级判定）、`assemble_resume_view`（纯函数装配 + fail-loud 输入门）、`validate_resume_view_shape`（冻结键集检查）、`resume_view_stale_reason`（过期/epoch 陈旧可判定出口） |
| `backend/app/services/episode_resume_service.py` | 聚合器（唯一 IO 入口，只读）：`EpisodeResumeService.build_resume_view` —— task/goal/plan 存在+属主门 → goal 终态/绑定不一致校准门 → 在途 run（X-05 `ACTIVE_RUN_STATUSES`）→ last_confirmed_step（subtask 完成戳优先/task 级兜底）→ pending_human_step（X-01 `action_plan_projection` 统一读侧门）→ why_now（v1 行=null 不臆测回填）→ last_valid_outcome（`OutcomeLedgerService.query` 公共读面有界扫描，correlation.task_id 匹配）→ memory epoch（`MemoryService.get_memory_epoch`，C-07 读失败按 0） |
| `backend/app/api/v1/episode_resume.py` | REST 入口 `GET /episode-resume/tasks/{task_id}`（route-tier: authed；404 不泄露存在性；降级类型化 200） |
| `backend/app/api/v1/router.py` | +2 行注册（import + include_router，纯增量） |
| `backend/gateway/internal/handler/proxy_routes.go` | +12 行 `/episode-resume` 代理组（house `registerREST` 同款，Go 零业务逻辑——分层边界不变；BA-ROUTES parity 门要求） |
| `scripts/guards/check_rule_ba_routes_parity.py` | `GATEWAY_ONLY` 挂账 1 行（`registerREST` 裸组面；`visual-elements` 同款先例） |

## 3. 数据源映射（只接既有权威，铁律「不建第二任务真值」）

| 视图字段 | 权威来源（复用不复制） |
|---|---|
| `goal_ref` | `goals`（存在+未软删+属主；经 `tasks.plan_id→plans.goal_id` 既有链路或显式 goal_id） |
| `task_ref` | `tasks`（存在+未软删+属主） |
| `run_ref` | `agent_runs`（X-05 run 唯一持久真源；仅 `ACTIVE_RUN_STATUSES` 非终态，最新一条） |
| `last_confirmed_step` | `subtasks`（status=COMPLETED+completed_at 最新）→ `task://`（task.confirmed_at/completed_at 兜底）；`version_token` 复用 X-03 `action_command.version_token` |
| `pending_human_step` | X-01 ActionPlan 列经 `action_plan_projection` 统一读侧门（脏值/legacy → null 诚实降级）；词表 `CognitiveOwnership`/`ExecutionMode` import 不复制；COMPLETED/ABANDONED 任务恒 null（旧计划不强推） |
| `last_valid_outcome` | D-02 `OutcomeLedgerService.query` 公共读面（有界 3×100 页扫描，correlation.task_id）；`truth_class` 全 5 值 1:1 透传（demo 不排除，R1-C4）；无 → null，不造「练了 N 分钟」替代面 |
| `why_now` | `action_plan.v1.1` 字段位（B05 §4）投影：v1 行（无字段位）=null；子结构校验失败=字段级降级 null+WARN（§4.1）；过期=不当作当前原因复用 |
| `expires_at`/`freshness` | 服务端 TTL（默认 30min，风格对齐 X-03 `DEFAULT_PROPOSAL_TTL_SECONDS`；上限 24h）+ C-07 memory epoch + 调用方传入的 `context_selection://` receipt ref（receipt 本体归 B05 §2/后续卡，本卡只绑 ref，缺失→`context_receipt_missing` 不出视图） |

## 4. 验收对照（必须可失败 → 已失败过并修复，最终全绿）

| 卡面验收 | 结果 |
|---|---|
| 跨会话/进程重开恢复同一对象 | 满足：`tests/integration/test_episode_resume_cross_process.py` 双引擎文件级 sqlite 模拟双进程——重开后同权威+同输入 → 视图逐键相等（含 run/subtask 引用自持久真源恢复）；聚合零写行（DB 表集合 == ORM metadata，无第二真值表） |
| 已删对象不复活 | 满足：软删 task/goal 后重建 → `object_not_found`，视图不出（service+integration 双面） |
| 目标改变或版本过期时退回明确校准，旧计划不强推 | 满足：goal ∈ {completed,archived,cancelled} 或 task.source_refs `goal://` 与解析 goal 不一致 → `goal_changed_requires_calibration`（视图不出）；`expires_at` 过期 → `resume_view_stale_reason="expires_at_passed"`（§9 反例「过期自动接续」钉死为不可为）；epoch bump → `memory_epoch_changed` 重算 |
| 无历史时不造连续学习/理解分数 | 满足：无 outcome → `last_valid_outcome=null`；无 V3 计划 → `pending_human_step=null`；冻结键集检查保证不存在 progress/mastery/minutes 类字段位（`validate_resume_view_shape` + 测试钉死） |

## 5. 自测证据（真实命令与 exit code，详见 run_manifest.json）

- `pytest tests/unit/test_episode_resume_view_contract.py tests/services/test_episode_resume_service.py tests/integration/test_episode_resume_cross_process.py tests/api/test_episode_resume_api.py` → **56 passed，exit 0**
- `mypy app --ignore-missing-imports`（ratchet 同口径）→ **55 errors，与改前基线 55 持平（零漂移），episode_resume 相关 0 条**
- `ruff check app/` → **All checks passed**；改动文件 black(120) clean
- `go build ./...`（gateway）→ exit 0；`go test ./internal/handler/` → ok
- `bash scripts/run_all_rule_guards.sh` → **all rule guards passed (86 rules)**（AT 孤儿门经 REST 入口接线后 PASS；BA-ROUTES 经 gateway 代理组+挂账后 PASS）
- 邻接回归：action_plan/outcome_ledger/run_steps 相关 141 tests passed

## 6. 红线自证

- 纯 backend（含 backend/gateway 桥接层）；零 mobile 改动；零 HEAVY；零模型调用（读模型纯确定性聚合）。
- 无迁移（ Alembic 零新增头，DB-HEAD guard PASS）、无新表、无 `*/gen/` 手改（proto-gen 产物 gitignored，未入库）。
- 契约行为测试钉死：词表扩展/字段漂移在 `validate_resume_view_shape`/封闭词表断言处 fail。

## 7. 边界与既知限制

见 `limitations.md`（goal 内容级变更检测受限于无 goal 版本绑定列、why_now 物理落点未绑死故经 `getattr(task,"why_now",None)` 前向兼容读取、receipt 本体未实现故入口只绑 ref 等 5 项）。
