# V4-I03 一审 receipt（独立审查 R1）

- **审查会话**：wtI03R1（未参与 I03 实现）
- **审查对象**：branch `agent/v4/i03`，HEAD `845751ce520fec368e78a983d857ac1c22730257`（实现 commit `ac6f9ae5` + receipt pin `845751ce`）
- **审查日期**：2026-09-28
- **方式**：只读审查 + 独立复跑 + 对抗性亲测 + 变异测试（全部变异已 `git checkout --` 还原，终态 worktree clean）
- **总裁决**：**PASS（一审通过）**。CHALLENGED：**无**。观察项 3 条（O-1/O-2/O-3），均不阻塞，移交下游消费卡。

## 复跑记录（本会话独立执行，非转录）

| 面 | 命令要点 | 结果 |
| --- | --- | --- |
| 新增测试 | `pytest tests/unit/test_semantic_selector.py -q`（SECRET_KEY=ci-test-key DATABASE_URL=sqlite://） | **77 passed** |
| 冻结语料 23 | 独立脚本直读 `probe_corpus_snapshot.json` 逐条对 `probe_complex_expression` + `rule_arm_decide` 复核（expected/actual/rule_arm_decision 三字段） | **23/23 零 mismatch** |
| orchestration 全量 | `pytest tests/orchestration -q` | **208 passed** |
| I09 受影响面 | 与 run_manifest 同 12 文件组合 | **300 passed** |
| mypy 棘轮 | `bash scripts/ci/mypy_ratchet.sh` | **71 / baseline 77**（低于基线，零新增） |

## R1-R5 逐点判定（实现方预登记挑战点）

### R1 探针语料覆盖边界 — **PASS（含确认预登记缺口）**

- **解耦性**：`probe_corpus_snapshot.json` 在 `tests/`/`app/` **零消费者**（grep 核实）；语料在测试 parametrize 与快照 json 双份维护，任一侧修改不会使另一侧红——存在**静默漂移面**（本会话已独立复核当前两侧一致，见 O-1）。
- **语料外变体亲测**（4 条，超出要求的 2 条）：
  1. `不是不想去，只是过两天再说`（双重否定+时间约束复合）→ multi_negation 正确命中；`过两天` 不在封闭时间指称表（有过阵子/过几天，无过两天），time_deferral **漏报** → 落回既有慢路，行为不变。「宁漏报回落慢路」成立。
  2. `材料不够，先不做了` → time_deferral 命中（`先不做了` 结构）；`不够` 不在材料否定词表（有「不足」无「不够」），material_insufficiency **漏报** → 回落慢路；可执行的搁置信号仍被正确捕获，无错误动作。
  3. `材料不够`（单句）→ 零形态，回落慢路（同上，安全方向）。
  4. `没有材料，但我可以先讲思路` → material_insufficiency **误命中**——「但我+替代方案」缓解缺口，与 limitations §7 预登记完全一致；后果 = 规则臂多问一次澄清（shadow 只记录不路由，保守方向非危险方向）。
- **判定**：单关键词零判定力机制在未预见形态下未发现翻转；假阴全部回落慢路（卡验收①的安全声明成立）；假阳仅限预登记的缓解词缺口。**PASS**。

### R2 成功话术标记表完备性 — **PASS**

- **结构保证亲验**：目录外 tool（`rm_rf_slash`）+ 悬空 ref（`task://dangling-404`）同拍注入 → `unknown_ref` 硬拒绝，`repairs_used=0`、proposer 仅 1 次调用（硬拒绝不花修复预算）；`to_dict()` 键集实测 `['confidence_band','cost','failure_form','refusal_code','refusal_copy','repairs_used','schema_version','verdict','violations']`——**无可执行声明字段**（selected_intervention_id/execution_mode/used_ref_ids/tool 结构性缺席，非置空）。
- 全量序列化 payload（含 refusal_copy + violations）对 11 个 `SUCCESS_TALK_MARKERS` 扫描**零命中**；render_refusal 只出 `_REFUSAL_COPY` 冻结表（测试钉死 `set(_REFUSAL_COPY)==set(RefusalCode)`，6 码全覆盖），标记表只是拒绝路径上的 belt-and-suspenders——未列变体无法穿过，因为文案本身是封闭集。**PASS**。

### R3 ArmCost 用量诚实口径 — **PASS**

- 对照 I10 权威（`app/orchestration/token_tracker.py`：usage_source ∈ {measured, estimated}、未核价→None 不填 0、sub_calls 切片）：I03 的 ArmCost 同口径——零模型臂 0+0 记 `measured`（0 是实测，与 I09 记账同款）；未上报→None；`sub_calls` 合并保留。
- **亲测异常路径**：
  - 首拍成功(measured 1369+72)→修复拍抛错 → `model_calls=1`（只计收到响应的调用，代码注释显式声明该口径）、tokens/usage_source 置 None 不冒充、**sub_calls 切片保留**（已完成调用的实测用量仍在审计明细可查）、violations 含 `proposer_exception:RuntimeError`。不吞不伪装。
  - 首拍即抛 → `model_calls=0` + 全 None。诚实零声明。
  - 混合来源合并（首拍 measured + 修复拍未上报）亲测 → tokens 加总 (150,15) 但 `usage_source=None`（None 传播，不挑 measured 冒充）；同源对照 → measured。合并规则正确。
- 小注：中断调用的 attempt 不入 `model_calls`（仅 violations 字符串可见）——显式声明的口径选择，不算不诚实。**PASS**。

### R4 影子钩子开销与语义污染 — **PASS**

- **开销实测**：`probe_complex_expression` 单次 4.8–6.2 µs（10–28 字消息）；影子全路径（探针+双臂对照+metrics+context 写入）**~29 µs/轮**。相对路由轮（embedding/模型调用百 ms 量级）可忽略（<0.03%）。
- 钩子位于 router_node 早退路径**之后**（协作/专家/I09 快路返零成本不付影子税）；只探 `messages[-1]` 一条（非全消息，优于挑战描述的假设）。
- **污染面**：`semantic_selector`/`semantic_selector_mode` 两键 grep 全仓**零下游消费者**（仅写入方）；钩子在权威 RouterNode **之前**运行且只写这两个名字空间隔离的键，路由器决策在其后覆写——影子物理上无法成为裁决。残余风险（未来消费者误读 `semantic_arm.verdict` 为裁决）由 `failure_form`/`verdict=refused` 显式字段 + I04/I07 消费卡门承担，见 O-3。**PASS**。

### R5 白名单绕过 — **PASS**

10 变体亲测（大小写/首尾空白/全角/unicode escape）：

| 变体 | 结局 |
| --- | --- |
| `TASK://T-1`（scheme 大写） | refused: unknown_ref |
| `task://t-1 `（尾空白） | refused: unknown_ref |
| ` task://t-1`（首空白） | refused: unknown_ref |
| `task：//t-1`（全角冒号） | refused: unknown_ref |
| `task://\u0074-1` | **selected（正确命中）**——`\u0074` 在 Python 字符串/JSON 解码层即 `t`，解码后与白名单成员逐字节相等；这是正确匹配非绕过 |
| ` get_plan_state `（tool 空白） | refused: out_of_catalog_tool |
| `ｇｅｔ_plan_state`（全角） | refused: out_of_catalog_tool |
| `AGENT` / ` agent `（模式） | refused: invalid_execution_mode |
| `Clarify`（干预大写） | refused: unknown_intervention |

成员判定为**逐字节精确匹配、零归一化**——危险方向是「归一化后撞入白名单」，实现不做任何 NFKC/casefold/strip，所有变体一律 fail-closed 拒绝。构造期 `__post_init__` 对 allowed_refs 的 scheme 校验同样精确（全角冒号 ref 连构造都进不来）。**未发现绕过路径。PASS**。

## 第 6-8 项

### 默认 off 零行为红线 — **PASS（断言可失败性经变异验证）**

变异测试（变异体均已还原）：
1. **内层 off 检查变异**（`if mode == "off"` → `"offx"`）→ `test_off_zero_behavior` **红**（1 failed）。off 断言钉在真实执法点。
2. **router 外门变异**（移除 mode 门）→ 77 全绿——非漏洞：`run_semantic_selector_shadow` 内部自有 off 检查，外门仅是性能优化（纵深防御，变异等价于无行为变化）。
3. **shadow 越权写 router_decision 变异** → 测试仍绿——写入被其后的真实 RouterNode 覆写，结构上钩子无法成为终局裁决；该断言能抓的是钩子崩溃路径（`test_router_node_shadow_failure_never_breaks_routing` 覆盖）与「钩子写路由器会读的键」场景（当前零消费者，grep 核实）。见 O-3。

### 词表复用声明 — **PASS（含 O-2 观察）**

grep 核实：`AURORA_INTERVENTION_TYPES`/`AURORA_DECISION_REF_SCHEMES`/`AURORA_UNCERTAINTY_KINDS` 全部 **import 自 `app/core/aurora_decision.py`**（唯一权威定义处），`ExecutionMode` import 自 `app/models/execution_intent.py`；`SelectionRequest.__post_init__` 构造期对权威 fail-loud。无复制。新封闭枚举（RefusalCode/RuleArmDecisionKind/confidence_band 等）为本层新词表，非第二权威。例外见 O-2。

## 观察项（不阻塞，移交下游）

- **O-1 语料快照零测试消费者**：`probe_corpus_snapshot.json` 与测试 parametrize 双份维护，单侧修改不互检（静默漂移面）。本会话已复核当前 23 条两侧一致 + 快照 actual/rule 字段与活代码行为逐条相符。建议 I04/I07 接线时加「重算快照并 diff」检查或让测试直读快照。
- **O-2 `_RULE_DECISION_TO_INTERVENTIONS` 硬编码字符串**（semantic_selector.py L755-761）：agree/disagree 分族映射的干预名为字面量，无 import 期不变式绑到 `AURORA_INTERVENTION_TYPES`；权威改名会静默漂移 agreement 分类（运行时白名单校验仍会拒绝越权干预，影响限于影子指标偏斜）。建议消费卡加一行模块级不变式断言。
- **O-3 路由一致性断言的检测边界**：`test_router_node_shadow_keeps_routing_identical` 用 FakeRouterNode，钩子在路由器前写入的键会被覆写，故该断言抓不到「钩子未来写路由器消费键」类回归；当前结构性保证（只写两个零消费键）成立。建议 I04/I07 挂真实消费时补一条「钩子键集 ⊆ {semantic_selector, semantic_selector_mode}」冻结断言。

## 结论

三条卡验收（①结构探针不单关键词误判 ②未知 ref/目录外 tool 拒绝且零成功话术 ③双臂对照保留成本与失败）全部独立复核成立；五条预登记挑战点逐一下判无 CHALLENGE；默认 off 红线可失败；词表复用属实；77+23+208+300+mypy 棘轮全部本会话复跑绿。**一审 PASS**，待第二位独立审查（risk=high 需 2 份）。
