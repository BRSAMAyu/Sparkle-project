# Reviewer B — E18: Plan health score计算准确性
Timestamp: 2026-04-26T11:45:00+08:00
Chain Index: 30 (Round 4 — E-chain audit)

## Chain Flow Summary
`PlanProgressService.evaluate_progress` 计算计划健康度：输入为 task_index（completed/total）、task_summaries（最近 10 条的 overrun ratio）、feedback_stats（difficulty 反馈）、time_progress（已过时间比例 vs 完成率）。输出 `PlanHealthReport` 含 severity（healthy/warning/critical）和 recommended_action（none/adjust/replan）。`AdaptiveReplanner` 根据 recommended_action 决定 incremental adjustment（warning）或 full replan（critical），有 cooldown 保护。`PlanHealthSignalService` 将评估结果发事件，`PlanHealthEventConsumer` 消费并创建 InterventionRecord。Mobile 端 `plan_detail_screen.dart` 不显示 health score/severity。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`**: 用户无法看到 plan health score 或 severity。`plan_detail_screen.dart` 无 health_score/plan_health/severity 相关 UI（grep 确认零匹配）。Expected: 用户知道当前计划是否健康，看到系统建议（如"进度滞后，建议精简"）。Actual: health 计算在后端正确执行，但用户完全不知道。系统可能已经自动调整或 replan 了计划，但用户不理解为什么任务变了。Evidence: `plan_detail_screen.dart` grep `health_score|plan_health|severity` = 零匹配。

## Minor Issues 🟢
**`backend/app/services/plan_progress_service.py:46-47`**: 阈值常量硬编码——PROGRESS_LAG_WARN=0.25, PROGRESS_LAG_CRITICAL=0.4, OVERRUN_RATIO_WARN=1.3。不可配置但合理。非关键。

## Working Well ✅
- **`backend/app/services/plan_progress_service.py:63-154`**: `evaluate_progress` 输入完整——完成率、overrun ratio、difficulty 反馈、时间进度 vs 实际进度，四维评估。
- **`backend/app/orchestration/adaptive_replanner.py:1313-1342`**: 基于 recommended_action 分流——critical→replan, warning→adjustment, healthy→none。有 cooldown 保护防频繁调整。
- **`adaptive_replanner.py:1314-1318`**: struggle streak 机制允许在高频困难反馈时 bypass cooldown，确保及时干预。
- **`backend/app/services/plan_health_signal_service.py:37`**: `maybe_publish` 有去重和频率控制，避免事件洪水。
- **`backend/app/services/plan_health_event_consumer.py:74`**: 消费 `plan.health.alerted` 事件，创建 WebSocket 更新推送到前端。
- **`backend/app/services/card_protocol/health_intervention_bridge.py`**: Health signal → InterventionRecord bridge，将健康问题转化为可追踪的干预记录。

## Files Examined
- `backend/app/services/plan_progress_service.py` (lines 22-154)
- `backend/app/orchestration/adaptive_replanner.py` (lines 1011, 1310-1350)
- `backend/app/services/plan_health_signal_service.py` (lines 37-90)
- `backend/app/services/plan_health_event_consumer.py` (lines 33-123)
- `backend/app/services/card_protocol/health_intervention_bridge.py` (lines 44-154)
- `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart` (grep — zero health references)

## Confidence: High — health 计算→action 分流→event 消费完整链路已确认；mobile UI 缺失已通过 grep 确认。
