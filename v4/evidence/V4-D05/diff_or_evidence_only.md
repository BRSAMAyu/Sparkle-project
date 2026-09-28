# V4-D05 · diff_or_evidence_only

执行：wtD05（worktree `../wtD05`，分支 `agent/v4/d05`，自 main@`90d8196a` 开出）· 2026-09-29 · 纯 backend，零 HEAVY，零模型调用，无迁移，无 proto/生成文件改动，mobile/ 与 gateway/ 零改动。实现 commit：`1e626998`。

## 1. 一句话设计

**D07 事实卡读面（`/insights/evidence-cards` → `EvidenceInsightService`）的全部出口过「呈现契约层」`backend/app/core/insight_presentation.py`（`insight.presentation.v1`，纯函数、零 IO/LLM、零第二真源）**：每张卡出面前过**夸大表述门**（M-06 因果断言扫描单一权威复用 + 数值面「因果/成效措辞×百分比」「部分关联子集上的百分比」双通道——三例只有两例关联写不出「因果提升67%」，违例卡整体扣下进 `meta.presentation_gate_dropped` 响亮失败）；呈现侧样本量按 D02 权威 `attr_<sha256[:32]>` 样本身份**先行去重**（D02-R1 C-3 消费方义务：重放投递如实计 raw、永不放大样本量，`duplicate_outcome_samples_dropped` 审计可见）；每卡挂**单主建议信封** `next_step`（一条观察≤一个主建议，>1 fail-loud；`user_can_reject=True`/`reject_penalty="none"` 结构冻结——拒绝路径真实存在（`record_response(REJECTED)` 一等事实）且零奖励后果）；挂**理解宣称门** `understanding`（无数据不出卡+不出宣称 `no_data_no_claim`；有 missing/censored 扣下「充分理解」资格 `incomplete_evidence`，档位定性）；payload 挂**回访记录** `data.revisit`（上次建议是否相关由真实事件证明：七态封闭词表——`related_outcome_observed` 必须携带去重后样本身份（`revisit_evidence_integrity` 钉死「非套模板」），用户拒绝是一等决定最高优先（即便事后有链接 outcome 也不改写），窗口/删失语义消费 D-05 `resolve_observation_status` 唯一权威；无事件不出回访 `no_prior_suggestion`）。

## 2. 「D07 事实卡」定位（卡面导航种子 → 真实路径）

- 卡面「D07 事实卡」= V3 遗产 **D-07 证据洞察卡读面**：`backend/app/api/v1/insights.py` `GET /insights/evidence-cards`（docstring 自证 "Evidence-driven insight cards (D-07)"）→ `backend/app/services/evidence_insight_service.py`（fact→interpretation→uncertainty→evidence→implication 五要素洞察卡）。本卡在该读面上做**呈现契约增量**，不重建、不造第二权威。

## 3. 实现面（真实路径）

| 文件 | 角色 |
|---|---|
| `backend/app/core/insight_presentation.py` | **新增·冻结契约**（615 行，`insight.presentation.v1`）：`presentation_sample_id`/`dedupe_outcome_samples`（D02 `derive_attribution_sample_id` 单一权威派生，重放恒同 id；domain=OCCURRENCE=decision_id 的 intervention occurrence 锚命名空间，与 D02 四域 UUID 锚点不同 id 空间不碰撞）；`exaggeration_gate`（三层：M-06 `scan_output_for_causal_assertions` 复用 / `CAUSAL_EFFECT_TERMS`（封闭，与 D-05 `FORBIDDEN_CLAIM_TERMS` 互补不重叠）×`_PERCENT_RE` / `n_linked<n_denominator` 分母门；文本面只扫 `SYSTEM_CLAIM_KEYS` 封闭键集——用户自述内容（goal 标题）不是系统宣称不进门）；`understanding_claim_gate`（samples=0→no_data；missing/censored>0→incomplete；`find_understanding_overclaims` 扫「充分理解」族）；`build_suggestion_envelope`（>1 主建议 ValueError fail-loud；`user_can_reject`/`reject_penalty="none"` 冻结常量）；`exclude_withdrawn_refs`（`<type>:<id>` 整串身份，I05 SourcePointer 同律：值同类型不同不连坐；unaffected 一等保留）；`build_revisit_record`+`RevisitRecord`+`revisit_evidence_integrity`（七态封闭词表；判定顺序确定性短路：no_prior → 用户拒绝 → 去重样本≥1 → D-05 观察窗二分） |
| `backend/app/services/evidence_insight_service.py` | 最小增量（+293/−47）：`build_cards` 全卡过夸大表述门（违例卡扣下+meta 登记，不静默改写/丢弃）；每卡挂 `next_step` 信封+`understanding` 块；`_interventions_that_helped_cards` 呈现侧样本量=按样本身识去重后的方向观察数（`uncertainty.samples` 去重口径 + `outcome_samples_raw`/`duplicate_outcome_samples_dropped` 如实随行；>0 时 qualifier `replayed_deliveries_excluded_from_sample`；fact 面计数保持 D-05 `SliceSummary` 权威原样）；`_build_revisit`（窗口内最近 exposure + 该 decision 的响应/outcome 行；拒绝最高优先否则最近响应；`resolve_observation_status` 算窗口态）；`_resolve_last_active`（users.last_login_at，D-05 同源读侧）；payload 根级 `presentation_schema: insight.presentation.v1`（五要素卡契约版本不变 v1，附加字段向后兼容） |

无新路由（`/insights/evidence-cards` 既有面零签名变化）、无迁移、无 proto/生成文件、无新表、无事件/registry 新名、无配置新旗标（呈现门为结构性恒在，无 off 开关需要——判定面只加严不改语义，回滚=revert 单 commit）。

## 4. 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **未重建 V3**：D-05 `association_summary`/`_aggregate_slices`/词表零改动（fact 计数仍出其权威）；D-02 账本/attribution 零改动（消费其派生函数）；M-06 扫描器零改动（复用）；Galaxy/D03/D04 面零接触。
- **V3 已满足面的差量举证**（不重做，测试钉死）：
  - 「标来源/样本/missing/censored」五要素结构 V3 已有（`uncertainty.qualifiers`/`samples`/`not_yet_observed`/`not_determinable`、`evidence[].refs`）——本卡只补样本量去重口径与理解档，正反测在 `test_evidence_insight_presentation.py` 全量断言沿用；
  - 拒绝记录路径 V3 已有（`record_response(REJECTED)`，无孤儿、幂等）——本卡补「零奖励后果」可读面（revisit `reward_consequence="none"`）与 photon_balance 不变量钉；
  - 已删行过滤 V3 已有（`not_deleted_filter()`/`deleted_at`）——本卡在**新读面**（revisit/方向观察行查询）同样过滤并加正反测（软删关联行→样本回落；软删 exposure→回访 no_prior 不复活）。
- **单一权威复用 5 处**（import 期消费，不复制语义）：D02 `derive_attribution_sample_id`；M-06 `scan_output_for_causal_assertions`；D-05 `FORBIDDEN_CLAIM_TERMS`/`resolve_observation_status`/`association_summary`；Goal/Task 真源读侧（goal_progress 卡零改动）。

## 5. 与验收逐条对照（可失败 = 每条一正一反；命令/exit code 见 run_manifest.json）

### 验收① 三例只有两例关联不能写因果提升 67% — PASS

- **反例钉（契约层）**：`test_three_examples_two_linked_causal_percentage_rejected`（n_linked=2/n_denominator=3 + 「关联后提升67%」→ `causal_percentage_claim`）；`test_partial_linkage_percentage_rejected_even_without_causal_word`（「67% 的情况如此」→ `percentage_over_partial_linkage`——分母未随行即拒）；`test_zero_denominator_percentage_rejected`（分母为零宣称百分比=假精确）。
- **反例钉（服务层）**：`test_three_exposures_two_linked_card_carries_no_causal_percentage`——3 exposure+2 链接 outcome 的真实卡：fact 3/2 随行、无「67%」无「提升/有效」族（全 payload 字符串扫描）、M-06 扫描零违例、`interpretation.causal is False`、qualifier `correlation_not_causation`+`small_sample` 在册。
- **正例**：`test_closed_template_claim_passes`/`test_full_linkage_descriptive_percentage_allowed_without_causal_terms`（分母完整的描述性百分比恒过门）；`test_user_content_not_scanned_as_system_claim`（用户自述内容不进门——门不误伤）。

### 验收② 无数据不出「充分理解」；已删来源不复用 — PASS

- **无数据**：`test_no_data_never_claims`（samples=0→`no_data_no_claim`，有删失无观察同判）；服务层 `test_no_data_means_no_cards_no_understanding_claim_no_revisit`（零证据→零卡+诚实空态+`no_prior_suggestion` 回访）；`test_three_exposures_two_linked_...` 同时断言 3 暴露 2 观察有删失 → `understanding.claim_allowed=False`+`incomplete_evidence_missing_or_censored`（「充分理解」资格扣下）。
- **已删来源不复用**：`test_deleted_source_rows_are_not_reused_by_cards_or_revisit`（软删关联行→样本 2→1 即刻回落；软删 exposure→回访不复活）；契约层 `test_withdrawn_ref_excluded_others_kept`/`test_same_value_different_type_is_not_same_source`（I05 同律：不连坐）。

### 验收③ 一条观察≤一个主建议，用户可拒绝且不扣奖励 — PASS

- **≤1 主建议**：`test_two_primary_candidates_fail_loud`（>1 → ValueError）；服务层 `test_every_emitted_card_has_at_most_one_primary_suggestion`（全卡型不变量）。
- **可拒绝且零惩罚**：`test_user_rejection_recorded_with_zero_reward_consequence`——真实 `record_response(REJECTED)` 落行恰一条、`photon_balance` 分毫不动、回访 `rejected_by_user`+`reward_consequence="none"`；契约层 `test_user_rejection_is_first_class_and_zero_penalty`（拒绝最高优先，事后链接 outcome 不改写用户决定，计数仍如实随行）。

### objective 回访证明相关性而非套模板 — PASS

- `test_revisit_proves_relevance_via_real_linked_outcome`（accepted+链接 outcome → `related_outcome_observed`+`proves_relevance=True`+`attr_` 样本身份在册；拒绝历史的回访结构化字段必然不同——模板复述不可能同构）；`test_related_claim_without_sample_ids_fails_integrity`（自封相关不携带真实链接身份→完整性假）；`test_no_prior_drops_fabricated_events`（无 exposure 编造响应=孤儿事件构建期丢弃）；窗口语义正反：`test_revisit_awaiting_states_from_real_window_semantics`（acted_awaiting vs awaiting_user）、`test_window_closed_without_outcome_is_censored_not_failure`/`test_churned_user_is_censored_churned`（超窗未回来=显式不结论，绝非失败）。

### D02-R1 C-3 重放不进样本量 — PASS

- 契约层 `test_replayed_deliveries_collapse_to_one_sample`（raw 3 → unique 1）+ `test_sample_id_matches_d02_authority_and_is_replay_stable`（与 D02 权威派生恒同）；服务层 `test_replayed_outcome_delivery_does_not_inflate_sample_size`（绕过写幂等的重放行：raw=2 如实、samples=1 不放大、qualifier 在册）。

## 6. 红线自查

- 纯 backend：mobile/ 与 gateway/ 零改动（`git status` 佐证）。
- 零 HEAVY、零模型调用：契约纯 stdlib 确定性函数；测试 sqlite 隔离（`db_session` fixture，不触 dev DB、不调模型、零费用；测试进程内的 LLMRouter init 为配置装载，无调用）。
- 无权限/跨用户/删除复活/假成功变更：全部查询带 user_id 属主过滤；门只加严（违例卡扣下更显眼，绝不把旧文案改成新文案）；回访 no_prior/censored 均为「显式不结论」；`.env` 零触碰（测试进程注入进程级 SECRET_KEY 环境变量，未读写任何 env 文件）。
- 不动 sparkle-cosmos 仓；不 push（本地银行领先 origin，本分支仅本地提交）。
