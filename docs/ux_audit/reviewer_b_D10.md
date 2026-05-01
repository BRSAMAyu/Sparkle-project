# Reviewer B — D10: 数据新鲜度全屏检查——切换屏幕后数据是否陈旧
Timestamp: 2026-04-26T01:30:00+08:00
Chain Index: 21 (Round 3 — D-chain audit)

## Chain Flow Summary
4 个关键 provider 的新鲜度机制：(1) Galaxy Provider 使用 `galaxyRefreshTriggerProvider` (StateProvider<int>) + SSE 事件流实时更新，`keepAlive` 持久化；(2) Learning Portfolio Provider 使用 `FutureProvider.autoDispose`，仅在 sprint completion 和错误重试时 invalidate；(3) Achievement Provider 使用 `StateNotifierProvider`（非 autoDispose），通过 `achievementEventConsumerProvider` 监听 SSE 事件刷新；(4) Task Provider 完成任务后 invalidate Galaxy + plan detail + weekly narrative，但不 invalidate portfolio 和 achievement。

## Critical Issues 🔴
None found.

## Major Issues 🟡
**`mobile/lib/features/task/presentation/providers/task_provider.dart:412-421`**: `completeTask` 的 cross-provider invalidation 不完整。Line 412 触发 Galaxy 刷新，line 419 invalidate plan detail，line 421 invalidate weekly narrative。但 **不** invalidate `learningPortfolioProvider` 和 `achievementProvider`。Expected: 完成任务后切到学习档案页看到更新后的进度，切到成就页看到新解锁。Actual: (1) 学习档案页仍显示旧数据直到用户触发错误重试或离开页面（autoDispose 回收后重新加载）；(2) 成就页依赖 SSE WebSocket 事件更新——如果 WebSocket 断开，成就列表不会刷新。Evidence: `task_provider.dart:412-421` — 仅 3 个 provider 被 invalidate。

**4 个关键页面中 3 个缺少 `RefreshIndicator`**: Galaxy (`galaxy_screen.dart`)、学习档案 (`learning_portfolio_screen.dart`)、成就页 (`achievement_list_screen.dart`) 均无 `RefreshIndicator`。仅任务列表 (`task_list_screen.dart:243`) 有 pull-to-refresh。Expected: 用户在任何页面下拉即可刷新数据。Actual: Galaxy 页有自定义刷新机制（galaxyRefreshTriggerProvider），档案页和成就页只能通过退出重新进入或触发错误重试来刷新。当 SSE/WebSocket 断连时，用户无手动刷新手段。Evidence: `task_list_screen.dart:243` 有 `RefreshIndicator`，其余 3 个 screen 文件 grep `RefreshIndicator` 为零匹配。

## Minor Issues 🟢
**`mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart`**: Galaxy 使用 `AutomaticKeepAliveClientMixin` (`wantKeepAlive = true`)，导航回 Galaxy 页时不重新加载。这是性能优化设计，但配合 `galaxyRefreshTriggerProvider` 机制，在 app 冷启动后首次进入 Galaxy 页时如果 trigger 未被递增（无任务完成），显示的是缓存数据。非严重问题，因为 Galaxy SSE 事件流会实时更新。

## Working Well ✅
- **`mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart:220-232`**: `galaxyRefreshTriggerProvider` 监听机制正确——trigger 变化时调用 `_loadGraph(forceRefresh: true, preserveCamera: true)`。
- **`mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart:426-456`**: SSE 事件流处理 `nodes_expanded`、`galaxy.node.updated`、`evidence_pack`、`galaxy.error.created` 四种事件，实时更新星图。
- **`mobile/lib/features/achievement/presentation/providers/achievement_provider.dart:249-263`**: `achievementEventConsumerProvider` 监听 `achievement_unlock` SSE 事件并自动刷新成就列表和连胜统计。
- **`mobile/lib/features/task/presentation/providers/task_provider.dart:388-397`**: 乐观更新 UI（立即标记 completed），后台同步后更新 syncStatus，用户体验流畅。
- **`mobile/lib/features/plan/presentation/screens/sprint_completion_screen.dart:149`**: 冲刺完成后正确 invalidate `learningPortfolioProvider`。

## Files Examined
- `mobile/lib/features/task/presentation/providers/task_provider.dart` (lines 375-466)
- `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart` (lines 220-232, 311, 426-456, 528-543)
- `mobile/lib/features/plan/presentation/providers/learning_portfolio_provider.dart` (line 7, autoDispose)
- `mobile/lib/features/achievement/presentation/providers/achievement_provider.dart` (lines 206-209, 249-263, 598-619)
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` (grep — no RefreshIndicator)
- `mobile/lib/features/plan/presentation/screens/learning_portfolio_screen.dart` (grep — no RefreshIndicator)
- `mobile/lib/features/achievement/presentation/screens/achievement_list_screen.dart` (grep — no RefreshIndicator)
- `mobile/lib/features/task/presentation/screens/task_list_screen.dart` (line 243 — has RefreshIndicator)

## Confidence: High — cross-provider invalidation 缺口和 RefreshIndicator 缺失已通过 grep 确认。
