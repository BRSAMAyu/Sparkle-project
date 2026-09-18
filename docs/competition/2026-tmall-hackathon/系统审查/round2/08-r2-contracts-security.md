# 08 跨层契约·安全横切 复审报告（round2）

- 审查员：8 号切片（R2：修复验证 + 代理路由全量连通 + F8 移交专项 + 安全增量）
- 基线：`main@ca86bda8`（R1 修复已集成），工作树 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt8`（只读，未改任何业务代码；临时脚本在 /tmp/sr8r2/）
- 日期：2026-09-18
- R1 对应报告：`round1/08-contracts-security.md`（修复由 commit `28a1e933`（F8）等承载，无独立 08-fixes.md）

---

## 1. 修复验证结论

| R1 ID | 结论 | 证据摘要 |
|---|---|---|
| C-01 迁移环 | **已修复（fresh 链实测通过）** | `7f807dcd4e5f.down_revision` 由 `comp_idx_20260508` 改指 `wp19_20260507`。静态构图 135 revisions、cycles=NONE、dangling parents=NONE、heads=`['0150e391736a']` 单头。fresh 库 `alembic upgrade head` 一次通过（135 步全绿，见 2.1） |
| C-02 sparkle_galaxy 引导缺失 | **已修复** | 新增 `boot_20260502_sparkle_galaxy`（down=c12_20260502，`CREATE SCHEMA IF NOT EXISTS sparkle_galaxy`），c17 改挂其下；c17 downgrade 只 revoke 不 drop schema，与 boot 的 downgrade no-op 语义一致。fresh 库升级后 `pg_namespace` 中 sparkle_galaxy 存在，无需任何手工干预 |
| C-03 schema.sql 快照漂移 | **已修复（但导出链路仍脆弱，见 R2-08-06）** | 全量表/列比对：快照 234 表 vs fresh 迁移库 234 表，`ONLY-IN-SNAPSHOT=NONE`、`ONLY-IN-LIVE=NONE`、column drift=0。R1 的 4 缺失项（post_comments、community_strategy_outcomes、chat_messages.metadata、user_devices.push_token_hash）全部在快照中；2 多余项（shared_resources 4 列、saga_instances 表）已移除 |
| C-04 release_approvals admin-tab 无鉴权 | **F8 判定"false-positive"不成立；且 C-05 修复使暴露面真实可达（新 P1，R2-08-01）** | `dashboard-summary`/`admin-tab`/`GET /`/`GET /{request_id}` 仍无任何鉴权依赖（仅 `Depends(get_db)`）；此前靠"网关不代理该前缀"的偶然性保护，C-05 把代理注册上后，网关侧仅 `authMiddleware`（普通用户 JWT 即可通过），admin 审批明细对全体登录用户可读 |
| C-05 /release_approvals 代理路径漂移 | **已修复（逐段核对一致）** | 网关 `proxy_routes.go:987` `{"/release_approvals","release_approvals"}` → 注册 `/api/v1/release_approvals/*path`（GET/POST/PUT/PATCH/DELETE）；`NewSingleHostReverseProxy` Director 只改 scheme/host，路径原样透传；引擎 `main.py:822 include_router(api_router, prefix="/api/v1")` + `router.py:234 include_router(release_approvals.router)` + `APIRouter(prefix="/release_approvals")`（release_approvals.py:23）→ 挂载 `/api/v1/release_approvals`，各段全对齐 |
| C-06/C-07/C-08/C-09/C-10 | 未在本轮范围内（P3），C-08 的 `backend/sparkle/{signals,rag}` 4 个 tracked pb2 现状未变 | — |

### 1.1 fresh scratch DB 全链输出（建库→upgrade→验证→drop）

```
CREATE DATABASE sr8_r2_fresh
$ alembic upgrade head    # wt8/backend, DATABASE_URL -> fresh 库
... Running upgrade wp19_20260507 -> 02a063d173ec, add_pii_hash_columns_for_encryption
... Running upgrade 02a063d173ec, p001_20260507 -> ac07dc579128, merge_pii_and_goal_id_heads
... Running upgrade ac07dc579128 -> comp_idx_20260508, add_composite_indexes_for_hot_paths
... Running upgrade z1a2b3c4d5e6 -> c1b2c3d4e5f6, add community_strategy_outcomes table
... Running upgrade a9af85273edc, fix_goals_plan_fk_20260510 -> 0150e391736a, merge_final_heads_20260516
EXIT=0 （"Running upgrade" 共 135 行）
SELECT version_num FROM alembic_version → [('0150e391736a',)]   # 单头单行
SELECT nspname FROM pg_namespace WHERE nspname='sparkle_galaxy' → 存在
DROP DATABASE sr8_r2_fresh
```

### 1.2 dev 库兼容检查 → **不通过（R2-08-06）**

```
$ alembic current   # DATABASE_URL -> dev 库 sparkle
ERROR [alembic.util.messaging] Can't locate revision identified by 't32_community_rooms'
```

dev 库 `alembic_version` 仍是基线不存在的 `t32_community_rooms`（R1 即如此，F8 未修），`alembic current/upgrade head` 在 dev 库上直接失败。"从零重建"路径（fresh）已通，但本机 dev 库依旧游离于迁移治理之外；`make db-migrate` 需 `FORCE_STAMP=1` 人工确认才能继续。

---

## 2. ★代理路由全量对照表（R2 核心新镜头）

方法：从 wt8 引擎 `from app.main import app` 导出全路由（933 条，其中 /api/v1 下 922 条 method+path 对）；解析网关 `proxy_routes.go`（298 条显式 proxyWithHeaders 路由 + 71 个 api.Group + 51 次 registerREST catch-all + Missing-Proxy-Loop 11 前缀）、`galaxy_handler.go`（~55 条）、`cmd/server/setup.go` NoRoute 公开 auth 前缀（11 条）与 Go 原生 handler（error_book/files/chat_history/health），逐条形状匹配（gin `:param`↔FastAPI `{param}`、`/*path`↔前缀通配）。

**总对照结论：网关代理前缀 60+ 个中绝大多数对齐良好；发现 2 个整组死路由 + 22 条死网关代理路由 + 90 条引擎路由从网关不可达（约 /api/v1 的 9.8%）。**

### 2.1 整组死代理路由（网关有组、引擎零挂载）

| 网关代理组 | 引擎实际挂载位置 | 说明 |
|---|---|---|
| `/api/v1/event-bus/*`（catch-all） | `/api/v1/admin/event-bus/*`（已被 `/admin` catch-all 覆盖） | 整组 404；组本身是历史遗留表面 |
| `/api/v1/observability/*`（catch-all） | `/api/v1/admin/observability/*`（同上） | 整组 404 |

### 2.2 死网关代理路由（请求会被引擎 404/405）

| # | 方法+路径 | 引擎实况 | 定性 |
|---|---|---|---|
| 1 | POST `/api/v1/chat` | 引擎挂载在 `/api/v1/chat/chat`（双前缀） | 404；REST chat 全组死（主链路是 /ws/chat，见 R2-08-05） |
| 2 | POST `/api/v1/chat/stream` | 引擎 `/api/v1/chat/chat/stream` | 404 |
| 3 | POST `/api/v1/chat/confirm` | 引擎 `/api/v1/chat/chat/confirm` | 404 |
| 4 | GET `/api/v1/cards`（bare） | 引擎无 bare GET /cards | 404 |
| 5 | POST `/api/v1/cards`（bare） | 引擎无 bare POST /cards | 404 |
| 6-7 | PATCH/PUT `/api/v1/cards/*` | 引擎 /cards 下无任何 PATCH/PUT | 全部 405/404（catch-all 方法面死） |
| 8 | GET `/api/v1/recommendations`（bare） | 引擎无 bare GET | 404 |
| 9 | POST `/api/v1/recommendations/feedback` | 引擎无此路径 | 404 |
| 10 | POST `/api/v1/exam-sprint/completion` | 引擎仅 `GET /completion` | 405 方法漂移 |
| 11 | POST `/api/v1/tasks/{id}/reopen` | 引擎全仓无 reopen | 404 |
| 12 | GET `/api/v1/tasks/suggestions` | 引擎仅 POST（网关 POST 兄弟路由存活） | 405 冗余方法 |
| 13 | PATCH `/api/v1/goals/{id}` | 引擎仅 PUT `{goal_id}`（网关 PUT 兄弟存活） | 405 冗余方法 |
| 14 | GET `/api/v1/cqrs/dlq/stats` | 引擎无 /api/v1/cqrs/*（DLQ 真身在 /dlq/*、/admin/event-bus/*） | 404 |
| 15-17 | POST `/api/v1/community/messages/private`、GET `/messages/private/{user_id}`、DELETE `/messages/private/{msg_id}` | 引擎无任何 private messages 路由 | 404（私信功能以 friends/{id}/messages 形态存在） |
| 18 | PATCH `/api/v1/community/posts/{post_id}` | 引擎无 PATCH posts | 405 |
| 19 | DELETE `/api/v1/community/groups/{group_id}/leave` | 引擎仅 POST leave（POST 兄弟存活） | 405 冗余方法 |
| 20 | DELETE `/api/v1/community/groups/{group_id}/messages/{msg_id}` | 引擎仅 PATCH + POST revoke | 405 冗余方法 |
| 21 | POST `/api/v1/community/share/{share_id}/adopt` | 引擎用 `/shared-resources/{id}/adopt`（网关新路由存活） | 404 旧别名 |
| 22 | GET `/api/v1/galaxy/nodes`（galaxy_handler ProxyToBackend） | 引擎仅 POST /galaxy/nodes | 405 |

### 2.3 引擎可达但网关未注册（从移动端不可达）——90 条，按簇汇总

| 簇 | 条数 | 内容与定性 |
|---|---|---|
| `/plans` 阶段/探索管线 | **16** | discovery/start·turn·finalize、compass/{id}/approve·review、phase-sketch/generate·materialize、phases/{id}/complete·design-tasks·feedback·feedback-gate(start·respond)·schedule/regenerate、{plan_id}/advance-phase·planning-context·today —— **P2（R2-08-03），新版计划执行核心管线从移动端 404** |
| `/community` | 20 | aggregates×4、strategy-outcomes×3、admin/reports×2、knowledge-base×2、groups/galaxy、files/copy-to-library、recommended-resources、resources、shared-resources/flag-misleading·reject、goals/similar-pursuers、tasks/{id}/complete、users/{id}/share-file —— P3 长尾 |
| `/recommendations` | **6** | collaborative、my-interactions、record-interaction、similar-items、similar-users、stats 全部不可达 —— **P2（R2-08-04）：整簇网关↔引擎错位** |
| `/health/health/*` | 11 | 引擎自身双前缀挂载（health+health）；网关健康检查本为 Go 原生，属"引擎侧死副本"（R2-08-09） |
| `/ws/*` | 5 | devices×3（与 `/devices/*` 挂载重复）、online/{user_id}、`ws/ws/ack`（双前缀副本）—— 引擎直连 WS 面，网关链路不需要（R1 C-06 同族） |
| `/achievements` | 4 | `achievements/achievements` 双前缀副本×3 + POST events/process |
| `/exam-sprint` | 4 | dashboard、sprint-summary、diagnose/generate·grade |
| `/marketplace` | 4 | admin/packs·skills 创建与 rollback（admin 面，网关未开） |
| `/seed-libraries` | 5 | admin/{id}/promote、items PUT/DELETE、rating、subscription |
| `/galaxy` | 3 | community/aggregate-errors、context-plan/timeline、documents/{file_id}/nodes |
| 单条散布 | 9 | POST files/process、GET client-telemetry/summary、POST calendar/{id}/restore、GET background-tasks/stream/events、POST push/interaction、GET/POST tasks/{task_id}/subtasks（网关 /subtasks 组只盖住 /subtasks/* 形态）、chat/history+sessions（Go 原生接管，by design） |

其余 820+ /api/v1 引擎路由全部经 catch-all 组、显式路由、galaxy handler、Go 原生 handler 或 NoRoute 白名单可达；Missing-Proxy-Loop 其余 9 前缀（analytics、audit、counterfactual、error-book、release_approvals、research、safe-experiments、scenario-packs、skills）引擎均有对应挂载，逐前缀验证非 404。

---

## 3. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|----|--------|-----------|----------|----------|----------|
| R2-08-01 | **P1** | `backend/gateway/internal/handler/proxy_routes.go:1005-1008`、`backend/app/api/v1/release_approvals.py:111-136,111(`GET ""`)` | 任意注册用户带普通 JWT 请求 `GET /api/v1/release_approvals`、`/dashboard-summary`、`/admin-tab`、`/{request_id}` → 读取全部待发布审批明细；F8 的"C-04 false-positive"判定不成立——C-05 修复反而撤掉了"网关不代理"这层偶然保护 | 网关 Missing-Proxy-Loop 仅 `rg.Use(authMiddleware)`（无 RequireAdmin）；引擎四个 GET 端点仅 `Depends(get_db)`，无 `get_current_active_superuser`（同文件的 submit/approve/reject/apply 反而都有 superuser 依赖） | 引擎侧给 4 个只读端点补 `Depends(get_current_active_superuser)`；或网关为 `/release_approvals` 组单独加 RequireAdmin。C-04 应改回"成立、未修复" |
| R2-08-02 | **P1** | `backend/app/core/llm_security_wrapper.py:85-97`（`__getattr__`）、调用面 `app/api/v1/chat.py:292,543,609,695`、`app/orchestration/execution_engine.py:1379`、`app/orchestration/plan_review_service.py:1031,1115` | 基线 ca86bda8 上 `__getattr__` 对除 dunder 外的一切属性无界转发：`llm_service.chat_stream_with_tools(...)`（chat.py:609，**线上流式聊天主路径**）、`continue_with_tool_results`（chat.py×3、execution_engine×1）、`reason_json/chat_json` 全部经包装器单例直达裸 LLMService，**跳过输入过滤（prompt 注入筛查）、per-user 配额/成本守卫与监控** | `chat.py:36 from app.services.llm_service import llm_service`（=LLMSecurityWrapper 实例，llm_service.py:1528）→ 直接调用非守卫方法。修复波 f813c3f0（F3-E1）引入转发时即存在 | 基线后 main 上的 G3 `b0051a76` 已改白名单，但仍显式放行 chat_json/reason/reason_json/continue_with_tool_results/chat_stream_with_tools/generate_push_content 六个"经审计旁路"——**主聊天流继续免配额免筛查**。建议：为这 6 个方法在 wrapper 内补安全包装（至少配额+监控），或将豁免决定显式登记进 KNOWN_CODE_DEBT_LEDGER 跟踪 |
| R2-08-03 | **P2** | `backend/gateway/internal/handler/proxy_routes.go:160-197`（plans 组）vs 引擎 plans 路由表 | 移动端调用新版计划阶段/探索管线（discovery、compass、phase-sketch、phases 状态机、advance-phase、planning-context、today）→ 网关 404 | 网关 plans 组最后一条是 `POST /phases/:phaseCardId/activate`；引擎 16 条管线路由无任何网关注册 | 按 R1 建议把"网关代理前缀↔引擎挂载前缀"自动比对固化为守卫（可扩 BA guard），并补注册 plans 新路由 |
| R2-08-04 | **P2** | `proxy_routes.go:302-309`（recommendations 组） | 同上：网关只注册 bare GET + /feedback（两者皆死），引擎 6 条真实路由全部不可达，簇级双向错位 | 引擎：collaborative/my-interactions/record-interaction/similar-items/similar-users/stats | 网关改 catch-all 或逐条对齐；删除两条死路由 |
| R2-08-05 | **P2** | `proxy_routes.go:236-245` vs `backend/app/api/v1/`（chat 路由文件 `APIRouter(prefix=...)` + 路由路径再带 `/chat`） | REST chat 三条代理（POST /chat、/chat/stream、/chat/confirm）全 404；引擎挂载成 `/api/v1/chat/chat*`。当前产品走 /ws/chat 掩盖了问题，但任何 REST 回退/第三方集成必炸 | 引擎路由表：`POST /api/v1/chat/chat`、`/chat/chat/confirm`、`/chat/chat/stream` | 统一命名：引擎去掉路由内层 `/chat` 前缀（消除双前缀挂载），网关保留现注册 |
| R2-08-06 | **P2** | dev 库 `alembic_version`（`t32_community_rooms`）；`Makefile:97-103`（db-dump 源 = `docker exec sparkle_db pg_dump --schema-only -d sparkle`） | C-03 修复的脆弱性：schema.sql 已对齐迁移终态，但 (a) dev 库 alembic 桩仍是基线外的 `t32_community_rooms`，`alembic current/upgrade` 直接失败；(b) `make sync-db` 的 db-dump 仍从**污染的 dev 库**导出——F8 当时是绕开 Makefile 手工从 migration-true 库导的，任何人重跑 `make sync-db` 都会把 21 值污染枚举（见 R2-08-07）重新写回 schema.sql | 本轮实测：`alembic current` → `Can't locate revision identified by 't32_community_rooms'`；dev 库 achievementtype 枚举 21 值 vs fresh 库 10 值 | dev 库一次性修复：`alembic stamp 0150e391736a`（配合 FORCE_STAMP 流程）+ 手工 `DROP TYPE` 清理重复枚举值或重建污染枚举；db-dump 改为从 fresh 迁移库导出（CI 化） |
| R2-08-07 | **P1** | `backend/app/models/achievement.py:40-53`（11 个小写枚举值，含 `PLANNING="planning"`）、`backend/app/data/achievement_seeds.py:536,552`、`backend/alembic/versions/cc9383c4c29f_full_baseline_schema.py`（10 个大写值） | fresh 迁移库上引擎成就子系统全量写入失败：引擎 `setattr(achievement,"type","planning")` 等 11 个小写值（achievement.py:153 `setattr(achievement, field, value)`）经 SQLAlchemy Enum 直发 PG → `invalid input value for enum achievementtype`；sync_achievement_definitions（populate_achievements.py:153-166，经 guest_seed_service.py:15 与 achievement_engine.py:318 触发）在重建环境必炸。dev 库因存在**21 值污染枚举**（10 大写+10 小写+planning）被掩盖 | 本轮直接 SQL 实证（fresh 迁移库）：`'MILESTONE'` OK；`'milestone'`/`'planning'`/`'PLANNING'` 全部 `invalid input value for enum achievementtype`。dev 库枚举 = 21 值 | 统一大小写契约（建议迁移链加 `ALTER TYPE ... RENAME` 或引擎侧 values_callable 产出大写）；`planning` 值需迁移补进枚举或从 seeds/模型移除；修复后 fresh 库重放验证。此发现属 N-2 诊断结论，升级为 P1 因其直接落在 C-01/C-02 同一条"从零重建"关键路径上 |
| R2-08-08 | **P3** | `backend/gateway/internal/db/models.go:154-158` | `sqlc diff`：重生成将删除 `AchievementtypePlanning("planning")`、`AchievementtypePLANNING("PLANNING")` 两个常量——F8 重生成 schema.sql 后没有重跑 `make db-sqlc`，tracked sqlc 产物陈旧 2 个常量 | `sqlc diff` 输出仅此 2 行删除；全仓 grep 无 Go 代码引用这两个常量 → 无运行时风险 | `make db-sqlc` 重生成一次即可归零（在 R2-08-06 的导出源修复之后做，避免把污染枚举再带回来） |
| R2-08-09 | **P3** | 引擎路由表（4 处双前缀挂载副本） | `/api/v1/chat/chat*`、`/api/v1/health/health/*`（11 条）、`/api/v1/achievements/achievements/*`（3 条）、`/api/v1/ws/ws/ack/{message_id}` —— router include 前缀与路由内路径叠加，产生不可达死副本并污染路由表/OpenAPI | 对应非双前缀版本同时存在且被网关/Go 原生覆盖 | 引擎侧清理重复 include 前缀；加"路由表无双前缀段"守卫 |
| R2-08-10 | **P3** | `proxy_routes.go:990,992`（event-bus、observability catch-all 组） | 两个整组代理 404（引擎真身在 `/admin/event-bus/*`、`/admin/observability/*`，已被 /admin catch-all 覆盖） | 引擎 /api/v1 下零 `event-bus`/`observability` 挂载 | 删除两组注册（或注释指向真身位置） |
| R2-08-11 | **P3** | 详见 2.2/2.3 表 | 长尾：community 私信×3、posts PATCH、exam-sprint completion 方法漂移+dashboard/sprint-summary/diagnose、marketplace admin×4、seed-libraries×5、galaxy×3、cards bare×2+PATCH/PUT 方法面、tasks reopen、cqrs/dlq/stats、client-telemetry summary、calendar restore、background-tasks SSE、push/interaction、tasks/{id}/subtasks 等 | 每条均经引擎路由表比对证实 | 按"删死路由/补注册/改方法"三类归档处理；建议守卫化（同 R2-08-03 建议） |
| R2-08-12 | **P2（加固项）** | `scripts/check_migration_contracts.py:13-17,60-61` | 守卫用 `git diff --name-only {BASE_REF}...HEAD`——只看已提交差异：本地未提交（staged/unstaged/untracked）的迁移文件完全不被检查（R1 实跑即输出 "No changed migration files"），坏合同迁移可静默过守卫直到 push | `git_changed_files` 仅 `base_ref...HEAD` 一种选取 | ① 选取并集：`{base}...HEAD` ∪ `git diff --name-only` ∪ `--cached` ∪ `git ls-files --others --exclude-standard`；② 与文件选取解耦的 always-on 结构守卫：每次必跑 `alembic heads==1` + ScriptDirectory 环检测（本轮脚本 ~1s）；③ CI 中每周/每 PR 跑 fresh-DB `upgrade head` 冒烟（本轮实测 135 步 <1min） |

**安全增量（R1 修复波 181 文件改动面扫描）**：新增 SQL 拼接 0（唯一 f-string 命中为日志文案）；eval/exec/subprocess 新增 0；PII 入日志新增 0；`audit.py` 修复仅补 settings 导入、superuser 依赖与审计装饰器原样；`tasks.py` 委托 TaskService.update 后 ownership 检查（`task.user_id != current_user.id`）保留；网关 auth/middleware 改动为注释与测试；main.py 改动为关停 drain 逻辑。唯一实质安全回归即 R2-08-01（C-05 修复重开 admin 读面）与 R2-08-02（wrapper 转发旁路），均已列入发现表。

---

## 4. F8 移交专项诊断

### N-1 SQLC 产物 tracked 与再生机制盘点

- **tracked**：`backend/gateway/internal/db/` 共 15 个 git 跟踪文件，其中 sqlc 生成物 4 个（`db.go`、`models.go`、`query.sql.go`、`scripts.go`），输入 2 个（`schema.sql`、`query.sql`），其余为测试与 Lua 脚本。`backend/gateway/gen/`、`backend/app/gen/` 均 gitignored（0 tracked）；`backend/sparkle/{signals,rag}` 4 个 pb2 仍 tracked（R1 C-08 现状未变）。
- **再生机制**：`make sync-db` = `db-migrate`（alembic heads==1 门禁 + upgrade）→ `db-dump`（db-validate 后 `docker exec sparkle_db pg_dump --schema-only`，`grep -v '^\\'` 去掉 `\restrict` 等行）→ `db-sqlc`（`sqlc generate`，pgx/v5 + emit_json_tags）。
- **结论**：机制闭环存在且门禁齐全，但 (a) 导出源钉死在 dev 库（R2-08-06 脆弱性）；(b) 本次 schema.sql 重生成后未重跑 db-sqlc，产物陈旧 2 常量（R2-08-08）；(c) sqlc 产物 tracked 而 proto 生成物不入库——两类"生成物"策略不一致，属已知取舍，建议在 REPOSITORY_STANDARDS 里写明。

### N-2 achievementtype enum 残留值

全链路证据链（三轮比对 + DB 实证，结论=R2-08-07）：
1. 迁移链/fresh 库/schema.sql：10 值全大写，无 planning。
2. dev 库：21 值（10 大写 + 10 小写 + `planning`）——纯 out-of-band 污染，是引擎"能跑"的唯一原因。
3. 引擎 SQLAlchemy 模型：11 个小写值（`values_callable` 显式产出 e.value），其中 `planning` 在任何库的真实枚举里都只靠污染存在。
4. 网关 sqlc models.go：残留 `planning`/`PLANNING` 两个无引用常量（旧污染导出的化石）。
5. 行为实证：fresh 库上 `'planning'`/`'milestone'` INSERT 直接报 invalid input value。

### N-4 迁移守卫对未提交改动失效的加固方案

见发现表 R2-08-12，三层：①变更选取改并集（committed ∪ staged ∪ unstaged ∪ untracked）；②always-on 结构守卫（单头 + 环检测，与文件选取无关，Makefile db-migrate 已有单头门禁可复用）；③周期性 fresh-DB upgrade 冒烟（本轮已验证可行性，135 步 <1 分钟）。另注意 `...`（三点 diff）在 BASE_REF 指向未 fetch 的远端引用时直接 crash，本地场景应回退 origin/main 或 merge-base 缺省。

---

## 5. 良好清单

1. C-01/C-02/C-03/C-05 四项修复本体质量高：fresh-DB 从建库到单头 135 步一次通过、快照 0 漂移、release_approvals 五段路径全对齐——R1 指出的"从零重建"主风险实质消除（仅剩 dev 库桩与导出源两个残留）。
2. Missing-Proxy-Loop 其余 9 个前缀与引擎挂载全部对齐（含 R1 修复的 release_approvals），网关 60+ 代理前缀基本面健康。
3. 网关 Go 原生接管面（errors 11 条、files 上传链、chat sessions/history、health）与引擎 REST 同形对齐，双栈职责边界清晰。
4. NoRoute 仍只放行 11 个公开 auth 前缀且保留 `path.Clean` 防穿越；`/admin` catch-all 有 RequireAdmin 双闸；`/dlq` 组同样有 RequireAdmin。
5. R1 修复波在注入/PII/凭据维度的 18k+ 行新增扫描全部干净；audit/tasks 修复保留原有授权与审计语义。

## 6. 测试执行记录

| 命令/脚本 | 结果 |
|---|---|
| 静态迁移图分析（alembic ScriptDirectory + 自写 DFS，wt8/backend） | 135 revisions、heads=[0150e391736a]、cycles=NONE、dangling=NONE |
| `alembic upgrade head`（fresh `sr8_r2_fresh`）→ 验证 → `DROP DATABASE` | EXIT=0，135 步，单桩单头，sparkle_galaxy 存在 |
| `alembic current`（dev 库 sparkle，只读） | FAILED：`Can't locate revision 't32_community_rooms'`（R2-08-06） |
| `alembic upgrade head`（fresh `sr8r2_c03chk`）+ information_schema 全表列比对 vs schema.sql（/tmp/sr8r2/schema_cmp.py） | 234/234 表、0 漂移；R1 六项抽查全过；库已删除 |
| `sqlc diff`（wt8/backend/gateway） | 仅 models.go 删 2 枚举常量（R2-08-08） |
| 枚举写入实证（fresh 库 achievements 表 INSERT + rollback） | 'MILESTONE' OK；'milestone'/'planning'/'PLANNING' REJECTED（R2-08-07） |
| 引擎路由表导出：`from app.main import app`（wt8/backend，SECRET_KEY/JWT_SECRET/DATABASE_URL 就绪） | 933 条（/api/v1 922），存 /tmp/sr8r2/engine_routes.json |
| 路由全量对照脚本（/tmp/sr8r2/route_cmp.py：解析 proxy_routes.go + galaxy_handler + NoRoute + Go 原生 handler ↔ 引擎表） | 死组 2、死网关路由 21+1、不可达引擎路由 90；结果存 /tmp/sr8r2/route_diff.json |
| 修复波安全扫描（`git diff 90daac8a..ca86bda8` 全量 + 定向 grep：SQL 拼接/PII 日志/eval/auth 依赖） | 仅 R2-08-01、R2-08-02 两个实质项 |
| 资源纪律 | 未跑全量测试套件；所有 DB 操作在 scratch 库（已全部清理）；未动 sparkle 主库与其它 worktree 的遗留 scratch 库（sr8r2_mig、sr8r2_ct8_mig、sparkle_rt02_probe、sparkle_repro_t42 归属不明，仅记录） |

---

**结论**：R1 四项核心修复（C-01/02/03/05）本体全部实测通过，"从零重建"主路径已通；但本轮系统化全量对照暴露出路由契约的长尾漂移（2 死组 + 22 死网关路由 + 90 不可达引擎路由，含 plans/recommendations 两个 P2 簇），并在修复波自身引入的改动里发现两个新 P1——C-05 修复重开的 release_approvals 只读越权面（C-04 误判为 false-positive）与 LLMSecurityWrapper `__getattr__` 无界转发造成的配额/筛查旁路。DB 契约链还剩三块尾巴：dev 库桩、sync-db 导出源、achievementtype 双端枚举漂移（fresh 库上成就子系统必炸）。
