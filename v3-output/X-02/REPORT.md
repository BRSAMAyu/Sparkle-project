# X-02 · Human/Agent/Hybrid Allocation Policy（delegation rubric）— REPORT

- Worker: X-02（Apex / stream ACTION / risk high / locks: action-policy）
- Base: `1ea854c9`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt4`）
- 交付物：`changes.patch`（同目录）+ `EVAL_RESULTS.md`（85 场景盲评基准）
- 状态：READY_FOR_REVIEW（禁 commit/push，按纪律交 patch）

---

## 1. 解决的实际问题

本卡之前，仓库内**不存在任何 delegation rubric**：一个步骤由 human / agent / hybrid
谁执行，完全由 LLM 自由裁量（"我来帮你做"倾向）——学习型任务的代写路径无任何拦截
（红态证据见 §5）。本卡把 HUMAN_AGENT_HYBRID.md 八维分配机制化为**单一权威纯函数
决策核心** + 可选 LLM 灰区通道 + 结构化决策记录，直接产出 X-01 已上线的
execution_mode / cognitive_ownership 列组合判定，并作为 A-04（Aurora 联合决策）
与 X-05（Unified Run）的上游输入接口。

## 2. 设计：可行集 + 分层选择（而非打分黑箱）

### 2.1 决策核心 `backend/app/services/action_allocation_policy.py`

```
decide_allocation(factors) -> AllocationDecision{mode, why[封闭reason codes], confidence,
                        feasible_modes, requires_human_approval, requires_user_authored_evidence,
                        recommended_cognitive_ownership, recommended_evidence_kinds}
```

- **Guard 层（硬规则，LLM 不可越）**——先算**可行集**（feasible set）：
  - R1 `high/critical` 或 `medium+不可逆` → 剔除 agent + `requires_human_approval`
  - R4 具身 / R5 restricted（agent 连准备面都无权限，仅 human）/
    R5a sensitive（非 agent）/ R6 系统置信 <0.4（非 agent）
  - **G1 学习守卫**：`task_type ∈ {LEARNING,TRAINING,REFLECTION}` 或
    `cognitive_ownership=user_core` 或 `learning_goal=True` → 剔除 agent
- **选择层**（feasible 内按优先级）：显式意图 X1/X2 > 持久偏好 U1-U3 > ownership×
  tool-advantage 默认判定 D1-D6；R0 因子缺失保守 hybrid
- **修饰层**：T1 仅救 D4（delegated+优势未确证+紧急+置信足够→agent）；
  T2 偏好 agent 但工具无优势（AI 反而更慢）→ 降 hybrid
- **语义层**（可选通道，默认 `SPARKLE_ALLOCATION_SEMANTIC_ENABLED=False`）：仅对
  D6/R0 灰区残留生效；**LLM 的 mode 提议必须在代码算出的 feasible set 内**（越界
  S2 拒收保规则默认——边界由代码强制，不信任 prompt）；熔断（3 连败开 300s）/
  限频 / 5s 超时 / 任何失败一律降级规则默认（M-02 gate 同款纪律）；语义层永不能
  清除 guard 标记（R1 审批、学习证据要求），confidence 封顶 0.75

关键取舍：**可行集模式而非逐条 first-match-wins**——多维 guard 可同时生效
（如 critical+具身+学习），feasible set 天然表达交集，why 集合完整记录每条剔除
理由，选择层只在可行集内做偏好排序。这让「LLM 只能越不过硬规则」成为结构性质
而非提示词性质。

### 2.2 「谁动脑 × 谁执行」组合判定（X-01 F5 文档警示 → 本卡硬规则）

`recommended_cognitive_ownership` 按最终 mode 推导（agent→delegated、
hybrid→user_core/shared、human→user_core/delegated），**永不落 X-01 F5 矛盾集**
`{agent×user_core, hybrid×delegated, human×shared}`。证据口径（R2 返修 F2 改正，
原文本把 62K 网格规模误安在专项测试头上）：

- `test_recommended_ownership_never_lands_in_f5_contradiction_set`：专项网格
  4×4×4×3×3×3 = **1,728 组合**，逐组断言矛盾集零命中；
- `test_all_reason_codes_are_in_closed_vocabulary`：**62,208 组合**全笛卡尔网格
  （封闭词表 + mode∈feasible）；**本轮返修已把 F5 矛盾集断言与
  `semantic_eligible ⇒ not learning_guard` 不变式并入同一 62K 循环**（R2 F2/F5），
  两条不变式均拿到 62K 全网格真覆盖。

`validate_action_plan_allocation` 把 F5 矛盾 + 学习守卫冲突落成可校验 violations；
`merge_into_action_plan` 构造性改写 planner 产出的坏组合（测试证明改写后零 violation）。

### 2.3 防代写守卫（acceptance ②）

- G1：学习型任务 feasible 永不含 agent——显式「帮我写完」/ 偏好 agent / 时间紧迫
  均不翻盘（X2 降级路径 + U4 部分满足，why 完整留痕）
- G2：学习 × hybrid → `requires_user_authored_evidence=True` +
  `recommended_evidence_kinds ⊆ {artifact, code, quiz_result, file}`（X-01
  EVIDENCE_KINDS 的 user-authored 子集）
- `vet_agent_offer(offer_kind, factors)`：封闭供给形态词表
  {complete_answer, draft, outline, materials, hint, review, mechanical}——
  学习守卫下 **complete_answer 一律拒（G3，建议降级 outline）**；user_core 下
  draft 也拒（G4）；outline/materials/hint/review（HYBRID handoff 准备面）不误伤；
  R1 下 mechanical 必须挂 human approval。**R2 返修 F1 后补齐两条硬边界**：
  - **R5 权限检查**：restricted = agent 零接触 → **一切**供给形态拒收（探针 P2
    原 allowed=True 已翻转为拒）；sensitive = 禁全自动 agent → 拒收
    complete_answer（建议降级 draft）与 mechanical，保留 hybrid 准备面；
  - **R1 错配防御**：approval 按「当下因子 `_high_risk(factors)` ∨ decision
    审批旗标」取或——传入陈旧/异因子低风险决策不再能替高风险因子免检
    （探针 P1 原 allowed=True 无审批已翻转为挂审批）。R6 刻意不在 vet 查
    （mode 可行性归 decide_allocation，docstring 已文档化）。

### 2.4 决策记录与事件（A-04 / X-05 / D-02 消费面）

- `AllocationDecision.to_dict()`：schema_version=allocation.v1 的结构化记录
  （mode/why/confidence/layer/feasible/两个 requires/ownership 推荐），JSON 可序列化
- `decision_id(factors)`：确定性 id（同因子同结论同 id，`alloc_` 前缀），对接
  X-01 `decision://` ref scheme
- 事件名 **`allocation.decision_recorded`** 已按 D-01 扩词表流程入 event_registry
  （stage=DECISION，aggregate=allocation_decision，与 `routing.decision_recorded`
  同族）；`build_allocation_event_metadata` 走 `build_event_metadata` shared-fields
  契约（event_id/user_id/source/correlation{task_id UUID 规范化}/occurred_at），
  落 outbox 属消费方（A-04/X-05）。冻结 sha256 已按流程故意 bump（33→34 names，
  注释注明 X-02 变更）
- Metrics：`sparkle_allocation_decisions_total{mode,layer}` +
  `sparkle_allocation_guard_rejections_total{guard}`（只在 stateful 包装层递增；
  纯核心无 IO——评测可复现）

## 3. 交付物清单（全部在 changes.patch 内）

| 文件 | 内容 |
|---|---|
| `backend/app/services/action_allocation_policy.py` | 决策核心（新，~700 行）：Guard/选择/修饰三层 + 语义层 + 决策记录 + event 构造 |
| `backend/app/core/event_registry.py` | +`allocation.decision_recorded`（封闭词表扩 1 名） |
| `backend/app/core/business_metrics.py` | +2 个 allocation Counter |
| `backend/app/config/settings.py` | +`SPARKLE_ALLOCATION_SEMANTIC_*` 4 项（默认关） |
| `backend/tests/unit/test_action_allocation_policy.py` | 66 项（含 R2 返修 +5）：词表双冻结（精确集+sha256）/guard×选择×修饰/韧性/F5 矛盾集网格（62K 网格含 F5+semantic 不变式）/X-01 组合面/事件/语义层 |
| `backend/tests/unit/test_action_allocation_guard.py` | 38 项（含 R2 返修 +19）：防代写守卫专项（含 FreeformAgentBaseline 对照 + F1 错配对抗 + R5 全谱） |
| `backend/tests/unit/test_action_allocation_eval.py` | 8 项：盲评阈值守卫（≥0.90 / high-risk auto=0 / 学习 agent=0 / 逐场景不变式 / 确定性） |
| `backend/tests/fixtures/action_allocation_eval_v1.json` | 85 场景盲评集（15 类 + 对抗叠加） |
| `backend/tests/contract/test_event_registry_contract.py` | 冻结 sha256 故意 bump（33→34，注释注明） |
| `scripts/devtools/x02_run_allocation_eval.py` | 评测报告生成器（EVAL_RESULTS.md 落盘） |

## 4. 验证证据（2026-09-19，wt4 @ 1ea854c9 + 本改动）

| 验证 | 命令 | 结果 |
|---|---|---|
| X-02 全套 | `pytest tests/unit/test_action_allocation_{policy,guard,eval}.py` | 首轮 **88 passed**；R2 返修后 **112 passed**（+24，见 §8） |
| 盲评基准 | 同上 eval + devtools 生成器 | **85/85 = 1.0000**（阈值 ≥0.90）；不变式违例 0 |
| high-risk auto=0 | eval 断言（类别断言 + 按因子动态断言双保险） | 8 场景 agent=0，全部 requires_human_approval |
| 学习不代写 | eval + guard 套件 | 学习守卫生效场景 agent=0（含 4 个全压力叠加对抗样例） |
| D-01 契约回归 | `pytest tests/contract/test_event_registry_contract.py` | 31/32 过（R2 返修 F6.3 计数改正；首轮误报 33/34）；1 败为**基线预存**（见 §6.3） |
| X-01 回归 | `pytest tests/unit/test_action_plan_contract.py tests/unit/test_action_plan_migration_sqlite.py tests/test_action_plan_v3_integration.py tests/unit/test_startup_smoke.py` | 40+29 passed |
| 契约回归 | `pytest tests/contract/test_api_router_openapi_contract.py` | passed |
| 循环依赖 | `python -c "import app.main"` | OK（延迟 import 解 services→core 环） |
| 风格 | `ruff check` + `black --line-length 120`（改动文件全量） | clean |

测试环境：homebrew python3.11（与运行中服务同环境），未触碰 dev PG，未重启任何服务。

### 4.1 红绿证据（防代写守卫）

- **RED**（2026-09-19 实证）：`test_action_allocation_guard.py` 首轮，模块移走后运行 →
  `ModuleNotFoundError: No module named 'app.services.action_allocation_policy'`（真红，
  与 X-01 红态口径一致）；且 `FreeformAgentBaseline` mock 固化现状威胁——本卡前
  仓库 0 拦截，学习型任务 agent+complete_answer 路径完全开放
- **GREEN**：模块就位后 19 项全绿（5 种学习触发形态 feasible 无 agent；显式委托/
  偏好/紧迫三压力不翻盘；hybrid 携带 user-authored 证据要求；complete_answer 拒 +
  降级建议；user_core draft 拒；outline/materials/hint/review 不误伤）

### 4.2 真实 LLM 冒烟（预算内 5/5 次）

`SPARKLE_ALLOCATION_SEMANTIC_ENABLED=true`（env 覆盖，未改任何配置文件），5 个灰区
场景走 `ActionAllocationPolicy.evaluate` → llm_service.chat_json（qwen3.8-flash）：

- 2/5 语义精化成功：mode=hybrid（均与规则默认同向），confidence 0.72/0.75（封顶内），
  均在 feasible set 内，layer=semantic + S1 留痕
- 3/5 5s 超时 → 干净降级规则默认（`timeout → rule default kept` 日志实证）——与
  M-02 记录的 qwen3.8-flash thinking 档延迟一致；降级路径与熔断计数按设计工作
- 0 次越界、0 异常上抛、guard 标记无丢失；结论：**语义层默认关是正确决策**，
  开启需接受 ~40% 超时率（可后续调 timeout 或换非 thinking 模型）

### 4.3 盲评诚实边界（必读）

85 场景 1.0000 的口径已在 EVAL_RESULTS.md 声明：target 与 rubric 同源于
HUMAN_AGENT_HYBRID.md 且同工标注——它证明 **rubric↔文档原则一致性 + 回归防护**，
不等价独立多标注者一致性。真正的硬验收是**按因子动态判定的结构性不变式**
（high-risk auto=0 / 学习 agent=0 / restricted=human / high-risk 必带审批），
与类别标签无关，逐场景断言全过。语义层的真实增益（灰区精化质量）由 LLM 冒烟
另证（§4.2，样本小、结论保守）。

## 5. 与地基的对接（不重建，只增量）

- **X-01**：mode 词表 import `ExecutionMode`（不造第二枚举，测试冻结）；
  ownership/risk 直接用 `CognitiveOwnership`/`RiskClass`；证据建议 ⊆ X-01
  EVIDENCE_KINDS；`merge_into_action_plan` 以 ActionPlanContract 为唯一写路径
  （不绕过 X-01 读侧门/写侧校验）；F5 文档警示落成硬规则
- **A-01（未开工）**：纯函数核心 + 决策记录结构即 A-04/X-05 的消费接口——
  无 DB/IO 依赖，可被 Aurora decision_fns 同款方式组合
- **C-01**：task_ref 复用 X-01 的 `task://` scheme（超集兼容）；决策记录与
  decision_context 的 why_included 同为封闭 reason code 风格
- **D-01**：事件名按扩词表流程注册 + 冻结 sha256 故意 bump；metadata 走
  build_event_metadata 共享字段契约
- **M-02**：语义层照搬 gate 纪律（熔断/限频/超时/降级/不自我授权）

## 6. 遗留风险与限制

1. **未接线生产链路**（刻意）：orchestrator/planner 何时调 decide_allocation、
   事件何时落 outbox 属 X-05/A-04 消费卡；本卡交付决策核心 + 消费接口
   （本仓所有调用点仍走旧路径，零行为变化）
2. 因子从真实信号（聊天/任务/profile）到 AllocationFactors 的**提取器**未建——
   现在 from_task 只投影 X-01 列 + 调用方显式传意图/偏好；灰区比例取决于上游
   提取质量，语义层是为它兜底的
3. `test_truth_path_modules_never_read_client_telemetry[app/state_aggregator/service.py]`
   **基线预存失败**（git stash 对照实证：干净基线同败；state_aggregator 注释提及
   tracking_events 触发 D-01 文本扫描）——非本卡引入，留给 D-01 维护者
4. 语义层真实超时率 ~40%（flash thinking 档 5s）：开启前需调
   `SPARKLE_ALLOCATION_SEMANTIC_TIMEOUT_SECONDS` 或换模型；默认关，无生产影响
5. 置信阈值（0.4/0.6）、T1/T2 修饰条件、USER_AUTHORED_EVIDENCE_KINDS 是首版
   校准值；调整需过评测集回归（85 场景阈值守卫会拦回退）
6. `AllocationFactors.from_task` 的 learning_goal 目前需调用方显式传
   （可从 smallest_useful_step.useful_because 含 builds_capability 推导——
   留给提取器消费卡，避免本卡偷偷读 guide_json）

## 7. 收工清理（首轮，已执行）

- 删：worktree `backend/.env`（冒烟用临时副本）、`backend/app/gen`（借入件，仅
  为回归测试链完整，不入 patch）、`/tmp/x02_*` 脚本与日志
- 留：代码/测试/fixture/devtools 脚本 + 本报告与 EVAL_RESULTS（v3-output/X-02）
- 未起任何进程/模拟器；未触 DB；未 commit/push

## 8. R2 返修记录（2026-09-19 第二轮，对应 REVIEW_RECEIPT_2 §8）

第 0 步自验：开工前 `git diff` 与首轮 `changes.patch` 逐文件字节比对（4 tracked
+ 6 untracked 全一致）——前任验收员的变异实验还原确认属实，无残留。基线对照
`/tmp/x02-rw-baseline`（本轮收工已清）。

| 发现 | 处置 | 落点 |
|---|---|---|
| **F1 (P2)** `vet_agent_offer` 错配绕过 R1 + 不查 R5 | ① R1 改为 `(decision.requires_human_approval) ∨ _high_risk(factors)` 取或——陈旧/异因子决策不能替当下因子免检；② vet 入口补 R5：restricted 一切供给拒收 / sensitive 拒收 complete_answer（降级建议 draft）+ mechanical、保留 hybrid 准备面（与 decide_allocation 的 feasible 语义逐级同构）；③ R6 豁免已文档化（mode 可行性归 decide_allocation，非供给形态安全性）；④ OFFER_VERDICT_REASONS +2 码（`R5.restricted_agent_supply_forbidden` / `R5.sensitive_autonomous_supply_forbidden`），按冻结协议 bump `ALLOCATION_POLICY_VERSION` → **allocation.v1.1**（决策 reason 词表与记录 schema 不变；经 R2 指令性返修 + R1 delta 复核两道评审） | `action_allocation_policy.py` `vet_agent_offer` + 模块 docstring |
| **F2 (P3)** 「6 万网格证明 F5」归属不实 | REPORT §2.2 改口径（62,208 网格 vs 1,728 专项网格分列）；F5 矛盾集断言并入 62K 循环拿到真覆盖 | REPORT + `test_all_reason_codes_are_in_closed_vocabulary` |
| **F3 (P3)** X2 显式委托无 T2 检查 | 裁决为**文档化豁免**（而非补 T2）：当轮显式意图 = 用户主权最强信号，系统不以成本启发替用户翻盘；硬规则 feasible 照常生效。已固化对比测试（X2+无优势→agent vs U1+无优势→hybrid+T2） | `_decide` X2 分支注释 + 模块 docstring + `test_explicit_delegate_exempts_t2_cost_check` |
| **F5 (P3)** 语义精化不重算 G2 旗标（隐式不变式） | 双保险：① `semantic_eligible ⇒ not learning_guard` 显式断言并入 62K 网格；② `_semantic_refine` 改 mode 后按 `(learning, mode)` 构造性重算 G2 三件套（旗标/证据类型/reason），未来放开灰区不沿用旧 mode 旗标；两个方向（hybrid→human 清除 / human→hybrid 补上）均有离线构造测试 | `_semantic_refine` + 网格断言 + `test_semantic_refine_recomputes_g2_evidence_flags` |
| **F6.1** merge 的 isinstance 防御在 replace 之后（死代码） | 防御前移至属性访问/replace 之前；非 ActionPlanContract 原样返还 + 决策照常返回 | `merge_into_action_plan` + `test_merge_with_foreign_plan_object_passes_through` |
| **F6.2** S2 边界仅 1 测试拦截 | 补「high-risk 灰区 + LLM 提议 agent → S2 拒收 + 审批旗标保留」显式对抗用例 | `test_semantic_agent_proposal_under_high_risk_rejected` |
| **F6.3** 契约计数 33/34 不实 | 改正为 31/32（§4 表） | REPORT |
| **F6.5** `_breaker_record_failure` 直呼 `time.monotonic` | 改用实例可注入 `now_fn`；离线断言 open_until 精确值 | `_breaker_record_failure` + `test_breaker_uses_injected_clock` |

**F4（F5 双副本无真源对账）未在本轮处理**——X-01 侧 F5 仍为 docstring，
无可 import 真源，复制是现状唯一选择；R2 建议的「与 action_plan.py docstring
文本对账」属跨卡协调（A-04/X-05 消费前），留待 Leader 裁决是否单开卡。
F6.4（app/gen 借入复现前提）与 F6.6（D-01 文档 33→35 过期）为 Leader/主会话
操作项，非本卡。

### 8.1 返修轮验证（全部本机重跑，2026-09-19）

| 验证 | 结果 |
|---|---|
| X-02 全套（policy 66 + guard 38 + eval 8） | **112 passed**（首轮 88 + 新增 24） |
| R2 探针 P1 复现 | mechanical+高风险因子+低风险决策 → `allowed=True, requires_human_approval=True, R1.autonomous_execution_needs_approval`（**已翻转**） |
| R2 探针 P2 复现 | complete_answer+restricted → `allowed=False, R5.restricted_agent_supply_forbidden`（**已翻转**） |
| R5 全谱对称性 | restricted：7/7 形态全拒；sensitive：complete_answer/mechanical 拒、outline/draft 等 5 形态放行 |
| D-01 契约 | 31 passed + 1 预存败（state_aggregator，与 R2 实测一致） |
| X-01 回归（借 `app/gen` 后删） | 69 passed（40+29） |
| API router 契约 / `import app.main` | 3 passed / OK |
| ruff + black(120) | 改动文件全量 clean |
| 决策核心行为不变式 | fixture 85 场景盲评 1.0000 保持（decide_allocation 规则路径零改动；本轮全部修改集中在 vet 入口/语义层加固/防御前移） |

真实 LLM 冒烟不重跑（费用纪律；语义层改动是防御性重算，当前路径不可达，
行为等价性由 `test_semantic_refine_recomputes_g2_evidence_flags` 离线证明）。
