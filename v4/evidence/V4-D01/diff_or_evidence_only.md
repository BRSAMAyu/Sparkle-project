# V4-D01 · diff_or_evidence_only

## 语义缺口清单（现状盘点结论）

| # | 缺口 | 现状证据（base @ 1a53b8c3） | 卡面判据 |
|---|---|---|---|
| G1 | **交付即曝光**：D-05 漏斗锚点 `exposed` 在 `mark_delivered`（服务端下发收敛点）落账，后台/不可见下发也计成"已曝光" | `intervention_lifecycle_wiring.py` 写面 1a「交付即暴露」；S07 裁决原文：*"任意 delivered=用户真的看到"* 不可推导，V4 增量 =「保留接线；增加渲染曝光」 | 「不可见/后台下发不算看到」 |
| G2 | **真实呈现无记录**：`mark_seen`（客户端确认真实渲染的 SEEN 转场）零接线——FIX-507 接线明确「seen/snoozed 无词表成员，不接线、不造语义」，渲染事实无任何记录 | `intervention_record_service.mark_seen` 原实现 = 单行转场，无 lifecycle/无事件 | 「曝光了没记录」「记录真实操作而非用下发代替看到」 |
| G3 | **呈现面无 experience_event.v1 投影**：全仓无该契约实现；呈现侧只有 outbox 集成通知 `intervention.exposed`（7 天清理、无 receipt_ref/commit_state/dedupe_key） | `grep experience_event backend/app` 仅 B05 合同文档命中 | 「按 experience_event.v1 契约把真实呈现落成事件」 |

## 实现面（一句话）

按 B05 冻结契约 `experience_event.v1` 落了确定性投影器（词表封闭、E1–E4 不变量、commit_state 唯一真源=X-03 终态/错误码全函数投影、ACTION_INVALID_COMMAND fail-loud）+ 真实呈现记录服务面（唯一入口 `mark_seen` 真实转场，receipt_ref 必指 D-05 权威 exposed 回执，内容寻址幂等、可重放、韧性壳），FIX-507 三写面原样保留，交付面 detail 增 `exposure_basis=delivered` 显式区分交付回执与真实呈现。

## 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- 未重建 V3：无新表、无迁移、无新事件总线（发布走既有进程内 EventBus 既有实例）、无 proto 改动、无 D-05 词表扩展。
- 复用既有权威 5 处：`build_record_decision_contract`（决策契约投影，恒同 decision_id）、D-05 exposed 行（权威回执真源）、`InterventionRecordService` 转场状态机（原事件挂点）、`EventBus.publish`（既有总线）、`derive_lifecycle_event_id` 派生风格（事件 id 内容寻址先例）。
- 新增仅 2 文件 + 2 处最小改动（见 run_manifest.json scope_and_denominator.deliverables）。

## 与验收逐条对照

1. **旧生产接线与测试不回退；无新同义事件总线** —— `tests/services/test_f507_lifecycle_wiring.py`（9 测）与 `test_intervention_lifecycle_service.py`（18 测）原样全绿；`tests/services` 全量 1018 passed。事件与 `intervention.exposed` 语义不同义：一个是服务端下发回执，一个是客户端确认的真实呈现回执（receipt_ref/commit_state/dedupe_key 结构不同）。
2. **不可见/后台下发不算看到；重复 render 不重复曝光** —— 投影唯一入口 `mark_seen` 真实转场（已 SEEN 短路不挂勾）；`mark_delivered`/spine 下发路径零调用；SNOOZED→SEEN 再渲染产生同 `event_id`（内容寻址身份恒一，唯一曝光数=1）；等价无障碍曝光以 `rendered_surface=accessibility`（封闭两值词表）按真实操作记录。
3. **丢事件可重放且不会拖跨主业务** —— `event_id` 派生不含时间，`replay_rendered_exposure` 任意时点重算恒同 id；发布失败/投影异常只 `logger.warning`，SEEN 转场照常成立（韧性壳，FIX-507/530 同款判例）。

## I2 双门（receipt_ref 必指权威回执）的机制化

1. 构造期：`receipt_ref` 必选 kind 无 ref → `ExperienceEventValidationError`；
2. 服务期：投影前查证 D-05 `exposed` 行真实存在（同 user、未软删）——缺失 → 可观测降级 `no_authoritative_receipt`，不产事件、不伪造成功呈现。

## 红线自查

- 纯 backend：mobile/ 与 gateway/ 零改动（git diff 佐证）。
- 零 HEAVY、零模型调用：投影器纯 stdlib 确定性函数；测试 sqlite 隔离，不触真库、不调模型。
- 停止条件无触发：无权限/跨用户/删除复活/假成功变更（事件无权限语义字段由键集冻结测试钉死）。
