# M-04 Memory Conflict Resolver 接线 — 执行报告（接续）

worktree: `Sparkle-sysrev/wt9 @ 0ea1e198`（基线）→ 改动见 `changes.patch`（6 文件：1 新增 + 5 修改，+2202/-106，含 R2 返修；未 commit/push，已遵守）
gate: V3-2 ｜ stream MEMORY ｜ risk **high** ｜ reviewers_required=2 ｜ locks: memory-semantics + conflict-resolver
接续说明：前任 Worker 于 19:07 宿主重启阵亡，本报告为 Apex Worker 盘点后续作——**未重做任何前任已完成的工作**，修复清单见 §1。
真实 LLM 调用：0 次。主仓/共享 DB：零写入（本卡全部证据为 hermetic sqlite）。

## 0. 六句总结

M-04 的落点是既有 Stage20 雏形 `conflict_resolver_service.py` 的原位扩展：lane 注册表与两张审计表仍是唯一真源，新增 priority tuple（validity > epistemic class > lane tier > user-correction > recency > confidence，序与 CONFLICT_RESOLVER.md §3 一致）与每对冲突的确定性类别标注（TEMPORAL_CHANGE/SCOPE_DIFFERENCE/SOURCE_DISAGREEMENT/INFERENCE_CONTRADICTION/UNSAFE_AMBIGUITY），33 组参数化矩阵逐组钉死 action/reason/败者集/类别。五种行为全部接线：auto-resolve（supersede 链）、preserve-both（时间 scope 或实体锚不同即共存，今天-only 不覆盖长期偏好）、revoke-inference（显式事实胜推断）、ask-once（平级不确定 → surface_to_user + 结构化 clarification 随 unresolved_conflict 落库，测试钉死不静默选）、abstain（双方均未登记 lane → 不写不问留审计）。V3-FIX-10 前置项全部落实：F2（apply_live_decision 行锁 + 锁内生命周期复查 + 已 superseded 行保留首链指针 + 重放 no-op）、F4（用户仲裁补为 epoch 契约第 5 破坏性入口，败者改 SUPERSEDED 语义对称 + 同事务 epoch bump + memory.invalidated + crash 恢复补 bump）、F6（provenance 显式 source_type 权威 + 机器/人类边界在契约与模块 docstring 显式声明）、F7（守卫跳过与仲裁结局双计数指标）；F5 为发布序事项，论证登记（§3）。每条有效破坏性仲裁经 M-07 管道原子落 epoch bump + content-free `memory.invalidated`（D-01 词表现有 35 名零新名，`user_arbitration` 是 payload action 值非事件名——Leader 知悉即可，无需重冻）。证据：新测试 64 passed（33 组矩阵 + 4 项 R2 返修回归 + 3 个经生产入口 `write_candidate_to_l1` 的端到端集成 + 24 个语义/修复钉子）；受影响面回归 4 批 193 passed，2 项失败经 `/tmp` 干净基线克隆复现证实为预存环境项（LLM demo-mode），与本卡无关；主仓推进 e7ef4d32 与本 patch 六文件零重叠，可干净合入。

## 1. 接续盘点（前任遗产判定）

阵亡时树内：5 个已改文件 + 1 个 untracked 测试文件。逐文件判定：

| 文件 | 前任状态 | 本任处置 |
|---|---|---|
| `conflict_resolver_service.py`（+674/-62） | 主体完备：priority tuple、四类别、五行为、F2/F4 全套、provenance、clarification | 修复 3 处中断残留（下表），black 归一，补 `epistemic_class` 候选字段接线 |
| `memory_epistemic_contract.py`（+23/-4） | 完备：F6 的 `EXPLICIT_PREFERENCE_SOURCE_TYPES` + provenance 语义 + 边界 docstring | 原样保留 |
| `memory_invalidation_pipeline.py`（+4） | 完备：`MemoryMutationAction.USER_ARBITRATION` 第 5 入口枚举 | 原样保留 |
| `memory_inferred_write_lane.py`（+8/-1） | 完备：accept 全路径留审计（含 preserve-both）、candidate 携带 decay_policy | 原样保留（清除 2 处 black 误排既有行） |
| `business_metrics.py`（+22） | 完备：双指标定义 | 原样保留 |
| `tests/unit/test_conflict_resolver_categories.py`（863 行 untracked） | 33 组矩阵 + 24 钉子已写，**但有未跑通的收尾** | 补完测试基座（下表），扩 3 个端到端集成测试 → 1237 行 60 用例 |

中断残留修复清单（前任猝死时测试 49 failed / 8 passed，根因全部是「写完没跑」的机械不一致，无一涉及设计变更）：

| # | 残留 | 症状 | 修复 |
|---|---|---|---|
| 1 | `classify_episemic_class` 两处使用点错拼为 `classify_episemic_class`（少一个 o，import 正确使用处错） | NameError，所有走 resolve() 的测试死 | 改正 2 处拼写 |
| 2 | 矩阵基座 `_M` 摊平传参把 `epistemic_class`/`decay` 传给 `_cand`，但 `_cand` 签名未收 | TypeError ×33 | `_cand` 补 `epistemic_class` 参数；2 处直呼点 `decay=` → `decay_policy=` |
| 3 | `ConflictCandidate` 缺 `epistemic_class` 字段——但 2 组矩阵行（`explicit_class_column_outranks_derived`、`experience_outranks_hypothesis`）设计意图是候选侧显式类胜 record 侧派生类 | 设计无法表达 | 补字段 + `_candidate_side` 以 `explicit_class=` 透传（与 record 侧列语义对称） |
| 4 | `resolve()` 把「既有记录全部 inactive」误报 `scope_difference_preserve_both`（coexisting 也为空时） | F2 测试期望 `no_conflict` 失败 | 拆分：`not contenders and not coexisting` → `no_conflict`（保留 `inactive_ignored_ids` 审计） |
| 5 | 一处矩阵期望值拼错 `UNSAFE_AMBIGUETY` | 断言字符串不等 | 改正 |

## 2. 设计与实现（对照 CONFLICT_RESOLVER.md）

### 2.1 Priority tuple（§2/§3）

`(validity, epistemic_class_rank, lane_tier, user_correction, recency, confidence)`，元组序即裁决序：
- epistemic class rank：FACT(4) > EXPERIENCE(3) > OBSERVATION(2) > HYPOTHESIS(1)——§3「当前明确用户陈述 > confirmed 事实 > 观察 > 推断」的落法；类由 M-01 契约派生（显式列 > lane+source_type 推导），不新建真源。
- lane_tier 复用雏形注册表（explicit 4 > rule 3 > llm 2 > working_memory 1 > unknown 0）。
- recency 先于 confidence（§3 无 evidence-strength-先于-recency 的表述；矩阵 `temporal.newer_lower_conf_still_wins_recency_first` 钉死此序）。
- validity 恒 1（两侧都活才有冲突；inactive 行在 resolve() 入口即被剔出 contender）。

### 2.2 类别判定（§4，每对冲突确定性标注，随 resolution record 落库）

scope 不同（时间 scope today/bounded/global 取自 M-03 TTL 词汇——soft half-life 是保留策略不是主张范围，故 7d/30d 记录按 global 参与仲裁；或实体锚 hash 不同）→ SCOPE_DIFFERENCE；否则类不同且一侧 HYPOTHESIS → INFERENCE_CONTRADICTION；类不同无推断侧 → SOURCE_DISAGREEMENT；完全平级 → UNSAFE_AMBIGUITY；其余 → TEMPORAL_CHANGE。

### 2.3 五种行为（§5）

| 行为 | 触发 | 效果 |
|---|---|---|
| auto-resolve | tuple 分出胜负 | accept/reject；accept 时败者 retracted+supersede 链指向新记录（与 `memory_preferences.replaced_by_id` 对称） |
| preserve both | SCOPE_DIFFERENCE | accept 无败者：两条都活，审计记 `coexisting_record_ids`（「今天只有20分钟」与「通常晚上能学一小时」共存——规格 §1 原例即测试用例） |
| revoke inference | 显式事实 vs 推断败者 | 即 auto-resolve 的 INFERENCE_CONTRADICTION 特例：`test_explicit_correction_supersedes_and_retracts_old_inference` 独立钉死 |
| ask once | 平级 tie（且至少一侧已登记 lane） | surface_to_user：结构化 clarification（policy/question/category/双侧 options）随 `UnresolvedConflict.left_payload` 落库，未决冲突 API 直接可取 |
| abstain | 双方均未登记 lane 的 tie | reject `abstain_unsafe_ambiguity`：不写、不问、留审计（负控：一侧已登记即正常裁决，`test_registered_lane_beats_unknown_lane_without_abstain`） |

### 2.4 resolution record + provenance（验收 ②）

每条 resolution（含 preserve-both、reject、abstain、用户仲裁）落 `ConflictResolutionRecord`，metadata 携带：`conflict_category`、`per_record_categories`、`coexisting_record_ids`/`inactive_ignored_ids`、`provenance`（resolver_version + epistemic_contract_version + 候选/裁决侧的 lane/类/tier/user_correction/time_scope 快照）。lane 写路径改为**每个 accept 都留审计**（原实现只在有败者时）——对齐 §5「所有 resolution 产生记录」；破坏性副作用仍严格败者门控。

## 3. V3-FIX-10（M-01 REVIEW_RECEIPT_2 前置验收）逐项

| 项 | 落实 | 证据 |
|---|---|---|
| F2 P2 apply_live_decision TOCTOU/生命周期/行锁 | **落实**：`_load_records` 加 `with_for_update` + `deleted_at` 过滤；锁内逐行 `derive_status != ACTIVE` 复查——revoked/archived 行零改写，已 superseded 行保留首链指针（只记 `skipped_loser_ids` 审计不重指）；重放（败者已全部指向本 winner）→ no-op 不重复审计/epoch/事件；有效 supersede 与 epoch bump + memory.invalidated 同事务原子 | `test_f2_revoked_loser_never_touched`、`test_f2_superseded_loser_keeps_first_chain_pointer`、`test_f2_replay_is_idempotent_audit_epoch_event`、`test_f2_effective_supersede_bumps_epoch_and_writes_content_free_event`（content-free 断言：payload JSON 不得含记忆正文） |
| F4 P2 arbitrate_unresolved_conflict 漏 epoch + 败者终态不对称 | **落实**：登记 `MemoryMutationAction.USER_ARBITRATION`（第 5 破坏性入口）；仲裁行 FOR UPDATE + 终态 no-op；败者 `superseded_by_id=winner`（SUPERSEDED 语义对称，no longer 裸 RETRACTED；选 none 双侧 retract 无指针）；有效撤下与 epoch bump + memory.invalidated 同事务；`_half_done_loser_ids` crash 恢复面（上次中断已撤下但 epoch 未落 → 重放补 bump，宁多勿漏）；物化幂等锚点 `materialized_record_id` 先行落库缩小 crash 重复物化窗口 | `test_f4_arbitration_supersedes_loser_with_winner_pointer`、`test_f4_arbitration_bumps_epoch_and_emits_invalidation`、`test_f4_arbitration_replay_is_idempotent`、`test_f4_none_selection_retracts_both_without_supersede` |
| F5 P3 部署窗口（新代码+旧 schema 500） | **论证登记，非本卡代码项**：M-04 读写 `epistemic_class`/`superseded_by_id`（m01a 列），继承 M-01 的 schema-先于-代码（或同发）发布序约束；本卡未新增任何迁移。合入说明请主会话沿用 M-01 的发布序钉法（REVIEW_RECEIPT_2 F5 建议） | 无代码改动；见 §6 |
| F6 P3 守卫 explicit 判据 = 非ai_inferred 而非人类 | **落实**：`EXPLICIT_PREFERENCE_SOURCE_TYPES={user_state, chat_preference}` 声明为权威——显式写引用 ai_inferred 证据仍判 EXPLICIT（修复反向边角误拦）；未知/机器类 source_type（behavior/system）不自动获显式权威，仍证据决定；机器/人类边界在契约 docstring 与 resolver 模块头双处显式声明（「explicit = 用户陈述 provenance，非一切自动化写」） | `test_f6_*` 5 项（含守卫回归 `inferred_may_supersede` 不弱化） |
| F7 P3 episodic 侧守卫跳过无指标 | **落实**：`MEMORY_EPISTEMIC_GUARD_SKIPS_TOTAL{winner_lane,loser_lane}`（F7 原诉求）+ `MEMORY_CONFLICT_RESOLUTIONS_TOTAL{action,category}`（结局可观测；仅在应用时计数，shadow 比较不灌 live 计数） | `test_f7_*` 2 项（增量计数 + 守卫实际拦截断言） |

## 4. 验收对照（卡面 Acceptance）

| 验收 | 结果 | 证据 |
|---|---|---|
| 矛盾测试 ≥30 组 | **33 组**参数化矩阵（TEMPORAL 12 / SCOPE 6 / SOURCE 3 / INFERENCE 7 / AMBIGUITY 5），`test_matrix_has_at_least_30_scenarios` 钉死下界与四类别各 ≥3 | §5 实跑 |
| explicit correction 胜旧 inference | 矩阵 2 组 + 独立钉子（低 conf 0.4 显式纠正胜 0.99 旧推断，败者 supersede+retract 链验证） | `test_explicit_correction_supersedes_and_retracts_old_inference` |
| scope difference 可共存 | 矩阵 6 组（today/bounded/global 三向两两 + 实体锚 + 软衰减负控）+ 独立钉子（共存行保持 active 零改写）+ lane 端到端 | `test_scope_difference_coexist_keeps_both_records_active` 等 |
| clarification 不静默选 | 平级 tie → surface_to_user + 结构化 clarification（policy=ask_once、问题、双侧 options 带 lane/摘要/token）随未决冲突落库；abstain 分支不产生用户问题 | `test_high_gain_uncertain_conflict_emits_clarification_not_silent_pick`、`test_clarification_surfaces_unresolved_conflict_for_ask_once`、`test_abstain_rejects_without_creating_user_question` |
| resolution record + provenance | §2.4；D-01 事件契约同构（content-free payload、幂等、审计与 M-07 完全同管线同事务模式） | `test_resolution_record_carries_provenance_and_category` + F2/F4 全套 |

**事件词表**：复用 `memory.invalidated`（D-01 现册 35 名，零新名，registry sha256 未动）。新增枚举 `MemoryMutationAction.USER_ARBITRATION` 是事件 payload 的 `action` 取值（同 `supersede`/`bulk_revoke` 先例），不是事件名——按 Leader 指令知悉性登记，无需重冻词表。

**不得重建权威真源**：lane 注册表、epistemic 契约、M-03 TTL 词汇、M-07 失效管线、Stage20 审计表全部复用，本卡零新表零迁移。

## 5. 测试与证据

复现命令（worktree `wt9/backend`，SECRET_KEY 为测试进程变量不落文件）：
```bash
SECRET_KEY=<任意> .venv/bin/python -m pytest tests/unit/test_conflict_resolver_categories.py -q
# → 60 passed
```

| 批次 | 结果 |
|---|---|
| 新测试 `test_conflict_resolver_categories.py`（**64 用例**：33 矩阵 + 1 守卫 + 3 验收钉子 + 4 clarification/abstain + 5 F2 + 4 F4 + 5 F6 + 2 F7 + 3 lane 端到端 + **4 R2 返修回归**（F-1 探针场景/F-1 失败序/F-2 收敛路径/F-5 残留清算）） | **64 passed** |
| 回归①冲突面：conflict_resolver_service / epistemic_guard / memory_conflict_resolver / layer_conflict_resolver / unresolved_conflicts_api | 58 passed |
| 回归②管线与 lane：memory_invalidation_pipeline / inferred_write_lane / inferred_write_lane_queue / epistemic_contract | 上批含；lane 文件 1 failed（见下） |
| 回归③memory service 家族：service/gating/reads/regression + context_pack_conflicts + version_conflict | 20 passed |
| 回归④改动模块全体导入方：ltm_health/ltm_release_gate/inference_write_guard/inferred_chinese/retrieval_prefilter/revival_capture/outcome_promotion/past_session_ranking/plan_outcome/spine_degradation/context_budget/rule_y_guard/reflection_kill_switch + services/memory_subject_type | 115 passed + 1 failed（见下） |
| 风格：ruff（6 个改动文件）+ black --check（120） | ruff 全过；black：**M-04 自身 hunks 全 clean**——`business_metrics.py`/`memory_inferred_write_lane.py` 两文件在本 venv（black 26.5.1）下 --check 失败，但失败 hunks 全为基线 0ea1e198 既有行（干净克隆同样失败，R2 F-8 核实），非本卡引入（R2 返修口径修正） |

**基线预存失败 2 项（均经 `/tmp/m04-baseline-clone`＝基线 0ea1e198 干净克隆复现，与本卡改动面无关，环境性 LLM demo-mode 签名，与 M-01 R2 回执记录同类）**：
1. `test_memory_inferred_write_lane.py::test_two_consecutive_sessions_prompt_includes_inferred_memory`（M-01 R2 已记录的已知项）
2. `test_outcome_promotion_governor.py::test_outcome_promotion_governor_synthesizes_profile_ledger_into_profile_learning`

端到端集成证据（生产入口真实链路，非 mock）：`test_integration_lane_supersedes_cross_lane_loser_e2e`（working_memory 旧败者 → inferred 候选经 `write_candidate_to_l1` → 败者 superseded+epoch=2+1 条 memory.invalidated(action=supersede)+审计，全链一次断言）、`test_integration_lane_blocked_by_stronger_cross_lane_fact`（user_confirmed 事实挡下 0.99 推断：候选不落库、事实零触碰、零 bump 零事件、留拒绝审计）、`test_integration_lane_preserve_both_across_time_scopes`（bounded vs today-only 共存：双活、零副作用、SCOPE_DIFFERENCE 审计）。

## 6. 风险、限制与后续

1. **行锁的 sqlite 盲区**：`with_for_update` 在测试 sqlite 上静默忽略——锁内 `derive_status` 复查与 F-2 重锁复查逻辑均已测（语义断言），但 PG 真实行锁互斥行为未在本机实测（与 M-07 交付时同一局限；锁序与 M-07 管道一致：conflict 行/败者行 → epoch 行）。
2. **时间 scope 词汇有限**：today/bounded/global 三值仅认 M-03 确定性信号（decay_policy/due_at），无自然语言范围解析（「这学期」会被 30d 保留策略归为 global 参与仲裁）；SCOPE 判定刻意收窄防误共存，扩展留给后续证据卡。
3. **F5 发布序**：m01a 未 apply 的库上新代码会炸读路径（M-01 已登记录）——M-04 加重依赖（写 superseded_by_id）。合入说明需钉「schema 先于代码或同发」。
4. **abstain 面较窄**（by design）：仅双方均未登记 lane 的平级 tie；一侧已登记即正常裁决（负控测试钉死），未登记 lane 的告警日志沿用雏形机制。
5. **合入冲突面**：主仓 e7ef4d32（D-02 + V3-FIX-17）与本 patch 六文件零重叠（已核对 `git diff --name-only 0ea1e198..e7ef4d32`）；R2 另对主仓 820c0203 `git apply --3way --check` 干净通过。patch 基于 0ea1e198 可直接合入，无需 rebase。
6. **shadow 模式**（`SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE`，默认关）沿用雏形语义，本卡未改其行为，仅 shadow 记录不灌 live 指标（指标注释钉明）。

### 6.1 R2 登记项边界（REVIEW_RECEIPT_2 F-3/F-6/F-7）

- **F-3（stash commit 的 epoch 迟滞窗口）**：返修后已大幅收窄——重构把全部破坏性效果（败者 supersede + epoch + 事件 + 审计 + 终态）移入物化/stash 提交**之后**的单一收口事务，stash 前的中间提交只剩加性效果（新记录 + 锚点）；「破坏性先于 epoch」只剩 stash 与收口事务之间的 crash 且无人重放这一窗口，且 `_half_done_loser_ids` 重放恢复钩子仍在。登记不另修。
- **F-6（resolve 类优先 vs apply 守卫 lane-only 的分歧）**：今日不可达（lane 写方永不设候选 `epistemic_class`，该字段为 M-06 预留）；**M-06 接线当日**须将 `apply_live_decision` 守卫升级为类感知（或登记为 M-06 前置条件），否则 inferred-lane EXPERIENCE 候选胜 explicit-lane OBSERVATION 记录时会双活。已在此显式挂旗。
- **F-7（tie 选择与多败者类别标签随 DB 返回序漂移）**：语义等价（皆平级），观测面不稳；登记为后续小卡（ contenders 加确定性次级排序键即可），不阻塞本卡。

## 6.2 R2 返修记录（REVIEW_RECEIPT_2，VERDICT: CHANGES → 已全部落实）

| 项 | 修复 | 验证 |
|---|---|---|
| **F-1**（P2 探针复现）仲裁物化静默丢答 | ①`_materialize_side` 删除 inferred-lane 特殊分支——物化直达 `MemoryService.create_episodic_memory`，lane 机器写守卫（duplicate/限流/禁用）与 lane 内再仲裁整体移出用户显式动作路径（docstring 声明理由：CONFLICT_RESOLVER.md §3 用户显式纠正首位）；②**先物化后毁败者**（旧序的「先撤败者防 lane 自挡」前提随 lane 绕开而消失）；③物化失败 → `ValueError` 响亮失败，冲突保持 `pending_user` 可重试，绝不静默 resolved | `test_r2_f1_third_same_key_row_does_not_silent_drop_user_answer`（R2 探针 A 场景回归：第三条同 key active 行存在时选中侧必落库、败者 SUPERSEDED 非裸 RETRACTED、审计 winner 非 None、第三行不受牵连）；`test_r2_f1_materialization_failure_keeps_conflict_pending`（失败序：pending 保持/败者未毁/零 epoch 零事件零仲裁审计） |
| **F-2**（P2 结构性）FOR UPDATE 被方法内提交提前释放 | 物化阶段（仅加性效果）结束后、破坏性阶段开始前，**重取 conflict 行 `FOR UPDATE`（populate_existing）复查 `status=="pending_user"`**——并发对手已处理 → 按已处理收敛返回，不进破坏性阶段。破坏性阶段（supersede+epoch+事件+审计+终态）本调用内单事务收口 | `test_r2_f2_midflight_status_change_converges_as_processed`（stash 提交点注入并发已解决 → 本调用收敛：不毁败者/零 bump/零事件/零仲裁审计/不覆盖对手结果） |
| **F-4**（P3 探针复现）重放双计数 | `MEMORY_CONFLICT_RESOLUTIONS_TOTAL` 的 accept 计数挪到 `already_applied` 幂等早退之后——重放对指标也是 no-op | R2 探针 B 场景（重放不增计数）由代码序保证 + 既有幂等测试组 |
| **F-5**（酌情，已做）跨选择 crash 残留 | right/none 选择现在也读对侧与自身的 `materialized_record_id` 暂存残留并按败者清算（left 分支对称处理 right 残留）——中断尝试物化的记录不再无人认领双活 | `test_r2_f5_right_selection_cleans_stashed_left_remnant`（残留被 supersede 指向 right 胜者 + epoch/事件落地） |
| **F-9**（酌情，已做）payload action 值无钉 | `test_f4_arbitration_bumps_epoch_and_emits_invalidation` 补断言 `payload["action"] == "user_arbitration"` | 该测试 |
| **F-8**（酌情，已做）报告口径 | §5 black 行改为 R2 核实口径（两文件失败均为基线既有行，M-04 hunks clean） | 本节 |
| F-3/F-6/F-7 | 登记边界（§6.1） | — |

附带改善：重构后 `_supersede_record_to(winner_id=...)` 的直达指针赋值落在被测路径上（R2 变异 M2 的覆盖缺口由 `test_r2_f1_third...` 与既有 F4 指针测试共同钉住——backfill 循环已随重构移除，指针只在直达路径赋值）。

## 7. 改动清单

```
修改  backend/app/services/conflict_resolver_service.py   # M-04 主体：tuple/类别/五行为/provenance/clarification + F2/F4
修改  backend/app/services/memory_epistemic_contract.py   # F6：显式 source_type 权威 + 边界声明
修改  backend/app/services/memory_inferred_write_lane.py  # accept 全路径留审计 + candidate 携 decay_policy
修改  backend/app/services/memory_invalidation_pipeline.py# F4：USER_ARBITRATION 第 5 破坏性入口枚举
修改  backend/app/core/business_metrics.py                # F7 + 结局：双指标
新增  backend/tests/unit/test_conflict_resolver_categories.py  # 64 用例（矩阵/钉子/F2-F7/端到端/R2 返修回归）
```

base SHA: `0ea1e198` ｜ final: 工作树未提交（`changes.patch` 对 0ea1e198 干净应用）｜ R2 返修后 STATUS: **READY_FOR_REVIEW**（R2 复核范围：F-1/F-2 返修点 + 64 测试重跑，见 §6.2）
