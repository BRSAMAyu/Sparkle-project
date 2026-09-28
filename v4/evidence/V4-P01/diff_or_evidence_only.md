# V4-P01 · diff_or_evidence_only

## 语义缺口清单（现状盘点，base @ 17c14cea）

| # | 缺口 | 现状证据 | 卡面判据 |
|---|---|---|---|
| G1 | **两渠道两套预算**：nudge 渠道（`comeback_nudge_task`）过 P-03 类型抑制 + P-06 `evaluate_burden`（quiet hours + 真实 Notification 账本日预算）；spine 渠道（`recall_notification_task`）只有自身 Redis per-trigger 冷却（6–48h）——**不过 quiet hours、不占共享日预算**。用户关停（cap=0）时 spine 照发 | `backend/app/core/celery_tasks.py` comeback_nudge_task（P-03+P-06 调用亲证）vs recall_notification_task（无任何负担检查）；`backend/app/signals/recall_notification.py` 仅 Redis 冷却 | 「将当前nudges/spine渠道归到同一用户预算……触发基于合法事件/作用范围/quietHours」 |
| G2 | **拒绝/静音不跨渠道**：P-03 抑制按 `notification.type` 键控（"comeback_nudge" ≠ "recall_notification"）——用户在 nudge 卡上「今天不再看/不再提醒此类」后，spine 渠道可就同一 plan/task 补发同主题提示；反向亦然。subject（plan/task/goal）维度全仓无抑制态 | `backend/app/services/proactive_suggestion_service.py`（`_MUTE_KEY`/`_IGNORE_KEY` 均按 suggestion_type 键）；`record_suggestion_action` 只写类型键 | 「拒绝/静音/过期计划不再被另一渠道补发」 |
| G3 | **过期计划反复触达**：FIX-48 在案（「今天不再看」24h 语义在每日扫描下失效 + 过期窗口每日打扰实证）；过期计划经 spine recall（如 task_missed「这张任务错过了截止时间」）可被重复提示，而已校准的 rescope 呈现只存在于 nudge 渠道（J-07） | `backend/app/aurora/runtime_v1/service.py` get_comeback_context（plan_expired/stale_focus/rescope 亲证）；spine 侧无过期检查 | 「过期计划不再被另一渠道补发」 |
| G4 | **同一提示多端 effect 无身份锚**：通知行有 id 但无「同一提示」的渠道无关身份；多端/多 tick 重复投递的去重散装在各渠道（comeback 的 plan_id 重复窗 / spine 的 Redis 冷却），跨渠道无一次 effect 保证；预算消耗与触发因果（channel/trigger/subject）未与账本行同源留痕 | `_has_recent_notification`（类型内匹配）；spine `spine:recall_notification_cooldown:*`；Notification.data 无预算信封 | 「同一提示多端一次effect，预算与因果来源可追」 |
| G5 | **回归语义无明确钉**：comeback/回归无预算豁免（好），但该性质无守卫测钉住——未来回归路径（ Foreground app-open、`include_short_gaps` 面扩）可能引入「回归必须打扰」豁免；且回归路径对情绪推断面（emotion_hint）的零写入无行为钉 | `evaluate_burden`/`evaluate_suppression` 无 channel 特权分支；`_build_emotion_hint_summary` 只读用户自撰 fragments+chat sentiment | 「回归不视为必须打扰，不改变主题推断情绪」 |

## 实现面（一句话）

新增**组合层**（零新真源）`backend/app/aurora/proactive/unified_budget.py`：`UnifiedProactiveBudgetService.evaluate` 固定顺序闸门（回滚开关 → P-03 类型级抑制[既有] → P-03 **subject 级跨渠道抑制**[本卡扩展：另一渠道拒绝/静音后同 plan/task/goal 不补发] → 过期/缺失计划 subject[spine 渠道不补发；nudge 保留 J-07 rescope] → 同 prompt_key **一次 effect** 去重[带 subject 提示；24h 窗] → P-06 `evaluate_burden` 透传[quiet + 真实账本日预算，两渠道同一份]）；预算与因果留痕 = `build_budget_envelope` 盖进 Notification.data `proactive_budget`（与 cap 计数账本行同源）+ Prometheus `sparkle_proactive_budget_decisions_total{channel,decision,reason}` 有界 label；写入口 = suggestion-action API 把用户反馈升格为 subject 抑制（task→plan 解析、一次 effect 不叠加、静音单向升级、写失败 503 不静默丢保证）；P-03 权威内扩展（同 explicit JSONB 命名空间 `proactive_subject_suppressed`，非第二真源）；接线 = comeback_nudge_task 以闸门替代散装调用（对外 skipped 原因形状兼容）、recall_notification_task 闸门前置（被抑制不消耗 spine 冷却）、两渠道放行路径均盖信封。

## 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **未重建任何 V3 真源**：零新表、零迁移、零 proto、零新事件名（`git diff 17c14cea -- backend/app/core/event_registry.py backend/proto` 零改动）。P-03 存储载体（UserPreferencesCenter.explicit CAS 合并写）、P-06 解析器（quiet/cap/低刺激交集）、Notification 账本（cap 计数对象）全部原样消费。
- **改动 5 个既有文件均为接线/扩展**：`proactive_suggestion_service.py`（+subject 级方法与纯函数辅助，既有类型级行为零改动）、`celery_tasks.py`（两任务闸门接线+信封）、`notification_center.py`（API 记录面追加）、`config.py`（+2 旋钮）、`metrics.py`（+1 计数器）；新增 3 文件（闸门 + 2 测试文件）。
- **对外形状兼容**：comeback 任务 skipped 响应的 `suggestion_suppressed`/`notification_burden`/`notification_settings_unavailable` 形状逐字段保持；既有 242 基线测（含 `execute_counter==1` 抑制路径单读钉）零改动全绿。

## 与验收逐条对照（可失败 = 每条一正一反 + 反例钉 + 突变演示）

1. **拒绝/静音/过期计划不再被另一渠道补发** —— 反例钉（闸门级+任务级双钉）：nudge 渠道拒绝 plan X → spine 同 subject 被拦 `cross_channel_suppressed`（`test_cross_channel_rejection_blocks_spine_nail` + `test_spine_recall_blocked_after_nudge_rejection_nail`：spine 构建/trace/投递/冷却记录全部不发生）；反向 task→plan 解析后 nudge 同拦；muted 不随 24h 自愈。过期计划：spine `subject_expired`、nudge 保留 rescope（`test_expired_plan_blocks_spine_only`）；删除计划不复活（`test_missing_plan_subject_blocks_spine`）。反面（不过度抑制）：冷却到期真实放行。突变注入①：subject 检查永假 → 2 钉齐红 → 还原绿。
2. **回归不视为必须打扰，不改变主题推断情绪** —— 钉：cap=0 时 comeback 与任何触发同级被拦（`test_regression_comeback_not_privileged_nail`，无豁免路径）；闸门+抑制判定对 `CognitiveFragment` 零写入（`test_gate_writes_no_emotion_signals`——回归不改变主题推断情绪的输入面）。反面：预算内回归照常可达（不误伤）。突变注入③：comeback 预算绕过 → 回归非特权钉红 → 还原绿。
3. **同一提示多端一次effect，预算与因果来源可追** —— 钉：同 prompt_key 第二次判定 `already_effected`（闸门级+任务级账本信封匹配双钉）；信封含 prompt_key/channel/type/kind/subject/count/cap/decided_at 且与账本行同源（两渠道接线测试）。反面：一次 effect 不叠加（重复拒绝先到先得）、不同 subject 不受牵连、无 subject 提示不启用去重（节奏归渠道既有冷却）。突变注入②：去重禁用 → 2 钉齐红 → 还原绿。

## 红线自查

- 纯 backend：mobile/ 与 gateway/ 零改动。
- 零 LLM、零模型调用、零费用；闸门确定性（同输入恒同裁决）。
- 不绕权限、不造第二权威：预算面只消费既有事件/读面（P-03 JSONB、P-06 解析器、Notification 账本、Plan/Task 读侧）；无权限语义变更。
- 回滚开关：`PROACTIVE_UNIFIED_BUDGET_ENABLED=false` = passthrough（恢复各渠道既有行为，有测试钉）；保留 V3 路径与数据向后兼容（既有响应形状/存储零迁移）。
