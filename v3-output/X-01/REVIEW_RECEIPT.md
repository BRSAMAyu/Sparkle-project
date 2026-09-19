# X-01 · ActionPlan V3 契约 — REVIEW RECEIPT（第一路独立 Reviewer）

- Reviewer: X-01-R1（独立复核，risk high 双审制的第 1 路）
- 复核对象: wt8 未 commit 改动（base `6470a6fb`）+ `v3-output/X-01/{REPORT.md,changes.patch}`
- 日期: 2026-09-19
- 结论: **ACCEPT**（附 2 条非阻塞备注）

## 逐条复核结果（对照 Worker 自报 6 条）

| # | 自报 | 复核方式 | 结果 |
|---|---|---|---|
| 1 | 8 nullable 新列 + execution_mode 复用 + 契约真源 | 读 `app/core/action_plan.py`、`app/models/task.py` diff、迁移文件 | ✅ 一致。8 列全 nullable 无 server default；`action_schema_version` NULL=legacy 判别位；execution_mode 复用既有 String(20) 列（`task.py:127`），`TestStructuredColumnsGuard.test_execution_mode_single_source_no_duplicate_column` 冻结无第二列；词表唯一真源 = `ExecutionMode`（`test_execution_mode_reuses_frozen_execution_intent_enum` 冻结） |
| 2 | 迁移挂 ent01 单头后、纯加法、可全量回滚、dev PG 未动、proto 不动 | `alembic heads`=x01_20260919（单头）；grep 图谱确认 ent01 唯一子=x01；sqlite 重放测 up/down 对称且 downgrade 后 execution_mode 仍在；只读 `docker exec psql` 复核 | ✅ 一致。dev PG `alembic_version=ent01_20260919`；`\d tasks` 无 8 新列（`count(action_schema_version)` 报列不存在）；`execution_mode varchar(20)` 1237 行（活库自 1231 微涨）非 NULL 计数 = 0，全 NULL 不变量成立；patch 无 proto/gateway 文件 |
| 3 | 三模式经 TaskService.create 落库 + legacy 全 NULL + update 显式 null 回 legacy | 逐个读集成测试 | ✅ 非空壳。`test_create_with_action_plan_persists_structured_columns[human/agent/hybrid]` 断言 9 列值 + `TaskDetail.model_validate` 读回；`test_legacy_create_without_action_plan_is_fully_compatible` 断言 8 列全 NULL + detail.action_plan None；`test_update_applies_and_clears_action_plan` 以 `model_fields_set` 区分「未 set=不变」与「显式 null=清除」，clear 后 schema_version/completion_evidence 为 NULL |
| 4 | TestStructuredColumnsGuard | 读测试 + 跑 | ✅ 5 项全绿：8 列真实存在、3 个 JSON 列非 Text、无第二 execution_mode 列、4 词表均 StrEnum、全 nullable |
| 5 | source_refs 封闭 scheme = C-01 五 scheme + 6 扩展；card_protocol 仅文档 | 与主仓 `backend/app/core/decision_context.py:46` 逐字对照 | ✅ `DECISION_REF_SCHEMES={memory,user_state,plan,document,profile}` 原样包含；差集恰为 {goal,task,subtask,chat,decision,run}（`test_source_ref_schemes_closed_and_c01_aligned` 冻结双向）；patch 中 card_protocol 仅出现于 action_plan.py 文档字符串，零代码改动 |
| 6 | 47 新 + 链线性 5 + 回归 151 全绿 | 本机重跑（串行） | ✅ 47 passed (3.09s) + 5 passed + 58 passed (99.9s) + 93 passed (185.4s)，合计 203，与自报 47+5+151 一致 |

## 专项审查

1. **8 列设计最小性**：REPORT §2.1「关键取舍」+ §6.5 有记录：execution_mode 复用（省第 9 列、避免 D-TASK 双真源）、EXP 级字段（why_now/friction/dependencies/fallback/expiry）明确不预埋、DB 不加 CHECK（沿 execution_intent.py `create_constraint=False` 先例）、不在 0 行无治理的 cards 上落 V3。更少列的替代（合并为单 JSONB blob）与验收要求「关键字段必须结构化列」冲突，取舍成立。
2. **判别位混读安全**：`action_plan_from_task` 三级容错（NULL→None；execution_mode 词表外→None；validate 不过→None），`Task.action_plan` property 对 schema_version 或 execution_mode 缺失均返回 None，单行脏数据不打断任务列表；OpenAPI 契约 + 线格式回归 151 项全绿佐证新旧行混读无破坏。
3. **正交性证据**：`validate()` 无任何 execution_mode↔cognitive_ownership 交叉约束（结构性正交）；组合实例已测：human+user_core、hybrid+user_core（roundtrip + update）、agent+delegated（DTO）。备注 A：建议后续补 3×3 全组合参数化测试（非阻塞）。
4. **红测基线**：三套件均在模块顶层 import 新文件/新符号（app.core.action_plan、ActionPlanIn、迁移文件路径），无实现时必然 ModuleNotFoundError/FileNotFoundError 全红——「先全红」自报成立。
5. **patch 完整性**：在 base `6470a6fb` 的 /tmp 共享克隆上 `git apply --check` 干净通过，应用后 9 文件与 wt8 工作树**逐字节一致**；+1203 行精确吻合（tracked 222 + 新文件 981）；密钥扫描无命中；无 .env；proto 与 gateway schema.sql 未触碰。
6. **D-01 对齐标注抽查**：`action_plan.py` 契约 docstring「待对齐点（D-01 并行中）」+ `run://` 注释（D-01 lineage run 域）+ REPORT §2.3，三处一致。

## 备注（非阻塞）

- A. 建议补 execution_mode × cognitive_ownership 3×3 全组合参数化测试（当前为结构性正交 + 组合实例覆盖）。
- B. 迁移未在真实 PG 实证（按合入窗口纪律，属预期）；PG 侧操作为 `op.add_column`×8 最稳类别 + sqlite 重放已绿，Leader 合入窗口跑 `make sync-db` 时需观察。

## 复核者清理声明

验证用的 /tmp 克隆（x01_patch_check）已删除；未写主仓、未动 dev PG（全部只读）、未 commit/push、未起模拟器/浏览器。
