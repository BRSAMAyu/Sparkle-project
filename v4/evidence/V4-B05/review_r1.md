# V4-B05 独立审查 receipt（一审 · wtB05R）

- 审查对象：`v4/evidence/V4-B05/contract_receipt_min.md` @ commit `1c1ad4e5`（branch `agent/v4/b05`，base `3c4618cc`）
- 审查人：wtB05R（未参与 B05 任何实现；只读审查 + 本 receipt）
- 方法：卡标准（`Sparkle-project/v4/04_tasks/cards/V4-B05.md`）逐验收项对照；合同 §1 权威映射 **11 处全量抽验（行号级 grep/sed 打开所引文件）**；12 条冻结反例逐条对不变量编号；越权与 RF-06 四要素核对；示例 JSON 与合同字段表交叉校验。

---

## 1. 可实现性 — CHALLENGED（1 处，可条件修复）

**CONFIRMED**：三契约字段表四列（类型/必选/默认/unknown 语义）齐备，逐字段可落码；`context_selection_receipt` 的 `candidates[].reason_code` 条件必选、`experience_event` 的 `receipt_ref` 按 kind 条件必选、`episode_resume_view` 的 `freshness` 绑定 receipt，示例 JSON 与字段表全部一致（epoch 42 跨 receipt/resume 一致；ref scheme 均落在 `ACTION_SOURCE_REF_SCHEMES` 11 值内；reason_code 均在封闭枚举内；dedupe_key 64-hex）。幂等键实现留实现卡已如实披露（limitations #6）。

**CHALLENGED-C1（why_now v1.1「对 v1 行零影响」缺版本门机制，按现码描述不成立）**：
- 合同 §4/§8 称 `action_schema_version` bump 为 `action_plan.v1.1` 后"v1 行读出 = why_now: null""对 v1 行为零影响""v1 行为完全等价"。但现行读侧门是**严格相等匹配**：
  - `backend/app/core/action_plan.py:259-260`（写侧 validate）：`if self.schema_version != ACTION_PLAN_SCHEMA_VERSION: violations.append(...)`
  - `backend/app/core/action_plan.py:340-341`（读侧 `action_plan_projection`）：`!=` 即**整块 None + WARN**，docstring 明言"版本 bump 未迁移存量行时该 WARN 会随读放大（已知代价）"。
- 后果：常量 bump 成 `v1.1` 后，存量 `action_plan.v1` 行全部过不了版本门 → 整块投影降级 None——**恰是合同声称不会发生的破坏**；反向（旧读者读 v1.1 新行）同理。合同只规定了 why_now 子结构失败的降级，未规定版本门本身需改为**版本集合成员判定**（`{action_plan.v1, action_plan.v1.1}` 双可读 + 按版本分派解码）。
- 另：§4 称读侧降级"整块降级纪律与 X-01 相同"，实际设计是**字段级降级**（why_now 置 null、不影响其余 v1 字段），与 X-01 整块降级是**有意的新 delta**，应明说而非"相同"。
- 修复要求（文档级）：§4 增补版本门兼容机制（集合成员判定 + v1→`why_now:null` 分派 + 写侧 validate 双版本接受窗口），并把字段级降级明示为相对 X-01 的有意差异。

## 2. 权威复用真实性 — CHALLENGED（3 处引用失实，其余全部属实）

11 处映射全量核验，**7 处行号级完全属实**：

| # | 引用 | 核验结果 |
|---|---|---|
| 1 | `action_plan.py:68/76/90/103`：`ACTION_PLAN_SCHEMA_VERSION`/`EVIDENCE_KINDS`(7)/`USEFUL_STEP_REASONS`(6)/`ACTION_SOURCE_REF_SCHEMES`(11) | ✅ 行号、成员数逐一精确（7/6/11 实测）；读门"脏值→None+WARN"属实（:318-397） |
| 2 | `action_command.py:117` `TerminalReason`（committed 唯一落账；expired 懒转+sweep 持久化） | ✅ :117 精确，docstring 逐句相符；`DEFAULT_PROPOSAL_TTL_SECONDS` :297 存在 |
| 3 | `aurora_decision.py:270/292/191`：`memory_use_receipts ⊆ evidence_refs`/字段位/`DecisionUncertainty` | ✅ :270 docstring 不变量原文、:292 `memory_use_receipts` 字段、:191 class，全部精确；`AURORA_UNCERTAINTY_KINDS` 在场（:108） |
| 4 | `calibration_receipt.py` A-06 四动作 `not_relevant/wrong/change_scope/delete` + surfacing 确定性门 | ✅ :17/:61-64 四动作词表；`evaluate_receipt_surfacing` :154 确定性门 |
| 5 | `correction_types.py` `AuroraCorrectionPayload.normalize` | ✅ :71 class / :91 normalize |
| 6 | FIX-507 三写面：`intervention_lifecycle_service.py:146/:218` `record_exposure`/`record_response`、`models/intervention_lifecycle.py:29` `InterventionLifecycleEvent`（exposure/accept/edit/reject/start/outcome_observed）；FIXED@8e503cd8 | ✅ 行号精确；dedupe+内容寻址 decision_id 属实；`LATEST_ISSUE_EXCERPTS.md:15` FIXED@8e503cd8 记录与合同 §11 表述逐句相符 |
| 7 | `event_registry.py:208-459` 全部事件名 | ✅ intervention.requested :208 … outcome.recorded :383 … memory.invalidated :459，逐名在场，范围精确 |
| 8 | `outcome_ledger.py:104/:209/:412` TruthClass、`RUN_RECEIPT_WORK_MATERIALIZED_STATUSES={SUCCEEDED}`、PARTIAL/FAILED 永不升 actual | ⚠️ 行号精确、SUCCEEDED 集/永不升 actual 属实；但 TruthClass 实为 **5 值**（含 `demo`），见 CHALLENGED-C3 |
| 9 | `context_manager.py:100/:246-256` memory epoch（快照钉 epoch；bump 后旧快照重建 fail-closed） | ✅ 字段在 :101（引 100 差一行，无碍）；读门语义逐句相符 |
| 10 | `experience_readouts.py:90` `_understanding_claim_payload`：claim/confidence/confidence_label/evidence_summary/scope/user_can_correct | ✅ :90 精确；8 键全对；`user_can_correct: True` 恒定属实 |
| 11 | Aurora 侧既有 why_now：`aurora_core_session.py:59`、`plan_quality_contract.py:211`；X-01 REPORT 自证 task 级缺位；WT806 S4 口径 A | ✅ 两处 :59/:211 精确；X-01 REPORT §6 第 7 条"why_now…字段位未预埋"（REPORT.md:171，"§6.7"系 §6 条 7 的松写，实质相符）；WT806 memo.md:112"口径A 干预/proposal 输出=载体 → PASS(task 级缺位登记后续卡)"原文在场 |

辅助引用亦属实：`proto/websocket.proto` InterventionPushMessage(:48)/MessageAck(:75) 且无 receipt proto；`task_repository.dart` 直发 JSON；`why_this_today_panel.dart` 在场且消费 `PriorityReasoning.primary_reason`（`data/models/priority_reasoning.dart:71`）；ARCHITECTURE_DELTA :29-32 四段引文近逐字、:40 kill-switch manifest/变更策略原文；MASTER_DESIGN"练了15分钟所以精通"(:44)、"最少澄清一个问题"(:37)；V4_DONE 第 7 问"音、震动效全关后价值是否仍成立"；V4-F03 卡验收原文（无 committed 回执不能触发成功/仅存记忆不算任务完成/证据登记不叫精通）逐条在场。

**CHALLENGED-C2（幻引 `AURORA_SEMANTIC_POLICY`）**：§4 confidence_band 称"对齐 `AURORA_SEMANTIC_POLICY` 受限输出"——全仓（backend/app、proto、mobile/lib，含大小写不敏感与 `semantic_policy` 变体）**零命中**，该符号不存在。修复要求：删除或替换为真实存在的权威（如 `AURORA_UNCERTAINTY_KINDS`/`DecisionUncertainty` 封闭词表纪律）。

**CHALLENGED-C3（`ACTION_ERROR_CODES` 计数失实 + 映射不总）**：§1 称"5 错误码 `ACTION_ERROR_CODES`"、§3 称"复用 ACTION_ERROR_CODES 五值，1:1 映射"、§6 称"五值 1:1 复用"。实际 `action_command.py:164` 为 **6 值**：含 `INVALID_COMMAND`（`ACTION_INVALID_COMMAND`）。无理由的排除使映射对源权威**不总**：权威回执若携带 `ACTION_INVALID_COMMAND`，`error_state` 封闭枚举无表示。修复要求（二选一并写明）：(a) 论证 INVALID_COMMAND 属命令构造期错误、不产生权威回执，故显式排除并登记为投影器断言；(b) 扩为 6 值映射。

**CHALLENGED-C4（"终端只有这两类/覆盖完备"与 TerminalReason 不符 + TruthClass 漏 `demo`）**：
- §6 称"`commit_state=committed` 与 `error_state` 互斥且覆盖完备（终端只有这两类）"。实际 `TerminalReason`（:117）有 **4** 终态：committed/user_cancelled/user_rejected/expired。user_cancelled/user_rejected 是权威终态回执，在 ExperienceEvent 的 `commit_state`/`error_state`/`kind` 中无任何投影规则。"覆盖完备"表述对所引权威不实。
- §5 `last_valid_outcome.truth_class` 写作 4 值（actual/self_reported/estimated/unknown）并称"复用 D-02 `TruthClass`"；实际 TruthClass 为 **5 值**（含 `demo`："demo/seed cohort，消费方标注"）。resume 聚合器遇 demo 行无法表达。修复要求：显式声明 demo 的排除或纳入，并补 user_cancelled/user_rejected 的投影规则（不产生事件 / 非成功 notice，二选一写明）。

## 3. 反例质量 — CONFIRMED

`examples/counterexamples.json` 12 条与合同 §9 表（9 条）为两个集合：12 条 JSON 中 7 条与 §9 重叠，5 条为 JSON 独有（error_state_mixed/cross_object_subject/empty_candidates/fabricated_ref_scheme/why_now_without_basis），2 条 §9 独有（tracking_events/harness_mock 未入机器可读集）——建议实现卡前对齐为单一冻结集（非阻塞）。

逐条核验：12 条 `violates` 指向的不变量**全部真实存在**（I1/I2/I3 §0；C1 §2；E1/E2/E3/E4 §3；§2 candidates unknown 语义；§4 basis_refs≥1；§5 expires_at/last_valid_outcome；"卡验收#3"在卡文件第 25 行）。每个 payload 均可机器判伪（scheme 封闭集、枚举互斥、条件必选、null 语义均可断言）。示例与反例自洽（receipt epoch 42 与 rejected note "epoch 38 < current 42"、resume `memory_epoch_at_compute: 42` 一致）。轻微不精确（不影响可证伪性）：`memory_save_presented_as_task_done` 标 violates=[E1]，实际首要违反的是 §3 receipt_ref 封闭 scheme 规范（memory:// 不在六 scheme 内）；`fabricated_ref_scheme` 首要违反是 I3/§2 ref 域（标 C1 可辩护）。

## 4. 越权检查 — CONFIRMED

- **零产品码 diff**：`git diff 3c4618cc..1c1ad4e5 -- backend mobile proto gateway` 为空；变更仅 evidence 目录 + tasks.json 状态行。
- 未替用户批色板/像素：§3 `asset_ref` "仅指向已过审 token 集，模型无权选"，选择权留视觉线（diff_or_evidence_only 明示）；copy_key 冻结文案表本身未定义/未指定 owner（建议实现卡前明确归属 F03/视觉线，非阻塞）。
- 未改发布行为：§8 off/shadow/live 与"既有 kill-switch manifest"逐字来自 ARCHITECTURE_DELTA:40 变更策略原文；无 live 声明。
- §7 明文"本设计不越权改 UI"，接线归 contract-owner。
- RF-06 四要素对齐**属实**：结论（claim→selected ref 溯源）、确定程度（confidence_band/label 审慎标签、禁虚构精度）、来源（selected ref 可点、被拒候选不出正文）、纠正动作相邻（`user_can_correct=true` 恒成立 + A-06 四动作封闭词表 + `AuroraCorrectionPayload.normalize` + 只委托既有写路径）——四个要素分别有已核验的权威承载；RF-06 分支未逐行核验已在 limitations #3 如实披露。

## 5. 证据与交付完整性 — CONFIRMED（附注）

- run_manifest.json 命令/证据与实核相符（其对 :164 的"五值"摘录随 C3 一并更正）。
- 卡证据清单中 `test_results.json`/`review_receipt.json` 未随交付：本卡为纯 design、无实现可测，limitations #4/#5 已如实披露；本 receipt 即一审记录，`review_receipt.json` 由两审汇总角色按卡格式归档。
- example JSON 5/5 语法有效（独立复跑 `python3 -m json.tool` 通过）。

---

## 总裁决：**APPROVE-with-conditions**

设计总体扎实：复用优先立场真实（11 处权威 7 处行号级精确命中、3 处文档引文近逐字），新增面收敛为 4 处最小增量，反例可证伪，无越权。但以下 5 项须在实现卡（V4-B06+/F03）开工前落回合同文档，全部为**文档级修订，不需结构返工**：

| # | 条件 | 类型 |
|---|---|---|
| 1 | §4 增补 action_plan 版本门兼容机制：`:259/:340` 严格相等需改版本集合成员判定（v1+v1.1 双可读、按版本分派、v1 行 `why_now:null`），并把"字段级降级"明示为相对 X-01 整块降级的有意 delta | 必须修复（不修则"零影响"声明失实，v1.1 上线即降级全部存量行） |
| 2 | 删除/替换幻引 `AURORA_SEMANTIC_POLICY`（全仓不存在） | 必须修复 |
| 3 | `ACTION_ERROR_CODES` 更正为 6 值；对 `ACTION_INVALID_COMMAND` 明确"论证排除"或"扩入映射" | 必须修复 |
| 4 | 补 `user_cancelled`/`user_rejected` 终态投影规则，更正"终端只有这两类/覆盖完备"表述；§5 truth_class 对 `demo` 显式排除或纳入 | 必须修复 |
| 5 | §9 表与 counterexamples.json 对齐为单一冻结集；copy_key 冻结文案表指定 owner/落点 | 建议（非阻塞） |

条件 1–4 修复后无需重审全卡，由任意独立会话对修订 diff 做点验即可。

— wtB05R，2026-09-28，审查基线 `1c1ad4e5`
