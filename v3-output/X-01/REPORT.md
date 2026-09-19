# X-01 · ActionPlan V3 契约：Outcome / Execution / Cognitive Ownership — REPORT

- Worker: X-01 (Apex / stream ACTION / risk high / locks: action-contract)
- Base: `6470a6fb`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt8`）
- 交付物：`changes.patch`（同目录）；返修轮：REVIEW_RECEIPT_2（R2 DeepAudit，CHANGES→返修）
- 状态：READY_FOR_REVIEW（禁 commit/push，按纪律交 patch）

---

## 1. 解决的实际问题

V3 的 Action Proposal 需要 outcome / execution / cognitive-ownership 语义，但今天的任务真值在
`tasks`+`subtasks`（live 1219 行），目标协议 `cards`+`task_occurrences` 仍 0 行、mid-flight、
**无治理**（CARD-DUAL-WRITE 守卫停用、consistency_validator 从未存在，债账 #4/#6 + 2026-09-18 节）。
此前 V3 关键字段（cognitive_ownership 等）全仓 0 实现。本卡把 V3 语义以**最小加法**落在 tasks 域，
不重建 task system、不偷偷切流，并为 card_protocol 给出文档级映射与演进方向。

## 2. 契约落点（设计决策）

### 2.1 结构化列（tasks 表 8 个 nullable 新列，迁移 `x01_20260919`，挂 `m01a_20260919` 单头之后）

| 列 | 类型 | V3 语义 |
|---|---|---|
| `action_schema_version` | String(16) NULL | `"action_plan.v1"`；**NULL = legacy/V2.x 行**（兼容判别位） |
| `desired_outcome` | Text NULL | 期望结果陈述（outcome 语义，独立列，不埋 guide_json） |
| `smallest_useful_step` | JSONB NULL | `{description, useful_because:[封闭枚举×n]}`——「为什么 useful」必须类型化（ACTION §2 六判据），空判据=伪步骤被拒 |
| `completion_evidence` | JSONB NULL | `[{evidence_kind(封闭枚举), ref?(封闭scheme), description?}]`——**类型化证据规格**，非自由文本（ACTION §4） |
| `cognitive_ownership` | VARCHAR NULL | `user_core / shared / delegated`——**D13 首版定义**（全仓第一落点） |
| `source_refs` | JSONB NULL | `["scheme://id", ...]`，scheme 封闭（见 §2.3） |
| `risk_class` | VARCHAR NULL | `low / medium / high / critical`（AGENT_RUNTIME §3 run contract 的 risk_class 同名对齐） |
| `reversible` | Boolean NULL | 可撤销性（ACTION §1 "risk / reversibility" 成对） |

关键取舍：
- **`execution_mode` 复用既有 `tasks.execution_mode` String(20) 镜像列，不新增第二列**（避免 D-TASK
  重复真源）。dev DB 复核（2026-09-19，只读 SELECT）：1231 行全 NULL，复用零风险；词表唯一真源 =
  `ExecutionMode`（human/agent/hybrid 小写），DTO 边界 `normalize_execution_mode` 归一大小写，读侧
  统一门同样归一（词表外值 → 整块降级 + WARN，不再打入 pydantic）。DB 不加 CHECK（沿用
  execution_intent.py `create_constraint=False` 先例；封闭词表由契约层强制）。
- ORM 枚举列（cognitive_ownership/risk_class）非原生 Enum → 编译 VARCHAR(9/8)，迁移按仓内先例
  （oc001a2b3c4d5：DB String(20) vs ORM VARCHAR 并存）给 String(16)，宽于词表不影响写入。
- 新列全部 nullable、无 server default：迁移对 1219 个旧行零影响；downgrade 全量可逆且**不动
  execution_mode**。
- proto 不动：tasks 契约载体是 REST/JSON（mobile `task_repository.dart` 直发 JSON），非 gRPC；
  网关 `schema.sql` 是自动导出快照（硬规则 2），Leader 合入窗口 `make sync-db` 时自然刷新。

### 2.2 契约真源：`backend/app/core/action_plan.py`

C-01 decision_context.py 同款风格：冻结 dataclass + 封闭词表 + `validate() -> tuple[str,...]` +
`to_task_columns()/apply_to_task()/action_plan_from_task()`。`ActionPlanIn`（pydantic）在 parse 时
归一化+全量校验（API 边界 422），`TaskService.create/update` 整块落列；`Task.action_plan` property
→ `TaskDetail.action_plan` 自动读回（API 层零改动，`TaskDetail.model_validate(task)` 既有路径直接生效）。

**读侧容错（返修后实测行为，修正初版声明）**：REST 投影（`Task.action_plan`）与类型化重构
（`action_plan_from_task`）共用**同一个门** `action_plan_projection`（版本 + 全封闭词表 +
execution_mode 归一）。legacy 行（`action_schema_version` NULL，正常态）→ None 无日志；
带版本门/词表任一不过的脏/未来值行 → 整块降级 None + **WARN 日志**（带 task_id 与原因——
区分「没有 V3 计划」与「V3 计划损坏/版本不符」）。`ActionPlanOut` 的封闭枚举因此安全：其输入
已过统一门，任何新读路径禁止绕过该门直接喂列值（初版 REST 路径曾原样投影，单行脏枚举值会使
该用户全部任务端点 500——F1 探针实证，返修修复并以 10 项回归测试钉死）。已知代价：版本 bump
未迁移存量行时 WARN 随读放大（观测优先于静默，可后加限流）。

### 2.3 与 C-01 / D-01 的对齐点

- **C-01（decision_context.v1）**：`ACTION_SOURCE_REF_SCHEMES` 完整包含 C-01 的
  {memory, user_state, plan, document, profile}（ref URI 封闭 scheme 语义一致，如
  `memory://episodic/<id>`、`plan://<id>`），另扩展 action 域 {goal, task, subtask, chat,
  decision, run}（`run://` → execution_intents，即 D-01 lineage 的 run 域）。
- **D-01（Event/Evidence Lineage，并行中，其交付未入我基线）**：本卡 evidence 字段命名为
  plan 侧「证据规格」（evidence_kind + ref）；outcome 侧 actual/self-reported/estimated/unknown
  验证分级**未在本卡重复定义**，留给 D-01 事件域。**待对齐点**：若 D-01 的
  intervention/action/run/outcome 关联词表引入新 ref 形态（如 `outcome://`、`intervention://`），
  需在 `ACTION_SOURCE_REF_SCHEMES` 扩展并 bump 版本——已在该常量注释中标注。
- **B-06 §1.5**：Action 分配唯一协议 = ExecutionIntent；本卡未新建分配服务，execution_mode
  词表直接 import `ExecutionMode`（测试 `test_execution_mode_reuses_frozen_execution_intent_enum` 冻结）。

### 2.4 cognitive_ownership 首版定义（D13）

与 execution_mode **正交**：`user_core`（该步骤即用户要获得的能力/判断/创作，不可只交结果）、
`shared`（agent 准备/校对，人做核心决定）、`delegated`（机械步骤可整体委托）。
例：execution_mode=hybrid + cognitive_ownership=user_core（agent 查文献、用户写论文）合法且常见。
依据：HUMAN_AGENT_HYBRID.md §2 维度 1。

### 2.5 消费方组合指引（F5，返修补——文档级警示，上消费卡前必须落成硬规则）

契约 `validate()` 对 9 种 mode×ownership 组合均放行（结构正交是设计意图），但消费方须知：

| 组合 | 风险 | 指引 |
|---|---|---|
| `agent × user_core` | **定义级矛盾**：user_core 不可「agent 做完只交结果」，agent 模式整体执行即替用户完成其核心能力建构并标记完成——与产品目标相反且不可见 | Planner 产出此组合时必须改写（升 shared/hybrid 或换 ownership） |
| `hybrid × delegated` | hybrid 必有 human 决策点，delegated 否认用户认知参与——模式承诺了 ownership 否认的参与 | Planner 应降为 agent 或升 ownership |
| `human × shared` | shared 承诺的 "Agent checks" 阶段在 human 模式无执行载体 | 接受但提示用户 checks 不会发生 |

（同步落在 `app/core/action_plan.py` 模块 docstring「消费方组合指引」；硬校验属 UI/Planner 消费卡。）

## 3. card_protocol 映射说明（文档级，未改 card_protocol 代码）

两态关系（B-06 D-TASK 继承）：**tasks = 今日真值（V3 契约先落此），cards+task_occurrences =
目标协议（shadow 验证通过后切流，切流前提=补齐 consistency_validator 并恢复守卫）**。
本卡不切流；以下为 V3 字段 ↔ 协议形态的映射，切流时按此搬运：

| V3 字段（tasks 列） | cards TASK-card metadata 键（协议形态） | task_occurrences 承载 |
|---|---|---|
| `desired_outcome` | `desired_outcome`（metadata 新键；今日 `description` 是 guide_content 投影，语义不同不混用） | — （outcome 属系列定义） |
| `smallest_useful_step` | `smallest_useful_step`（同构 JSON：description + useful_because） | 演进方向：B-06 D-TASK 明示「V3 Smallest Useful Step 落在 task_occurrences」——切流后 occurrence 级 payload 携带当次步骤（`feedback_payload` 或新键） |
| `completion_evidence` | `completion_definition`（cards 既定键名，card_protocol.py:252 注释；形态=本卡类型化 JSON） | 完成时实证归 D-01 事件域（`completed_at`/`completion_quality` 已有） |
| `execution_mode` | `execution_mode`（**已在线**：`legacy_adapter.task_to_card` line 312 已投影 `task.execution_mode`） | 既有镜像列语义不变 |
| `cognitive_ownership` | `cognitive_ownership`（metadata 新键，D13 随系列定义走） | — |
| `source_refs` | `CardEdge(REFERENCES)` 边（ref 指向 card 的场景）+ `metadata.source_refs`（跨域 ref 如 memory:// 保持 URI 原样） | — |
| `risk_class` / `reversible` | `metadata.risk_class` / `metadata.reversible` | — |
| `action_schema_version` | `schema_version`（cards 已有 String(16) 列，语义对齐，切流时映射为 card 侧版本） | — |
| （V2 对照）`tasks.success_criteria` | 今日 TASK card 无对应键（metadata 仅 description=guide_content 投影） | — |

**F6 优先级规则（返修补）**：`action_schema_version` 非空时 `desired_outcome` 为唯一完成标准语义，
`success_criteria` 视为 V2 遗留冻结展示；过渡期 UI 不得把两者同时呈现为生效标准。「用户改
title/success_criteria 时 desired_outcome 是否跟随」= 后续 UI 消费卡的显式决策项。

实现注意（给切流 worker）：`legacy_adapter.TaskAdapter.task_to_card` 的 `card_metadata` dict
是唯一投影点，切流时在此追加 V3 键即可；本卡未动它（表 0 行、无治理状态下不扩大双写面）。

## 4. 交付物清单（全部在 changes.patch 内）

| 文件 | 内容 |
|---|---|
| `backend/app/core/action_plan.py` | 契约真源（新） |
| `backend/app/models/task.py` | CognitiveOwnership/RiskClass 枚举 + 8 列 + `action_plan` 投影 property |
| `backend/app/models/__init__.py` | 导出新枚举 |
| `backend/app/schemas/task.py` | ActionPlanIn/Out + TaskCreate/TaskUpdate/TaskDetail 挂块 |
| `backend/app/services/task_service.py` | create/update 接线（update 支持显式 null 清除回 legacy） |
| `backend/alembic/versions/x01_20260919_add_action_plan_v3_columns.py` | 加法迁移（新） |
| `backend/tests/unit/test_action_plan_migration_sqlite.py` | sqlite 隔离重放（新） |
| `backend/tests/unit/test_action_plan_contract.py` | 契约冻结/校验/三模式（新） |
| `backend/tests/test_action_plan_v3_integration.py` | service 落库 + 三模式 + 结构化守卫（新） |

## 5. 验证证据（返修后重跑，2026-09-19）

红→绿说明：初版三套件先写先跑确认全红（ModuleNotFoundError/FileNotFoundError）。返修 F1 的红态由
R2 探针独立实证（完整 fixture，ValidationError loc 落在 `action_plan.*`，收据 F1 节）；本 worker
本地红跑首轮 fixture 不完整（混入无关字段错误），修正 fixture 后转绿——红态归属以 R2 探针为准。

| 验证 | 命令 | 结果 |
|---|---|---|
| 新契约全套（含 F1/F2 新增 10 项） | `pytest tests/unit/test_action_plan_migration_sqlite.py tests/unit/test_action_plan_contract.py tests/test_action_plan_v3_integration.py` | **57 passed** |
| 迁移单头守卫（真链 ent01→e05→m01a→x01） | `pytest tests/test_migrations_single_head.py tests/unit/test_alembic_chain_linearity.py` | 5 passed；alembic heads = `['x01_20260919']` |
| 契约回归 | `pytest tests/contract/test_api_router_openapi_contract.py tests/contract/test_json_wire_format_contract.py` | 7 passed |
| 回归：task 生产逻辑（初版轮） | `pytest tests/test_plan_task_service_production.py tests/contract/test_api_router_openapi_contract.py` | 58 passed |
| 回归：启动/进度/工具/线格式（初版轮） | `pytest tests/unit/test_startup_smoke.py tests/test_plan_progress_update.py tests/test_plan_task_tools_production.py tests/contract/test_json_wire_format_contract.py` | 93 passed |
| 全 app import（循环依赖，返修后再跑） | `python -c "import app.main; ..."` | OK, no cycles |
| 三模式落库证据 | `test_create_with_action_plan_persists_structured_columns[human/agent/hybrid]` | 各自断言 9 列 + TaskDetail 读回 |
| 非自然语言守卫 | `TestStructuredColumnsGuard`（5 项）：结构化列存在、JSON 非 Text、无第二 execution_mode 列、封闭枚举、全 nullable | 全绿 |
| 脏/未来值行不打断读端点（F1） | `TestDirtyRowTolerance`（10 项）：7 类脏形态降级 None、列表混脏行不 500、两读路径同答案（F2）、WARN 可观测 | 全绿 |
| 旧记录兼容 | 迁移重放 legacy 行存活 + `test_legacy_create_without_action_plan_is_fully_compatible` + update 显式 null 清除 | 全绿 |

测试环境：homebrew python3.11（与运行中服务同环境），sqlite 隔离（aiosqlite/in-file），未触碰 dev PG
（唯一一次 DB 访问是只读 `SELECT DISTINCT execution_mode`）。`app/gen` 与 `e05/m01a` 两个迁移文件为
**借入文件**（gitignored 生成物 / 主仓 main `7ef808ee` 已合入的同名文件只读副本，仅为本地验证链完整），
均**不在 changes.patch 内**。

## 6. 遗留风险与限制（如实，返修后更新）

1. **迁移未在真实 PG 应用**（按 Leader 合入窗口纪律）；sqlite 重放 + 真链单头守卫已绿。F8 评注：
   PG11+ 8×ADD COLUMN nullable 为 catalog-only；建议合入窗口 `SET lock_timeout=3s` + 重试（防锁队列）。
   R2 建议的临时库干跑五步（`sparkle_x01_dryrun`）**属 Leader 动作**，未执行。
2. 版本 bump 未迁移存量行 → 全部 V3 行降级 legacy + WARN 随读放大（F2 统一为可观测降级后的已知代价）。
3. action 域 ref scheme 集（goal/task/subtask/chat/decision/run）是第一版，**与 D-01 最终词表待对齐**（§2.3）；
   bump 契约版本需两位 reviewer。
4. update 路径 `action_plan=None` = 显式清除、未 set = 不变；mobile 未消费该块（现只发 execution_mode 字符串）。
5. F5 组合警示（agent×user_core 等）目前为文档级（契约 docstring + 本报告 §2.5 消费方指引），
   **上 UI/Planner 消费卡前必须落成硬规则**。
6. F7：ORM 非原生枚举列若被直连 DB 写入词表外值，行加载即 LookupError（比 F1 更早的爆炸点，
   仓内既有模式延伸；今日无消费路径，文档化接受，可选后续 CHECK 迁移）。
7. EXP-级未来项（未做，ACTION §1 其余字段）：why_now / friction_addressed / dependencies / fallback /
   expiry——字段位未预埋；需要时按本卡模式增量加列 + bump 版本。

## 7. 返修记录（REVIEW_RECEIPT_2 判 CHANGES 后的处置）

| 发现 | 级别 | 处置 |
|---|---|---|
| F1 REST 读路径对 JSONB 内嵌封闭枚举零容错（单行脏/未来值 → 全部任务端点 500，与初版 REPORT 声明相反） | P1 | **已修**：`Task.action_plan` property 改为委托统一门 `action_plan_projection`（延迟 import 解循环），不再原样投影列值；`ActionPlanOut` 保持封闭枚举（输入已过门）；新增 `TestDirtyRowTolerance` 10 项回归（7 类脏形态 + 列表混脏 + 两路径同答案 + WARN 可观测）钉死。红态由 R2 探针实证，绿态本轮全过 |
| F2 版本门分歧（typed 严格→None 静默 vs REST 无门照读） | P1 | **已修**：版本门并入 `action_plan_projection` 单一函数，两读路径同一行为；降级路径 `_degrade()` 打 WARN（loguru，带 task_id 与原因）。REPORT §2.2 声明同步改写为实测行为 |
| F3 迁移链外部分叉（ent01→{x01,e05}，dev DB 已在 e05） | P0（外部成因） | **已修（Worker 侧）**：`x01_20260919.down_revision` 改挂 `m01a_20260919`（主链 ud01→ent01→e05→m01a 单头，M-01 已合入主仓 main 7ef808ee）；单头守卫测试期望同步更新；本地借入 e05/m01a 文件验证真链 heads=`['x01_20260919']`（借入文件不入 patch）。PG 临时库干跑（sparkle_x01_dryrun 五步）留 Leader 合入窗口执行 |
| F4 C-01 对齐守卫是手抄副本非交叉导入 | P2 | **未修（记录）**：wt8 基线（6470a6fb）无 `app/core/decision_context.py`（C-01 尚未进入本 worktree 基线），交叉 import 测试在基线内必红。建议随 C-01 合入后由消费卡/D-01 落地：`app/core/ref_schemes.py` 单一注册表或互相 import 守卫 + rule_guard 登记 |
| F5 execution_mode×cognitive_ownership 组合无警示（agent×user_core 定义级矛盾） | P2 | **文档级已补**：契约模块 docstring「消费方组合指引」+ 本报告 §2.5；硬规则留 UI/Planner 消费卡（验收项） |
| F6 desired_outcome 与 tasks.success_criteria 零关联零优先级 | P2 | **文档级已补**：映射表补 success_criteria 对照行 + 优先级规则（action_schema_version 非空 → desired_outcome 唯一生效，success_criteria 冻结展示）；跟随问题列为消费卡决策项 |
| F7 ORM 枚举列 DB 脏值 → 行加载 LookupError | P3 | **记录**：直连 DB 写入才可达（列无 CHECK，沿 execution_intent.py 先例）；遗留 §6.6 |
| F8 迁移 PG 特有风险（锁队列/sqlite toy 表不覆盖列名冲突） | P3 | **记录**：8 列名经 R2 在 dev PG information_schema 只读复核 0 冲突；lock_timeout 建议入 §6.1 Leader 清单 |

返修改动面（对照 R2「≈30 行 + 测试」预估）：`core/action_plan.py` 统一门 + WARN（净增 ~120 行，
含门内全词表判别与投影 dict 构造）、`models/task.py` property 改委托（净 -20 行）、
`schemas/task.py` 注释、迁移 down_revision 一行 + docstring、测试 +10 项（含 fixture 完整化）。
设计不变项：字段集/词表/迁移列/复用 execution_mode/card_protocol 不动——与 R2「不动其余设计」一致。
