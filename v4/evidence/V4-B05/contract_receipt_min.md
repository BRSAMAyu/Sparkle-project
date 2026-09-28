# V4-B05 · 冻结呈现与上下文回执最小合同（`receipt_min.v1`）

- 卡：V4-B05（design · risk high · 独立审查 2 位）
- 状态：DESIGN_PROPOSAL（本文件是契约设计，不是实现声明；未改任何产品码）
- 契约版本：`context_selection_receipt.v1` / `experience_event.v1` / `episode_resume_view.v1` / `action_plan.v1.1`（增量字段位）
- 基线 SHA：见 `run_manifest.json`（worktree wtB05 @ agent/v4/b05）
- 纪律：与 C-01 `decision_context.v1`、X-01 `action_plan.v1`、X-03 `action_command.v1` 同款——封闭词表 + 冻结结构 + 测试钉死；词表扩展 = 契约变更，需 bump 版本过 reviewer。

---

## 0. 一句话与不变量

**回执 = 服务器对"确实发生了什么"的权威记录；呈现 = 回执的投影。** 三条不变量贯穿全部三个契约：

- **I1 授权无关**：回执与呈现事件不授予任何权限、不构成任何业务事实。消费方（Flutter/Go）不得从 `ExperienceEvent` 推导出任何写操作资格。
- **I2 成功必须可溯源**：任何成功语义的呈现，`receipt_ref` 必须指向 committed 状态的权威回执；无 committed 回执不能触发成功（V4-F03 验收同源）。模型只能提议动作，不能发"成功"。
- **I3 跨对象拒绝**：`(subject_type, subject_id)` 绑定校验；ref 必须落在封闭 scheme（`ACTION_SOURCE_REF_SCHEMES`）内且属于同一授权用户；不匹配一律拒绝并记安全遥测，不得 500 泄漏或静默跨读。

---

## 1. 现有权威映射（复用优先，缺项才增）

| 现有权威 | 位置 | 本合同复用 | 状态 |
|---|---|---|---|
| ActionPlan 契约 `action_plan.v1`：`ACTION_PLAN_SCHEMA_VERSION`/`EVIDENCE_KINDS`(7)/`USEFUL_STEP_REASONS`(6)/`ACTION_SOURCE_REF_SCHEMES`(11 scheme) | `backend/app/core/action_plan.py:68/76/90/103` | ref scheme 封闭集、evidence_kind、读侧整块降级门（脏值→None+WARN） | **复用** |
| 命令链 `action_command.v1`：proposal→approve→validate(version+permission)→commit(effects)→authoritative receipt；`CommandEffects`；5 错误码 `ACTION_ERROR_CODES`；终态词表 `TerminalReason` | `backend/app/core/action_command.py:164/117/288` | committed 判定唯一来源；5 错误状态词表；TTL 契约 | **复用** |
| Aurora 决策回执：`AuroraDecisionContract.memory_use_receipts ⊆ evidence_refs` 不变量、`DecisionUncertainty`、`AURORA_UNCERTAINTY_KINDS` | `backend/app/core/aurora_decision.py:270/292/191` | 「回执的 memory 必须真进证据面」不变量原样继承；confidence 语义（审慎标签，非精度百分比） | **复用** |
| 校准回执 `aurora_calibration_receipt.v1`（A-06 "Why this?"）：rationale 摘要+refs+uncertainties；四动作 `not_relevant/wrong/change_scope/delete` 全部委托既有权威；surfacing 确定性门 | `backend/app/aurora/calibration_receipt.py` | 呈现侧"来源可点、可纠正"面；四动作是 ExperienceEvent `correction_applied` 的上游 | **复用** |
| 纠正载荷 `AuroraCorrectionPayload`（surface/source/semantic_value/is_disconfirming/…） | `backend/app/aurora/correction_types.py` | 纠正动作回执的载荷标准化 | **复用** |
| 干预生命周期（FIX-507 三写面）：交付面 mark_delivered/accepted/dismissed/acted→`record_exposure`/`record_response`（幂等 dedupe+内容寻址 decision_id）+ spine directive 下发 hook + 6h beat `associate_pending_outcomes` 扫描；`InterventionLifecycleEvent`（exposure/accept/edit/reject/start/outcome_observed） | `backend/app/services/intervention_lifecycle_service.py:146/218`、`backend/app/models/intervention_lifecycle.py:29` | intervention 面回执的写真源；本合同**不新增**干预写路径，呈现只读投影 | **复用** |
| 事件登记 `event.v1`：intervention.requested/delivered/exposed/…、action.proposed/accepted/rejected、run.created/status_changed/awaiting_user/user_resumed、outcome.recorded、memory.invalidated | `backend/app/core/event_registry.py:208-459` | ExperienceEvent 的 `receipt_ref` 所指权威事件均已登记；新呈现事件名走该 registry 注册 | **复用** |
| Outcome 账本（D-02/X-08）：`TruthClass`（actual/self_reported/estimated/unknown）；`RUN_RECEIPT_WORK_MATERIALIZED_STATUSES={SUCCEEDED}`；PARTIAL/FAILED receipt 永不升 actual | `backend/app/core/outcome_ledger.py:104/209/412` | `last_valid_outcome.truth_class`；"完成≠精通"的分级语义 | **复用** |
| memory epoch（C-07/M-07）：快照编译钉 epoch；删除/纠正/权限收紧 bump；旧快照必失效重建 | `backend/app/core/context_manager.py:100/246-256` | `ContextSelectionReceipt.input_versions.memory_epoch`；原子性与过期章节 | **复用** |
| 理解条目读面（RF-06 交接的移动端"理解条目"组件）：`claim/confidence/confidence_label/evidence_summary/scope/user_can_correct` | `backend/app/api/v1/experience_readouts.py:90`（`_understanding_claim_payload`） | 移动端消费对齐目标（§7） | **复用，本合同补契约位** |
| 任务级 why-now（**X-01 缺口**） | Aurora 侧已有 `AuroraCoreSessionEntryReason.why_now`（`backend/app/signals/aurora_core_session.py:59`）、`plan_quality_contract.py:211` SECTION_GOAL_FRAME.why_now；但 **ActionPlan/task 级输出契约无字段位**（X-01 REPORT §6.7 自证；WT806 S4 裁口径 A：intervention/proposal 输出=载体→PASS，task 级缺位登记后续卡=本卡） | `action_plan.v1.1` 新增 `why_now` 字段位（§4） | **新增（最小）** |
| 接续读模型（EpisodeResumeView） | 目标/任务/run/outcome 各自权威已存在；`last_confirmed_step`/`pending_human_step`/`expires_at` 组合视图无 | 纯读模型聚合，不建第二任务真值（§5） | **新增（聚合）** |
| proto | `proto/websocket.proto`（InterventionPushMessage/MessageAck）；无 receipt proto。任务域契约为 REST/JSON（X-01 先证：mobile `task_repository.dart` 直发 JSON） | 见 §8 双读与生成入口 | **最小增量** |

> 禁止假设上表之外"类名已存在"；开工由 V4-B06+ 实现卡按当前 HEAD 复核映射（卡边界条款）。

---

## 2. `context_selection_receipt.v1`（上下文回执）

**语义**：一次上下文选择（chat 装配 / 提案依据 / 接续视图 / 干预定向）完成后，记录"读了哪些权威的哪些版本、候选了什么、用了什么、拒了什么、为什么、在哪生效"。正文呈现只用合法依据；debug 侧可看摘要但不泄露被拒内容（ARCHITECTURE_DELTA §新契约最小面 1 原文落实）。

**产生时机**：Context Compiler（+记忆效用门+可用性过滤）完成选择时、在 proposal 发出 / resume view 返回**之前**。同一轮一个 receipt；无选择发生（L0 确定性应答）不产生。

**消费方**：(a) 呈现层——"为什么是这个"面板的来源与 why-now；(b) debug/审计——拒用摘要；(c) 记忆效用门与经验投影（I05/M-06）的遥测锚。

| 字段 | 类型 | 必选 | 默认/unknown 语义 | 来源 |
|---|---|---|---|---|
| `schema_version` | string const `"context_selection_receipt.v1"` | 是 | — | 新（本合同） |
| `receipt_id` | string，服务端生成（`csr_<ulid>`） | 是 | — | 新；幂等键=同一轮可重算不重复计数 |
| `selection_role` | 封闭枚举 `chat_context \| proposal_basis \| resume_view \| intervention_targeting` | 是 | — | 新 |
| `decision_id` | string \| null | 否 | null=无 Aurora 决策参与（纯规则快路） | 复用 spine/decision 关联键 |
| `input_versions` | object | 是 | 各键值可为 null=null 表示"该权威未读取"；**不得**填 0/"" 冒充已读 | 复用各权威版本位 |
| `input_versions.memory_epoch` | int ≥0 \| null | 是 | 快照编译时钉住的 epoch（C-07） | `context_manager.py:100` |
| `input_versions.goal_version` | string \| null | 是 | goal 乐观锁版本 token | 既有 goal 版本 |
| `input_versions.task_version` | string \| null | 是 | task 版本 token | X-03 `version_token` |
| `input_versions.policy_version` | string \| null | 是 | A05 policy 版本 | 既有 policy |
| `input_versions.selector_version` | string | 是 | 选择器实现版本（L0 规则/L2 语义 selector 各自版本串） | 新（ARCHITECTURE_DELTA 明文要求） |
| `candidates` | array&lt;CandidateRef&gt; | 是 | `[]`=选择已运行但无合格候选；字段缺失=旧生产者→读侧按 unknown 处理，**不得**渲染为"无依据可用"或"有依据"任一 | 新（候选集记录） |
| `candidates[].ref` | string，scheme ∈ `ACTION_SOURCE_REF_SCHEMES`（11 scheme） | 是 | — | 复用 `action_plan.py:103` |
| `candidates[].status` | 封闭枚举 `selected \| rejected \| unavailable` | 是 | — | 新 |
| `candidates[].reason_code` | 封闭枚举 `out_of_scope_memory \| stale_epoch \| utility_gate_rejected \| conflicts_confirmed_preference \| permission_denied \| budget_exhausted \| duplicate \| expired` | status≠selected 时必选 | selected 时 null | 新（效用门/过期/权限判定的类型化出口，不喂自由文本） |
| `candidates[].note` | string ≤140 \| null | 否 | null；**debug-only**，不得进用户正文 | 新 |
| `budget` | object `{candidate_scan_limit:int, selected_max:int, clarifications_used:int}` | 是 | — | 对齐澄清预算（≤1 轮）与扫描上限 |
| `why_now` | WhyNow \| null | 否 | null=本轮无任务级 why-now 语义；**缺口补位见 §4** | 新（复用 Aurora 侧词义） |

**不变量**：
- C1 `selected` 候选的 ref 必须真实进入本轮依据面——继承 `memory_use_receipts ⊆ evidence_refs` 同款校验：呈现层引用的依据 ⊆ `status=selected` 集合。
- C2 `reason_code` 是封闭词表；新增值 = bump `v1.x` + 测试冻结断言同步。
- C3 receipt 只读：它不证明"写入成功"，只证明"读与选"；写入成功归 §3 的 committed receipt。

## 3. `experience_event.v1`（呈现回执 / 呈现投影）

**语义**：把权威回执投影成呈现指令（文本/像素/声/触统一入口，V4-F03 消费）。它是呈现事件，**不可授予写权限或表示额外业务事实**（ARCHITECTURE_DELTA 原文）。模型不能直接发"成功音效"；只有本事件且 `commit_state=committed` 才能驱动成功类呈现。

**产生时机**：权威回执落账后由服务端投影器生成（确定性、无模型参与）；经 WS 下发。同 `event_id` 重播不重复触觉/音效（F03 去重）。

| 字段 | 类型 | 必选 | 默认/unknown 语义 | 来源 |
|---|---|---|---|---|
| `schema_version` | string const `"experience_event.v1"` | 是 | — | 新 |
| `event_id` | string 服务端生成 | 是 | 幂等/重播抑制键 | 新 |
| `kind` | 封闭枚举 `state_confirmed \| state_syncing \| correction_applied \| calibration_notice \| resume_available \| progress_delta \| terminal_failed` | 是 | — | 新（最小集；扩展=bump） |
| `receipt_ref` | string，closed-scheme URI：`action_command://<proposal_id>` \| `run://<run_id>` \| `outcome://<outcome_id>` \| `intervention_lifecycle://<decision_id>` \| `calibration_receipt://<ref>` \| `context_selection://<receipt_id>` | kind∈{state_confirmed, progress_delta, correction_applied, calibration_notice} 时**必选** | null 仅允许 kind∈{state_syncing, resume_available, terminal_failed 中非命令类} | 复用 `ACTION_SOURCE_REF_SCHEMES` + D-02/lifecycle 关联键 |
| `commit_state` | 封闭枚举 `committed \| error` | 是 | — | **唯一真源 = X-03 权威回执的 TerminalReason/ACTION_ERROR_CODES，投影器转写，任何上层不得改写** |
| `error_state` | 封闭枚举 `version_conflict \| unauthorized \| not_pending \| expired \| not_found` | commit_state=error 时必选，committed 时必须 null | 与 committed 互斥（§6 表） | 复用 `ACTION_ERROR_CODES` 五值，1:1 映射 |
| `subject` | object `{type: task\|goal\|run\|intervention\|memory\|plan, id, version_token}` | 是 | version_token 为投影时点版本 | 复用 X-03 subject 绑定纪律 |
| `presentation` | object `{modalities: [visual\|audio\|haptic], copy_key: string, asset_ref?: string}` | 是 | modalities 空数组合法（音/触/动效全关价值仍须成立，V4_DONE Q7） | `copy_key` 取冻结文案表键，**不是**模型自由文本；`asset_ref` 仅指向已过审 token 集，模型无权选 |
| `dedupe_key` | string = sha256(receipt_ref + kind + subject.version_token) | 是 | 内容寻址，重播抑制 | 对齐 FIX-507 内容寻址 decision_id 先例 |
| `issued_at` / `expires_at` | timestamp / timestamp\|null | 是 / 否 | expires_at null=不过期 | TTL 对齐 `DEFAULT_PROPOSAL_TTL_SECONDS` 风格 |

**不变量**：
- E1 `kind=state_confirmed` ⇒ `commit_state=committed` 且 `receipt_ref` 必选。无例外。
- E2 `commit_state=error` ⇒ `error_state` 必选，呈现走非成功模态；五错误态不得混入 committed（卡验收第 3 条）。
- E3 事件无权限字段；Flutter 消费端不得由 `kind/subject` 推导任何请求权限（I1）。越权呈现 = 安全缺陷，不是样式问题。
- E4 `subject` 校验失败（跨对象 ID、他人对象）→ 事件不出、记安全遥测（I3）；不降级为"通用成功动画"。

## 4. X-01 why-now 缺口补法（`action_plan.v1.1` 字段位）

WT806 S4 裁定口径 A 成立的前提是"task 级缺位登记后续卡"。本合同把该缺口补进设计——**字段位级最小增量，不改既有列语义**：

- 在 ActionPlan 契约加可选对象字段 `why_now: WhyNow | null`（DB 侧为 tasks 表 1 个 nullable JSONB 列，或并入既有 plan JSONB 块的版本化子键——**由 contract-owner 二选一，本合同不绑死物理落点**）。`action_schema_version` 由 `"action_plan.v1"` bump 为 `"action_plan.v1.1"`；v1 行读出 = `why_now: null`，**不迁移臆测回填**（对齐 ARCHITECTURE_DELTA「老行 unknown，禁止回填臆测」）。
- 词表沿用 Aurora 侧已有词义，不新造第二语义：
  - `statement`: string ≤200，用户可读的"为什么现在做"
  - `basis_refs`: array&lt;closed-scheme ref&gt;，≥1 当 statement 非空（无依据的 why-now = 伪依据，契约层拒，同 `USEFUL_STEP_REASONS` 空集=伪步骤纪律）
  - `expires_at`: timestamp | null——why-now 有时效；过期后呈现层显示"当时的原因"，不得当作当前原因复用
  - `confidence_band`: `high | medium | low | unknown`——审慎标签，不向用户显示虚构精度百分比（对齐 `AURORA_SEMANTIC_POLICY` 受限输出）
- 数据流：proposal 生成时，Aurora 侧既有 `why_now`（`aurora_core_session.py:59`、`plan_quality_contract.py:211`）经受限于白名单的 selector 落入本字段位；**移动端 `WhyThisTodayPanel`/`PriorityReasoning.primary_reason`（`mobile/lib/features/task/presentation/widgets/why_this_today_panel.dart`）为既有渲染面，v1.1 落地时由 contract-owner 接线，本设计不越权改 UI**。
- 读侧门：整块降级纪律与 X-01 相同——v1.1 新子结构任一校验失败 → `why_now` 置 null + WARN（带 task_id 与原因），不影响块内其余 v1 字段投影。

这样 S4 五要素（outcome/step/**why-now**/evidence/mode）在 task 级输出契约内齐备，且对 v1 行为零影响（全 nullable、无 server default，迁移对旧行零写入）。

## 5. `episode_resume_view.v1`（接续读模型）

**语义**：首页接续卡的读模型。**它是读模型，绝非另一份主任务；原 run/task 状态始终优先**（ARCHITECTURE_DELTA 原文）。任何与权威不一致 → 重建视图，不就地修补。

**产生时机**：首页装载时由服务端聚合器按需计算；带 TTL，不落第二真值表（缓存可挂既有投影缓存，key 绑 §1 各版本位）。

| 字段 | 类型 | 必选 | 默认/unknown 语义 |
|---|---|---|---|
| `schema_version` | const `"episode_resume_view.v1"` | 是 | — |
| `goal_ref` / `task_ref` | closed-scheme URI（`goal://`、`task://`） | 是 | 所指对象必须存在且属当前用户 |
| `run_ref` | `run://<run_id>` \| null | 否 | null=无在途 run |
| `last_valid_outcome` | `{outcome_ref: outcome://, truth_class: actual\|self_reported\|estimated\|unknown, recorded_at}` \| null | 否 | truth_class 复用 D-02 `TruthClass`；null=无可引用成果——**不得**以"练了 N 分钟"类替代呈现（MASTER_DESIGN §6：不显示"练了15分钟所以精通"） |
| `last_confirmed_step` | `{step_ref: task\|subtask scheme, description, confirmed_at, version_token}` \| null | 否 | null=无已确认步 |
| `pending_human_step` | `{description, cognitive_ownership: user_core\|shared\|delegated, execution_mode: human\|agent\|hybrid}` \| null | 否 | 词表复用 X-01 `cognitive_ownership` 与 `ExecutionMode`，import 不复制 |
| `expires_at` | timestamp | 是 | 过期 → 呈现不确定性说明，**不强行接续、后台任务不复活**（MASTER_DESIGN 接续时刻） |
| `freshness` | `{context_receipt_ref: context_selection://, computed_at, memory_epoch_at_compute}` | 是 | 绑定本轮 ContextSelectionReceipt；epoch 已变 → 视图 stale，重算 |

## 6. 五错误状态与 committed 的不混用（卡验收 3）

`commit_state=committed` 与 `error_state` 互斥且覆盖完备（终端只有这两类）。`error_state` 五值 **1:1 复用** `ACTION_ERROR_CODES`（`backend/app/core/action_command.py:164`），不造第二词表：

| error_state | 源错误码 | 触发 | 呈现 copy_key（冻结表） | 可重试 |
|---|---|---|---|---|
| `version_conflict` | `ACTION_VERSION_CONFLICT` | 确认前对象/记忆/策略版本已变（含 memory_epoch bump） | `err.version_conflict`（"你的设置已更新，需要重新生成"） | 是（重新生成提案） |
| `unauthorized` | `ACTION_UNAUTHORIZED` | 授权拒绝/跨对象 | `err.unauthorized` | 否（用户侧无动作） |
| `not_pending` | `ACTION_NOT_PENDING` | 提案已终态后再次操作 | `err.not_pending` | 否 |
| `expired` | `ACTION_EXPIRED` | TTL 过（懒转+sweep 已持久化） | `err.expired` | 是（重新生成） |
| `not_found` | `ACTION_NOT_FOUND` | 提案/对象不存在（含误用他用户 ID→按 unauthorized 处理并记安全遥测，不区分泄漏） | `err.not_found` | 否 |

呈现纪律：五态渲染为中性/失败模态，**永不渲染成功**；`terminal_failed` ExperienceEvent 与 committed 事件不得共用以掩盖失败。断网/未知状态查询可用，但不渲染为绿色成功（F03 验收同源）。

## 7. 移动端消费对齐（RF-06 交接「理解条目」组件合同）

既有读面 `_understanding_claim_payload`（`experience_readouts.py:90`）已产出 `claim / confidence / confidence_label / evidence_summary / scope / user_can_correct`。本合同对齐规则（**结论/确定程度/来源/纠正动作相邻**四要素）：

1. **结论**：`claim` 必须可溯源到 `ContextSelectionReceipt.candidates[status=selected].ref`——呈现的每条理解都有 ref；无 selected 依据的 claim 不得渲染为"我理解"。
2. **确定程度**：`confidence_band`（`WhyNow`）/`confidence_label` 用审慎标签（如"较确定/不确定"），禁止虚构精度百分比。
3. **来源**：selected ref 原样可点（记忆/材料/任务），点击走既有 tray/detail 面；被拒候选不出现在正文（debug 面才可见摘要）。
4. **纠正动作相邻**：每条理解条目同组件内固定携带纠正入口（`user_can_correct=true` 恒成立），动作即 A-06 四动作封闭词表 `not_relevant/wrong/change_scope/delete`，载荷经 `AuroraCorrectionPayload.normalize`，全部委托既有权威写路径（FIX-507 三写面含 correction 记账）——本合同不新增纠正写路径。纠正确认后 UI 先转"等待真实回执"，收到 `correction_applied` ExperienceEvent（`receipt_ref` 指向 lifecycle/记忆权威）再转态（MASTER_DESIGN 校准时刻）。

## 8. 版本化、双读与生成入口

- **版本策略**：三契约首版 `.v1`；只加必填=false 的字段 → `.v1.x` 递增；改必填性/改词表成员/改字段语义 → `.v2` 新读门（不 in-place 改语义）。`ACTION_ERROR_CODES`/`cognitive_ownership`/`ExecutionMode` 等既有词表**只复用不复制**，其扩展归各自 owner。
- **旧客户端双读**：REST/JSON 面（ContextSelectionReceipt、EpisodeResumeView、ActionPlan v1.1）——旧客户端忽略未知可选字段（Dart `fromJson` 容错 + 服务端不删字段）；`why_now=null`/字段缺失对 v1 行为完全等价。WS 面（ExperienceEvent）——旧客户端对未注册 `kind` 一律降级为"忽略 + 静默计数"，**不得**当成功处理。双读用例：同一权威回执分别喂 v1 消费方与 v1.1 消费方，断言 v1 路径行为逐字节不变（进 V4-B06+ 实现卡测试清单）。
- **proto 入口**：本合同初版 REST/JSON 为主（X-01 先证：任务域契约载体 REST/JSON 非 gRPC）。ExperienceEvent 需 WS 下发时，由 contract-owner 在 `proto/websocket.proto` 增 `ExperienceEventFrame`（`oneof` 挂 `WebSocketMessage`），随后 `make proto-gen` 生成 Go/Dart/Python——**禁手改 `*/gen/` 与 SQLC 产物**（硬规则 1）。schema 列（如 tasks.why_now JSONB）唯一入口 Alembic 迁移单头（硬规则 2）。
- **开关**：三个契约均 shadow 写先行、默认读关闭；off/shadow/live 登记进既有 kill-switch manifest，不造第二组常量（ARCHITECTURE_DELTA 变更策略）。
- **跨对象拒绝**：`(subject_type, subject_id)` 与 ref scheme 二重校验（I3）；`run://` 解析 `agent_runs` 且校验属主（X-05 lineage 同款）；失败拒绝不 500 泄漏。

## 9. 反例——什么不是回执（冻结反例，实现卡不得漂移）

| 反例 | 为什么不是 |
|---|---|
| 模型自评"已完成/已理解"的文本 | 无权威回执；模型只能提议。渲染它 = 假成功 |
| WS `MessageAck` | 传输层确认，不证明业务 committed |
| `tracking_events` 遥测行 | 观测数据，无权威语义，不可驱动状态卡 |
| proposal 已 accept 但 commit 未完成 | `committed` 唯一真源是 X-03 receipt；accepted≠committed，不得放成功音/震 |
| 用 ExperienceEvent 驱动删除任务/授权 | 违反 I1；事件无权限语义 |
| "保存了一条记忆"的回执当"任务已修改"呈现 | 记忆写入不是任务域 committed（F03 验收原句） |
| 证据登记（evidence 登账）当"精通"呈现 | D-02 分级：self_report 永不升 actual；呈现必须带 truth_class |
| harness/mock 生成的 receipt（Q-01 mock-provider 类） | 非生产写路径产物，不得进用户可见成功面 |
| 过期 EpisodeResumeView 自动接续 | `expires_at` 过期只允许"说明不确定性"，不允许静默续跑旧授权 |

## 10. 最小示例

见 `examples/`：`context_selection_receipt.example.json`、`experience_event_committed.example.json`、`experience_event_error.example.json`、`episode_resume_view.example.json`、`counterexamples.json`（每个反例附机器可读 `violates` 字段）。

---

## 11. 与其他卡/面的关系

- **FIX-507 三写面**：intervention 面的 exposure/response/associate 写路径已由 wt797 接线（FIXED@8e503cd8）；本合同只做呈现投影与纠正动作的只读对齐，不加第四写面。
- **V4-F03**（experience-presenter 锁）：本合同是它的输入规格；F03 负责去重/重播抑制/对象版本校验的实现。
- **V4-I02/I03/I04**：ContextSelectionReceipt 的 `reason_code.utility_gate_rejected` 等是效用门与受限语义选择的类型化出口，门逻辑归实现卡，本合同只冻结出口词表。
- **V4-B06+**：实现按 §8 生成入口与开关策略；契约/迁移由单一 owner 单独合并。
