# GUARD-DEBT 治理守卫存量债清偿 — 报告

- Worker: wt95（wt95-v3，基线 main@fd85f9b5）
- 日期: 2026-09-22
- 交付物: `v3-output/GUARD-DEBT/changes.patch`（9 文件，+50/−4）+ 本报告
- 纪律: 未 commit/push；守卫检测逻辑零改动（仅加合法 EXPECTATIONS 数据 / ledger 登记 / 豁免注释）；gateway 代理路由带测试

## 基线

开工全量守卫实跑 7 红：任务卡 5 项存量债（AS / BI / GOV-DATA-MIN / BJ / BA-ROUTES）+ 2 项**环境缺生成物**（AQ：`No module named 'app.gen'`；BG：gen 产物缺失——`*/gen/` 不入库，worktree 未跑过 `make proto-gen`）。收工全量 **73/73 绿**（`all rule guards passed (73 rules)`）。

---

## 1. AS001 — 5 个 attached field（实为 context_builder.py，非 profile_context_service.py）

**判断**：守卫违规行号 649/802 实际来自 `backend/app/orchestration/context_builder.py`（守卫的 AS001 消息模板固定打印 profile_context_service 路径，属显示瑕疵；扫描面 = profile_context_service 的 `context.*=` + context_builder 的 `payload["*"]= `）。逐字段读装配与消费链后分两类：

**修法 A — 补 expectation 断言**（`_attach_stage34_memory_context`，方法级 ignore 会连带停用 active_goals/episodic_memories/last_session_mood/recent_corrections 四个已 enforce 字段，不可接受）：

| 字段 | expectation | 依据 |
|---|---|---|
| `memory_selfcheck` | CONTEXT_BUILDER token `payload.get("memory_selfcheck")` | M-05 SelfReCheck payload 在同文件被 C-08 漏斗捕获**回读**（internal_only → selfcheck_dropped_refs 归因）——非赋值位真实读取点，删消费即 AS002 红 |
| `context_funnel_memory` | CONTEXT_BUILDER token `payload["context_funnel_memory"]` | 真实下游消费者是 `agents/standard_workflow.py:2214` 统一 context funnel 记录（C-08），不在守卫 consumer 三文件（routing_engine/prompts/context_builder）内；**不能**改 consumer_targets（那属检测逻辑）。按既有 `aurora_stage39_modes` 先例（其 CONTEXT_BUILDER token 也只命中装配面）钉装配接线，防止字段被静默改名/移除 |

**修法 B — 合理 ignore**（`_attach_experience_memory_context`，方法上 3 行内 `# rule-as: ignore`，恰好只覆盖该方法 3 字段、零连带）：

- `experience_memories`：memory 桶 manifest 登记面（`context_sources.py` USER_CONTEXT_FIELD_BUCKETS + LATE_STAGE_WRITERS，WIRING-1/FIX-33）——prompts.py 无渲染点（全文件 grep 仅 decision_context.experience_mode）、standard_workflow 仅回读 episodic；消费面在守卫 consumer 集之外。
- `experience_memory_meta` / `experience_memory_selfcheck`：CONTROL_BUCKET 观测面，经 `agents/standard_workflow.py:2219` C-08 漏斗记录消费（experience_meta），非 prompt/routing 面。

ignore 理由全文写在 context_builder.py 该 def 上一行（含消费指向），后续接 UI 渲染时可删 ignore 改 expectation。**未无脑 ignore**：两个有真实消费点的字段钉了 expectation，三个守卫范围外消费的字段才豁免。

## 2. BI — tests/memory_eval/harness.py:159 硬编码哑密码

**判断**：`hashed_password="m09-eval"` 是 eval 环境的哑占位（harness 永不认证，列值仅非空约束）。
**修法**：跟随守卫既有 tests 豁免机制——`_EXCLUDE_FILES` 中的 `backend/tests/_credentials.py`（"centralized test credential fixtures"）。harness.py 改为 `from tests._credentials import TEST_HASHED_PASSWORD`（conftest 同款 import 路径），赋值点换用该常量。未改守卫正则，未加新豁免语法。值 `m09-eval` → `hashed` 语义等价（opaque 列占位）。

## 3. DM002 — InterventionLifecycleEvent 未登记

**判断**：`backend/app/models/intervention_lifecycle.py`（D-05 生命周期事件存储）因 linkage 注释含 `intervention_request_id` + `user_id` 列命中守卫 high-risk×cross-user 启发式，属真应登记的干预域跨用户存储。
**修法**：按相邻 model 注册模式（`intervention_request/audit_log/outcome/feedback/strategy_outcome` 全部 alias → `intervention_episode`）在 `TARGET_MODEL_ALIASES` 补 `"intervention_lifecycle_event"`/`"intervention_lifecycle_events"` → `intervention_episode`，附注释说明 content-light 语义与「check_before_store 当前无该表调用方，将来接线需按列补细 scope」的保守边界。已核实 `check_before_store` 在生产代码零调用（仅 context_manager 用只记日志的 `audit_data_collection`），故该登记无字段剥离风险、纯治理覆盖面。

## 4. BJ001 — cost_wvpl_worker.py 零生产导入

**判断**：**非废弃**——已运行时接线，守卫 AST 导入图看不见字符串引用：
- `app/core/celery_app.py:78` Celery `include=["app.workers.cost_wvpl_worker", ...]`
- `:184` `task_routes` 该任务 → `low_priority` 队列
- `:1024` beat 日程 `refresh_cost_wvpl_metrics` 条目

**修法**：走守卫自身提供的第三出口，文件头部加 `# rule-bj: exempt 已运行时接线——app/core/celery_app.py 以字符串引用本模块（:78 include / :184 low_priority 队列 / :1024 beat 日程），AST 导入图看不见字符串引用`。不删代码、不在 workers/__init__ 里加真实 import（避免为过守卫改变包导入副作用）。

## 5. BA-ROUTES — 3 条引擎路由逐条裁决

**① POST /api/v1/tasks/{task_id}/reopen（tasks.py:1228）→ 补 gateway 代理。**
依据：移动端真实在调——`mobile/lib/core/network/api_endpoints.dart:73 reopenTask` + `task_repository.dart:1464 reopenTask()` 完整仓库实现；引擎端是 X-04 新增真转型（COMPLETED/ABANDONED→IN_PROGRESS，reopen_history 归档）。gateway 无此路由 = 移动端该功能必 404（NoRoute 回退只覆盖 /api/v1/auth/*）。R2-08 §2.2 #11 当初删除的理由「engine has no reopen transition anywhere」已被 X-04 推翻。
实现：proxy_routes.go tasks 块补 `tasks.POST("/:id/reopen", h.proxyWithHeaders)`，行内 `// rule-bm: ignore engine gained this reopen surface post-R2-08 (X-04)`（Rule BM 的 FORBIDDEN_REGISTRATIONS 钉了该 fragment，其自身消息明示「annotate with rule-bm: ignore if the engine gained this surface」——本改动正是该情形）；同步更新 `proxy_routes_r208_test.go` 钉测试（reopen 条目移出 mustNotExist 并留 supersession 注释）与 `proxy_routes_test.go` expectedTasksRoutes（正向钉）。

**② POST /api/v1/tasks/{task_id}/rescope（tasks.py:1249）→ 补 gateway 代理。**
依据：同上——`api_endpoints.dart:74 rescopeTask` + `task_repository.dart:1495 rescopeTask()`（X-04 stale-plan 重定范围）；R2-08 清单从未钉过 rescope（BM FORBIDDEN 表无此项），按 tasks action 路由既有模式（route-tier: authed + proxyWithHeaders）直接注册。

**③ GET /api/v1/insights/understanding-dimensions（insights.py:87）→ ENGINE_ONLY ledger 豁免。**
依据：无任何客户端调用——mobile 全库 grep 无该路径（移动端理解面板走 `/experience/understanding-snapshot`，api_endpoints.dart:247，由 gateway `registerREST(experience, "/*path")` catch-all 覆盖）；gateway 无 insights 原生 handler（insights 组仅代理 recent-directives / understanding-depth）；唯一引用方是引擎自己的 API 测试。该端点是 D-03 五维可解释诊断面，UI 接线前挂账：ledger 理由写明「no client consumer yet; proxy when a UI wires up, then drop this entry」。

**Gateway 测试**（CGO_ENABLED=0）：
- `go test ./internal/handler/ -count=1` → ok（28.5s，含更新后的 r208 钉测试与 expectedTasksRoutes）
- `go build ./...` → OK

---

## 回归证明

1. **全量守卫**：`bash scripts/run_all_rule_guards.sh` → `all rule guards passed (73 rules)`（0 红；含修复项 AS/BI/GOV-DATA-MIN/BJ/BA-ROUTES/AX/BM 及环境项 AQ/BG）。
2. **相关 pytest**（python3.11 -m pytest，进程内哑 SECRET_KEY/JWT_SECRET，无 .env）：
   - `tests/unit/test_data_minimization.py` + `tests/api/test_insights_understanding_dimensions_api.py` + `tests/api/test_task_complete_and_update_api.py` → 15 passed
   - `tests/services/test_friction_chat_wiring.py` + `tests/unit/test_context_source_contract.py` + `tests/unit/test_memory_eval_service.py` → 72 passed（覆盖 harness 的 TEST_HASHED_PASSWORD 改动）

## 附注

- `docs/product/stage22_prompt_coverage_baseline.md` 的 audited_at 抖动是 Rule S22-PROMPT 守卫自身每次运行重写所致（check_prompt_render_coverage.py:95），已 `git checkout --` 还原，不入 patch。
- AQ/BG 环境修复 = `make proto-gen`（gen/ 产物不入库，patch 天然不含）。

## 收工核查

- [x] 零 commit / 零 push，改动全部在 wt95 worktree
- [x] 未改任何守卫检测逻辑（AST/正则/扫描面/consumer 集零变动；只加 EXPECTATIONS 数据、ENGINE_ONLY ledger 行、豁免/ignore 注释）
- [x] 未创建 .env；测试用进程内哑值；未起模拟器/构建链（go build/test 与 pytest 除外）
- [x] /tmp 无遗留产物；无遗留进程
- [x] 产物：`v3-output/GUARD-DEBT/changes.patch` + `REPORT.md`（会话产物按纪律放 v3-output）
