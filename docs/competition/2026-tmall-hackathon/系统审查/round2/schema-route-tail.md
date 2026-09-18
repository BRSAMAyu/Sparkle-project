# Schema/路由长尾收口 — gfix03 死列 drop + BA-ROUTES 两条挂账

> 2026-09-19。基线 `main@b97a0674`（wt9 worktree）。承接
> [schema-consistency-audit.md](schema-consistency-audit.md) §三 P1 / §四移交清单第 1 条
> 与 [BA-ROUTES 守卫](../../../../../scripts/guards/check_rule_ba_routes_parity.py)
> ENGINE_ONLY / GATEWAY_ONLY 台账中的两条挂账。补丁：同目录 `schema-route-tail.patch`。

## 变更一览

| # | 变更 | 文件 |
|---|---|---|
| A | 新增 `gfix03_20260918` drop 迁移（三列 MIG-only 死列，带 IF EXISTS） | `backend/alembic/versions/gfix03_dead_columns_drop_20260918.py` |
| A | 删除对非映射属性 `card.archived_at` 的死赋值（不落库，随列退役） | `backend/app/services/card_service.py` |
| A | 网关快照/SQLC 产物按流程再生（非手改）：`schema.sql` -5/+2、`models.go`/`query.sql.go` 随动 | `backend/gateway/internal/db/{schema.sql,models.go,query.sql.go}` |
| A | 审计白名单收窄：3 个死列条目移出（漂移已归零，保留 DB-only tasks 三列） | `scripts/devtools/orm_migration_audit.py`、`scripts/devtools/db_debris_cleanup.py`（注释） |
| B | `POST /plans/:id/today` 方法漂移修正为 GET（以引擎为准） | `backend/gateway/internal/handler/proxy_routes.go` |
| B | 删除死路由 `GET /goals/:id`（引擎无 goals GET-by-id） | 同上 |
| B | BA-ROUTES 台账收窄：移除 `/api/v1/plans/{}/today`（ENGINE_ONLY）与 `/api/v1/goals/{}`、`/api/v1/plans/{}/today`（GATEWAY_ONLY） | `scripts/guards/check_rule_ba_routes_parity.py` |
| — | 审计移交清单第 1 条的死列部分勾销 | `docs/competition/.../round2/schema-consistency-audit.md` |

## A · MIG-only 死列 alembic drop 迁移

### A1 零消费确认（全仓 grep，含网关 SQLC）

三列在 ORM（`Card`/`ChatMessage`/`UserSettings`）均无映射、proto 无字段、mobile 无引用；
网关 `query.sql` 无一引用（`GetChatHistory` 等的 `SELECT *` 展开由 sqlc 生成，随 schema
再生自动收缩）。逐列排查出的"疑似消费"均澄清为非消费：

| 列 | 迁移链来源 | 疑似消费 → 澄清 |
|---|---|---|
| `cards.archived_at` | `cp001a2b3c4d5_add_card_protocol_tables` | `card_service._transition` 对 `card.archived_at` 赋值——列未映射，纯实例属性、不落库（本次随迁移删除该死赋值） |
| `chat_messages.metadata` | `wp19_20260507_add_chat_messages_metadata_jsonb` | `age_gate.SENSITIVE_FIELDS` 声明 `"chat_messages": ["content","metadata"]`——全仓仅声明、无任何 DB 操作（死规格） |
| `user_settings.accessibility_settings` | `fv14_20260502_add_accessibility_settings` | mobile `kAccessibilitySettingsUserSettingsKey` 经 `PUT /user/settings` 上送——`UserSettingsService.update_settings` 以 `hasattr` 过滤，该 key 本就被静默丢弃（DB 列从未被写） |

注意区分：`cards.metadata`（`metadata_` 映射，活列）与 `chat_messages.metadata`（死列）
不同表同名列，前者不受影响（演练与实库均复核存活）。

### A2 迁移本体

`gfix03_20260918`，`down_revision = "gfix02_20260918"`，单头链尾。upgrade 用
`ALTER TABLE … DROP COLUMN IF EXISTS` ×3（幂等）；downgrade 按各来源迁移的原始列定义
复原（`cards.archived_at` timestamp 可空；`chat_messages.metadata` jsonb 可空；
`user_settings.accessibility_settings` jsonb NOT NULL DEFAULT '{}'::jsonb）。

### A3 演练库验证（pg_dump 克隆法，串行）

依 [db-debris-cleanup.md](db-debris-cleanup.md) 的流程：`pg_dump -Fc`（1.5 MB）→
`pg_restore` 克隆出 `sparkle_gfix03_rehearsal`（stamp=`gfix03_20260918`，三列已不在）。
因克隆库已在后置状态，演练改为**双向驱动迁移文件本体**：

| 步骤 | 结果 |
|---|---|
| 克隆库 `alembic downgrade gfix02_20260918` | 三列按原始定义复原（timestamp 可空 / jsonb 可空 / jsonb NOT NULL DEFAULT），stamp=gfix02 ✅ |
| 克隆库 `alembic upgrade head` | 三列精确删除（`pg_attribute` 逐列复核=0），`cards.metadata` 活列存活，stamp=gfix03 ✅ |
| 收尾 | `DROP DATABASE … WITH (FORCE)` + dump 文件即删 ✅ |

### A4 实库与快照

特殊情况如实记录：动工前发现 dev 库 `sparkle` 已被此前某会话**带外**删去三列并
`stamped gfix03_20260918`（当时仓库内并无对应迁移文件）。本次迁移文件的 revision 与该
stamp 恰好对齐，实库操作退化为确认性空转：

- 实库 `alembic upgrade head`：no-op（stamp 已在 head，且与文件链一致）✅
- `make sync-db` 等价管线（wt9 无 `backend/.venv`，按 Makefile 同款命令以
  `/opt/homebrew/bin/python3.11` 串行执行）：
  - **fresh scratch 库从零全链重放至 gfix03 通过**（顺带证明链对全新环境健康）；
  - `db-dump` 同款 grep/sed 管线再生 `schema.sql`（-5/+2，三列消失）；
  - `sqlc generate` 再生 `models.go`/`query.sql.go`：`ChatMessage.Metadata`、
    `Card` 的 `ArchivedAt`、`UserSetting.AccessibilitySettings` 移除；快照同时补上
    此前滞后缺失的 gfix02 `item_similarities` 两列。
- `scripts/devtools/orm_migration_audit.py`（含 scratch 重放）：**三方全绿**
  ——ORM/迁移/实库 表数 216/233/233，全部漂移桶为 0，`✅ 三方一致` ✅
- 定向 pytest：`tests/unit/test_card_operations_service.py` +
  `tests/test_db_partitioning.py` → **7 passed, 2 skipped** ✅

### A 白名单收窄

`orm_migration_audit.py` 的 `WHITELIST_COLUMNS` 移除三行死列登记（保留 tasks 三列
DB-only 豁免），并留 2026-09-19 消化注记；`db_debris_cleanup.py` docstring 同步注明
"已由 gfix03 收口、排除条款保留为防 out-of-band 污染的历史依据"。

## B · BA-ROUTES 两条挂账

守卫台账原文（`scripts/guards/check_rule_ba_routes_parity.py`）：

1. **`POST /plans/:id/today` 方法漂移**（ENGINE_ONLY `/api/v1/plans/{}/today`）：
   引擎只有 `GET /plans/{plan_id}/today`（`api/v1/plans.py:851`，
   `@router.get("/{plan_id:uuid}/today")`），网关却注册 `plans.POST("/:id/today")`
   ——POST 打过去引擎 405/404。**以引擎为准**：网关注册改为
   `plans.GET("/:id/today", h.proxyWithHeaders)`（参照 exam-sprint 补齐先例
   `35b29ba5` 的注释+route-tier 风格）。双侧 grep：mobile/测试无 POST 调用方；
   引擎自身测试用的就是 GET。
2. **`GET /goals/:id` 死路由**（GATEWAY_ONLY `/api/v1/goals/{}`）：引擎 goals 只有
   GET 列表（`""`/`"/"`）、`GET /arbitrate`，**无 GET-by-id**（仅 PUT/DELETE
   `/{goal_id}`）。双侧 grep：mobile goal 仓库只用 `PUT /goals/$goalId`
   （`updateGoal`），`/goals/:id` 其余命中均为 Flutter 导航路由非 API；tests_e2e
   零引用。→ 删除 `goals.GET("/:id", h.proxyWithHeaders)`，PUT/DELETE 保留，
   并在白名单注释留档。

白名单收窄：ENGINE_ONLY 删 `/api/v1/plans/{}/today`；GATEWAY_ONLY 删
`/api/v1/goals/{}` 与 `/api/v1/plans/{}/today`，两处以 2026-09-19 处置注记替代。

### B 验证

- `check_rule_ba_routes_parity.py`：**RULE BA-ROUTES OK**（373 网关路由 ↔ 923 引擎
  路由，54 catch-all，112 ledgered diffs），exit 0 ✅
- `check_rule_ax_route_ownership.py` PASS、`check_rule_bm_r208_dead_routes.py` OK ✅
- 定向 Go：`go test ./internal/handler/ -run "TestRegisterProxyRoutes|TestProxyRoutes"`
  ok；**`go test ./...`（CGO_ENABLED=0）10 包全 ok**；gofmt 干净 ✅
- 引擎定向：`pytest tests/api/test_plans_api.py` → **3 passed** ✅

## 全套守卫

`bash scripts/run_all_rule_guards.sh` → **all rule guards passed (71 rules)**
（含 DB-HEAD：`✅ alembic 单头: gfix03_20260918`）。

注：守卫套件会自动刷新 `docs/product/stage22_prompt_coverage_baseline.md` 的
`audited_at` 时间戳（运行时副产物，与本次改动无关），已还原，不入补丁。

## 环境备注（复现）

- wt9 为全新 checkout：`backend/gateway/gen/`、`backend/app/gen/`、`mobile/lib/gen/`
  均为 gitignore 的生成物，需从已构建环境复制（`cp -RL` 解引用；主仓 `app/gen` 内有
  指向主 worktree 的**绝对符号链接**，直接 `cp -R` 会把链接带进来，导致 Rule K 的
  rule-z 扫描在越界路径上崩溃——已用 `cp -RL` 规避）。
- 测试环境变量：`SECRET_KEY=rule-guard-secret-0123456789abcdef`
  `JWT_SECRET=rule-guard-jwt-0123456789abcdef`
  `REDIS_URL=redis://:sparkle_dev_redis_2026@localhost:6379/1`
  `DATABASE_URL=postgresql+psycopg://postgres:sparkle_dev_pg_2026@localhost:5432/sparkle`
  Go 侧 `CGO_ENABLED=0`。
- 未 commit/push；演练库/scratch 库用后即删，dev 库本任务全程无业务写入。
