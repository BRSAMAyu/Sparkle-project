# Schema 一致性专项审计 — ORM ↔ Alembic 迁移链 ↔ 网关快照 三方列集对齐

- 审计员：数据库 schema 一致性专项（round2 移交专项）
- 基线：`main@c6b3fae0`（= ac16dc7b 语义 + relay 文档），工作树 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt9`
- patch：[schema-consistency-audit.patch](schema-consistency-audit.patch)
- 方法：自动化三方 diff（新工具 `scripts/devtools/orm_migration_audit.py`）+ 定向测试红绿证明 + 快照重放验证

---

## 一、背景：两次咬人的系统性缺口

| 事故 | 缺口 | 后果 |
|---|---|---|
| gfix01 | `shared_resources` ORM 有 `adoption_count` 等 4 列而迁移链上没有（ORM 领先迁移） | G8 收敛到迁移真值后游客种子查询 UndefinedColumn → 事务毒化 → 游客登录 500 |
| G2/G8 | 两个 agent 各自建迁移 parented 同一节点（0150e391736a），alembic 双头 | 双头潜伏数周无人发现，集成期才显性化 |

根因：**三方一致性没有任何自动防线**。本次落地三道闸：全列审计工具、单头守卫（提交侧 pytest + manifest 守卫）、快照重放验证。

## 二、方法与工具

`scripts/devtools/orm_migration_audit.py`（一次性 devtools，可直接挂 CI）拉平三个事实源：

1. **ORM**：importlib 遍历 `backend/app/models/` 全部 99 个模块注册进 `Base.metadata`（含 mixin、关联表；`pii_encryption_listeners` 仅数据级加密不产 DDL，无需特殊处理）→ 216 张表。
2. **迁移链**：对 throwaway 库（`sparkle_orm_audit_scratch`，用后即删）从零 `alembic upgrade head` 重放整链后读 `information_schema`。**不用 `--sql` 离线推导**：实测离线模式在 `5f2b9b3c0e6f`（`inspect(bind)` 内省）直接抛 `NoInspectionAvailable`，且链上大量 `op.execute` 裸 SQL 无法静态解析；真重放让 PG 自己当解析器，与 Makefile `db-dump` 既有工作流同构。
3. **实库**：连 `sparkle` dev 库读 `information_schema.columns`（public schema；`ag_catalog`/`sparkle_galaxy` 归 AGE 图引擎，白名单整体忽略）。

按表分组 diff，产出：整表漂移（ORM-only / MIG-only / DB-only）+ 共享表列漂移三桶；**退出码非零当且仅当白名单外有漂移**。白名单逐条写明理由与登记日期（脚本头 + 本文 §四）。

## 三、三方 diff 结果（修复前）

总量：ORM 216 表 ⊂ 迁移链 233 表（+alembic_version）⊂ 实库 262 表（+alembic_version）。漂移合计 652 项（含整表列展开），定性如下。

### P0（会导致运行时 UndefinedColumn，已修复）

| 表 | ORM-only 列 | 定性 | 运行时证据 |
|---|---|---|---|
| `item_similarities` | `total_learners_either`, `subject_id` | **ORM 领先迁移 = 缺迁移**（gfix01 同类） | `collaborative_filtering_service.py` `select(ItemSimilarityModel)` 会带出全部映射列，迁移真值库上直接 UndefinedColumn |
| `post_comments` | `deleted_at`（SoftDeleteMixin，带索引） | 同上 | `api/v1/community.py` 多处 `select(PostComment)`，游客/社区链路同 gfix01 毒化模式 |

实库 `sparkle` 同样缺这 3 列 → **当时实跑即崩**（不只是新库风险）。整表级 ORM-only：0（所有 ORM 模型都有迁移）。

### P1（不崩，挂账移交）

| 桶 | 数量 | 明细与定性 |
|---|---|---|
| 迁移-only 整表 | 17 | **网关 CQRS 读模型（活，Python ORM 有意不映射）5 张**：`event_outbox`、`event_store`、`projection_snapshots`、`processed_events`、`projection_metadata`（`backend/gateway/internal/db/query.sql` 引用）；**退役 spine/decision-contract 死 schema 12 张**：`aurora_policy_versions`、`commitments`、`event_sequence_counters`、`focus_contracts`、`identity_evidence`、`insight_claims`、`mastery_audit_log`、`probe_outcomes`、`release_approval_requests`、`transition_decision_records`、`user_scenario_states`、`window_states`（ORM 与网关 query.sql 均零引用，Python 侧 `commitments` 命中为 Redis key 非本表） |
| 迁移-only 列（共享表） | 3 | `cards.archived_at`、`chat_messages.metadata`、`user_settings.accessibility_settings` — **迁移领先 = 模型已删迁移未删的死列**，网关 query.sql 亦零引用 |
| DB-only 整表 | 29 | `agent_runs`/`agent_run_steps`/`agent_run_receipts`、`billing_*`×6、`llm_usage_ledger`/`llm_attempt_lineages`、`memory_claims`/`memory_candidates`/`user_memory_epochs`、`knowledge_lineage_*`×2、`document_source_*`×2、`material_citations`、`source_acl_grants`、`outbox_dead_letters`/`outbox_deliveries`、`room_*`×3、`study_rooms`、`saga_instances`、`task_command_*`×2 — **DB 领先 = dev 库会话遗留**：仓库内无任何创建来源（无迁移、无模型、无脚本 DDL），疑为历次审查/探针会话产物（同库另有 `sparkle_rt02_probe`、`sparkle_repro_t42` 残库可佐证） |
| DB-only 列（共享表） | 3 | `tasks.scheduled_at`/`timezone`/`version` — 迁移链从未创建（`scheduled_at` 仅存在于 aurora runtime 迁移、不同表），ORM/网关均无引用 → 历史 create_all/手改库残留 |

## 四、处置

### 1. P0 修复：gfix02 迁移（已落地并实测）

`backend/alembic/versions/gfix02_orm_column_p0_20260918.py`（down=gfix01_20260918，链仍单头）：

- `item_similarities` + `total_learners_either`（Integer NOT NULL default 0）、`subject_id`（UUID NULL）
- `post_comments` + `deleted_at`（DateTime NULL）+ 索引 `ix_post_comments_deleted_at`（对齐 SoftDeleteMixin `index=True`）

验证链：
- dev 库 `alembic upgrade head`：gfix01→gfix02 应用成功，重复执行空转（幂等）；`alembic current` = `gfix02_20260918 (head)`
- scratch 库从零全链重放：通过
- ORM 烟雾：修复后 `select(ItemSimilarity)` / `select(PostComment)` 真连 dev 库执行通过（修复前必 UndefinedColumn）

### 2. 白名单回填（口径内归零）

脚本头白名单按 §三 P1 结论逐条登记（含理由+日期）：17 张迁移-only 表、29 张 dev 会话遗留表、6 个死列。回填后审计 exit 0；**新增漂移（尤其 ORM-only P0 桶）会直接顶爆退出码**。

### 3. 移交清单（P1，不阻塞合入）

- [ ] 12 张退役 spine 死 schema：评估 `drop_table` 收敛迁移（连带 3 个死列 `cards.archived_at` 等）
  - ✅ 2026-09-19 死列部分完成：3 个 MIG-only 死列已由 `gfix03_20260918` drop 迁移收口（零消费 grep + 演练库双向验证 + 三方审计归零，见 [schema-route-tail.md](schema-route-tail.md)）；12 张表本身仍挂账。
- [ ] dev 库 29 张会话遗留表 + `sparkle_rt02_probe`/`sparkle_repro_t42` 残库：运维清理（属运行时数据，不入库不入补丁）
- [ ] `tasks.scheduled_at/timezone/version`：确认无消费后从 dev 库 drop

## 五、alembic 单头守卫（红绿已证）

| 工件 | 位置 | 门 |
|---|---|---|
| pytest 闸 | `backend/tests/test_migrations_single_head.py`（2 tests） | heads 恰好 1；失败信息直接给出分叉点（单父多子节点）；revision 唯一且链可解析 |
| manifest 守卫 | `scripts/guards/check_alembic_single_head.py`，登记 `scripts/rule_guard_manifest.tsv` 规则名 **DB-HEAD** | 同上，纯脚本解析不需要 DB，供 `run_all_rule_guards.sh` 与 CI 挂载 |

红绿证明（两工件各做一轮）：

- **红**：临时注入 `down_revision='gfix01_20260918'` 的平行迁移（复刻 G2/G8 挂链模式）→ pytest `FAILED: alembic 双头/多头（2 个）: ['gfix02_20260918', 'zzredtest_dh']，分叉点 {'gfix01_20260918': [...]}`；守卫脚本 exit **1**
- **绿**：删除注入文件还原 → pytest **2 passed**；守卫 exit **0**

注：历史上已 merge 的分叉点（分叉后接 merge 迁移）是合法 DAG 形态，唯一门是 heads=1——测试 docstring 已写明，避免后来者误改严。

## 六、网关快照校验（尽力项 → 已闭环）

- **可重放性验证通过**：复刻 `make db-dump` 管线（throwaway 库 → `alembic upgrade head` → `pg_dump --schema-only` + 同款 grep/sed 过滤）重新导出，与仓库 `backend/gateway/internal/db/schema.sql` 对比：差异 **100%** 由未刷快照的近三个迁移解释（gfix02 三列+索引、gfix01 四列、sr8r2g2 的 `plan_execution_records.execution_intent_id`+唯一索引+FK），零不可解释漂移 → 导出管线确定性成立
- **快照刷新**：已用同一管线再生成 `schema.sql`（+34/-4），恢复"快照=迁移链终态派生物"不变量（sqlc 产物不受影响——新列不在既有 query 里；`make db-sqlc` 由网关侧例行执行即可）
- **顺手清障**：删除 `backend/gateway/backend/gateway/internal/db/schema.sql`——历史误路径产生的**第二份陈旧快照**（11569 行 vs 正主 21463 行，无任何构建/代码引用）。双快照正是"快照静默漂移"温床

## 七、复现

```bash
# 三方审计（exit 0 = 白名单口径内一致）
/opt/homebrew/bin/python3.11 scripts/devtools/orm_migration_audit.py
# 单头守卫（提交侧）
SECRET_KEY=rule-guard-secret-0123456789abcdef0 JWT_SECRET=rule-guard-jwt-0123456789abcdef0 \
  /opt/homebrew/bin/python3.11 -m pytest backend/tests/test_migrations_single_head.py -q
# manifest 守卫
bash scripts/run_all_rule_guards.sh --rule DB-HEAD
# 快照重放校验（= make db-dump 前半段，diff 到临时文件勿直接覆盖）
```

环境注意：本机 homebrew python3.11 无 psycopg(v3)，审计脚本自动回退 psycopg2 并归一 URL 方言；scratch 库经 `postgres` 管理库创建/销毁，不触碰 dev 库（除 `alembic upgrade head` 本身的语义内写入）。
