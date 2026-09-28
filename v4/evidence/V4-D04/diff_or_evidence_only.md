# V4-D04｜星图证据与参与足迹分离 · diff_or_evidence_only

执行：wtD04（分支 `agent/v4/d04`，自 main@`7fd77b6d` 开出）· 2026-09-28 · backend 实现，零迁移、零 proto、零新表，无 UI 截图面（数据/判定面卡，呈现词表归 F 线），零模型调用。

## 1. 一句话设计

**星图只接「有效 outcome」**：吸收器在点亮前先过能力通道分类（`capability_channel.CapabilityChannel` 四值封闭词表：verified/practiced/non_human/trace_only），通道由 D-02 账本真相面（`TruthClass` 全 5 值 1:1，I01 `last_valid_outcome` 同口径，经 `OutcomeLedgerService.query` 公共读面有界扫描取得，不另立第二真相）× 证据面细化（人类独立检验 vs Agent receipt）决定——**只有 VERIFIED（独立检验通过）融合掌握度后验**；PRACTICED（练习过：自报完成/focus 覆盖）只解锁+溯源零融合；NON_HUMAN（run receipt/纯 receipt 升格）不计人类能力；demo/estimated/unknown 与纯时长源只留痕迹。同步三面收口：①spark 纯时长路径降级为活动痕迹（零掌握增长）；②展示面视觉/数据双区分（未检验节点 80+ 掌握标签封顶 + `capability_channel` 字段 + `projection_version` 透传）；③撤回读门接世代（D03 R2-C1/C-3 移交项落地）+ 分享不再加掌握度。

## 2. 可失败验收逐条（正反配对，全部真实命令/exit code 见 run_manifest.json）

### 验收① 只学习计时不显示掌握；Agent产物不计人类能力 — PASS

- **时长→活动痕迹（正）**：`test_time_only_spark_leaves_mastery_untouched_but_grows_trace`——无 outcome 的 spark：解锁+study_count+minutes 增长，mastery 恒 0；（反）`test_repeated_time_sparks_never_display_mastery`——5 次 60 分钟 spark 后 mastery 仍 0，审计行全 projection（重放跳过）、真实证据计数为 0。spark 写路径删除时长增量（`stats_service.spark_node`：`new_mastery = old_mastery`；`_calculate_mastery_delta`/`capped_legacy_mastery` 保留为 V3 兼容面不再进写路径）。
- **练习过≠检验通过（正/反）**：`test_focus_covered_completion_is_practiced_never_lights`——focus 覆盖把完成升到账本 ACTUAL（D-02 真相面），但时长型行为观察通道=PRACTICED：解锁可见、溯源在、mastery 0、零证据行；`test_self_reported_click_completion_is_practiced_never_lights` 同理。
- **独立检验点亮（正）**：`test_quiz_verified_completion_fuses_and_lights`——quiz 物化支撑的完成 → VERIFIED → Kalman 融合 30.0 + 证据账本行（`oc=` 幂等标记）；（幂等反例）重放 → duplicate 零双计。
- **Agent 产物隔离（正/反）**：`classify_outcome_channel` 对 `run_receipt` 事件面恒 NON_HUMAN（纯函数面 22 测钉死全映射）；DB 面 `test_run_receipt_outcome_alone_never_lights_never_unlocks`——SUCCEEDED receipt 单独到达：不解锁、不融合、只留溯源。X-08 的 receipt→ACTUAL 升格是账本「工作发生了」真相面，星图能力面不消费为人类能力。

### 验收② 撤回证据后节点、列表、insight 同 version — PASS

- **R2-C3 落地（读门接 epoch 为主）**：`test_same_second_retraction_caught_by_epoch_gate`——撤回事件与旧重算 trace 同墙钟秒（sqlite 秒粒度，D03 R2 量化的系统性漏检场景）：墙钟比对漏检（断言旧门确实漏），世代比对判 pending（节点级+用户级同判）。重算 trace 行把所钉世代写进 `request_id` 空位（`epoch=N`，R2 指定空位），`capability_node_read_state`/新增 `capability_user_read_state` 主判定切世代、墙钟仅作迁移前行兜底（`test_recompute_trace_row_pins_base_epoch`）。
- **R2-C1 落地（commit 前重读为辅）**：`_commit_epoch_gate`（单一判定点，与发布栅栏同 fail-closed 口径）——`test_commit_epoch_gate_discards_on_mid_window_advance`：窗口内 epoch 前进 ⇒ 拒绝；世代未动 ⇒ 放行；不可证世代（None）⇒ 拒绝。
- **同门同 version（正/反）**：`test_predict_next_gated_by_pending_read_state`（insight 面）——pending ⇒ 建议（predict-next）禁用，重算收敛后恢复且 `user_node_status.revision`（=新 version，经 `UserStatusInfo.projection_version` 透传到节点/列表两面）可见；图面响应新增 `capability_read_state`（`CapabilityReadStateInfo`，D03 `evaluate_read_gate` 出口的 schema 透传，不重造判定）——节点/列表/insight 消费**同一个门**。登记与重算发布后即时失效图面视图缓存（ttl=600 不再拖成分钟级分裂）。
- **撤回行零贡献（显示面）**：`get_evidence_counts_by_node` 排除 `effect_kind='retracted'/'projection'` 行（与 G-01 重放存在语义同口径），撤回行不再清 legacy 旗、不再计入检验证据。
- **用户级门不越权（反）**：`test_user_gate_fresh_when_no_retraction_despite_memory_epoch`——记忆域 epoch bump（M-01 删除/纠正）不得判星图过期；门比对限定撤回事件携带的世代谱系。

### 验收③ sprint奖励不读AI掌握分，跨用户分享不加个人能力 — PASS（分享=修复；sprint=差量举证）

- **分享不加分（正/反）**：`test_share_records_participation_without_mastery_change`——`handle_resource_shared` 掌握度分毫不动（原实现 +5 掌握，**已删除** `KNOWLEDGE_SHARE_BONUS`/`update_node_mastery` 调用），参与足迹经 `append_graph_event_source`（source_type=community_share，payload `capability_effect=none`）留痕，`galaxy.node.updated` 事件 delta=0，系统消息不再声称「掌握度提升」；（反）`test_share_writes_no_mastery_effect_rows`——零 mastery 审计行、不创建状态行（分享不证明学习）；（边界）非节点资源分享只有 community 事件。
- **sprint 奖励差量举证（卡面「当前仓库已满足本卡行为时做差量举证，不重写」）**：sprint 任务统计唯一口径 `sprint_task_ledger`（BP-4 裁决）只读任务账本（`Task.status`，`sprint_ledger_condition`），零 mastery 读取；photon 奖励走成就事件账本（`achievement_engine.SUPPORTED_REWARD_TYPES`），奖励路径无 mastery 读点（grep 证据见 run_manifest）；D04 后 spark 纯时长零增长进一步保证「时长刷不出 NODE_MASTERED（≥80）成就触发」——掌握分只能由 VERIFIED 证据推进。AI 打分（exam-sprint 诊断 set-point）写掌握度但**无任何奖励/付费路径读它**（DATA_AND_GRAPH「不把AI打分影响奖励和付费身份」）。

## 3. 交付物（真实路径）

| 文件 | 角色 |
|---|---|
| `backend/app/services/galaxy/capability_channel.py` | **新增·纯函数**（`capability.channel.v1`）：`CapabilityChannel` 四值封闭词表 + `TRUTH_CLASS_CHANNELS`（TruthClass 5 值显式映射，ACTUAL 证据面细化）+ `NON_TASK_SOURCE_CHANNELS`（quiz/behavioral→verified；focus/study_record→trace_only——「只学习计时不显示掌握」在词表钉死）+ `classify_outcome_channel`（确定性全函数，run_receipt 恒 NON_HUMAN、账本未命中 fail-closed PRACTICED）+ `fusion_observation_params`（非 VERIFIED 恒 None=不融合）+ `node_capability_channel` |
| `backend/app/services/galaxy/outcome_absorption_service.py` | 吸收器通道分流：`_resolve_capability_channel`（D-02 公共读面 3×100 有界扫描，I01 同款边界）+ `_absorb_positive_without_fusion`（练习解锁/痕迹零效果，absorbed 标记重放幂等）+ action 词表扩展（practiced/non_human/trace_only）+ `practiced` 进读面失效集 |
| `backend/app/services/galaxy/stats_service.py` | spark 纯时长零掌握增长（活动痕迹：study_count/minutes/unlock/projection 审计行保留；audit 写点补 GUID bindparams 修 sqlite 纪律方言）+ `get_verified_evidence_counts_by_node`（检验级计数，排除墓碑行）+ `get_evidence_counts_by_node` 排除 retracted/projection |
| `backend/app/schemas/galaxy.py` | `MasteryEvidenceInfo.capability_channel`（数据面区分）+ `UserStatusInfo.projection_version`（同 version 载体）+ `NodeWithStatus._calculate_status(status, verified)`（未检验 80+ 封顶 SHINING——「标签不能叫精通」；亮度保留存量分数=参与足迹）+ `CapabilityReadStateInfo` + `GalaxyGraphResponse.capability_read_state` |
| `backend/app/services/retraction_recompute_service.py` | **D03 R2-C1/C-3 移交项落地**：trace 行钉世代（request_id `epoch=N`）+ `capability_node_read_state` 世代为主/墙钟兜底 + `capability_user_read_state`（用户级门，图面/建议面共用）+ `_commit_epoch_gate`（commit 前重读，fail-closed）+ 登记/重算发布后失效图面视图缓存 |
| `backend/app/services/galaxy_service.py` | 图面接线：verified 计数→`from_models`（视觉/数据双区分）+ `_capability_read_state_info`（门出口进图响应，查询失败降级 None）+ `predict_next_node` 接 `suggestions_allowed` 门（重算中不给建议） |
| `backend/app/api/v1/galaxy.py` | 节点详情面 user_stats 增 `capability_channel`/`projection_version`（与图列表同源同门） |
| `backend/app/services/community_signal_bridge.py` | 删除 `KNOWLEDGE_SHARE_BONUS`+掌握度写入；分享=参与足迹（溯源快照+delta=0 事件+不声称掌握的系统消息） |

测试：5 个新文件 46 测（纯通道 22 / 吸收通道 7 / spark+标签 7 / 读门世代 7 / 分享 3）+ 更新 6 个既有文件中被 D04 合法取代的断言（15 处，逐条见 §5）。

## 4. 不做什么（边界守护）

- 不重建 V3：G-01 Kalman 融合数学、账本重放、`LEGACY_TIME_MASTERY_CAP` 纯函数（含其 V3 测试）原样保留；D04 只改**写路径与消费面**。存量 mastery 不动（参与足迹保留，展示面加诚实标签）。
- 不造第二归因/第二真相：通道判定只消费 D-02 公共读面与 `TruthClass` 词表；撤回零贡献复用 D-03 墓碑+世代，不重复判定。
- 零迁移：trace 钉世代用既有 `request_id` 列空位（R2 指定）；通道字段是读模型/schema 追加；`absorbed_outcomes` 标记复用既有快照键。
- 不接「结果撤回」以外的 UI/FSM 入口（D03 移交的生产触发方仍按卡序归其消费卡）。

## 5. 既有测试断言更新（D04 合法行为变更，非删断言凑绿；逐条对照）

| 测试 | 原断言 | 新断言 | 依据 |
|---|---|---|---|
| `test_stats_service.py::test_spark_node_flow_with_mocks` | 时长 spark 后 mastery>0 | ==0（解锁/痕迹断言保留） | 卡面「只学习计时不显示掌握」 |
| `test_mastery_evidence.py::test_spark_time_only_path_capped` | 39 封顶到 40 | 保持 39（封顶公式保留为纯函数面，其 V3 断言不动） | 同上 |
| `test_outcome_absorption.py` 9 处点亮机制测（GJ05/重放幂等/同因 receipt/异任务各计/FIX-292/翻转防御/节点解析×3/消费者路由） | 无检验点击完成点亮 | 各补 `_add_quiz_pass`（独立检验载体），原融合数值/幂等/解析断言逐字节保留 | 卡面「星图接有效 outcome」 |
| `test_outcome_read_model_visibility.py` 2 处 | 无检验完成点亮后读面可见 | 同上补 quiz | 同上 |
| `test_delete_correction_consistency.py::test_provenance_prune_cannot_resurrect_absorbed_light` | 无检验完成点亮后剪溯源不复活 | 同上补 quiz（剪除/复活红线断言不动） | 同上 |

## 6. 突变注入（可失败性实证）

- **M1 吸收器通道门旁路**（`if channel is not VERIFIED` → `if False and ...`）：`test_outcome_absorption_channels.py` 4 failed（focus 练习点亮 30.0 / 点击完成点亮 / receipt 解锁 / 重放非 duplicate）——还原后 sha256 恒等（`1e9f77f5…` 前缀快照）。
- **M2 读门世代分支旁路**（`_pending_by_epoch` 恒 False）：**0 失败**——`evaluate_read_gate` 契约层世代比对构成第二道防御（服务层 pending 分类被旁路后，钉世代仍经 computed_epoch<current_epoch 判 stale）。非测试空洞，记录为纵深防御实证；服务层分支的价值在 RECOMPUTED/FRESH 状态命名与墙钟兜底选择。
