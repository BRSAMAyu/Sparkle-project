# X-02 REVIEW_RECEIPT — R1 标准验收 + 返修 delta 复核（合并一趟）

- Reviewer: R1（V3 Fleet · 标准验收路线）
- 日期: 2026-09-19
- 对象: wt4 @ `1ea854c9` + X-02 未提交改动（4 M tracked + 6 untracked + `v3-output/X-02/`，含 R2 DeepAudit 后 Apex 返修）
- 方法: delta 复核（自写探针 + 2 组反向变异 + 全套实跑）为主、标准验收补位为辅；主仓只读。开工时工作树状态与返修员自报一致，变异实验全部还原（sha256 逐字校验）。

---

## A 部 · delta 复核（R2 REVIEW_RECEIPT_2 返修项逐条）

### A1. F1 修复真实性（变异实验）— **Verdict: PASS（修复真实且有 wiring 牙齿）**

- **修复行核读**：`backend/app/services/action_allocation_policy.py:646`
  `if (decision is not None and decision.requires_human_approval) or _high_risk(factors):`
  ——因子侧为独立或分支，陈旧/异因子 `requires_human_approval=False` 决策不再短路 `_high_risk`；R5 检查在 `:623-630`，且**先于** decision 逻辑与学习守卫判定执行（权限边界优先，decision 无法绕过 R5，被更严分支拒收时优先拒）。
- **自写探针（独立构造，非复制返修员测试）**：
  - **P1** `vet_agent_offer("mechanical", risk=high+reversible=False 因子, decision=低风险陈旧决策)` → `allowed=True, requires_human_approval=True, reason=R1.autonomous_execution_needs_approval` ——**已翻转**（R2 实测原为无审批放行）。
  - **P2** `vet_agent_offer("complete_answer", privacy=restricted)` → `allowed=False, reason=R5.restricted_agent_supply_forbidden` ——**已翻转**（R2 实测原为 allowed=True）。
- **反向变异（证明测试不是同义反复）**：
  - **M-F1**：`:646` 改回旧逻辑 `if decision is not None and decision.requires_human_approval:`（去掉 or 分支）→ guard 套件 **2 failed**（`test_vet_mechanical_high_risk_with_stale_low_risk_decision_still_needs_approval` + `test_vet_mechanical_medium_irreversible_without_decision_needs_approval`），恰好是 F1 对抗测试。
  - **M-F1b**：R5 两分支置 `and False`（模拟未修）→ guard 套件 **11 failed**（restricted 7 形态参数化 + sensitive complete/mechanical + 2 条降级建议测试）。
  - 每轮变异后经 `/tmp` 备份还原，sha256 逐字一致（`70d311b3…`），全套 112 复绿。

### A2. R5 三级语义同构核对 — **Verdict: PASS（逐级同构，无分叉地雷）**

实测两入口同因子对照（本 reviewer 探针输出）：

| privacy | `decide_allocation` feasible | `vet_agent_offer` 全谱（7 形态） | 同构性 |
|---|---|---|---|
| restricted | `("human",)` | 7/7 全拒 `R5.restricted_agent_supply_forbidden` | ✅ agent 零接触 ⇒ 连准备面供给都无 |
| sensitive | `("human","hybrid")` | complete_answer/mechanical 拒（`R5.sensitive_autonomous_supply_forbidden`，complete 建议降级 draft、mechanical 无降级），draft/outline/materials/hint/review 放行 | ✅ 禁全自动 ⇒ 拒「独立交付/独立执行」形态，保留人在环准备面 |
| public | 三元全集 | 按学习守卫/G3/G4 正常判定 | ✅ |

restricted 拒全部供给 = feasible={human} 的供给侧镜像；sensitive 拒的恰是 hybrid 里不需要人的两形态 = feasible 剔 agent 保留 hybrid 的镜像。语义将来不分叉。
**词表钉住**：两新码在 `OFFER_VERDICT_REASONS`（`:173-174`）；`test_offer_verdict_reasons_frozen`（policy 测试 `:92-108`）精确集断言含两码；行为层由 guard 套件 restricted 7 参数化 + sensitive 7 参数化测试钉死。

### A3. allocation.v1.1 冻结协议 — **Verdict: PASS（extend-only，协议执行正确）**

- bump 范围核实：`ALLOCATION_POLICY_VERSION = "allocation.v1.1"`（`:75`）；仅 `OFFER_VERDICT_REASONS` +2 码；决策词表 `ALLOCATION_REASONS` **一字未动**（`_FROZEN_REASONS_SHA256=c4fc32a9…` 双冻结测试原样通过）；`AllocationDecision.to_dict()` 记录 schema 键集不变（仅 `schema_version` 字符串值随版本走）。
- 模块 docstring `:49-53` 记录 v1→v1.1 变更事由 + 两位 reviewer 流程——冻结协议声明完备。
- 消费方兼容性：grep 两仓（wt4 + 主仓 backend/app）`ALLOCATION_POLICY_VERSION`/`OFFER_VERDICT_REASONS` 消费点为 **0**（A-04/X-05 未开工，零接线复核属实）→ v1.1 对旧码集消费方不存在，extend-only 天然成立。两新码均为 `allowed=False` 拒收值，未来按 `allowed` 位消费的调用方不受影响。
- 附注（P4，不阻塞）：无测试字面钉住 `"allocation.v1.1"` 版本号本身；`decision_id` 种子含 `schema_version`，bump 会改变同因子 id——当前无持久化消费方，无影响，A-04/X-05 接入时若按 id 跨版本去重需知悉。

### A4. F2/F5 覆盖真实性 — **Verdict: PASS（归属改正 + 真 62K 覆盖均落实）**

- **F5 断言在 62K 网格里**：`test_all_reason_codes_are_in_closed_vocabulary`（policy 测试 `:418-465`）循环体内 `:459` F5 矛盾集断言、`:460-463` `semantic_eligible ⇒ not learning_guard` 断言，均逐组合执行。网格维度 4×3⁵×2⁶ = **62,208**（复算属实）。
- **REPORT §2.2 口径改正**：REPORT `:54-62` 明示「R2 返修 F2 改正，原文本把 62K 网格规模误安在专项测试头上」，62,208 与 1,728 两网格分列——夸大表述已消除。
- F5 双保险第二路：`_semantic_refine` 改 mode 后按 `(learning, mode)` 构造性重算 G2 三件套（模块 `:942-963`），`test_semantic_refine_recomputes_g2_evidence_flags` 双向（清 G2 / 补 G2）离线断言。

### A5. 测试实跑 — **Verdict: PASS（三组数字全部独立复现）**

| 套件 | 命令（backend/ 下，进程内注入 SECRET_KEY） | 结果 | 自报 |
|---|---|---|---|
| X-02 全套 | `pytest tests/unit/test_action_allocation_{policy,guard,eval}.py -q` | **112 passed**（0.7s） | 112 ✅ |
| D-01 契约 | `pytest tests/contract/test_event_registry_contract.py -q` | **31 passed, 1 failed**（败者 state_aggregator 预存，与 R2 观测一致） | 31+1 ✅ |
| X-01 回归 | 借主仓 `app/gen` 后跑 4 文件（跑完已删） | **69 passed** | 69 ✅ |
| 裸 worktree 复现性 | 删 `app/gen` 后跑同组 | collection error（`No module named 'app.gen'`）——F6.4 所述「不可裸复现」属实且已如实声明 | — |

**新增测试反同义反复抽查（读断言体 >3 个）**：
1. `test_vet_mechanical_high_risk_with_stale_low_risk_decision_still_needs_approval`——先断言陈旧决策 `requires_human_approval is False`（前置自证），再喂高风险因子断言审批置位；M-F1 变异实证其杀伤力。
2. `test_semantic_refine_recomputes_g2_evidence_flags`——用 `replace()` 人为构造 `semantic_eligible=True` 的不可达态，双向断言 G2 清/补，防未来放开灰区。
3. `test_breaker_uses_injected_clock`——注入假时钟断言 `_semantic_open_until == fake_now + 300` 精确值（非真等 300s 睡眠）。
4. `test_explicit_delegate_exempts_t2_cost_check`——X2 vs U1 同因子对照 + 硬规则不豁免三段断言。
全部构造独立输入、断言具体行为，无同义反复。

---

## B 部 · 标准验收补位

### B6. patch 一致性 — **Verdict: PASS**

- `changes.patch` = **159,340 字节**（与自报逐字一致）；结构 = 4 tracked diff（settings/business_metrics/event_registry/契约测试）+ 6 untracked 内嵌 new file，与工作树清点一一对应。
- **逐字节验证**：`git clone wt4 → /tmp`（HEAD 1ea854c9）→ `git apply` patch → 10 文件 `cmp` 全部 **IDENTICAL** 工作树现态。patch 即完整交付，无 drift。
- 卫生扫描：无密钥（唯一 `SECRET_KEY` 出现为 docstring 用法占位 `SECRET_KEY=...`）、无主仓绝对路径、无 `/Users/brsama`、无夹带文件。
- 收工态：本 reviewer 变异实验与 app/gen 借用全部清理，`git status` 恢复 4 M + 6 untracked + v3-output 原态。

### B7. 范围核对（主仓卡面）— **Verdict: PASS（符合卡面）**

主仓 `v3/07_tasks/cards/X-02.md` 要求：八维 → mode、规则管硬边界 LLM 管灰区、记录 why+confidence；验收 = ≥60 场景盲评 ≥90% 且 high-risk auto=0、学习目标不默认代写。交付对应：rubric 纯函数核心 + 85 场景 eval 套件（阈值 ≥0.90 断言 + 类别断言 + 按因子动态不变式断言三层）+ vet 防代写 + 决策记录/事件结构。零生产接线正确——卡面 work 域是策略本体，orchestrator/planner 接线归 X-05/A-04（REPORT §6.1 已声明）；Forbidden 四条无违（复用 X-01 ExecutionMode/CognitiveOwnership/RiskClass，未重建真源）。证据项：base SHA 有、targeted tests 有、盲评基准有、review receipt 有（本件 + R2）。

### B8. 合入预演 + M-07 冲突预测 — **Verdict: PASS（附 Leader 操作项）**

- **预演**（主仓只读，`--check` 不落盘）：主仓 HEAD 已前进至 `ee885386`（任务给的 `42180162` 为其祖先；event_registry 仍 33 名/`4e8ccdcd…` 态）。对当前 HEAD：`git apply --check` **CLEAN**，`git apply --3way --check` **CLEAN**（全部 hunk 干净落位）。1ea854c9 是主仓祖先，无基线漂移风险。
- **M-07（wt8）重叠行范围**：
  - `event_registry.py`：wt4 单 hunk `@@ -192`（DECISION 段插 allocation.decision_recorded）；wt8 hunks `@@ -359 / -426 / -448 / -461`（STATE_UPDATE 段 + memory_id）——**区间不相交，三方自动合并 → 35 名**。
  - `test_event_registry_contract.py`：两侧改**同一行区间**（L49 `_FROZEN_VOCABULARY_SHA256`：wt4 → `a9f01867…`、wt8 → `c2815560…`）+ 各自注释块——**必然文本冲突**，且任一侧哈希对 35 名合并态都是假红。
  - **独立复算**：以主仓 33 名实集 + 两新名排序 join 求 sha256 = **`26cf482de89a844045914af996eae8872080c8d4c69a6b46c3132cb237f66472`**，与 R2 §5.2 预测**逐字一致**；同时证实 wt4 的 `a9f01867…` 恰为其 34 名集精确值（wt4 侧冻结数学正确）。
  - **Leader 操作项不变**：后合入者按 R2 §5.2 重冻 35（预期值如上，以合入后实算为准），注释块合并两卡说明。

---

## 必修项分级

- **R2 F1（P2）**：已返修 + 本趟 delta 复核三重证实（代码核读/自写探针翻转/反向变异必红）→ **关闭**。
- **R2 F2（P3）**：REPORT 口径改正 + F5 断言入 62K 网格 → **关闭**。
- 建议 F3/F5/F6.1/6.2/6.3/6.5：全部落实且有固化测试 → 关闭。
- **遗留（不阻塞，责任人明确）**：F4（F5 双副本无真源对账，跨卡协调，REPORT §8 已声明留 Leader 裁决）；F6.4（裸 worktree 不可复现 X-01 回归，复现需 `make proto-gen` 或借 app/gen，已如实声明）；F6.6（D-01 归档文档 33→35 过期，Leader 合入时顺手改）。

## 总 Verdict

# ACCEPT（可合入）

**依据**：两项必修（F1/F2）返修真实、有测试牙齿、全部数字独立复现（112 / 31+1 / 69）；探针 P1/P2 行为翻转实证；R5 三级语义与 decide_allocation 逐级同构；allocation.v1.1 extend-only 且零消费方；patch 与工作树逐字节一致且对主仓最新 HEAD 干净可落；范围符合卡面。D-01 契约测试的 34 名哈希数学正确，35 名合并冲突是流程内预期（双卡均按扩展流程走），非本卡缺陷，Leader 按 §5.2/B8 操作即可。

— R1（标准验收 + delta 复核），2026-09-19
