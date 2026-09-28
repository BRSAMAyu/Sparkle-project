# V4-D03 · diff_or_evidence_only

执行：wtD03（分支 `agent/v4/d03`，自 main@`150bc205` 开出）· 2026-09-28 · 纯 backend，零 HEAVY，零模型调用，无 UI。

## 1. 一句话

**撤回是幂等的一等事实，不是分数减法**：结果撤回登记（内容寻址 `rtr_<sha256[:32]>`，重放恒同）→ 依赖索引（G-02 `oc=` 分段标记，分号精确分段）找出吸收了该 outcome 的 `mastery_audit_log` 证据行并**钉持久墓碑**（`effect_kind='retracted'`，任何后续重放结构性跳过——账本本身成为"旧 job 不能复活"的第二道防御）→ 同事务 bump **既有** per-user `memory_epoch`（复用 M-01/M-07 唯一世代权威，context 快照/I01 resume freshness/profile context 等一切钉 epoch 的读侧门自动判 stale）→ 重算在**发布栅栏**（base_epoch ≠ current_epoch / 排除集不全 / 目标已删 ⇒ 整体丢弃）下由 G-01 权威 `recompute_evidence_state` **前向回放仍有效事件**（无任何逆推减分）→ 值真变才推进 `revision`（新 version 发布，重放恒同值不产生版本抖动）；重算期读门 `pending_recompute` ⇒ UI 标 `stale_recomputing` **且**工具 `suggestions_allowed=False`（同一门两个出口，不存在"UI 标了过期、工具还在用旧建议"的分裂态）。

## 2. 语义缺口清单（现状盘点结论，base @ 150bc205）

| # | 缺口 | 现状证据 | 卡面判据 |
|---|---|---|---|
| G1 | **撤回无依赖索引**：记忆域撤回有 M-07 权威管线（epoch bump + `memory.invalidated` + 缓存 DEL），但 outcome→星图能力节点的派生依赖边（`oc=` 标记）无任何"撤回后查受影响面"入口——outcome 消失后 mastery 账本行永久保留其效果 | `grep -rn "pending_recompute\|retraction" backend/app` 仅 memory 域命中；`outcome_absorption_service` 只写不撤 | 「沿epoch与revocation机制实现受影响策略/insight/能力节点重算」（DATA_AND_GRAPH §撤回与重算：依赖索引查受影响） |
| G2 | **重放无法排除被撤回证据**：G-01 重放词表（evidence/set_point/projection）无撤回成员——即使想做重算，被撤回证据行仍会被融合（复活）；全证据被撤回时回落到**含撤回效果的存储值** | `mastery_evidence.py` `MasteryEffectKind` 三成员；`_load_prior_belief` 空历史回落 `current_mastery` | 「并发旧job不能复活已删内容」「严格区分删除材料、撤回推断、撤回结果，保留合法其他来源」 |
| G3 | **重算无并发栅栏**：全仓无"计算所依世代 vs 发布时点世代"比对；重算 job 与新撤回交错时会把过期世界写回 | `grep -rn "base_epoch\|publish.*gate" backend/app` 零命中（epoch 只用于读侧缓存门） | 「并发旧job不能复活已删内容」 |
| G4 | **重算期无统一过期读门**：UI 过期标记与工具建议门无共同判定面；重算中间态无类型化出口 | `grep -rn "stale_recomputing\|suggestions_allowed" backend/app` 零命中 | 「重算中UI与工具均标过期，不继续旧建议」 |

## 3. 实现面（真实路径）

| 文件 | 角色 |
|---|---|
| `backend/app/core/retraction_recompute.py` | **冻结契约**（513 行，`retraction.recompute.v1`）：撤回三分类 `RetractionKind`（material_deleted/inference_retracted/result_retracted，严格区分）+ 派生面 `DerivedFace`（capability_node/insight/strategy）+ 状态机 `RecomputeStatus` + 内容寻址 `derive_retraction_id`（幂等身份，不含时间）+ `plan_recompute` 依赖索引判定（`SourcePointer=(type,id)` 精确身份对，值同域不同不构成同源；`unaffected`=保留合法其他来源的显式一等结论）+ `assemble_valid_replay`（剔除撤回身份、`(occurred_at,event_id)` 确定顺序、显式减除）+ `evaluate_publish_gate`（三栅栏全函数：stale_epoch/missing_exclusion/target_gone，任一命中整体丢弃；世代不可证 fail-closed）+ `evaluate_read_gate`（UI+工具同门：pending 或世代落后 ⇒ `stale=True`+`suggestions_allowed=False`+`ui_marker=stale_recomputing`）+ `next_projection_version`（逻辑时钟严格 +1 永不复位）。import 期断言：墓碑值 = G-01 `MasteryEffectKind.RETRACTED` |
| `backend/app/services/retraction_recompute_service.py` | **服务面**（唯一 IO 入口）：`register_retraction`（幂等检出→墓碑条件更新→同事务 epoch bump（`_bump_memory_epoch_in_txn` 原样复用）→ content-free `retraction.registered` outbox 事件（event_registry 新注册名）→ 提交后 DEL 派生缓存（M-07 键集原样复用））；`recompute_capability_nodes`（依赖索引→幂等自愈墓碑→逐节点发布栅栏→G-01 `_load_prior_belief` 回放→值变才写回+revision+1+trace 行（projection，重放跳过）+复用 `GalaxyService._write_mastery_outbox_event` 同步下游投影）；`capability_node_read_state`（登记晚于最近重算 ⇒ pending ⇒ 读门） |
| `backend/app/services/galaxy/mastery_evidence.py` | 最小增量（+15/-2）：`MasteryEffectKind.RETRACTED="retracted"` 词表成员 + 重放 skip 集扩展（projection ∪ retracted）——撤回观测永不回炉；`parse_effect_kind` 经枚举自动显式识别；未知值 fail-closed 语义不变 |
| `backend/app/services/galaxy/stats_service.py` | 最小增量（+20/-0）：`_load_prior_belief` 墓碑分支——撤回行不融合、不进 presence，但其 `old_mastery`（写行时的诚实前置值）仍冻结重放锚（撤回最早证据必须回落其前置基线，而非把撤回效果烘焙进锚点）；全证据被撤回且历史为空 ⇒ 回落冻结基线（绝不回落含撤回效果的存储值） |
| `backend/app/core/event_registry.py` | +15：注册 `retraction.registered`（aggregate `user_retraction`，producer 本服务；payload content-free 纪律注释同 M-07） |
| `docs/aurora/rule_at_exceptions.md` | +2：Rule AT orphan-by-design 登记（生产触发方按卡序接线） |

零迁移、零 proto 改动、零新表（墓碑复用 `mastery_audit_log.effect_kind` 既有列；事件复用 `event_outbox`；世代复用 `user_memory_settings.memory_epoch`）。

## 4. 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **未重建 V3**：G-01 融合数学零改动（重放仍 = `recompute_evidence_state` 前向 Kalman + decay，测试钉权威值精确相等）；M-07 记忆域管线零改动（material_deleted 的记忆撤回仍归其所有）；D-02/D01/D-05 词表与行为零改动。
- **复用既有权威 6 处**：世代=C-07/M-01 `memory_epoch`（`_bump_memory_epoch_in_txn` 原子 UPDATE 原样复用，不造第二计数器）；依赖边编码=G-02 `_evidence_request_id`（`oc=` 分段，测试与编码器往返一致钉死）；回放=G-01 `recompute_evidence_state`；mastery 事件面=GalaxyService `_write_mastery_outbox_event`；缓存失效=M-07 `invalidate_derived_caches`；事件元数据=`build_event_metadata` 共享契约。
- **新增仅 2 文件 + 3 处最小改动 + 2 处登记**（见 §3；`git diff 150bc205 --numstat`：15/0 + 15/2 + 20/0 + 2/0，tracked 改动共 52 行）。

## 5. 与验收逐条对照（可失败 = 每条一正一反 + 突变注入演示）

1. **并发旧job不能复活已删内容** —— 正：`test_register_retraction_tombstones_derived_rows`（登记 ⇒ 依赖行墓碑 + epoch 1→2 + 事件恰一条）；反例：`test_stale_job_with_old_epoch_cannot_publish`（撤回后 epoch 前进，携旧 base_epoch 的 job ⇒ `discard_stale_epoch`，分数/revision 不动）+ `test_replay_after_tombstone_excludes_retracted_evidence`（完全不知晓撤回的 G-01 直呼重放也拿不回效果——账本防御纵深）+ `test_register_retraction_replay_is_idempotent`（重放零重复副作用）。突变注入 M1（栅栏旁路恒放行）⇒ 3 红 → 字节级还原（sha256 恒等）。
2. **非线性状态按有效事件回放而非减旧分数** —— 正：`test_recompute_equals_authoritative_replay_of_valid_events`（重算值 == G-01 权威对仍有效事件的回放值，精确相等；≠ 55 没撤回态、≠ 40 减法态）；反例面：`test_replay_is_forward_fusion_not_inverse_subtraction`（契约层：减旧分数继承存储漂移、回放只认账本恒同幂等，两者必然分歧）+ `test_retracted_entries_never_reenter_fusion` + `test_retract_all_events_falls_back_to_baseline_not_stored_value` + `test_legitimate_other_source_is_preserved`（吸收其他合法 outcome 的节点行不受连坐）。突变注入 M2（重算改 `old - (old-20)` 减法）⇒ 权威回放相等测红 → 字节级还原。
3. **重算中UI与工具均标过期，不继续旧建议** —— 正：`test_read_state_pending_marks_stale_and_blocks_suggestions`（登记后未重算 ⇒ `stale=True`+`suggestions_allowed=False`+`stale_recomputing`）；反例面：`test_discarded_gate_keeps_pending_stale_state`（栅栏丢弃后不静默恢复新鲜）+ `test_read_state_after_recompute_serves_fresh`（重算完成才转新鲜）+ 契约层同门断言（pending 无条件过期；世代落后同出口；新鲜且同代不保守过界）。突变注入 M3（读门 pending 分支旁路）⇒ 3 红 → 字节级还原。

三分类纪律：`test_invalid_kind_target_combination_rejected`（材料删除/推断撤回不走结果执行体；结果撤回只收 outcome 目标——不静默落错依赖边）；`plan_recompute` 候选面按撤回类型收窄（推断撤回不波及能力节点）。

## 6. 红线自查

- 纯 backend：mobile/ 与 gateway/ 零改动（git status 佐证）。
- 零 HEAVY、零模型调用：契约纯 stdlib 确定性函数；测试 sqlite 隔离（不触 dev DB、不调模型、零费用）。
- 无权限/跨用户变更：登记/重算全程 user_id 属主过滤；事件 payload content-free（ids/类型/世代，SECURITY_PRIVACY audit-without-exposure 同 M-07）；无假成功语义位（读门只会让"没重算完"更显眼，不会把旧账说成新账）。
- 删除不复活（双向）：被撤回证据结构性退出重放（墓碑）；合法其他来源不连坐（`unaffected` 一等结论 + `test_legitimate_other_source_is_preserved`）。
- 已知债务如实登记：服务面生产触发方本卡零接线（Rule AT/BJ 守卫自身机制收口 + `docs/aurora/rule_at_exceptions.md` 登记，消费卡=结果撤回 UI/FSM 入口 + 重算 job 调度）。
