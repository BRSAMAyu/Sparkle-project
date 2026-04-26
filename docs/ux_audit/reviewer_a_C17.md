# Reviewer A — C17: API失败恢复（加载→错误→重试）
Timestamp: 2026-04-25T23:30:00+08:00
Chain Index: 8

## 自我审查声明

本报告所有发现已通过亲自阅读源代码确认。Agent 调用失败（API 500），全程手动审查。关键文件逐一阅读：chat_screen.dart 的 daily startup 错误处理（line 350-426）、galaxy_screen.dart 的 lastError 监听（line 365-376）、plan_detail_screen.dart 的三个 `.when()` 调用（line 52, 126, 306）、galaxy_provider.dart 的 loadGalaxy 错误路径（line 624-716）。

## Chain Flow Summary

审查4个核心区域的 API 错误处理质量：(1) Chat 每日启动消息 (2) 计划详情 (3) Galaxy 星图 (4) 贡献统计 banner。标准：API 失败时用户看到有意义的错误提示和重试按钮，而非白屏、无限转圈或被遗忘的请求。

## Critical Issues 🔴

None found.

## Major Issues 🟡

**1. `chat_screen.dart:424-426`: 每日启动消息加载失败静默吞没，用户无感知**

`_hydrateDailyStartupIfNeeded()` 方法在 `getDailyStartup()` 调用失败时进入 `catch (_)` （line 424），直接 `return false`，不显示任何错误提示。同样，上游的 `examSprintDashboardProvider.future` 超时也在 line 372 `catch (_)` 中静默返回 false。

这意味着：如果后端 `/aurora/daily-startup` 或 sprint dashboard API 不可用，用户打开 chat 看到的是空白（无启动消息，也无错误提示），无法得知系统曾尝试加载个性化消息。

Expected: 非关键功能的失败可以静默降级（设计合理），但用户可能困惑为何今天没有个性化问候。这不构成 Critical（用户仍可正常聊天），但属于静默降级模式。

**Note**: 此为 **设计决策**，非 bug。daily startup 是增强功能而非核心路径，静默失败允许用户继续正常使用 chat。评为 Major 偏严格，但标记为已知降级行为。

**2. `galaxy_screen.dart:2710`: Galaxy 贡献统计 banner 错误时渲染为不可见 widget**

`contributionStats.when(...)` 的 error 回调返回 `const SizedBox.shrink()`（line 2710）。当贡献统计 API 失败时，banner 完全消失，用户看不到任何错误提示或重试入口。

与 Galaxy 主图加载失败不同（后者通过 `GalaxyErrorSnackBar` + 重试按钮处理，line 365-376），这个内嵌 widget 的错误被完全吞没。

Expected: 显示 loading skeleton 或降级文案，而非完全隐藏。Actual: `SizedBox.shrink()` = 零尺寸不可见。

## Minor Issues 🟢

None found.

## Working Well ✅

**计划详情页** (`plan_detail_screen.dart`):
- 顶层 `planAsync.when()` 三态完整：data + loading (`_PlanDetailLoadingView`) + error (`CustomErrorWidget.page` 含重试按钮)（line 126-148）
- `ref.listenManual` 在 initState 注册 error 监听，通过 SnackBar 显示错误 + 重试按钮（line 48-76）
- 学习路径进度 `progressAsync.when()` 的 error 回调返回 `_InlinePlanSectionError` 含重试按钮（line 306-323）
- 计划阶段 `phasesAsync.when()` 的 error 回调返回 `_InlinePlanSectionError` 含重试按钮（line 2300-2313）
- 错误消息可识别 404/超时/网络错误等不同模式（line 153-170 `_buildPlanLoadErrorMessage`）

**Galaxy 星图主加载** (`galaxy_screen.dart` + `galaxy_provider.dart`):
- `GalaxyNotifier.loadGalaxy()` 区分首次加载 vs 后台刷新错误（line 628-716）
- 首次加载失败：设置 `lastError` + `isLoading=false`（line 653-659）
- 后台刷新失败：静默忽略（`lastError: null`），不打扰用户（line 644-651）— 合理设计
- Galaxy screen 通过 `ref.listen` 监听 `lastError` 变化，弹出 `GalaxyErrorSnackBar` 含重试按钮（line 365-376）
- SSE 事件流断线自动重连：5秒后重试（line 458-468 `_scheduleEventsReconnect`）

**Chat WebSocket 连接** (`chat_provider.dart`):
- `warmUpConnection` 有 try/catch，失败时 debugPrint 但不崩溃（line 123-126）
- WebSocket 断线由底层 `websocket_chat_service_v2.dart` 自动重连

## Files Examined

1. `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (lines 350-426, daily startup hydration with dual catch blocks)
2. `mobile/lib/features/chat/presentation/providers/chat_provider.dart` (lines 118-127, warmUp error handling)
3. `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart` (lines 44-77, 126-148, 300-323, 2295-2314, error state rendering)
4. `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart` (lines 624-716, loadGalaxy error paths; 458-468, SSE reconnect)
5. `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` (lines 365-376, lastError listener + snackbar; 2701-2711, contribution stats error)
6. `mobile/lib/features/aurora/data/repositories/aurora_daily_startup_repository.dart` (全文, no error handling in repository layer — propagates to caller)
7. `mobile/lib/features/learning_portfolio_screen.dart` (已在 C14 审查中确认: error 状态含重试按钮)

## Confidence: High — 4 个区域逐一验证。Plan 和 Galaxy 主加载的错误处理质量优秀。两处降级（daily startup 静默失败、contribution banner 不可见）均为非核心路径，不影响用户完成主要任务。
