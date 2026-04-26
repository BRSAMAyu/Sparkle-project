# Reviewer B — E18: Plan health score计算准确性
Timestamp: 2026-04-26T15:20:00+08:00 (amended)
Chain Index: 30 (Round 4 — E-chain audit)

## Chain Flow Summary
`PlanProgressService.evaluate_progress` 计算计划健康度：输入为 task_index（completed/total）、task_summaries（最近 10 条的 overrun ratio）、feedback_stats（difficulty 反馈）、time_progress（已过时间比例 vs 完成率）。输出 `PlanHealthReport` 含 severity（healthy/warning/critical）和 recommended_action（none/adjust/replan）。`AdaptiveReplanner` 根据 recommended_action 决定 incremental adjustment（warning）或 full replan（critical），有 cooldown 保护。`PlanHealthSignalService` 将评估结果发事件，`PlanHealthEventConsumer` 消费并创建 InterventionRecord。Mobile 端 `plan_detail_screen.dart` 不显示 health score/severity。

## Critical Issues 🔴
None found.

## Major Issues 🟡

**1. Mobile端"计划健康度"显示的数据源与后端 PlanHealthReport 完全脱节**
- **File**: `mobile/lib/features/home/presentation/widgets/today_growth_status_card.dart:71` + `home_growth_provider.dart:27-34`
- **Expected**: Home 页"计划健康度 ●●●○○"反映后端 `PlanHealthReport.severity` 或 `PlanHealthReport.metrics`
- **Actual**: `HomeActivePlanStatus.healthScore` 通过 fallback 链 `json['health_score'] → json['healthScore'] → planMap['health_score'] → planMap['healthScore'] → planMap['mastery_level'] → planMap['progress']` 读取。但后端 `_serialize_plan()` (plans.py:150) 只返回 `mastery_level` 和 `progress`，不返回 `health_score`。结果：UI 显示的"健康度"实际上是 `mastery_level`（掌握度），不是后端计算的 plan health severity
- **Impact**: 用户在 Home 页看到的"计划健康度"与后端 PlanProgressService 的 health evaluation 无关——后端认为 critical 的计划在 Home 页可能显示 5 个满点（如果 mastery_level 高）

**2. Plan detail 页完全无 health/severity 展示**
- **File**: `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`
- **Expected**: 用户知道当前计划是否健康，看到系统建议（如"进度滞后，建议精简"）
- **Actual**: grep `health_score|plan_health|severity` = 零匹配。系统可能已经自动调整或 replan 了计划，但用户不理解为什么任务变了
- **Impact**: 用户对计划健康状态完全不可见，health 评估完全是一个后端内部信号

## Minor Issues 🟢

**3. PlanHealthReport 缺少"压缩次数"维度**
- **File**: `backend/app/services/plan_progress_service.py:42-48`
- **Expected**: E18 链路描述提到"压缩次数"作为输入数据之一
- **Actual**: `evaluate_progress` 仅使用 overrun_count、feedback_stats、progress_lag 三个维度，无压缩次数指标
- **Impact**: 低——三维已足够覆盖主要场景

**4. `_compute_time_progress` 在 plan 无 target_date 时返回 None**
- **File**: `backend/app/services/plan_progress_service.py:215-222`
- **Impact**: 低——无截止日计划不应有时序压力，跳过合理

## Working Well ✅
- **`backend/app/services/plan_progress_service.py:63-154`**: `evaluate_progress` 输入完整——完成率、overrun ratio、difficulty 反馈、时间进度 vs 实际进度，四维评估。
- **`backend/app/orchestration/adaptive_replanner.py:1313-1342`**: 基于 recommended_action 分流——critical→replan, warning→adjustment, healthy→none。有 cooldown 保护防频繁调整。
- **`adaptive_replanner.py:1314-1318`**: struggle streak 机制允许在高频困难反馈时 bypass cooldown，确保及时干预。
- **`backend/app/services/plan_health_signal_service.py:37`**: `maybe_publish` 有去重和频率控制，severity 升级时总是 re-emit（warning→critical 不受 cooldown 限制）。
- **`backend/app/services/plan_health_event_consumer.py:74`**: 消费 `plan.health.alerted` 事件，创建 InterventionRecord 和系统更新。
- **触发链路完整**: TaskEventConsumer → AdaptiveReplanner → evaluate_progress → _handle_report → PlanHealthSignalService.maybe_publish
- **额外触发点**: `error_replan_bridge.py:393` 和 `error_book_mastery_sync_service.py:532` 也会调用 `evaluate_plan_health_now`

## Files Examined
- `backend/app/services/plan_progress_service.py`（全文 223 行）
- `backend/app/services/plan_health_signal_service.py`（全文 245 行）
- `backend/app/services/plan_health_event_consumer.py`（全文 173 行）
- `backend/app/orchestration/adaptive_replanner.py`（lines 530-590, 1011-1031, 1272-1357）
- `backend/app/services/task_event_consumer.py`（lines 105-174）
- `backend/app/api/v1/plans.py`（lines 134-164）
- `mobile/lib/features/home/presentation/providers/home_growth_provider.dart`（lines 4-51, 350-465）
- `mobile/lib/features/home/presentation/widgets/today_growth_status_card.dart`（lines 68-73, 371-373）
- `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`（grep health/severity — 零匹配）

## Confidence: High — 计算公式、触发链路、消费者逻辑全部通过源码直接确认。Mobile 端 healthScore 数据源通过 fallback 链追踪确认实际读取 mastery_level 而非后端 health evaluation。
