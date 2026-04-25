# Reviewer B — E10: 通知偏好设置→实际投递行为一致性
Timestamp: 2026-04-26T11:35:00+08:00
Chain Index: 26 (Round 4 — E-chain audit)

## Chain Flow Summary
用户在设置页可配置 `NotificationPreferences`（enable_system 全局开关、enable_interventions 干预开关、quiet_hours_start/end 免打扰时段）。`NotificationService.create` 调用 `_should_push_notification` 检查 `enable_system` 和 `quiet_hours`——关闭时跳过 WebSocket push 但通知仍写入 DB（用户可在通知列表中看到）。Celery 定时任务 `scan_daily_sprint_reminders` 和间隔重复扫描不检查偏好，仅依赖 `NotificationService.create` 内部检查。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`backend/app/models/notification_interaction.py` + `backend/app/services/notification_center_service.py:930-933`**: 通知偏好只有 `enable_system`（全局）和 `enable_interventions`（干预类）两个粗粒度开关，没有 per-type 开关。Expected: 用户能选择关闭复习提醒但保留冲刺提醒，或关闭每日提醒但保留里程碑通知。Actual: 用户只能全局开/关所有通知，无法按类型控制。`enable_interventions` 只控制干预类通知，6 种推送类型中只有干预类受此控制，其余 5 种（spaced_repetition、sprint_reminder、comeback、milestone、weekly_report）全部跟随 `enable_system`。Evidence: `NotificationPreferences` 默认创建时只有 `enable_system=True, enable_interventions=True`（line 932-933），无 per-type 字段。

## Minor Issues 🟢
**`backend/app/services/notification_service.py:127-136`**: 用户关闭 `enable_system` 后，通知仍写入 DB。Expected: 关闭通知后不再收到任何通知记录。Actual: WebSocket push 被跳过，但 DB 记录仍然创建，用户在通知列表页能看到"被关闭"的通知。行为一致（用户在通知列表页能看到历史），但可能让用户困惑——"我关了通知为什么还在出现"。

## Working Well ✅
- **`backend/app/services/notification_service.py:66-95`**: `_should_push_notification` 实现正确——检查 `enable_system` 全局开关 + `quiet_hours` 免打扰时段 + timezone 转换。
- **`notification_service.py:48-63`**: `_is_quiet_hours_active` 正确处理跨午夜时段（start > end 时 current >= start OR current <= end）。
- **`notification_service.py:119-149`**: push 抑制有完整日志——suppression_reason 记录具体原因（"system_notifications_disabled" 或 "quiet_hours"），便于排查。
- **`notification_center_service.py:130-154`**: `has_recent_spaced_repetition_reminder` 按节点去重 + 冷却期检查，防止频繁推送。

## Files Examined
- `backend/app/services/notification_service.py` (lines 35-160)
- `backend/app/services/notification_center_service.py` (lines 59-128, 923-951)
- `backend/app/core/celery_tasks.py` (lines 1289-1415, 1002-1004)
- `backend/app/models/notification_interaction.py` (referenced via imports)

## Confidence: High — preference 检查路径和 per-type 缺口已通过代码确认。
