# V4-I03｜diff_or_evidence_only

**结论：IMPLEMENTATION（新增受限语义选择器实现 + 影子接线；零真模型调用）**

## 一句话设计

I09 快慢路之间的**受限语义判定层**：对「多否定 / 时间约束 / 材料不足」复杂表达做**结构探针**（多 token 结构单元承载判定，单关键词零判定力），为语义选择提供**封闭词表校验**（干预/执行模式/ref/tool 全部白名单硬校验，未知 ref / 目录外 tool 显式拒绝澄清，schema 不合规最多修复一次），并以**同输入规则臂/语义臂对照**保留判定、成本（I10 诚实口径）与失败形态，可审计落账。

## 做了什么（最小增量）

新增：

- `backend/app/orchestration/semantic_selector.py`（~900 行）——三面：
  1. **`probe_complex_expression`**（验收①）：四形态结构探针（`multi_negation` / `time_deferral` / `deadline_pressure` / `material_insufficiency`），冻结结构模式表（每个 pattern 为 ≥2 token 连续单元：拆任一算子即不匹配——这就是「判定不因单个关键词翻转」的实现机制）；材料不足形态带缓解词作废逻辑（「没有材料也不影响」不构成阻塞）。输出 `ComplexExpressionProfile`（形态标志 + pattern 级证据，可审计）。
  2. **`run_selection`**（验收②）：`sparkle_semantic_selection.v1` schema 校验（封闭键集、confidence_band 审慎标签、abstain_reason ∈ `AURORA_UNCERTAINTY_KINDS`、惰性干预 mode 必空、缺失变量必须带问句），**未合规最多修复一次**（`MAX_SCHEMA_REPAIRS=1`，修复轮携带违规反馈）；白名单硬校验（干预 ∈ 契约词表且 ∈ 传入白名单、执行模式 ∈ `ExecutionMode` 白名单、ref scheme ∈ `AURORA_DECISION_REF_SCHEMES` 且 ∈ 传入 ref 白名单、tool ∈ 传入工具目录）——硬违规首拍即显式拒绝（不花修复调用）；拒绝码封闭 6 值（`unknown_ref` / `out_of_catalog_tool` / `unknown_intervention` / `invalid_execution_mode` / `schema_invalid_after_repair` / `proposer_unavailable`）；**拒绝结局结构上不携带可执行声明**（selected_intervention_id/execution_mode/used_ref_ids/tool 恒空），澄清话术冻结文案表全部「先不执行」句式，`SUCCESS_TALK_MARKERS` 扫描由测试钉死——「已执行」话术无处可拼。`SelectionRequest` 构造期 fail-loud（白名单 ⊄ 契约词表即 ValueError）。
  3. **`run_arm_comparison`**（验收③）：同输入跑规则臂（`rule_arm_decide`：探针 → 5 值封闭判定，零模型）与语义臂（`run_selection`），`ArmComparisonRecord` 保留：确定性 comparison_id（版本+输入 sha256+白名单摘要哈希）、每臂判定、每臂成本（I10 口径 `ArmCost{model_calls, prompt_tokens, completion_tokens, usage_source, sub_calls}`——零模型臂 0+0 measured；模型臂如实上报；未上报/中断 → None 不冒充 0）、每臂失败形态（封闭词表）、agreement（agree/disagree/not_comparable）。`to_audit_json()` 可审计；`run_semantic_selector_shadow` 落 `context_data["semantic_selector"]` + 两个新 metrics 计数器。

修改（全部 flag-gated）：

- `backend/app/config/settings.py`：`SEMANTIC_SELECTOR_MODE: str = "off"`（off/shadow/live；off=零行为；未知值 fail-closed 按 off）。
- `backend/app/core/metrics.py`：`SEMANTIC_SELECTOR_COMPARISON_TOTAL{agreement,rule_decision,semantic_verdict}` + `SEMANTIC_SELECTOR_REFUSAL_TOTAL{refusal_code}`。
- `backend/app/agents/standard_workflow.py`：`router_node` 内 I09 快路块之后的影子钩子——mode≠off 时跑对照并写 context_data，**永不改变路由**（测试断言 shadow 下 router_decision/router_confidence 与 off 逐项一致）；影子观测自身失败只 WARN 不阻塞路由。零真模型：影子不挂 proposer，语义臂如实记 `proposer_unavailable` 失败形态。

## 词表纪律（不造第二权威）

干预词表 = `AURORA_INTERVENTION_TYPES`（A-01）；执行模式 = `ExecutionMode`（X-01/X-02）；ref scheme = `AURORA_DECISION_REF_SCHEMES`（X-01 派生）；abstain 原因 = `AURORA_UNCERTAINTY_KINDS`；confidence_band = B05 §4 同款审慎标签。**不推翻 I09 词表**：本层不参与问候/确认判定（回归断言复杂表达永不落 I09 快路，`TestFastLaneUntouched`）。

## 验收逐条

1. **多否定/时间约束/材料不足不靠单关键词误判**：满足。冻结探针语料 23 条（10 正例 + 13 反例）全数命中（`probe_corpus_snapshot.json`，`all_match=true`）；测试三族：每形态正例、单关键词零判定力（14 反例含「不是想学」「以后每天背50个单词」「没有材料也不影响」）、去算子翻转（拆任一结构算子即不触发）。
2. **未知 ref / 目录外 tool 拒绝，不拼「已执行」话术**：满足。未知 ref（含 scheme 封闭集外）、目录外 tool、词表外/白名单外干预、非法执行模式 → 首拍封闭拒绝码显式拒绝 + 冻结澄清话术；全部拒绝码文案测试扫描 `SUCCESS_TALK_MARKERS` 零命中且含「先不执行」；拒绝结局结构上无可执行声明字段；proposer 缺位/异常 = 可观测降级（PROPOSER_UNAVAILABLE + 用量 None 不冒充）。
3. **同样输入的规则/语义臂对照保留成本和失败**：满足。`ArmComparisonRecord` 测试断言：规则臂 0+0 measured 零模型成本、语义臂 stub 成本如实透传（usage_source/sub_calls 切片保留、未知→None）、失败形态（out_of_catalog_tool / proposer_unavailable 等）落账、comparison_id 确定性、`to_audit_json` 往返可解析。对照数据三落点：`context_data["semantic_selector"]`（shadow）+ 2 个 metrics 计数器 + 记录对象 json。

## 与既有事实的关系

- 不重建 V3、不动 proto/迁移/生成文件；`backend/app/gen` 为 gitignored 实体目录（本 worktree 从主检出复制，不入库）。
- B06 实测能力面约束：语义臂 proposer 为协议插口（`SemanticProposer`），本卡不接真模型（费用授权线，零真实调用、零上游请求）；B06 t1/t2 实测的 dashscope fast 用量形态是未来 proposer 成本上报的对照基线。
- I02 结构化锚派生模式参照（不从自由文本猜类型 → 本卡不从自由文本猜白名单：白名单一律调用方传入）；I10 计量口径直接沿用（usage_source/sub_calls/未知→None）。
