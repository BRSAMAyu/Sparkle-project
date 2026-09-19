# X-02 REVIEW_RECEIPT_2 — R2 深层验收（DeepAudit）

- Reviewer: R2（V3 Fleet · DeepAudit 路线）
- 日期: 2026-09-19
- 对象: wt4 @ `1ea854c9` + X-02 未提交改动（10 文件 / 2437 行 patch，状态 READY_FOR_REVIEW）
- 方法: 主仓只读；wt4 内重跑全部自报验证 + 5 组变异实验（做完还原，`diff` 确认字节一致）+ 9 组对抗探针；D-01 冲突按 wt8（M-07）实际 diff 三方推演。未重跑真实 LLM 冒烟（费用纪律，静态审 Worker 证据）。

---

## 0. 自报核验总表（全部独立重跑）

| Worker 声称 | 重验结果 | 证据 |
|---|---|---|
| X-02 全套 88 测试绿 | **属实**（重跑两次含变异还原后） | `pytest tests/unit/test_action_allocation_{policy,guard,eval}.py -q` → `88 passed` |
| X-01 回归 40+29 passed | **属实但有环境前提**：裸 worktree 下 `test_action_plan_v3_integration.py`（collection error）与 `test_startup_smoke.py` 5 项均 `ModuleNotFoundError: No module named 'app.gen'`（proto 生成件未入库，Worker §7 已声明借入后删）。借入主仓 `app/gen` 后重跑 → **69 passed**（40+29 成立） | 命令输出见本节 |
| D-01 契约 33/34 过、1 败基线预存 | **属实（计数 nit）**：实际 `31 passed, 1 failed`，败者 `test_truth_path_modules_never_read_client_telemetry[app/state_aggregator/service.py]`（state_aggregator 文件不在 X-02 patch 内，预存可信）；REPORT 写 33/34，实际 31/32 | `pytest tests/contract/test_event_registry_contract.py -q` |
| 规则层独跑盲评 1.0000（85 场景） | **属实**（eval 套件 8 项全绿即含 0.90 阈值 + 逐场景不变式 + 确定性双跑） | `pytest tests/unit/test_action_allocation_eval.py -q` |
| 85 场景、含 11 对抗叠加 | **属实**：fixture 85 条、**16 类**（REPORT 表格同；任务卡摘要"15 类"为汇总口径，交付物自报 16 类，一致） | fixture 逐条核对 |
| 零生产接线 | **属实**：`grep -rn "decide_allocation|vet_agent_offer|ActionAllocationPolicy"` 仓内命中仅自身/自家测试/注释 | grep 输出（见 §5.6） |
| 语义层默认关 | **属实**：`settings.py:762 SPARKLE_ALLOCATION_SEMANTIC_ENABLED: bool = False` + 单测 `test_semantic_disabled_by_default` + 变异无关独立验证 | settings diff |
| 事件 status=reserved | **属实且语义正确**：D-01 reserved=生产者未上线禁造假数据，X-02 零接线与 reserved 自洽 | `event_registry.py` diff |

---

## 1. 风险面 1：守卫真实性（变异实验）

**Verdict: PASS（5/5 变异必红），守卫非假防线。**

| 变异 | 手法 | 结果 |
|---|---|---|
| M1 删 R1 | `if _high_risk(factors):` → `if False and ...` | **6 failed**（含 eval high-risk 不变式） |
| M2 删 G1 | `_learning_guard_active` 首行 `return False` | **16 failed**（guard 套件大面积红） |
| M3 S2 越界静默接受 | `if mode not in feasible:` → `if False and ...` | **1 failed**（`test_semantic_outside_feasible_is_rejected`） |
| M4 审批旗标永不置位 | `requires_approval = False` | **6 failed** |
| M5 R5 restricted 不剔 hybrid | 删 `feasible.discard("hybrid")` | **3 failed** |

每轮变异后 `cp /tmp/x02_aap_backup.py` 还原，最终 `diff` 字节一致 + 88 全绿复核。

**审计问「LLM 灰区通道开启时 high-risk 还能被翻到 agent 吗 / 审批流谁触发」——实测（探针 P3）：**
高风险灰区因子（risk=high, reversible=False, tool=high, ownership 未知→D6 eligible）+ 开语义层 + LLM 提议 `agent`：
```
mode=hybrid layer=semantic_fallback requires_human_approval=True
why=('R1.high_risk_requires_human_approval','D6.gray_zone_default_hybrid','S2.semantic_outside_feasible_rejected')
feasible=('human','hybrid')
```
R1 先剔除 agent → LLM 提议越界 → S2 拒收保规则默认；`requires_human_approval` 经 `replace()` 保留（`action_allocation_policy.py:905-915` 未触碰该字段），审批触发属 X-05 消费契约（本卡零接线，旗标即契约）。restricted 灰区 + LLM 提议 hybrid 同样被 S2 拒（探针 P9，feasible 只剩 human）。

**薄点（P3-4）**：M3 只有 1 个测试拦截——S2 边界是结构性强制（代码路径唯一），但测试冗余度低；建议把「high-risk + LLM 提议 agent → S2」写成 eval 套件的显式用例。

---

## 2. 风险面 2：盲评口径自证

**Verdict: PASS（声明如实且充分）。**

- `EVAL_RESULTS.md` 尾部「口径声明（诚实边界）」+ `REPORT.md §4.3` 双处明示：target 与 rubric 同源同工标注，证明的是 **rubric↔HUMAN_AGENT_HYBRID.md 原则一致性 + 回归防护**，不等价独立标注一致性。声明措辞足以防误读（"真正的硬验收是按因子动态判定的结构性不变式"）。
- 硬守卫确实独立于标签：`test_action_allocation_eval.py:106-131` 逐场景按 `_learning_guard_active/_high_risk/privacy/embodiment` **从因子动态推导**断言（不读 category）；`x02_run_allocation_eval.py:58-71` 同逻辑。类别断言（`test_high_risk_auto_agent_is_zero`）与动态断言双保险成立。
- 「85=1.0000」因同源标注不构成正确性证明——Worker 未夸大此点。

**但「6 万组合网格」的归属有假（→发现 F2）**：`REPORT.md §2.2` 称 F5 矛盾集零命中由"6 万组合网格遍历测试冻结（`test_recommended_ownership_never_lands_in_f5_contradiction_set`）"证明。实测两网格规模：

- `test_all_reason_codes_are_in_closed_vocabulary`（`test_action_allocation_policy.py:414-449`）：4×3×3×3×3×3×2⁶ = **62,208 组合**，全笛卡尔（非采样）——但它只断言 why 封闭集与 `mode ∈ feasible`，**不断言 F5**。
- `test_recommended_ownership_never_lands_in_f5_contradiction_set`（`test_action_allocation_policy.py:467-488`）：4×4×4×3×3×3 = **1,728 组合**。

REPORT 把 62,208 的规模安在了 1,728 的测试头上（夸大 ~36×）。不变式本身成立（`_recommend_ownership` 是 (mode, ownership, learning) 上的全函数、按构造避开三对矛盾；1,728 网格 + 62,208 网格实测零命中），属**证据归属错误**而非不变式失效。

---

## 3. 风险面 3：可行集空集与降级语义

**Verdict: PASS（结构证明）。**

- Guard 层只 `discard("agent")` / `discard("hybrid")`（`action_allocation_policy.py:439-457`），**没有任何路径剔除 human** → 可行集恒非空、恒含 human。选择层 `feasible_ordered[0] if feasible_ordered else "human"`（:472/:478）是防御性死代码。R5 restricted 最严场景 feasible={human} 单元素集，eval 有实测（`x02-pv01..03`、探针 P9）。
- LLM 通道前置条件 `semantic_eligible`（gray/insufficient tier）+ feasible 非空恒成立 → 无空集连锁。低置信 + 灰区 + 超时组合：R6 剔 agent → feasible={human,hybrid}，D6 默认 hybrid，超时 `asyncio.wait_for` → `TimeoutError` → 熔断计数 + 规则默认（:874-882），资源无泄漏（无句柄持有）。
- `decide_allocation` 对任意输入不 raise：catch-all 降级 `E1 + hybrid + 0.3`（:419-431）；探针 `{"garbage": object()}` 过。

---

## 4. 风险面 4：X-01 F5 矛盾集断言真实性

**Verdict: PASS（当前），附结构性风险（F4）。**

- X-01 真源形态核实：`app/core/action_plan.py:47-49` 的 F5 只是 **docstring 文档级警示**，X-01 未提供可 import 的机器可读常量。X-02 在模块（`validate_action_plan_allocation`:624-648）与测试（`F5_CONTRADICTIONS`:464）各持一份硬编码三对矛盾——**现状下不存在可 import 的真源，复制是唯一选择**，不构成违规。
- 风险：X-01 若日后把 F5 机制化为常量并扩语义（如新增第 4 对），X-02 两处副本静默过期、测试假绿。建议 X-02 侧加一条「与 action_plan.py docstring 文本对账」或推动 F5 上提为共享常量（A-04/X-05 消费前）。
- 「既传 mode 又传 ownership 谁赢」：`validate_action_plan_allocation` 校验 plan 自身组合（报 violations，不改写）；`merge_into_action_plan` 以**决策为准**构造性改写（:668-675），改写后自洽有测试（`test_merge_corrects_agent_learning_plan_to_hybrid` 同断言 `validate == ()`）。语义清晰无双主。

---

## 5. 风险面 5：D-01 词表合入冲突（重点）

**Verdict: 冲突真实存在，非 Worker 过错（双卡均按流程走），但**合入次序决定谁做重冻**，操作清单如下。**

### 5.1 冲突形态（基于 wt4 与 wt8 实际 diff）

| 文件 | wt4 (X-02) | wt8 (M-07) | 合入推演 |
|---|---|---|---|
| `backend/app/core/event_registry.py` | DECISION 段（~L192）插 `allocation.decision_recorded` | STATE_UPDATE 段（~L359）插 `memory.invalidated` + `CORRELATION_KEYS`/`CorrelationIds` 加 `memory_id`（~L438-476） | **hunk 不相交，git 三方合并自动干净** → 35 names |
| `backend/tests/contract/test_event_registry_contract.py` | L46-53 `_FROZEN_VOCABULARY_SHA256` 由 `4e8ccdcd…` → `a9f01867…`（+注释块） | 同一 L46-49 由 `4e8ccdcd…` → `c2815560…`（+注释块） | **同一行区间、同基线、不同目标值 → 必然文本冲突** |

两张冻结哈希各自只对 34 名版本正确；**任一侧直接采纳都会使合并态（35 名）的契约测试假红**（sha 对不上 35 名集合）。

### 5.2 「后合入者重冻到 35」操作清单

前提：主仓当前 `4e8ccdcd…`（33 名，实测 `grep -c 'name="' = 33`）。设先合 X-02、后合 M-07（次序反之同理，责任在后合者）：

1. 合入 X-02 patch（event_registry.py + 契约测试 a9f01867…），跑 `pytest tests/contract/test_event_registry_contract.py` 应 31+1 预存（34 名态）。
2. 合入 M-07：`event_registry.py` 自动合并出 35 名；契约测试在 `_FROZEN_VOCABULARY_SHA256` 处冲突时，**不采纳任一侧哈希**，改为重算：
   ```python
   import hashlib
   from app.core.event_registry import EVENT_REGISTRY
   hashlib.sha256("|".join(sorted(EVENT_REGISTRY)).encode()).hexdigest()
   ```
   **预期值（本 reviewer 预计算，35 名集合）：`26cf482de89a844045914af996eae8872080c8d4c69a6b46c3132cb237f66472`**（以合入后实际重算为准——M-07 若另改了 CORRELATION_KEYS 不影响名集哈希）。
3. 注释同步：冲突注释块合并两卡变更说明（allocation.decision_recorded + memory.invalidated，33→35）。
4. 复跑：`pytest tests/contract/test_event_registry_contract.py`（除 state_aggregator 预存败外全绿）+ `pytest tests/unit/test_action_allocation_policy.py::test_allocation_event_name_is_registered` + M-07 侧事件测试。
5. （可选文档同步）`v3-output/D-01/EVENT_REGISTRY.md` §3 标题「封闭，33 个」在两卡合入后均过期，改为 35 并补两行表格条目——归档文档，不阻塞。

### 5.3 预防性建议

同类冻结词表（本舰队 D-01 sha256 / X-02 ALLOCATION_REASONS sha256 / C-01 等）在并行 worktree 下的 bump 冲突会反复发生。建议主会话维护「冻结哈希登记表」（文件 × 当前值 × pending bump 的卡），后合入者照表重冻——本轮先按 §5.2 手工执行。

---

## 6. 风险面 6：business_metrics / settings 增量冲突

**Verdict: PASS（无冲突）。**

- C-02（wt9 实测 diff）：`ENABLE_CONTEXT_SOURCE_*` 插在 `settings.py` ~L664-671（另有 L153/217/261 三处纯空白重排）；X-02 插在 ~L755-763（`SPARKLE_STORAGE_GATE_*` 之后）。**区间相距 90+ 行，git 自动合并无冲突**；C-02 的空白重排 hunk 也远离两侧。
- business_metrics.py：全舰队扫描仅 wt4 改动（+2 Counter 插在 ROUTING_CONFIDENCE 后），无对撞。
- 语义层配置默认全关核实：`SPARKLE_ALLOCATION_SEMANTIC_ENABLED=False`；`MODEL="qwen3.8-flash"` / `TIMEOUT=5.0` / `MAX_PER_MINUTE=30` 仅在 enabled 时生效（`evaluate`:793 先查开关再进 `_semantic_refine`）。

---

## 7. 风险面 7：LLM 通道越界面

**Verdict: PASS（核心边界），附消费面缺口（并入 F1）。**

- S2 拒收后行为 = **降级规则默认**（非报错）：返回携带 `S2.semantic_outside_feasible_rejected` + `layer=semantic_fallback` 的规则决策（:888-901），`evaluate` NEVER raises（:788-799 双层 catch）。
- 精化结果再 Guard 校验问题：LLM 的 mode 只能在 feasible 内（代码强制），guard 旗标（approval/evidence）经 `replace` 原样保留且语义层无清除路径——变异 M3 证明唯一绕过点被测试盯住。**但** `vet_agent_offer` 这条独立入口存在决策/因子错配绕过（→F1）。
- 超时资源清理：`asyncio.wait_for` 取消任务句柄，无遗留协程；熔断/限频为类级计数（进程内单线程事件_loop 安全），`_breaker_record_failure` 直用 `time.monotonic()` 而其余用可注入 `now_fn`（:925-934 vs :836-843）——纯测试性问题（P3-6）。
- `_parse_mode` 对非 JSON 散文返回 None（`json.loads` 先炸被吞）——此前担心的"否定句首词误匹配"仅存在于「合法 JSON 且 mode 字段本身是散文」的窄路径（regex 首匹配仍偏 agent，P3 级观察）。

---

## 8. 发现分级

### F1 (P2 · 高概率缺陷) `vet_agent_offer` 决策/因子错配绕过 R1 + 完全不查 R5/R6

- **位置**: `backend/app/services/action_allocation_policy.py:607-616`
- **机制**: mechanical 分支 `if decision is not None and decision.requires_human_approval: …` `elif decision is None and _high_risk(factors): …`——传入**任意 requires_human_approval=False 的 decision**（陈旧/异因子）即令 `_high_risk(factors)` 永不可达。
- **实测**（探针 P1）：`vet_agent_offer("mechanical", 高风险因子(risk=high,reversible=False), decision=低风险决策)` → `allowed=True, reason=OK.hybrid_preparation_allowed, requires_human_approval=False`。REPORT §2.3「R1 下 mechanical 必须挂 human approval」被证伪。
- **实测**（探针 P2）：`vet_agent_offer("complete_answer", privacy=restricted)` → `allowed=True`——与本模块自己「restricted 连准备面都无权限」的 R5 语义直接矛盾（vet 入口对 R5/R6 零检查）。
- **影响**: 当前零调用方（零接线已核实）→ 无线上影响；但这是 X-05/A-04 将消费的防代写/安全 vetting API，错配契约是地雷。
- **修复**: `if (decision is not None and decision.requires_human_approval) or _high_risk(factors):`；restricted/sensitive 因子下拒收 agent 侧供给（或显式文档化为何不查 + 由调用方强制先过 decide_allocation）；补 2-3 个错配对抗测试。

### F2 (P3 · 报告证据归属错误) 「6 万网格证明 F5」名不副实

- 62,208 网格不断言 F5；F5 测试实为 1,728。不变式为真（构造性 + 实测零命中），但验收文书夸大证据规模 ~36×。修复：REPORT §2.2 改口径；顺手把 F5 断言加进 62K 网格循环（一行）拿到真覆盖。

### F3 (P3 · 语义不对称且无测试) X2 显式委托分支无 T2/工具优势检查

- 探针 P4：`explicit_intent=delegate + tool_advantage=none` → `mode=agent`（仅 X2 理由）——「AI 全自动」被授予一个 AI 无优势（文档维度 7「让 AI 做反而更慢更贵」）的步骤；同一逻辑在 U1 偏好分支有 T2 降级。fixture 无此场景、无单测。属意图主权 vs 时间成本维度的未裁剪设计决策：要么 X2 分支补 T2，要么文档化「显式意图豁免成本检查」并加测试固化。

### F4 (P3 · 结构性风险) F5 矛盾集双副本无真源对账

- X-01 侧 F5 仅 docstring（`action_plan.py:47-49`），X-02 模块+测试各持硬编码副本。X-01 语义演化 → 假绿。见 §4。

### F5 (P3 · 隐式不变式未测) 语义精化不重算 G2 证据旗标

- `_semantic_refine` 改 mode 后不重算 `requires_user_authored_evidence/recommended_evidence_kinds`（:905-915）。当前不可达（探针 P5：learning ⇒ tier=default ⇒ semantic_eligible=False），但该不变式是**隐式的**（由选择层 else 分支结构派生），无直接回归测试；未来放开灰区即静默失守。加一条 `semantic_eligible ⇒ not learning_guard` 的显式断言或改精化时重算。

### F6 (P3 · 杂项)

1. `merge_into_action_plan` 对非 dataclass 且属性不匹配的 plan 直接 `TypeError: replace() should be called on dataclass instances`（探针 P7；isinstance 防御在 replace 之后是死代码）——消费方（X-05）接入前包一层。
2. S2 边界仅 1 测试拦截（M3 变异 1 failed），建议补 high-risk+LLM 提议 agent 用例。
3. REPORT 计数 nit：契约测试「33/34 过」实为 31/32。
4. X-01 回归依赖不入库的 `app/gen`（借入后删已声明，但意味着验收不可裸复现；建议 devtools 注明 `make proto-gen` 前置）。
5. `_breaker_record_failure` 直用 `time.monotonic()` 绕过 `now_fn` 注入。
6. `v3-output/D-01/EVENT_REGISTRY.md`「封闭，33 个」在两卡合入后过期（§5.2 第 5 条）。

---

## 9. 总 Verdict

# CHANGES（一轮小修后可 ACCEPT）

**通过面**：决策核心 `decide_allocation` 的可行集+分层架构成立且被 5/5 变异实验证明非假防线；LLM 灰区边界（feasible 内选 + S2 拒收 + 旗标不可清除 + 默认关 + 熔断限频超时降级）实测有效；可行集恒非空有结构证明；88+69 回归全绿（前提已列）；零接线属实；D-01 扩词表流程执行正确（34 名哈希独立重算逐字匹配）；盲评口径声明如实；C-02/settings 与 business_metrics 无冲突面。

**必修（本轮）**：
1. **F1**：修 `vet_agent_offer` R1 错配绕过 + 补 R5 检查（或文档化豁免理由）+ 对抗测试——REPORT §2.3 的无条件声称当前为假。
2. **F2**：REPORT §2.2 证据归属改正；建议 F5 断言并入 62K 网格。

**建议同轮**（不阻塞）：F3 测试或文档化、F5 显式不变式断言。

**主会话操作项**（非 Worker）：D-01 后合入者按 §5.2 重冻到 35（预期 `26cf482d…`，以实算为准）。

— R2 DeepAudit，2026-09-19
