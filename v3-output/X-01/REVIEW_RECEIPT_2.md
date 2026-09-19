# X-01 · ActionPlan V3 契约 — REVIEW RECEIPT（第二路 DeepAudit Reviewer）

- Reviewer: X-01-R2（risk high 双审制第 2 路，深层审计焦点：演化地雷 / 写竞争 / PG 迁移 / 词表治理 / 组合语义 / 僵尸列）
- 复核对象: wt8 未 commit 改动（base `6470a6fb`）+ `v3-output/X-01/{REPORT.md,changes.patch}`
- 日期: 2026-09-19
- 结论: **CHANGES**（架构与写路径验收通过；读路径容错性声明与实现不符 + 合入窗口存在外部双头阻塞，需小补丁后再合）

方法：wt8 读 diff 全量 + 定向探针测试（backend/tests/test_x01_deepaudit_probe.py，验证后已删）+ dev PG 只读检查（psql SELECT / information_schema / pg_stat_activity）+ 主仓 main 只读对照（C-01 decision_context.py、v3 卡片 spec）。未改 Worker 代码、未跑 alembic、未 commit/push。

独立复跑证据：X-01 三套件 47 passed（2.78s）；`test_migrations_single_head + test_alembic_chain_linearity` 5 passed；`test_api_router_openapi_contract + test_json_wire_format_contract` 7 passed。探针 18 项（P1×5 / P2×2 / P3×1 / P5 组合 9 / P4 脏枚举 1）全部按预期复现。

---

## F1 · [P1 · 确认缺陷（探针复现）] REST 读路径对 JSONB 内嵌封闭枚举零容错——单行脏/未来值行会打挂整个任务列表端点，与 REPORT 的容错声明相反

**事实链**（全部代码在本次 patch 内）：

1. `backend/app/models/task.py:205-229` `Task.action_plan` property：只检查 `action_schema_version` 与 `execution_mode` 非空，**原样投影** JSONB 列内容（不校验 useful_because / evidence_kind / cognitive_ownership 词表，不归一 execution_mode 大小写，不看版本）。
2. `backend/app/api/v1/tasks.py` 所有任务读端点（list:302/447、today:491、recommended:514、get:537、update 响应:1006 等）都走 `TaskDetail.model_validate(task)`。
3. `backend/app/schemas/task.py:133-155` `ActionPlanOut` 用**封闭 pydantic 枚举**（`useful_because: list[UsefulStepReason]`、`evidence_kind: EvidenceKind`、`execution_mode: ExecutionMode`、`desired_outcome: str`）。

**探针复现**（test_x01_deepaudit_probe.py，错误 loc 均断言在 `action_plan.*` 路径）：

- `useful_because=["builds_habit_v2"]`（v2 词表扩展值）→ `ValidationError: Input should be 'produces_artifact', ... [type=enum]`
- `evidence_kind="streak_data_v2"` → 同类失败
- `execution_mode="manual"`（镜像列词表外值）→ 同类失败
- `desired_outcome=None`（半写行）→ 同类失败
- 合法行对照 → 正常序列化（排除探针构造问题）

**触发条件与潜伏期**：写路径（ActionPlanIn parse）今天确实挡住了所有词表外值，所以**合并当天无毒源**。地雷在三个计划内/可预期事件上引爆：(a) 契约按自身文档的演进程序**第一次扩展词表**（"扩展需 bump 契约版本"是明文路径）——新写入的 v2 值被旧读端（滚动部署窗口、或消费卡未同步 bump 的实例）读取；(b) 任何直连 DB 的手工修复/回填写入非规范值；(c) 未来某个 execution_mode 第三方写点写出词表外值（今日 7 个写点全在词表内，但列上没有 CHECK）。

**影响面**：一行被污染 → 该用户的 `GET /tasks`（整列表）、`/tasks/today`、`/tasks/recommended`、`GET /tasks/{id}`、PUT 响应全部 500——不是单任务降级，是**端点级故障**，且只能靠 DB 手术或 `action_plan:null` 清除解毒。

**为什么标准验收没发现**：Worker 的容错测试全部驱动 `action_plan_from_task`（确实三级容错），没有任何测试把**脏/未来词表行**喂给 `TaskDetail.model_validate`。绿测试没建模 v2 演进也没建模脏数据。REPORT §2.2「读侧容错，单行脏数据不打断任务列表」与 `models/task.py:209-212` property docstring「半写坏行按 legacy 读」对已上线的 REST 路径**不成立**——容错只覆盖"execution_mode 缺失"一种形态。

**修复建议（最小）**：让 REST 投影与类型化路径同语义——`ActionPlanOut` 的枚举字段放宽为 `str`（写侧已强校验，读侧只需呈现），或 property 内 try/except 词表校验失败返回 None；同时 property 里对 execution_mode 做归一（把 `normalize_execution_mode` 挪到 `models/execution_intent.py` 即可解除 models↔core 循环依赖借口）。修复量 ≈ 20 行 + 1 个"未来词表行读侧降级"测试。

**验证方式**：探针改造为回归测试——未来 useful_because / 词表外 execution_mode / NULL desired_outcome 行经 `TaskDetail.model_validate` 应得 `action_plan=None`（或宽松呈现），list 端点冒烟不 500。

---

## F2 · [P1 · 确认分歧] 版本判别位在两条读路径行为相反：typed 严格版本门（→None），REST 无版本门（照读）——bump 当天同一行两副面孔

**探针复现**：行 `action_schema_version="action_plan.v0"`（模拟"版本常量已 bump、存量行未迁移"混合态）：

- `action_plan_from_task` → **None**（`validate()` 的 `schema_version mismatch` 兜底）——所有存量 v1 行对 Planner/Aurora **静默集体降级为 legacy**，且**无任何日志/指标**（可观测性缺口：无法区分"没有 V3 计划"与"V3 计划损坏/版本不符"）；
- `TaskDetail.model_validate` → **完整读回**（`ActionPlanOut.schema_version` 是裸 `str`，不对照常量）。

**触发与影响**：`ACTION_PLAN_SCHEMA_VERSION` 一旦 bump 而未迁移行（或滚动窗口中新旧版本并存），UI 显示 V3 块、类型化消费方看到 legacy——两表面对同一数据给出相反答案，排查成本极高。

**修复建议**：统一版本门策略（两端同宽或同严）；`action_plan_from_task` 在「非 NULL schema_version 但重构失败」时打 WARN 日志（带 task_id 与原因）。可与 F1 同一小补丁完成。

---

## F3 · [P0 级合入窗口阻塞（外部成因，非本 patch 代码缺陷）] 迁移链已分叉 `ent01 → {x01, e05}`，且共享 dev DB 已被 wt5 前移到 `e05`——直接 `upgrade head` 必失败

**证据**（2026-09-19 本审计实测）：

- `wt5/backend/alembic/versions/e05_20260919_embedding_version_columns.py`：`down_revision = "ent01_20260919"`（与 x01 **同父**）；跨 worktree 扫描分叉点唯一：`ent01 → {x01_20260919, e05_20260919}`。
- dev sparkle DB：`alembic_version = e05_20260919`（且 `knowledge_nodes` 已有 `embedding_model/embedding_dim` 列，即 e05 **已实际应用**，非仅 stamp）。
- wt8 树内不含 e05 → wt8 本地单头守卫（5 passed）**只对 wt8 的世界成立**；两卡都合入后仓库双头，`make sync-db`/`alembic upgrade head` 报 multiple heads；只合 X-01 时 dev DB 从 e05 出发报 "Can't locate revision e05_20260919"。
- 附带事实更正：第一路收据写「dev PG alembic_version=ent01_20260919」——与当前实测不符（应为复核后被 wt5 改变，或当时误读；tasks=1237 行与其一致故是同一库）。

**处置（给 Leader 的合入窗口清单）**：

1. 合入顺序定后**rebase 落后者**：`x01_20260919.down_revision` 改挂 `e05_20260919`（或反向），一行改动；
2. PG 干跑缺口的最小补法（不违反"dev 库状态不动"）：在同容器开**临时库** `docker exec sparkle_db createdb sparkle_x01_dryrun` → 对该库 `alembic upgrade head`（需在已含 e05 的树上跑，或先 `alembic stamp ent01`）→ `information_schema` 验 8 列 nullable 无 default → `alembic downgrade -1` 验列消失且 `execution_mode` 仍在 → `dropdb`。全程不触碰 sparkle 主库。

---

## F4 · [P2 · 确认治理缺口] C-01 对齐守卫是硬编码副本而非交叉导入；D-01 落地时三方词表漂移在测试期不可见

- `tests/unit/test_action_plan_contract.py:74-79`：`c01_schemes = {"memory","user_state","plan","document","profile"}` 是**手抄**，未 import `app.core.decision_context.DECISION_REF_SCHEMES`。C-01 将来扩展（decision_context.v2）时本守卫依然全绿——"对齐"只在评审时点成立，测试不设防。交叉导入无循环依赖障碍。
- D-01.md:25 明文将引入 intervention/action/run/outcome 的 ID 关联词表；X-01 scheme 集已有 `run`、无 `outcome`/`intervention`。现状 = 三个封闭词表散在三处（decision_context.py / action_plan.py / D-01 未来文件），`scripts/rule_guard_manifest.tsv` 无任何契约词表守卫项。
- 建议：抽 `app/core/ref_schemes.py` 单一注册表（C-01 与 X-01 均引用），或最低限度互相 import 的守卫测试 + rule_guard 增一行；D-01 卡合入时把「与 ACTION_SOURCE_REF_SCHEMES 对齐」写进其验收清单。

## F5 · [P2 · 结构性] execution_mode × cognitive_ownership 组合空间无警示——`agent×user_core` 是定义级矛盾却被静默接受

探针实证 9/9 组合全过 `validate()`（结构性正交，R1 结论一致）。业务误用排序：

1. **agent × user_core**（最危险）：user_core 定义即"不可委托给 agent 完成后只交结果"，agent 模式整体执行 = 定义级矛盾。未来 LLM Planner（本契约首要消费方）产出此组合会被静默接受 → 系统替用户完成其核心能力建构步骤并标记完成——与产品目标相反且不可见。建议：契约模块内加冻结的 `SUSPICIOUS_COMBOS`（警示级，非硬拒——保留正交演化空间）+ REPORT/docstring 写明消费方指引。
2. **hybrid × delegated**：delegated 否认用户认知参与，hybrid 模式却必有 human 决策点——模式承诺了 ownership 否认的参与。
3. **human × shared**：shared 承诺的 "Agent checks" 阶段在 human 模式无执行载体。

当前无消费方，文档级警示即够；上 UI 消费卡之前必须落地。

## F6 · [P2 · 数据一致性故事缺口] `desired_outcome` 与既有 `tasks.success_criteria`（Text 列，TaskUpdate/TaskDetail 今日在线可写）零关联、零优先级规则

tasks 表现在有三个"完成标准"载体：title（标签）、success_criteria（V2 自由文本，`models/task.py:117`，TaskUpdate 今日可改）、desired_outcome（V3）。过渡期用户可同时持有互相矛盾的两者；D-01 outcome lineage 将读 desired_outcome 而今日 UI 展示 success_criteria——REPORT 的 card 映射表只字未提 success_criteria。建议：契约 docstring + 映射表补一行优先级规则（如「action_schema_version 非空时 desired_outcome 为准，success_criteria 视为 V2 遗留冻结」），并把"用户改 title/success_criteria 时 desired_outcome 是否跟随"作为后续消费卡的显式决策项。

## F7 · [P3 · 纵深防御] ORM 非原生枚举列 DB 脏值 → 行加载即 LookupError（整查询失败，比 F1 更早爆炸点）

探针复现：绕过 ORM 写入 `cognitive_ownership='bogus'` 后，`select(Task)` 在结果处理阶段抛 `LookupError: 'bogus' is not among the defined enum values`——ORM 层就把整查询打挂。可达路径仅直连 DB 写入（`create_constraint=False` 无 CHECK，沿 execution_intent.py 先例，属仓内既有模式延伸到最热表）。可选缓解：后续迁移加 CHECK 或维持文档化。今日无需阻塞。

## F8 · [P3 · 迁移 PG 特有风险评注]（补 Leader 干跑清单的输入）

- 8×`ALTER ADD COLUMN nullable 无 default` 在 PG11+ 为 catalog-only、瞬时 ACCESS EXCLUSIVE；1237 行表本身无风险。真实风险是**锁队列**：排在长事务后会阻塞 tasks 全部读写（实测 `pg_stat_activity` 当前无长事务）。建议合入窗口 `SET lock_timeout=3s` + 重试。
- sqlite 重放用 3 列 toy 表，**不覆盖真实 60+ 列 tasks 上的列名冲突**——已在 dev PG 只读复核 8 列名 0 冲突（information_schema count=0），风险关闭。
- JSONB vs sqlite TEXT 差异（写入校验、键序归一、重复键丢弃）对本契约无实际影响（全部按键读取、无索引、无默认值）；`astext_type` 与 ADD COLUMN 无关。
- 迁移本身 up/down 对称、不触 execution_mode、判 ent01 单父——代码质量无异议。

## execution_mode 写点全量清单（焦点 2 结论）

写点共 8 个：既有 7（`execution_service.py:799/951/1721/3075/3226`、`execution_ingestor.py:251/555`，全部写词表内小写值）+ 新增 1（`apply_to_task` 契约路径，DTO 边界归一）。评估：

- **无双写半写**：X-01 自身写路径单事务原子；`clear_action_plan` 留 execution_mode 是文档化行为且语义自洽（列共享）。
- **写竞争为 last-writer-wins 语义级**：execution 流程翻 mode（handback/degrade/decision）与客户端 action_plan 更新并发时后写胜，契约块因 mode 即列本身保持内部一致，无腐蚀。
- **读侧表现**：Gateway `query.sql.go:949` 显式列名 SELECT，不见新列、不受伤；cards 影子投影（`legacy_adapter.task_to_card` metadata `execution_mode`）在 create/update **commit 之后**运行，读到已提交值，小写词表内一致。
- 前瞻：若未来任何写点产出词表外值落到带 V3 块的行，REST 读路径即 F1 向量 3 引爆——F1 修复同时封住此口。

---

## 结论与要求

**验收通过面**：契约/模型/DTO/service 设计与实现一致、8 列最小加法、execution_mode 单列复用、写路径原子、47+5+7 独立复跑全绿、OpenAPI/线格式无破坏、dev PG 未被本卡触碰（1237 行 execution_mode 全 NULL、8 列 0 存在）。

**CHANGES 清单（合并前，预计 ≈30 行 + 测试）**：

1. （F1）REST 读路径容错：`ActionPlanOut` 枚举字段放宽或 property 降级，补"未来词表行不 500"回归测试；修正 REPORT §2.2 与 property docstring 的容错声明。
2. （F2）统一版本门 + `action_plan_from_task` 降级 WARN 日志。
3. （F3，Leader 动作）x01 rebase 到 e05（按合入顺序）+ 临时库 PG 干跑五步。
4. （F4/F5/F6，可并入本补丁或立后续卡）C-01 交叉导入守卫；SUSPICIOUS_COMBOS 警示表；success_criteria 优先级规则一行文档。

完成 1-2 后可快速复审合入（改动面小，无需全量重验）。

## 复核者清理声明

探针文件 `backend/tests/test_x01_deepaudit_probe.py` 已删除；未改 Worker 代码与 dev PG（全部只读）；未 commit/push；未起模拟器/浏览器；无 /tmp 残留；本收据为 wt8 内唯一新增产物。
