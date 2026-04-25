# Reviewer B — C02: 任务完成→Galaxy节点mastery更新→星图颜色变深
Timestamp: 2026-04-26T00:40:00+08:00
Chain Index: 13 (Round 2 re-audit)

## Chain Flow Summary
用户完成一个 Sprint 任务后，`TaskService._update_sprint_pack_mastery_for_completed_task` 提取任务的 sprint pack node IDs，调用 `GalaxyService.update_node_mastery` 将 mastery +0.25（0-1 刻度）。Mobile 端 `task_provider` 在完成回调中递增 `galaxyRefreshTriggerProvider` 并调用 `galaxyProvider.refreshForTaskCompletion` 触发重新加载。Galaxy API 返回 `mastery_score`，mobile 用 `(json['mastery_score'] as num?)?.toInt()` 解析为 `int masteryScore`，再通过 `galaxyMasteryRatio(masteryScore)` = `masteryScore / 100` 映射颜色。

## Critical Issues 🔴
**`backend/app/services/task_service.py:477` + `backend/app/services/galaxy_service.py:1396` vs `mobile/lib/features/galaxy/domain/entities/galaxy_llm_protocol.g.dart:88`**: Sprint Pack 使用 0-1 刻度写入 mastery（line 477: `min(1.0, current_mastery + 0.25)`），`update_node_mastery` 的 `new_mastery` 被夹到 `max(0.0, min(float(new_mastery), 100.0))` 后写入 DB 为 0.25。但 mobile 端解析用 `?.toInt()` 将 0.25 截断为 0，然后 `galaxyMasteryRatio(0)` = `0 / 100` = 0，颜色永远是最低等级灰色。Expected: 完成 4 个 sprint 任务后 mastery 到 1.0，颜色变深。Actual: Sprint pack 节点 mastery 在 mobile 端始终显示为 0，颜色不变。普通 Galaxy 节点（用 0-100 刻度写入）不受影响。Evidence: `task_service.py:477` (0-1 scale) → `galaxy_service.py:1396` (stored as 0.25) → API returns 0.25 → `galaxy_llm_protocol.g.dart:88` (`toInt()` → 0) → `star_map_painter.dart:42` (`0/100 = 0` → gray)。

## Major Issues 🟡
None found.

## Minor Issues 🟢
None found.

## Working Well ✅
- **`mobile/lib/features/task/presentation/providers/task_provider.dart:412-416`**: 完成任务后正确触发 galaxy 刷新——`galaxyRefreshTriggerProvider.state++` + `galaxyProvider.refreshForTaskCompletion()`。
- **`mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart:528-543`**: `refreshForTaskCompletion` 清除缓存并重新加载星图数据，有 `forceRefresh: true`。
- **`mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart:45-56`**: `galaxyMasteryNodeColor` 有 4 级颜色映射，逻辑正确（0-25% 灰 → 25-50% 浅蓝 → 50-75% 蓝 → 75-100% 深蓝）。
- **`backend/app/services/galaxy_service.py:1076-1100`**: `get_sprint_mastery_summary` 通过 `_mastery_ratio` 正确归一化，后端内部 0-1 刻度一致。

## Files Examined
- `backend/app/services/task_service.py` (lines 440-486)
- `backend/app/services/galaxy_service.py` (lines 970-1100, 1371-1400)
- `backend/app/api/v1/galaxy.py` (lines 75-95, 320-340)
- `mobile/lib/features/galaxy/domain/entities/galaxy_llm_protocol.dart` (lines 220-235)
- `mobile/lib/features/galaxy/domain/entities/galaxy_llm_protocol.g.dart` (line 88)
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart` (lines 42-56, 1614, 2177)
- `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart` (lines 528-543)
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` (lines 216-232)
- `mobile/lib/features/task/presentation/providers/task_provider.dart` (lines 405-421, 505-518)

## Confidence: High — 双刻度 bug 从写入路径到读取路径完整追踪，每一步都有代码行号确认。
