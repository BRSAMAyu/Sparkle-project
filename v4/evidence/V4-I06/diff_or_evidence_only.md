# V4-I06 · Context使用回执与来源验证 — diff_or_evidence_only

- 卡：V4-I06（implementation · risk normal · 独立审查 1 位 · HEAVY=False）
- 分支：`agent/v4/i06`（worktree wtI06，未 push）；基线 commit：`a616f27f`
- 合同权威：`v4/evidence/V4-B05/contract_receipt_min.md` §2（`context_selection_receipt.v1`，双审 APPROVE）+ `examples/`（`context_selection_receipt.example.json`、`counterexamples.json`）
- 锁：context-receipt（本卡唯一 owner；无其他并行卡触该词表）

## 实现面（纯 backend；零 HEAVY；零模型调用）

**契约模块（新增）`backend/app/core/context_selection_receipt.py`**
- `CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION = "context_selection_receipt.v1"`（冻结）
- 四个封闭词表（冻结，测试钉死精确集合相等）：`SELECTION_ROLES`(4) / `CANDIDATE_STATUSES`(3) / `REJECTION_REASON_CODES`(8：`out_of_scope_memory|stale_epoch|utility_gate_rejected|conflicts_confirmed_preference|permission_denied|budget_exhausted|duplicate|expired`) / `WHY_NOW_CONFIDENCE_BANDS`(4，R1-C2 口径对齐既有审慎标签，不造档)
- ref scheme **复用不复制**：直接 import `ACTION_SOURCE_REF_SCHEMES`（`action_plan.py` 11 scheme 封闭集）；`parse_ref_scheme`/`ref_in_closed_schemes` 机器判定（反例 `fabricated_ref_scheme` 契约层拒）
- `ContextSelectionReceipt.validate_contract()`：C1（selected⇒reason_code=null；why_now.basis_refs ⊆ selected）、C2（非 selected⇒reason_code 必选且在词表）、duplicate ref、selector_version 非空白（不得 `""` 冒充已读）、`input_versions` null=未读取语义
- `rejection_reason_code()`：M-03 维度前缀 / M-05 selfcheck / C-08 漏斗 → 封闭码的**冻结映射表**（表序=判定序；未知 reason 兜底 `out_of_scope_memory`，实现卡钉死并声明）
- `apply_utility_gate_metadata()`：**V4-I02 接口点**——鸭子类型消费 `UtilityGateResult.to_metric_payload()` 冻结形状（`decisions:[{item_id,selected,score,reasons}]`）；门开→门拒覆盖为 `utility_gate_rejected`（门 reasons 进 debug-only note，≤140）、门选中转 selected；门关（metadata 缺席/形状不符）→ 原候选原样；未知 item_id 不构造悬空 ref（I3）
- `build_why_now()`：statement 非空但无 selected 依据 → None+WARN（反例 `why_now_without_basis` 契约层拒）
- `new_receipt_id()`：`csr_` + 26 位 Crockford Base32 ULID 形态；`context_selection_receipt_from_payload()` 读侧门（版本集合外→None+违例；candidates 缺失=旧生产者→unknown 标记不炸）

**装配层（新增）`backend/app/orchestration/context_receipt_assembly.py`**
- `assemble_pack_receipt()` 纯函数：装配面观测 → 回执。候选集=被扫描全集，归因判定序冻结：prefilter 拒用（M-03 映射）> surfaced（selected）> M-05 selfcheck（`duplicate_in_pack`→`duplicate`，其余→`utility_gate_rejected`）> 冲突 suppressed（`conflicts_confirmed_preference`）> deny-quiet（`permission_denied`）> ranked 被裁/无 attributable 缺口（`budget_exhausted`，缺口带 `unattributed_downstream` note，不悬空）
- 不可解析锚的记录不构造 ref 也不计扫描数；`budget.candidate_scan_limit`=实际扫描数、`selected_max`=实际选中数（如实读数；本面 token 预算裁剪为准，无独立整数上限——limitations 登记）

**服务层（新增）`backend/app/services/context_selection_receipt_service.py`**
- `record_receipt()`：落库前过 `validate_contract`，违例**不落库**（fail-closed，防第二真值污染）；`receipt_id` 唯一约束幂等（同轮重算不重复计数）
- `verify_receipt_sources()` / `verify_source_ref()`：**来源验证 E4 双重校验**——第一重 scheme 封闭集；第二重 join 真实存储（`episodic_memories`/`memory_preferences`/`memory_goals`/`plans`/`tasks`/`goals`/`stored_files`）+ 属主过滤；跨用户/不存在/畸形/集合外 scheme 统一 `unresolved/unknown`（不区分泄漏，不 500）；已删来源 `unresolved/deleted`。**永不构造 quote/时间**（卡验收「来源不可定位时明确unknown；不编时间/quote」）
- 「删除后旧receipt更新」= 读时验证语义：回执行只读不改写，每次读面消费现场 join——删除/纠正/越权如实反映（卡验收第 2 条）

**落库面（新增）`backend/app/models/context_selection_receipt.py` + Alembic 迁移 `i06_20260928`**
- `context_selection_receipts` 表（对齐 `context_pack_runs` 先例；JSONB 结构面唯一权威在契约模块，表不造第二真值）；`memory_epoch` 独立列（C-07 读侧 join/失效判定键）；`receipt_id` 唯一约束 + user/created_at 复合索引
- 迁移链 `wt598_20260927 → i06_20260928`（单头）；真库验证 upgrade→downgrade→upgrade 全通（见 run_manifest）

**接线（修改）`backend/app/core/context_pack.py`**
- `ContextPackBuilder.build`（chat/plan_review/context_focus 共用装配点，同一轮一个 receipt）：mode∈{shadow,live} 时捕获被扫描全集 → 装配 → 落库 → 挂 `ContextPack.context_selection_receipt`（新可选尾字段，默认 None 零破坏）
- **红线**：回执**刻意不进 `to_prompt_context()`**（note 是 debug-only，不进模型输入/用户正文；测试钉死）
- `metadata["memory_utility_gate"]` 为 I02 合入后的 metadata 落点（本分支无 I02 代码，键缺席=门关语义，回执照常产生）

**读面（修改）`backend/app/api/v1/experience_readouts.py`**
- `GET /experience/context-receipts/latest`（authed）：off/shadow → `receipt: None`（B05 §8「shadow 写先行、默认读关闭」）；live → 最近回执 + 逐条 `source_verification` + `resolved_selected_count`。消费纪律（合同 §7.1）：U03「我的理解」/移动端理解条目只可引用 `resolution=resolved` 的 selected ref

**开关**：`settings.CONTEXT_SELECTION_RECEIPT_MODE`（off|shadow|live，默认 **shadow**）；off=零产生零落库（V3 路径零变化，测试钉死）

## 卡验收对照（必须可失败）

| 验收 | 落点 | 测试 |
|---|---|---|
| 来源不可定位时明确unknown；不编时间/quote | `verify_source_ref` 统一 `unknown`；验证结果 metadata-only | `test_cross_user_and_missing_refs_are_unknown`、`test_fabricated_or_malformed_refs_are_unknown`、泄漏探针断言 |
| 用户看到的scope与后台一致，删除后旧receipt更新 | 读时验证（回执行不改写）；deleted→`unresolved/deleted` | `test_deleted_source_reads_unresolved_after_delete` |
| RAG引用可点原文；外部文本不变用户事实 | selected ref 原样可解析（`memory://episodic/<uuid>` join 真实行）；`document://<file_id>` join `stored_files`；why-now basis_refs ⊆ selected 拒伪依据 | `test_selected_refs_join_real_storage`、`test_why_now_basis_refs_are_verified`（RAG 引用句面归 C-04 citation/funnel 既有权威，本卡不重建——见 limitations） |

## B05 §8 双读/反例用例覆盖

- 版本门：集合外版本 → `(None, violations)`；旧生产者缺 candidates → unknown 标记不炸（`test_read_gate_*`）
- 反例机器集相关项：`fabricated_ref_scheme` / `empty_candidates_rendered_as_has_evidence`（结构面：空候选合法+`selected_refs==[]`）/ `why_now_without_basis` 全部钉死进契约测试

## 差量举证（no_duplicate_rule）

仓库此前无任何 `context_selection_receipt` 符号（`grep -rn` 零命中，见 run_manifest commands）；本卡为该契约的首个实现，不重写 V3：C-08 `context_funnel`（观测面）与 M-03 prefilter（词表来源）保持原样，回执只做其上的权威记录层，零行为改变（mode=off 全绿对照）。
