# V4-I02 · diff_or_evidence_only（合法历史的效用筛选与反向迁移抑制）

- 实现会话：wtI02（worktree `../wtI02`，分支 `agent/v4/i02`）
- base SHA：`ebd878ff`（B01 销账后 HEAD）；本卡交付 commit：见 run_manifest.json `commit_after`
- 状态：实现 + 自测完成，**待独立审查（2 位，风险 high）**；review_receipt.json 由审查会话落盘，作者不自审

## 一句话

在原 Context Compiler（`context_pack.build`）的 M-03 硬预筛**之后**新增 optional history（episodic 排序面）阶段二效用门（`backend/app/services/memory_utility_gate.py`）：异类型失败经验硬拒（FIX52）、冻结 outcome 权重 + 可解释规则打分、TopK 预算、required-memory 全拒不能过门（bypass 保召回 + miss 如实登记）；行为开关 `ENABLE_MEMORY_UTILITY_GATE` 默认关（零行为变化），灰度可开。

## 差量（全部新增/插入，零删除既有断言或检查）

| 文件 | 变更 |
|---|---|
| `backend/app/services/memory_utility_gate.py` | 新增：效用门模块（冻结权重锚 / 特征派生 / 打分 / 纯核心 evaluate / RankedItem 适配） |
| `backend/app/core/context_pack.py` | +32 行：`build()` 在最终 `ranked_episodic` 计算后、语义门控前接效用门（旗标内），metadata 落 `pack.metadata["memory_utility_gate"]`；`passed=False` 时回退 V3 预筛后路径并登记 `bypassed` |
| `backend/app/core/business_metrics.py` | +11 行：`MEMORY_UTILITY_GATE_DECISIONS_TOTAL`（outcome/reason 计数） |
| `backend/app/config/settings.py` | +9 行：`ENABLE_MEMORY_UTILITY_GATE: bool = False`（默认关）+ `MEMORY_UTILITY_GATE_TOP_K: int = 6` |
| `backend/tests/unit/test_memory_utility_gate.py` | 新增 20 测：B03 冻结锚对表 / FIX52 三态 / required-memory 召回与全拒不过门 / 子集与确定性 / TopK·成本·confirmed·stale·conflict 序 |
| `backend/tests/unit/test_memory_utility_gate_wiring.py` | 新增 5 测：AST 接线双钉（删调用/摘旗标必红）+ flag OFF 零行为 + flag ON 验收①②③集成（in-memory SQLite） |

## 验收对照（必须可失败）

1. **FIX52 异类型失败不拉向 skill/difficulty**：`test_fix52_cross_type_failure_is_hard_rejected`（异类型失败经验对当前类型零交集 → 硬拒 `negative_transfer_cross_type`，无论分数）；同类型失败 `test_fix52_same_type_failure_still_informs_within_type`（只在同类型/有效时间影响候选）。集成面 `test_flag_on_suppresses_negative_transfer_keeps_good_recall` 证明污染条目不进 `pack.episodic_memories` 也不进 `to_prompt_context()`。
2. **required-memory 场景有召回，全部拒用不能过门**：`test_required_memory_with_good_history_recalls`（有召回）；`test_required_memory_all_rejected_fails_the_gate`（`passed=False` + `required_memory_recall=False` + precision N/A=None，不是 0% 更不是 100%）；集成 `test_flag_on_required_memory_all_rejected_bypasses_without_silent_empty`（bypass 保召回 + `required_memory_recall_miss_bypass` 如实登记，不静默清空、不包装成通过）。
3. **已删/越权/过期/错 scope 任何条目不入 prompt**：合法性归 M-03 预筛所有（既有测试不重写）；本门选择集 ⊆ 输入集（`test_selection_is_subset_of_input_never_resurrects`），接线只消费预筛 allowed；集成含 wrong-user 行，flag ON 下不进 pack/prompt（`test_flag_on_suppresses_negative_transfer_keeps_good_recall`）。AST 双钉防接线被删。

## 四臂锚（B03 frozen_utility）

- 臂定义：A=V3 现部署（=本卡旗标关路径）；B=无可选历史；C=V4 语义控制+所有合法历史；**D=V4 语义控制+效用筛选历史（本卡）**。
- 冻结权重逐项对表：`test_frozen_outcome_weights_match_b03_freeze` 直读 `v4/evidence/V4-B03/frozen_utility.json`，`FROZEN_OUTCOME_WEIGHTS == utility_frozen.weights`。
- 反 gaming 口径：门级不给伪 precision（空选择 → None=N/A）；utility 数值比较归 B03 协议的离线四臂评测（本卡零模型调用、零 live 预算，纯确定性规则）。

## 开关与回滚

- `ENABLE_MEMORY_UTILITY_GATE`（默认 **False**）：关 = 不调用、无 metadata、零行为变化（`test_flag_off_default_keeps_v3_behavior`）。开 = 门生效 + metadata。
- 回滚 = 关旗标；独立 commit，无 schema/契约/生成文件改动，V3 路径与数据不受影响。
