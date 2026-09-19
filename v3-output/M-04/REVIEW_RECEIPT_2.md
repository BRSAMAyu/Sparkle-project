# M-04 REVIEW_RECEIPT_2 — 第二路 Reviewer（DeepAudit 深层审计）

- reviewer: R2（DeepAudit；M-04 risk=high、reviewers_required=2 之路 2）
- date: 2026-09-19
- 对象: wt9 未 commit 改动（6 文件 +2003/-68，基线 0ea1e198）+ `v3-output/M-04/{REPORT.md, changes.patch}`
- 方式: 全量代码审读（resolver 1301 行 + 契约/管线/lane 全链）+ 对照 CONFLICT_RESOLVER.md 与 M-01 REVIEW_RECEIPT_2 逐条推演 + 定向/回归 pytest 实跑 + **7 组变异验证 + 2 项一次性探针（复现后即删）** + patch 对主仓 dry-run
- 纪律: 未 stash/reset/clean/切分支；变异用 cp /tmp 备份法、结束已逐字节还原（`diff` 确认与审计开始前一致）；主仓与 dev DB 只读；未 commit/push

## 0. 实跑记录

| 项 | 结果 |
|---|---|
| 新测试 `test_conflict_resolver_categories.py` | **60 passed**（复现自报） |
| 回归①冲突面（conflict_resolver_service / epistemic_guard / memory_conflict_resolver / layer_conflict_resolver / unresolved_conflicts_api） | 20 passed |
| 回归②③管线/lane/契约/memory service 家族（invalidation_pipeline、lane_queue、epistemic_contract、memory_service、context_pack_conflicts、version_conflict） | 46 passed |
| 回归④导入方抽样（ltm_health_snapshot / ltm_release_gate / memory_inference_write_guard） | 11 passed |
| lane 文件 | 6 passed + 1 failed（`test_two_consecutive_sessions_prompt_includes_inferred_memory`） |
| 预存失败复核（/tmp/m04-r2-baseline＝干净克隆 0ea1e198） | 同 1 failed + outcome_promotion_governor 1 failed **均复现** → 确认预存环境项，与本卡无关 |
| `changes.patch` vs `git diff HEAD` | 六文件一致 |
| patch 对主仓 820c0203 `git apply --3way --check` | **干净可应用**（exit 0） |

## 1. 变异验证清单（7 组）

| # | 变异（对 conflict_resolver_service.py） | 结果 |
|---|---|---|
| M1 | 删 apply_live_decision 的 F2 生命周期过滤（`derive_status != ACTIVE` skip） | **红**：`test_f2_revoked_loser_never_touched`、`test_f2_superseded_loser_keeps_first_chain_pointer` 双挂 |
| M2 | 删 `_supersede_record_to` 内的 `superseded_by_id = winner_id` 赋值 | **绿**——指针实由仲裁 backfill 循环补上，该赋值自身的直达路径（left+stash、right 选择）无测试钉住（覆盖缺口，见 F-8） |
| M2b | 删仲裁 backfill 循环（败者补 winner 指针） | **红**：`test_f4_arbitration_supersedes_loser_with_winner_pointer` 挂 → SUPERSEDED 对称语义已被钉（经 backfill 路径） |
| M3 | 禁用仲裁的 `pipeline.apply_in_txn`（F4 核心） | **红**：3 个 F4 测试挂（bumps_epoch / replay / none_selection） |
| M4 | tie 分支 `surface_to_user` 改 `accept`（静默选钉子） | **红**：5 测试挂（矩阵 ambiguity×3 + clarification×2）→ 「不静默选」钉得很死 |
| M5 | 回退 no_conflict 拆分（全 inactive 仍落入 preserve_both） | **红**：`test_f2_revoked_loser_never_touched` 挂（拆分被钉） |
| M6/M6b | M6 单删 `already_applied` 标志 → **绿**（它与「effective 为空即早退」在受测路径不可区分）；M6b 删整个早退块 | M6b **红**：`test_f2_replay_is_idempotent_audit_epoch_event` 挂 → 重放幂等被钉；`already_applied` 标志的区分行为（败者被他人取胜时仍记审计）无测试 |
| M7 | 删全部 3 处 `with_for_update()` | **全 60 绿**——行锁在 sqlite 测试环境不可证伪（Worker §6.1 已自认；与 M-07 同一局限，PG 互斥行为未实测） |

## 2. 探针（一次性，复现后即删）

- **探针 A（仲裁物化丢弃）——复现**：构造 surface 冲突（left=推断候选，right=同 key 推断记录），再放一条**同 semantic_key 的 active 推断行**（today scope、preserve-both 共存产物）。用户选 left 后：`right superseded_by=None retracted=True`，落库 summaries=`['右侧旧说法','今天的临时安排']`——**用户选中的「左侧新说法」从未物化**，败者照样被销毁、冲突照样 resolved、epoch 照样 bump。详见 F-1。
- **探针 B（重放双计数）——复现**：同一 accept 决策重放，audit/epoch/event 均正确 no-op（各 1），但 `MEMORY_CONFLICT_RESOLUTIONS_TOTAL` 1.0 → 2.0。详见 F-4。

## 3. 发现（分级）

### F-1｜P2（探针复现）——用户仲裁的选中侧可被 lane 守卫静默丢弃：败者已销毁、胜者从未落库

- **执行链**：`arbitrate_unresolved_conflict(selection="left")` → `_supersede_record_to(right)`（flush 撤下败者）→ `_materialize_side(left_payload)` → left 侧 `source_lane="inferred_extraction"`（lane 写路径产出的候选恒为此值）→ `write_candidate_to_l1` 的**机器写治理守卫**：`_is_duplicate`（同 semantic_key 或同 evidence_token 的 active inferred 行存在即拒）/ `_within_rate_limit`（降级队列返回 None）/ `_is_user_disabled` → 返回 None → `winner_record_id=None` → backfill 跳过 → 败者保持裸 RETRACTED（无 supersede 指针——恰是 F4 声称消灭的不对称在该路径回潮）→ `effective_loser_ids` 非空 → epoch bump + memory.invalidated → `conflict.status="resolved"`。
- **触发条件**：同 semantic_key 存在另一条 active 推断行——**M-04 自己把 preserve-both 共存做成一等产出后，这类第三行状态是常态而非边角**（`mixed.one_coexisting_one_tie` 即此形态）；或仲裁落在限流窗口/用户关闭 inferred 写。60 个测试从未构造第三行，故全绿。
- **结果**：用户的显式回答被消费（冲突 resolved、另一侧销毁）而所选内容静默消失；审计 `winner_record_id=None` 无法揭示原因。这是「用户显式纠正 > 一切」产品语义（CONFLICT_RESOLVER.md §3 首位）的反例：显式人类动作被机器写守卫吞掉。
- **机制归属**：物化经 lane 的复用是基线遗留，但本卡重写该入口并宣称第 5 入口「落实」——丢答面未被处置亦未被登记。
- **修复建议（最小）**：仲裁物化路径对 duplicate/rate-limit/user-disabled 三守卫显式豁免或前置预检——物化失败时**不得 resolved**（保持 pending_user + 响亮失败），绝不先销毁败者后丢胜者。
- **验证**：探针 A 改后应失败（断言 left 已物化）。

### F-2｜P2（结构性，代码实证）——仲裁的 FOR UPDATE 串行化被方法内 commit 打断：并发重复仲裁可双 bump/双事件/矛盾审计

- **机制**：`arbitrate_unresolved_conflict` 入口对 conflict 行 `FOR UPDATE`，幂等完全依赖「锁保持到终态写入」。但 left-物化路径中途多次提交：`_materialize_side` → `create_episodic_memory`（memory_service.py 内部 `await self.db.commit()`）与 lane 内 `apply_live_decision`（结尾 commit）→ **锁随第一个内部 commit 释放**；M-04 自己新增的 `_stash_materialized_id` 又补了一刀显式 `await self.db.commit()`。此后到 `conflict.status="resolved"` 最终 commit 之间，并发 arbitrate 重新拿锁、看到 `status` 仍为 pending_user，全路径再执行一遍。
- **后果**：第二次物化被 `_is_duplicate` 挡下（无重复记录——讽刺的是正是 F-1 的守卫），但 `_half_done_loser_ids` 会把已终态败者当 crash 残留 → **epoch 双 bump、memory.invalidated 双写、ConflictResolutionRecord 双写且 winner_record_id 互相矛盾**（一有值一 None）——违反 M-07 管道自己声明的「exactly one bump / one audit row / one event per effective mutation」。方向保守（epoch 多跳号）不致腐化缓存，但审计真相分叉。
- **触发**：移动端双击/HTTP 重试层对同一冲突的近并发请求。顺序重放已被正确挡住（`test_f4_arbitration_replay_is_idempotent` + M3 变异红），并发交错在 sqlite（StaticPool 单连接）不可测——「测试全绿」掩盖的典型面。
- **修复建议（最小）**：物化与 stash 的 commit 之后、进入 epoch/事件/终态阶段之前，**重取 conflict 行 FOR UPDATE 并复查 status==pending_user**（一查即收敛）；或物化阶段整体移出锁窗（先决后物化）。

### F-3｜P3（代码推演）——stash commit 使「破坏性效果先于 epoch 落地」成为设计内窗口

- `_stash_materialized_id` 的先行 commit 使败者 supersede（此前经物化内部 commit 已可见）在 epoch bump 之前持久化。crash 于 stash commit 与最终 commit 之间且用户不重试 → 破坏性撤下永久无 epoch/事件（M-01 F4 所诉类别的静默复发）；`_half_done_loser_ids` 仅在**有人重放**时补 bump。窗口窄、有恢复钩子，登记即可。

### F-4｜P3（探针复现）——重放的 accept 双计数结局指标

- `_metric_inc(MEMORY_CONFLICT_RESOLUTIONS_TOTAL)` 在 `already_applied` 早退**之前**执行：重放对 audit/epoch/event 是 no-op，对指标不是（探针 B：1.0→2.0）。指标语义「counted at application time」被重放稀释。修复：挪到早退之后。

### F-5｜P3（代码推演）——跨选择的 crash 恢复缺口：残留的物化 left 永不被 right 选择清算

- 中断的 left 尝试已物化并 stash（`left_payload.materialized_record_id`）但冲突仍 pending；用户随后选 **right** → intended losers 只含 `conflict.left_record_id`（恒 None，候选侧从未回填行 id）→ `_supersede_record_to(None)` → `[]` → 无 bump 无撤下 → **物化出的 left 记录与 right 双活**，无人再问。stash 锚点只在 left 分支被读，right 分支不查。窗口：crash + 用户改选，窄但状态机洞。

### F-6｜P3（latent）——resolve() 类优先与 apply 守卫 lane-only 的裁决分歧（为 M-06 埋雷）

- `resolve()` 以 `(class, tier, …)` 排名：inferred lane 候选携带 `epistemic_class="EXPERIENCE"`（M-06 未来写法，字段已为此存在；矩阵 `inference.experience_outranks_hypothesis` 已承认类可越 lane）时可胜 explicit-lane 的 OBSERVATION 记录；但 apply 守卫只比 lane tier（`inferred(3) < direct_capture(4)` → guarded）→ 败者跳过、新记录照写 → **双活**。今日 lane 永不设候选 `epistemic_class` 故不可达；M-06 接线当日即兑现。建议守卫升级为类感知或登记 M-06 前置条件。

### F-7｜P3（观察）——平级 tie 的「哪条既有记录」与多败者的类别标签随 DB 返回序漂移

- `tie_record`/`primary_loser` 取 contender 迭代首见（无次级确定性键，SELECT 无 ORDER BY）：PG 上同一数据两次执行，clarification 的 right 选项与多败者场景的 `conflict_category` 可漂移。语义等价（皆平级），观测面不稳。

### F-8｜P3（报告失实）——「black --check 6 文件全部通过」不成立（实质无碍）

- 本 venv（black 26.5.1）下 `business_metrics.py` 与 `memory_inferred_write_lane.py` black --check 失败——但失败 hunks 全在**基线既有行**（snapshot_metric 的 zip 行、lane 的 docstring 空行/正则行），**基线 0ea1e198 干净克隆同样失败**；M-04 自身 hunks 全部 clean。即：回滚 black 误排是对的、diff 最小面成立，错的只是 REPORT §5 那一句自报。ruff 6 文件全过。

### F-9｜P3（微）——`user_arbitration` payload action 值无测试钉住

- F4 测试断言 `reason_code=="user_arbitrated"` 但从未断言 `payload["action"]=="user_arbitration"`；枚举封闭性靠 StrEnum 构造保证。词表纪律实质达标（registry 35 名未动、patch 零 registry 文件、`memory.invalidated` 复用），此为测试钉子缺口。

## 4. 逐风险面 Verdict

| # | 风险面 | Verdict | 要点 |
|---|---|---|---|
| 1 | 仲裁语义正确性 | **PASS（带登记）** | 抽 12 组矩阵行对照 CONFLICT_RESOLVER.md §1-§5 逐条推演全部吻合（TEMPORAL 新胜旧、recency 先于 evidence、FACT 胜新 OBSERVATION、explicit correction 0.4 胜 0.99 旧推断、today/global 与实体锚共存、平级 ask-once、双未登记 abstain、scope 优先于 inference 撤销）。`no_conflict` 拆分正确且被钉（M5 红）。tuple 为全序（validity 恒 1、datetime 归一 naive-UTC、float 末位）——确定性成立，唯 tie 场景**选哪条**受 DB 序影响（F-7）。user_correction 先于 recency 属文档化选择（旧 confirmed 胜新 registered 陈述；今日无此写方，理论面）。 |
| 2 | F2/F4 修复真实性 | **PASS（变异实证）** | F2 生命周期过滤真实（M1 双红）；行锁存在但 sqlite 不可证伪（M7 全绿，Worker 已披露）；F4 败者 SUPERSEDED 语义经 backfill 被钉（M2b 红；`_supersede_record_to` 直达指针赋值无钉，M2 绿）；F4 epoch+事件真实（M3 三红）；F2 重放幂等真实（M6b 红）。**但** F4 幂等的并发半边不成立（F-2）、指针对称在物化失败路径回潮（F-1）。 |
| 3 | 第 5 入口幂等 | **PARTIAL** | 顺序重放：真 no-op（测试+变异）；与 M-07 的 FOR UPDATE+derive_status 复查同构衔接。并发重放：锁被内部 commit 打断 → 双 bump/双事件/矛盾审计（F-2）；crash 无重试 → epoch 永缺（F-3）；跨选择残留（F-5）。 |
| 4 | clarification 不静默 | **PASS** | 判定是**确定性规则**非启发式：六元组严格相等 = 平级 → surface_to_user + 结构化 clarification（policy/question/双侧 options 带 lane/token）随 `UnresolvedConflict.left_payload` 落库；「信息增益」未做数值计算——平级即认定高增益（文档化于 §2.3，可辩护）。钉死程度极高（M4 五红）。abstain 不产生用户问题有独立负控。**但**澄清后的用户回答可被 F-1 丢弃。 |
| 5 | 词表纪律 | **PASS** | patch 六文件零 registry 改动；event_registry 35 名与 sha 不变；`memory.invalidated` 复用；`MemoryMutationAction` StrEnum 封闭，`user_arbitration` 为 payload action 值（与 supersede/bulk_revoke 同列）。微缺口：action 值无直接断言（F-9）。 |
| 6 | black 误排回滚 | **PASS（报告句失实）** | resolver 的 -63 行删除全部语义性（旧比较逻辑/`_retract_if_present` 替换），无格式噪声；两文件 black 失败为基线遗留、M-04 hunks clean（F-8）。diff 最小面成立。 |
| 7 | 测试语义 | **PASS（两处覆盖缺口）** | 60 用例真实且断言到肉；3 个端到端经生产入口 `write_candidate_to_l1`，**事件+审计+epoch 三链全断言**（accept: retracted+pointer+epoch=2+1 事件 action/memory_ids+audit reason/category/winner；reject: 零落库零触碰零 bump 零事件+审计；preserve-both: 双活零副作用+SCOPE 审计）。缺口：M2（`_supersede_record_to` winner 参数无钉）、F-1 形态（第三行共存）无测试。 |
| 8 | 合入预演 | **PASS** | `git apply --3way --check` 对主仓 820c0203 全文件干净（exit 0）；e7ef4d32→820c0203 只动 social/leaderboard 六文件，与本卡零重叠。C-03（context-retrieval 锁；orchestration/working_memory/services 种子）：文本冲突面预计仅 `business_metrics.py`（两侧皆为追加式，git 可自动合）；语义交互为设计内协同（C-03 过滤消费 active 行，M-04 supersede 收缩 active 集）。发布序：F5 论证成立（零迁移、依赖 m01a 列），合入说明须钉「schema 先于代码或同发」。 |

## 5. 总评

核心交付真实且质量高：33 组矩阵与规格逐条吻合、五行为全部接线、F2/F4 主体经变异红绿证实、词表零越界、diff 干净、合入无碍。两处 P2 均藏在「测试无法构造的形态」里——F-1（第三行共存/限流下的用户答案静默丢弃，探针已复现）直接违背本卡「用户显式纠正最高」的产品语义；F-2（锁窗被打断的并发双计）违背 F4 自己声称关闭的幂等面。两者修复面都小（守卫豁免/预检 + 终态前重锁复查），不动主体设计。

**VERDICT: CHANGES** —— 要求最小返修 F-1（仲裁物化失败不得静默 resolved/不得先毁败者）与 F-2（终态阶段前重取锁复查 status）；F-3 至 F-9 登记即可（F-4 一行修复可顺手带上）。返修后无需全量重审，R2 复核两个返修点 + 重跑 60 测试即可。
