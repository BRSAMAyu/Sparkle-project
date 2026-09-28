# V4-I05 · diff_or_evidence_only（经验策略影子验证与有界启用）

- 实现会话：wtI05（worktree `../wtI05`，分支 `agent/v4/i05`）
- base SHA：`ff02ec03`（main 心跳#9，含 I04 闭环）；本卡实现 commit：见 run_manifest.json `commit_after`
- 状态：实现 + 自测完成，**待独立审查（2 位，风险 high）**；review_receipt.json 为 PENDING 占位，由审查会话落盘，作者不自审

## 一句话

在 A-05 policy patch 既有六面白名单+真源证据门+版本化之上补齐学习闭环的中段（`backend/app/core/experience_strategy.py` 新增纯函数契约层 + `policy_patch_service.py` 模式化消费面）：策略候选先**影子对照**（`shadow_report` 两臂投影——control=不启用基线 / treatment=有界启用后经 A-05 既有 `reorder_nominations` 单一权威的应用结果，内容寻址 `expshadow_` 工件可审计复现）再**受限 live**（`EXPERIENCE_STRATEGY_MODE` 三档 off/shadow/live，默认 **shadow**=观察零行为、live 需显式开）：live 三道有界边界=admission **收益门**（同域观察面负向等权参与，无收益不静默自动激活、留 evidenced 等显式 confirm）+ **观察窗**（激活缺省补 `expires_at`=now+72h，无无限期 live）+ decision 面 **precondition/do_not_apply 门**（`human_required_step` 情境门出——I07 掌握门结构性不绕过）；证据纪律=重复引用保序折叠（`fold_evidence_refs`，重复摘要不累积为多源证据）+ censored 三态显式不结论（`censored_insufficient_evidence`，既非收益也非失败）+ 撤回传播（`invalidate_on_source_withdrawal` 消费 D03 `plan_recompute` strategy 面，命中源 revoke（actor=`evidence_withdrawal`）、unaffected 显式保留）。

## 差量（全部新增/插入；零删除既有断言或检查；A-05 core 契约词表零改动）

| 文件 | 变更 |
|---|---|
| `backend/app/core/experience_strategy.py` | **新增**纯函数契约层（`experience_strategy.v4.i05.v1`）：模式解析（unknown fail-closed off）／证据折叠+评估版本（`evalver_`）／观察面（方向只读 M-06 方向谓词，censored/unknown 永不产生方向）／收益判定（封闭四词表；严格多数，负向等权）／策略卡（A-05 patch 纯投影信封，构造期过既有 `validate_patch_request`——V1/V2/V3 fail-loud）／前置判定（precondition 键值域逐一 import 既有权威 GOAL_SLICE_TYPES/INTERVENTION_FRICTION_TAGS/EXECUTION_MODE_SLICES/GOAL_PURPOSES；do_not_apply 三键封闭）／影子对照工件（因果断言红线扫描 M-06 `scan_output_for_causal_assertions` 消费）／treatment 臂投影（直接调 A-05 `reorder_nominations`+因子投影，零第二实现）／撤回计划（D03 `plan_recompute` strategy 面 + 封闭 `SourcePointer` 身份域）。import 期断言：六面恰好 6（漂移 fail-fast）、strategy face ∈ D03 候选面 |
| `backend/app/services/policy_patch_service.py` | +消费面（v1 服务语义零破坏，全部 flag-gated）：`propose_patch` 折叠重复引用（重复不获独立 patch_id 身份）；`admit_evidence` shadow=策略卡+同域观察面+收益判定进指标/日志（激活行为照 V3）、live=收益门扣下无收益自动激活+有界窗；`confirm_patch` live 缺省补窗；`patched_decision_inputs` +`decision_context` 参数，shadow=门出投影只观察（返回与 off 逐字节恒等）、live=门出 patch 不进应用面（重排/因子/归因只看 allowed 集）；策略档位进决策输入缓存键（模式切换立即失效旧键）；新增 `shadow_report`（两臂对照审计工件，只读零副作用）与 `invalidate_on_source_withdrawal`（D03 strategy 面消费，版本前后入审计）；`revoke_patch` +`actor` 参数（默认 `user` 零行为变化）；`_verify_evidence` 抽取 `_memory_record_matches` 单一出处（判定语义零改写，P3-7/P3-4 注释随迁） |
| `backend/app/config/settings.py` | +2：`EXPERIENCE_STRATEGY_MODE: str = "shadow"`（默认 shadow=观察零行为；live 需显式开；未知值 fail-closed 按 off）+ `EXPERIENCE_STRATEGY_LIVE_WINDOW_HOURS: int = 72`（≤0 关闭有界化=回滚面） |
| `backend/app/core/metrics.py` | +1 计数器：`sparkle_experience_strategy_shadow_total{stage, verdict}`（stage ∈ {admission, decision}；verdict ∈ 收益判定+门出理由封闭词表） |
| `backend/tests/unit/test_experience_strategy.py` | **新增 56 测**（纯契约层：六面封闭正反/折叠+censored 正反/收益判定参数化/模式 fail-closed/前置判定含 I07 门/两臂对照/撤回精确身份+跨域不同域反例） |
| `backend/tests/services/test_experience_strategy_service.py` | **新增 17 测**（sqlite 隔离真实证据链：propose 折叠同身份+single 档不过线+naive 突变面对照；live 收益门三档对照 off=V3 激活/shadow=观察+激活/live=扣下留 evidenced；有界窗 live-only；**shadow 零行为红线**（加严形态：传入会门出的情境事实 shadow 仍与 off 逐字节恒等）；live 门出+无事实正常应用；shadow_report 双臂确定性+门出审计；撤回三档一致失效+unaffected 保留+同内容不复活+词表外 ref 拒绝） |
| `v4/04_tasks/tasks.json` | I05 状态流转（本 evidence commit） |

**零迁移、零 proto、零生成文件改动、零新表、零事件/registry 新名、A-05 core 词表（POLICY_PATCH_REASONS/STATES/TRANSITIONS）零改动、HEAVY=False、零真实模型调用。**

## 验收逐条（卡面，全部可失败）

1. **不新增任意 prompt/code 字段，不越六表面权限**：
   - 正例：合法六面 patch → 策略卡构造成功（payload 原样；`test_card_from_legal_six_surface_patch`）；`STRATEGY_ALLOWED_SURFACES is POLICY_PATCH_SURFACES`（import 同一对象非复制）+ 恰好 6 双钉（`test_six_surface_whitelist_is_exact_and_shared` + 模块 import 期断言）。
   - 反例（可失败）：surface=`prompt`/`code`/`system_prompt`/`temperature`/`memory_core` → ValueError（`test_card_rejects_non_whitelisted_surface` 参数化×5，与 A-05 服务测试同款词表）；payload 夹带 `hidden_prompt` 未知键 → V2 ValueError（`test_card_rejects_fabricated_payload_fields`）；词表外值 → V3（`test_card_rejects_out_of_vocabulary_payload_value`）。「prompt/code」没有合法 surface 名，结构上进不了策略层。
2. **缺失结果 censored；重复摘要不累积为多源证据**：
   - 正例（censored）：censored-only 观察面 → `censored_insufficient_evidence`——既 ≠ `no_benefit` 也 ≠ `benefit_observed`（`test_censored_only_is_explicit_no_conclusion`）；删失计数永不产生方向证据（`test_censored_counts_never_enter_direction`，M-06 红线 1 消费侧同律）；有方向证据时删失体量不改变判定输入（`test_direction_evidence_ignores_censored_volume`）。真实链路：D-05 生产路径 outcome 的 censored/unknown 由上游排除在 n_positive/n_negative 外，观察面只读 M-06 方向谓词（零重实现）。
   - 正例（折叠）：[ref,ref,ref] 与 [ref] 同 patch_id、同 single_observation 档、停 evidenced 不自动激活（`test_duplicated_refs_fold_to_unique_single_tier`——真实 D-05 证据链 + sqlite 落库断言 `len(evidence_refs)==1`）；折叠计数审计可见（`duplicate_folded_count=2`）。
   - 反例（可失败）：**突变面对照**——naive 按出现次数计证据时 3 份重复 = 3 观察 = repeated（D-05 `association_evidence_tier(3)=="repeated"` 事实钉死，`test_duplicate_refs_cannot_inflate_evidence_tier`/`test_naive_counting_would_have_crossed_auto_activation`）：即「若折叠被移除，该 patch 会过自动激活线绕过确认门」这一突变事实被钉住，生产路径的折叠即堵点。
3. **撤回源后相关策略失效；无收益策略不静默启用**：
   - 正例（撤回）：active patch 源被撤回（`material_deleted`，精确 `SourcePointer` 身份）→ revoke（actor=`evidence_withdrawal`、reason=`evidence_source_withdrawal` 入 transition_history）、effective 集立即排除、policy_version bump；其他来源 patch unaffected 显式保留；三档（off/shadow/live）一致——失效是账本事实不是模式行为（`test_withdrawn_source_invalidates_related_patch[off/shadow/live]`）；同内容再提议 = 同一 revoked 行不可复活（`test_reactivated_content_cannot_revive_after_withdrawal`）；词表外 ref → ValueError 不猜（`test_unknown_source_ref_rejected_loudly`）；跨域同值不同域不构成同源（`test_cross_domain_same_value_is_not_same_source`）。
   - 反例（可失败）：负向反超/平手 → `no_benefit`（负向证据等权，`test_prefer_requires_strict_positive_majority` 参数化×4；demote 对称×3）。
   - 正例（无收益不静默启用，live 收益门）：2 正 2 负同域（方向门过、收益判定 no_benefit）——off 照 V3 自动激活（零行为基线）、shadow 激活行为恒等 + `no_benefit` 进指标（不静默：观察在案）、**live 扣下留 evidenced 等显式 confirm**，confirm 路径保持合法（`test_live_mode_withholds_auto_activation_on_no_benefit`）；正向占优（3 正 1 负）live 照常激活且缺省补 72h 观察窗（`test_live_mode_bounded_window_on_beneficial_activation`）；off 激活不带窗（有界化 live-only，`test_off_mode_activation_has_no_bounded_window`）。

## shadow 零行为红线（I04 范式；突变反转变红实证）

- **红线断言（加严形态）**：`test_shadow_payload_identical_to_off_byte_for_byte`——即使传入**会门出 patch 的情境事实**（`human_required_step: True`），shadow 档 `patched_decision_inputs` 返回载荷（annotations ∪ context_component 的 canonical JSON）与 off 档**逐字节恒等**（提名序/applied ids/版本/因子全同）；门出投影只进指标（`stage=decision` 逐理由码计数）+结构化日志。
- **反转变红实证**：临时突变 `patched_decision_inputs`（shadow 档同 live 应用门出集，`strategy_mode == STRATEGY_MODE_LIVE` → `!= STRATEGY_MODE_OFF`）→ 复跑服务套件 **1 failed / 16 passed**（恰为红线测 FAILED：`test_shadow_payload_identical_to_off_byte_for_byte`）；还原后 17/17 绿。「shadow 偷跑 live 门」的任何实现都会翻红。
- **live 契约面**：同情境 live 档 → `applied_patch_ids == ()`、重排消失（V3 基线序）、`do_not_apply_human_required_step` 进指标（`test_live_gated_out_by_human_required_step`）；无门出事实时 live 正常应用（`test_live_without_human_required_fact_applies`——fail-closed 只对缺事实的门，不错杀）。
- admission 面同律：shadow 激活行为与 off 恒等（`test_shadow_mode_observes_but_activation_unchanged`），唯一差量 = 指标/日志观察（`admission` stage verdict 计数 +1）。

## 与既有事实的关系（不重建 V3；单一权威复用清单）

- **六面白名单/生命周期/证据门/版本化** = A-05 `policy_patch` 既有契约（本卡零词表改动；策略卡是 patch 的纯投影信封，非第二真源——构造期过既有 `validate_patch_request`）；
- **重排与因子投影** = A-05 `reorder_nominations` + `allocation_user_preference`/`proactive_gate_overrides`/`explanation_style`（treatment 臂零第二实现）；
- **方向谓词/censored 三态/因果断言扫描** = M-06 `experience_memory`（消费侧同律，零重实现）；
- **撤回分类/依赖索引/SourcePointer** = D03 `retraction_recompute`（strategy 面 = D03 docstring 预留的「后续卡接线」消费点，本卡落地；D03 服务面/星图重算零改动）；
- **precondition 值域** = D-05 `GOAL_SLICE_TYPES`/`INTERVENTION_FRICTION_TAGS`/`EXECUTION_MODE_SLICES` + I07 `hybrid_policy.GOAL_PURPOSES`（import 不复制）；
- **I07 掌握门不绕过**：双保险——策略卡 `human_required_step` 门出（decision 面过滤）+ 结构性（patch 应用面只经 A-02/X-02 既有守卫，本卡零新应用通道；`test_live_gated_out_by_human_required_step` + 纯层 `test_human_required_step_blocks_enablement`）；
- **I06 回执**：零改动（本卡对照工件自带内容寻址审计面；与 context receipt 的联动归后续消费卡，见 limitations）；
- **D04**：未启动（tasks.json PENDING）——本卡对照/启用效果的星图融合面**不在本卡**（策略效果不写 galaxy；observation face 只读 M-06/D-05 既有真源），D04 落地后「VERIFIED 才融合」由其通道承接，见 limitations #5。
- 本卡无 DB 迁移、无 proto 变更、无生成文件改动（wtI05 内 `backend/app/gen/` 为 gitignored 生成产物拷贝，仅测试环境需要，零提交）、无 HEAVY、零真实模型调用。

## 三档行为（回滚 = 关旗标；独立 commit）

| 档位 | 行为 |
|---|---|
| `off` | 本卡零行为：无折叠外语义变化（折叠是证据身份修正非行为面）、无指标、无窗、无门出、无影子观察——admission/decision 全链路 = V3（`test_off_mode_auto_activates_despite_no_benefit` / `test_off_mode_activation_has_no_bounded_window` 钉死） |
| `shadow`（**默认**） | 指标+结构化日志留痕（admission 收益判定 / decision 门出投影），**行为零变化**（shadow 载荷与 off 逐字节恒等——红线测 + 突变反转变红实证见上节） |
| `live` | 有界启用三边界生效：收益门（无收益不静默自动激活）+ 观察窗（激活缺省 72h）+ decision 门出（do_not_apply/precondition）；门出/扣下均显式 WARN + 指标审计；未知模式值 fail-closed 按 off（`test_unknown_mode_fails_closed_to_off` 参数化×6——live 只认字面） |

## 交付物索引

`run_manifest.json`（命令/exit/环境/零模型预算声明，pin 实现 commit）、`test_results.json`（73 测 + 受影响面 17 文件 549 passed 明细 + 突变反转记录）、`review_receipt.json`（PENDING 占位——high 风险待 2 位独立审查落盘）、`limitations.md`。
