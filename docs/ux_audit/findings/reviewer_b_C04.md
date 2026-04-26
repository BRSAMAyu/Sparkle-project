# Reviewer B — C04: 错题录入→修复任务插入→计划页橙色卡可见
Timestamp: 2026-04-26T00:10:00+08:00
Chain Index: 11 (Round 2 re-audit)

## Chain Flow Summary
用户记录错题后，如果错题关联了知识节点且满足触发条件（错误压力>=3次/7天 或 新用户>=1次），`ErrorReplanBridge.on_error_created` 评估计划健康度并插入修复任务。修复任务有两种路径：(1) 普通修复：`_insert_next_day_repair_tasks` → `planning_workflow._insert_repair_task` 创建带 `targeted_repair` tag 的15分钟修复任务；(2) 专项修复：`materialize_specialized_repair_task_from_record` 创建带 `specialized_repair` tag 的30分钟专项任务。计划页 `_isTargetedRepairTask` 检查 tag 或 guideJson 的 task_kind 来显示橙色。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`backend/app/services/error_replan_bridge.py:1263-1267` vs `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart:1715-1726`**: Specialized repair 任务（由 `materialize_specialized_repair_task_from_record` 创建）使用 tags `["specialized_repair", "mistake_cluster", ...]` 且 guideJson 没有 `task_kind: "targeted_repair"` 字段。Expected: 计划页显示橙色背景+警告图标。Actual: `_isTargetedRepairTask` 只检查 `tag == 'targeted_repair'` 或 `guideJson['task_kind'] == 'targeted_repair'`，specialized repair 任务不会被识别为橙色修复卡。普通路径的修复任务（通过 `planning_workflow._insert_repair_task` 创建，line 1305 tag 含 `targeted_repair`）可以正常显示橙色。Evidence: `error_replan_bridge.py:1263` tags 列表 vs `plan_detail_screen.dart:1725` 检查条件。

**`backend/app/services/error_replan_bridge.py:82-91`**: `TRIGGERING_ERROR_TYPES` 有8种类型，但 `_classify_trigger_type_from_analysis` 的 fallback 逻辑对 `analysis.get("error_type")` 的分类依赖后端分析结果。如果 `latest_analysis` 为空或 `error_type` 为 `"other"`（默认值，line 1746），`_classify_trigger_type` 返回 `None`，bridge 直接返回 `blocked(gate="unsupported_error_type")`，不会触发任何修复。Expected: 用户录入错题后如果分析结果尚未返回，应该在分析完成后异步触发 bridge。Actual: bridge 在 `on_error_created` 时同步触发一次，如果分析为空则跳过。

## Minor Issues 🟢
None found.

## Working Well ✅
- **`backend/app/services/error_replan_bridge.py:184-464`**: `on_error_created` 有完整的门控和降级逻辑：kill switch (shadow/live)、cooldown、error type 过滤、new user 降低阈值等。错误处理有 metrics 上报和 system update 通知。
- **`backend/app/orchestration/planning_workflow.py:1071-1113`**: `_insert_repair_task` 创建的修复任务有正确的 `targeted_repair` tag（line 1305）和 `task_kind: "targeted_repair"`（line 1099, 1272），mobile 端可以正确显示橙色。
- **`mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart:1053-1061`**: 橙色卡视觉设计完整——`DS.warning` 作为 accent color，背景 `DS.warning.withValues(alpha: 0.08)`，圆形序号变成警告图标。
- **`mobile/lib/features/error_book/presentation/screens/error_list_screen.dart:443-452`**: 新增错题后正确 `invalidate` 了 `errorListProvider` 和 `errorStatsProvider`。

## Files Examined
- `backend/app/services/error_replan_bridge.py` (full file, 1906 lines — 重点 lines 82-91, 184-464, 976-1002, 1043-1125, 1218-1310, 1741-1774)
- `backend/app/orchestration/planning_workflow.py` (lines 1071-1113, 1240-1310)
- `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart` (lines 1045-1085, 1245-1285, 1715-1726)
- `mobile/lib/features/error_book/presentation/screens/error_list_screen.dart` (full file, 636 lines)
- `mobile/lib/features/task/presentation/providers/task_provider.dart` (lines 605-613)

## Confidence: High — 两条路径（普通修复 vs 专项修复）的 tag 差异已通过代码确认。
