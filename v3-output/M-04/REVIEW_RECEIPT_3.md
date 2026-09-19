# M-04 REVIEW_RECEIPT_3 — R2 返修复核（快复核）

- reviewer: R2（同 REVIEW_RECEIPT_2 作者；按约定范围：F-1/F-2 两点 + 64 测试重跑，不做全量重审）
- date: 2026-09-19（返修轮）
- 对象: wt9 返修后工作树（6 文件 +2202/-106，基线仍 0ea1e198）+ REPORT §6.2 + 重生成 changes.patch
- 方式: 返修代码审读 + 64 测试与回归 sampler 实跑 + **R2 探针 A 原构造复跑**（一次性，跑后即删）+ **2 组定向变异**（cp /tmp 备份法，结束 diff 确认逐字节还原）+ 豁免范围核查 + patch 对主仓 2375694c dry-run

## 0. 实跑记录

| 项 | 结果 |
|---|---|
| `test_conflict_resolver_categories.py` 全量 | **64 passed**（60+4，复现自报） |
| 回归 sampler（conflict_resolver_service / epistemic_guard / memory_conflict_resolver / layer_conflict_resolver / unresolved_conflicts_api / invalidation_pipeline / lane / lane_queue / epistemic_contract） | 58 passed + 1 failed（`test_two_consecutive_sessions_prompt_includes_inferred_memory`——首轮已在干净基线克隆 0ea1e198 复现确认的预存环境项，与本卡无关） |
| R2 探针 A 原构造复跑（第三条同 key active 行在 surface **之前**存在、参与 contender 集——比 Worker 回归测试更早注入的变体） | **翻转绿**：`左侧新说法` 恰落库 1 条、败者 retracted+superseded_by=胜者（非裸 RETRACTED）、第三行零牵连、epoch=2、1 事件 |
| patch 对主仓 2375694c `git apply --3way --check` | exit 0；5 文件干净，`business_metrics.py` **3way 冲突**（预期内，见 §4） |
| 变异后还原 | `diff` 确认与返修态逐字节一致 |

## 1. F-1 复核 — **PASS**

| 验证点 | 结果 | 证据 |
|---|---|---|
| ①物化绕开 lane 机器守卫 | **通过** | `_materialize_side` 的 inferred-lane 特殊分支已整删，全 lane 直达 `MemoryService.create_episodic_memory`；resolver 中对 `write_candidate_to_l1`/`MemoryInferredWriteLaneService`/lane 模块的引用**清零**（grep 无命中）——不是旗标豁免而是结构性解耦，机器写路径不可能搭便车 |
| ②先物化后毁败者 | **通过（变异实证）** | 顺序：物化（L822-833）→ F-2 复查 → 失败即 ValueError（L866-870）→ 破坏性阶段（L873+）。变异 R2 把旧序（先毁败者）注回 → **两条 F-1 回归双红**：failure 测试挂（败者已毁）、third-row 测试挂（裸指针 `superseded_by_id=None`，胜者指针断言失败）——顺序与指针两个性质都被钉死 |
| ③物化失败响亮失败、保持 pending | **通过** | `test_r2_f1_materialization_failure_keeps_conflict_pending`：ValueError + status 仍 pending_user + 败者未毁 + 零事件/零仲裁审计/epoch=1 |
| ④探针 A 场景翻正 | **通过** | Worker 回归测试（第三行后置注入）+ 我的原构造复跑（第三行先置、参与 contender）双双通过——两种注入形态都覆盖 |
| ⑤审计揭示真实胜者 | **通过** | third-row 测试断言 `audit.winner_record_id == winner.id`（旧实现为 None） |

## 2. F-2 复核 — **PASS**

| 验证点 | 结果 | 证据 |
|---|---|---|
| ①终态阶段前重锁复查 | **通过（变异实证）** | L848-862：重取 conflict 行 `FOR UPDATE` + `populate_existing=True` 复查 `status=="pending_user"`，非 pending 按已处理收敛返回。变异 R1 删该块 → `test_r2_f2_midflight_status_change_converges_as_processed` **红**（覆盖对手结果被改写/败者被毁/双计）——复查块（含 `populate_existing`，否则 identity map 旧值穿透）被钉死 |
| ②破坏性阶段单事务收口 | **通过** | 复查通过后至最终 commit（L939）之间无任何内部 commit：`_supersede_record_to` 仅 flush、`apply_in_txn` 默认 commit=False、`record_resolution` flush——锁保持到终态落地，并发对手自此被 status 门挡住 |
| ③收敛语义 | **通过** | midflight 测试：不覆盖对手 selected_side=right、不毁败者、零 bump/零事件/零仲裁审计；且失败 ValueError 在复查**之后**——并发对手已处理时不抛错而是收敛返回，语义正确 |
| 残留窗口（登记，不阻塞） | — | 物化 commit 与 stash commit 之间的并发入场可产生**重复物化的胜者行**（双 active 同 key；lane 去重守卫已随 F-1 移除，此处无 backstop）。破坏性面仍单计（F-2 门有效），数据面为重复行 wart，且后续同 key 写入会再仲裁/ask-once 自愈。窄窗 + 保守后果，登记为已知边界 |

## 3. 豁免范围核查（用户仲裁豁免 ≠ 机器写豁免）— **PASS**

- lane 文件三个机器守卫（`_within_rate_limit` L500 / `_is_user_disabled` L513 / `_is_duplicate` L517）原样在位且仍由 `write_candidate_to_l1` 强制执行；lane 文件 diff 与首轮完全一致（+9/-1）。
- 机器写路径（lane → resolve → apply）测试 58 项全绿（含 lane 自身 6 项与 queue 套件）——守卫行为未弱化。
- 豁免实现方式为**路径分离**而非开关旗标：用户显式动作（仲裁物化）根本不经过 lane，机器写没有任何新旁路。`forbidden_practices`（不得弱化既有守卫）合规。

## 4. patch 对主仓 2375694c — **PASS（一个预期内 3way 冲突）**

- `git apply --3way --check` exit 0：resolver / contract / lane / invalidation_pipeline / 新测试 5 文件干净。
- `business_metrics.py` 3way 冲突——**正是首轮 RECEIPT_2 预测的插入竞争**：C-03 在 `MEMORY_PREFILTER_REJECTIONS_TOTAL` 之后插入 `KNOWLEDGE_PREFILTER_REJECTIONS_TOTAL`，M-04 在同一锚点插入两个仲裁指标——additive-vs-additive，两段全保留即解（指标名互异、零逻辑依赖，~30 秒手工合入）。
- C-03 其余文件（context_retrieval_pipeline / graph_rag / retrieval_service / redis_search_client）与 M-04 六文件零交集。语义协同方向一致：C-03 prefilter 的 `lifecycle_inactive` 拒因消费的正是 M-04 supersede 收缩的 active 集，无反向耦合。

## 5. 变异表

| # | 变异 | 结果 |
|---|---|---|
| R1 | 删 F-2 终态前重锁复查块（含 populate_existing） | **红**：`test_r2_f2_midflight_status_change_converges_as_processed`（对手结果被覆盖/败者被毁/双计三连断言） |
| R2 | F-1 顺序改回「先毁败者再物化」（旧序注入 left 分支） | **红×2**：`test_r2_f1_materialization_failure_keeps_conflict_pending`（败者已毁）+ `test_r2_f1_third_same_key_row_does_not_silent_drop_user_answer`（裸 RETRACTED 指针断言） |

## 6. 附带返修项抽查

- **F-4**：accept 计数已挪至 `already_applied` 幂等早退之后（apply_live_decision 顶部不再有 metric inc）——重放不再双计数。✔
- **F-5**：right/none 选择的 intended_loser_ids 现纳入对侧与自身 stash 残留（L835/L837-842），left 取 right stash 兜底（L821）；回归测试断言残留被清算且 supersede 指向 right 胜者。✔
- **F-9**：`payload["action"] == "user_arbitration"` 已补断言（L951）。✔
- **F-8**：REPORT §5 已改为 R2 核实口径。✔
- 首轮 M2 覆盖缺口（`_supersede_record_to` 直达指针赋值无钉）：backfill 循环已随重构移除，指针唯一赋值点在直达路径且被 third-row/F4 测试覆盖。✔

## 7. 结论

两处 P2 返修均为**结构性修复**（路径解耦 + 重锁复查门），非表面补丁；四个新回归把两个发现钉死到变异级；我的原探针构造翻转绿；机器写守卫零弱化；合入面只剩一个预测内的 additive 3way 冲突。残留为一条窄窗重复物化（登记，保守后果、可自愈，不阻塞）。

**VERDICT: ACCEPT**
