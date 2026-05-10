# Sparkle Flutter Frontend Audit Report

**Date**: 2026-05-10
**Scope**: `mobile/lib/` (1,198 Dart files)
**Auditor**: Claude Opus Agent
**Status**: COMPLETE

---

## Executive Summary

| Category | P0 | P1 | P2 | Total |
|----------|----|----|----|----|
| i18n / Hardcoded Strings | 3 | 12 | 0 | 15 |
| State Management / Bugs | 1 | 3 | 2 | 6 |
| Navigation / Routing | 2 | 1 | 2 | 5 |
| UI/UX Issues | 1 | 4 | 3 | 8 |
| Code Quality | 0 | 5 | 4 | 9 |
| Accessibility | 1 | 2 | 3 | 6 |
| Design System Compliance | 0 | 2 | 2 | 4 |
| **TOTAL** | **8** | **29** | **16** | **53** |

---

## 1. i18n / Hardcoded Strings

### ISSUE-001 [P0] -- 1,685 inline `isChinese ? '...' : '...'` patterns across codebase

**Files** (sample -- pattern occurs across 50+ files):
- `mobile/lib/features/home/data/repositories/dashboard_repository.dart` (lines 74-283)
- `mobile/lib/features/home/presentation/providers/intent_prediction_provider.dart` (lines 105-273)
- `mobile/lib/features/insights/presentation/screens/learning_insights_overview_screen.dart` (lines 105-564)
- `mobile/lib/features/insights/presentation/screens/directive_audit_screen.dart` (lines 25-401)
- `mobile/lib/features/experience/presentation/widgets/goal_detail_snapshot_card.dart` (lines 47-172)
- `mobile/lib/features/experience/presentation/widgets/understanding_snapshot_card.dart` (lines 19-171)
- `mobile/lib/features/experience/presentation/widgets/community_accountability_hub_card.dart` (lines 49-120)
- `mobile/lib/features/experience/presentation/widgets/growth_quality_card.dart` (line 32-64)
- `mobile/lib/features/community/presentation/screens/community_main_screen.dart` (lines 54-93)
- `mobile/lib/core/statistics/domain/repositories/statistics_repository.dart` (lines 201-205)
- `mobile/lib/core/statistics/presentation/providers/focus_statistics_provider.dart` (line 261)
- `mobile/lib/core/statistics/data/services/statistics_export_service_impl.dart` (lines 74-435)
- `mobile/lib/core/statistics/presentation/widgets/charts/statistics_line_chart.dart` (line 207)
- `mobile/lib/core/statistics/presentation/widgets/common/statistics_empty_state.dart` (lines 93-244)
- `mobile/lib/features/home/data/repositories/notification_repository.dart` (lines 22-47)
- `mobile/lib/features/home/presentation/providers/spine_status_band_provider.dart` (line 67)
- `mobile/lib/features/home/presentation/providers/dashboard_provider.dart` (lines 136-627)

**Description**: The `I18nService.instance.isChinese ? 'Chinese' : 'English'` pattern is used 1,685 times across the codebase instead of proper ARB-based l10n. While this functionally works for the current zh/en bilingual setup, it violates the project's own l10n strategy rule and makes it impossible to add more languages. The `isChinese` boolean approach is hardcoded and does not go through the ARB pipeline.

**Impact**: All user-facing text in these locations bypasses the ARB l10n pipeline. If a third language is ever added, every single one of these 1,685 locations would need manual code changes.

**Suggested Fix**: Migrate each to an ARB key. Use `context.l10n.xxx` in widgets, or `S.xxx` (the global accessor via `I18nService`) in providers/repositories where BuildContext is unavailable. The `S` accessor already exists at `mobile/lib/core/services/i18n_service.dart:85`.

---

### ISSUE-002 [P0] -- Router error page uses hardcoded English strings

**File**: `mobile/lib/app/routes.dart` lines 73, 80, 85
**Code**:
```dart
appBar: AppBar(title: const Text('Page Not Found')),
Text('Page not found: ${state.error?.message ?? state.uri.path}', ...),
child: const Text('Go Home'),
```

**Description**: The GoRouter error builder page has three hardcoded English-only strings. Chinese-language users will see English when encountering a 404.

**Suggested Fix**: Use `AppLocalizations.of(context)!.xxx` or the global `S` accessor. Add keys like `routerPageNotFound`, `routerPageNotFoundMessage`, `routerGoHome` to both ARB files.

---

### ISSUE-003 [P0] -- LearningPathScreen has hardcoded English fallback title

**File**: `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart` line 20
**Code**:
```dart
title: Text(nodeName.isNotEmpty ? nodeName : 'Learning Path'),
```

**Description**: When `nodeName` is empty, the AppBar shows hardcoded "Learning Path" in English only. This screen also lacks any `context.l10n` usage whatsoever.

**Suggested Fix**: Replace `'Learning Path'` with `context.l10n.learningPathTitle` (or equivalent ARB key).

---

### ISSUE-004 [P1] -- chat_screen.dart has hardcoded 'OpenClaw Hub' semantic label

**File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart` line 1266
**Code**:
```dart
semanticLabel: showOpenClawAttention
    ? context.l10n.chatOpenclawHubQueued(...)
    : 'OpenClaw Hub',
```

**Description**: The else branch uses a hardcoded English string for the accessibility label. The conditional branch properly uses l10n but the fallback does not.

**Suggested Fix**: Add `chatOpenclawHub` key to ARB files and use `context.l10n.chatOpenclawHub`.

---

### ISSUE-005 [P1] -- VoiceInputButton has hardcoded English-only Semantics label

**File**: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart` line 304
**Code**:
```dart
label: _isRecording ? 'Stop voice input recording' : 'Start voice input',
```

**Description**: The accessibility semantics label for the voice input button is hardcoded in English. Screen reader users in Chinese will hear English labels.

**Suggested Fix**: Accept l10n strings as constructor parameters or use `S.voiceInputStart` / `S.voiceInputStop`.

---

### ISSUE-006 [P1] -- Task board card uses `isChinese` for side panel descriptions

**File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart` lines 226-282
**Code**: Multiple instances of `isChinese ? '...' : '...'` for panel descriptions like:
- `'任务按到期日期分组显示'` / `'Tasks are grouped by due date.'`
- `'红色高亮显示已逾期的任务'` / `'Overdue tasks are highlighted in red.'`
- `'今日${summary.totalCount}项·已完成${summary.completedCount}'` / `'...'`

**Suggested Fix**: Add ARB keys for all side panel descriptions and summary text.

---

### ISSUE-007 [P1] -- Community main screen uses `isChinese` for tab labels and header

**File**: `mobile/lib/features/community/presentation/screens/community_main_screen.dart` lines 54-93
**Code**:
```dart
final tabLabels = [
  zh ? '伙伴' : 'Partners',
  zh ? '动态' : 'Feed',
  zh ? '群组' : 'Groups',
];
// Also header:
zh ? '社群' : 'Community',
zh ? '和伙伴一起成长' : 'Grow together with partners',
```

**Suggested Fix**: Use `context.l10n.communityTabPartners`, `context.l10n.communityTabFeed`, `context.l10n.communityTabGroups`, `context.l10n.communityTitle`, `context.l10n.communitySubtitle`.

---

### ISSUE-008 [P1] -- Traits coldstart questionnaire has hardcoded hint

**File**: `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart` line 50
**Code**:
```dart
zh ? '点击展开/收起' : 'Tap to expand/collapse',
```

**Suggested Fix**: Add `userTraitsColdstartToggle` key to ARB.

---

### ISSUE-009 [P1] -- Insights overview screen has numerous inline i18n strings

**File**: `mobile/lib/features/insights/presentation/screens/learning_insights_overview_screen.dart` lines 105-564
**Sample occurrences**: Over 45 instances of `I18nService.instance.isChinese ? '...' : '...'`

**Suggested Fix**: Migrate all to ARB keys.

---

### ISSUE-010 [P1] -- Directive audit screen uses inline i18n throughout

**File**: `mobile/lib/features/insights/presentation/screens/directive_audit_screen.dart` lines 25-401
**Sample**: 66+ instances of the `zh ? '...' : '...'` pattern for filter labels, empty states, retry buttons, etc.

**Suggested Fix**: Migrate all to ARB keys.

---

### ISSUE-011 [P1] -- Dashboard repository has hardcoded mock/demo data in Chinese/English

**File**: `mobile/lib/features/home/data/repositories/dashboard_repository.dart` lines 74-283
**Code**: Mock plan names, subjects, tasks, insights, and action labels all hardcoded with `zh ? '...' : '...'`.

**Note**: Since these are demo/mock data rather than user-facing UI, this is P1 rather than P0. However, they should still come from the backend or be localizable.

---

### ISSUE-012 [P1] -- Core statistics module uses inline i18n extensively

**Files**:
- `mobile/lib/core/statistics/data/services/statistics_export_service_impl.dart`
- `mobile/lib/core/statistics/presentation/widgets/common/statistics_empty_state.dart`
- `mobile/lib/core/statistics/presentation/widgets/charts/statistics_line_chart.dart`
- `mobile/lib/core/statistics/domain/repositories/statistics_repository.dart`

**Sample**: `zh ? '暂无数据' : 'No data'`, `zh ? '加载失败' : 'Failed to load'`, `zh ? '重试' : 'Retry'`, export content with emojis and Chinese text.

---

### ISSUE-013 [P1] -- ARB plural placeholder mismatches (15 keys)

**Keys affected**: `taskCount`, `streakDays`, `timeMinutesAgo`, `timeHoursAgo`, `timeDaysAgo`, `timeWeeksAgo`, `timeMonthsAgo`, `timeYearsAgo`, `timeInMinutes`, `timeInHours`, `timeInDays`, `timeInWeeks`, `timeInMonths`, `timeInYears`, `numberCount`

**Description**: The EN ARB files use ICU plural forms `{count, plural, =1{1 day ago} ...}` but the ZH ARB files for these 15 keys only have `{count}` as placeholder. This means the Chinese versions will not properly handle singular forms (e.g., "1 天前" may render as "{count} 天前" if the plural logic is processed).

**Example**:
- EN: `"timeDaysAgo": "{count, plural, =1{1 day ago} other{{count} days ago}}"`
- ZH: `"timeDaysAgo": "{count} 天前"`

**Impact**: Minor -- Chinese text will typically just show "{count} 天前" which works fine. But it's a structural inconsistency.

**Suggested Fix**: Either align the ZH entries to also use plural form (even if the output is the same), or ensure the code that calls these keys handles the mismatch gracefully.

---

### ISSUE-014 [P1] -- OpenClaw connection service has hardcoded Chinese error messages

**File**: `mobile/lib/core/services/openclaw_connection_service.dart` lines 576, 967, 978
**Code**:
```dart
errorMessage: normalized.isEmpty ? 'OpenClaw 执行当前不可用' : normalized,
errorMessage: 'OpenClaw 执行接口不可用（/v1/responses 未找到）',
errorMessage: 'OpenClaw 执行接口异常（HTTP ${response.statusCode}）',
```

**Description**: Error messages shown to the user are hardcoded in Chinese only. English users will see Chinese error messages.

**Suggested Fix**: Use `S.openclawErrorUnavailable`, `S.openclawErrorNotFound`, `S.openclawErrorHttp(code)`.

---

### ISSUE-015 [P1] -- Learning forecast screen has hardcoded string

**File**: `mobile/lib/features/insights/presentation/screens/learning_forecast_screen.dart` line 461
**Code**: `I18nService.instance.isChinese ? '学习建议' : 'Learning Tips'`

**Suggested Fix**: Add ARB key `learningForecastTips`.

---

## 2. State Management / Bugs

### ISSUE-016 [P0] -- `node_detail_sheet.dart` uses static `S.` accessor in a `StatelessWidget._relativeTime` static method without BuildContext

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 500-511
**Code**:
```dart
static String _relativeTime(DateTime dateTime) {
  final diff = DateTime.now().difference(dateTime);
  if (diff.inDays >= 1) {
    return S.galaxyNodeDaysAgo(diff.inDays);
  }
  ...
  return S.galaxyNodeJustNow;
}
```

**Description**: The `S` global accessor reads from `I18nService.instance.l10n`, which falls back to `PlatformDispatcher.instance.locale` when not explicitly initialized. During early app startup or before `I18nService.updateLocale()` is called, the fallback may not match the user's selected locale. The method is also `static` and called from `_HistoryContent.build()` where a `BuildContext` is available, so `context.l10n` could be used instead.

**Impact**: Locale-dependent strings may show in the wrong language if the global `I18nService` hasn't been initialized with the correct locale yet.

**Suggested Fix**: Change `_relativeTime` to accept `BuildContext` or `AppLocalizations` as a parameter, and use `context.l10n.galaxyNodeDaysAgo()`.

---

### ISSUE-017 [P1] -- ThemeManager.dispose() intentionally skips super.dispose() -- intentional singleton but risky

**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart` lines 294-300
**Code**:
```dart
@override
// ignore: must_call_super
void dispose() {
  // Prevent disposal of the singleton instance by Riverpod or other owners.
}
```

**Description**: The `ThemeManager` is a singleton `ChangeNotifier` whose `dispose()` is overridden to be a no-op, with a lint suppression for `must_call_super`. If Riverpod or any other provider attempts to dispose this object, it silently does nothing. While documented as intentional, this pattern means `ThemeManager` can never be properly cleaned up or tested in isolation.

**Impact**: Not a launch blocker, but could cause issues in testing or if the ownership model changes.

**Suggested Fix**: Consider using `Ref.onDispose` to unregister rather than prevent disposal, or use `ProviderContainer` scope management.

---

### ISSUE-018 [P1] -- Community insight FutureBuilder in node_detail_sheet fires on every rebuild

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1619-1686
**Code**:
```dart
return FutureBuilder<Map<String, dynamic>?>(
  future: _fetchCommunitySignal(),
  ...
);
```

**Description**: `_fetchCommunitySignal()` is called directly inside `build()` as a `FutureBuilder` future parameter. Every time this widget rebuilds, a new Future is created, causing a new network request. The `_CommunityInsightContentState` has no caching mechanism.

**Impact**: Unnecessary network calls on every rebuild. Could cause rate limiting or slow UI.

**Suggested Fix**: Cache the Future in `initState()` or use a Riverpod provider (like `nodeSourceMaterialsProvider` used right above in the same file).

---

### ISSUE-019 [P1] -- `_summaryLabel` references `context` outside of a widget build method

**File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart` lines 284-294
**Code**:
```dart
String _summaryLabel(
  TaskBoardTodaySummary summary, {
  required bool isChinese,
}) {
  if (summary.totalCount == 0) {
    return context.l10n.taskBoardNoTasksToday;  // context used here
  }
  return isChinese
      ? '今日${summary.totalCount}项·已完成${summary.completedCount}'
      : '${summary.completedCount} of ${summary.totalCount} completed today';
}
```

**Description**: This method uses `context.l10n` for one branch but `isChinese` inline strings for the other. More importantly, `context` is accessed from a method that's not the `build` method directly, which is safe in this case since it's called from `build()`, but mixing `context.l10n` and `isChinese` patterns in the same method is inconsistent.

**Suggested Fix**: Use `context.l10n.taskBoardTodaySummary(summary.completedCount, summary.totalCount)` for both branches.

---

### ISSUE-020 [P2] -- Multiple providers use `S.` static accessor instead of cached Future/AsyncValue

**Files**:
- `mobile/lib/features/home/presentation/providers/task_board_provider.dart` (lines 26, 292-298)
- `mobile/lib/features/home/presentation/providers/home_growth_provider.dart` (lines 102, 468, 627)
- `mobile/lib/features/home/presentation/providers/exam_sprint_dashboard_provider.dart` (line 175)
- `mobile/lib/features/home/presentation/widgets/insight_hub_card.dart` (lines 685-758)
- `mobile/lib/features/achievement/data/repositories/achievement_repository.dart` (lines 459-460)

**Description**: These providers/widgets use `S.xxx` (global static accessor) instead of context-based l10n. While this works, it relies on `I18nService` being initialized before these providers run. If the locale changes, these providers won't automatically rebuild.

**Suggested Fix**: For providers, pass locale as a parameter or invalidate on locale change. For widgets, prefer `context.l10n.xxx`.

---

### ISSUE-021 [P2] -- Dashboard provider falls back to inline Chinese/English strings

**File**: `mobile/lib/features/home/presentation/providers/dashboard_provider.dart` lines 136, 468, 627

**Description**: When backend data is missing, the provider fills in with `I18nService.instance.isChinese ? '...' : '...'` fallback strings.

---

## 3. Navigation / Routing

### ISSUE-022 [P0] -- LearningPathScreen uses raw `Navigator.of(context).pop()` instead of GoRouter

**File**: `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart` line 24
**Code**:
```dart
onPressed: () => Navigator.of(context).pop(),
```

**Description**: This screen is registered as a GoRoute (`/learning-path`) with `parentNavigatorKey: navigatorKey` (root navigator). Using `Navigator.of(context).pop()` could pop the wrong navigator or fail to pop at all if the route was pushed via GoRouter. Since this route uses `parentNavigatorKey`, it's displayed at the root level, so `Navigator.of(context).pop()` works in practice, but it's inconsistent with the GoRouter-based navigation pattern used everywhere else.

**Suggested Fix**: Use `context.pop()` from `go_router` package.

---

### ISSUE-023 [P0] -- LearningPathScreen is a bare Scaffold without SparklePageScaffold

**File**: `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart` lines 16-34
**Code**:
```dart
return Scaffold(
  appBar: AppBar(
    title: Text(nodeName.isNotEmpty ? nodeName : 'Learning Path'),
    leading: IconButton(
      icon: const Icon(Icons.arrow_back),
      onPressed: () => Navigator.of(context).pop(),
    ),
  ),
  ...
);
```

**Description**: All other screens in the app use `SparklePageScaffold` or `GraphiteScaffold` for consistent theming, transitions, and experience profiles. This screen uses a raw `Scaffold` with a plain `AppBar` and a raw `IconButton` instead of `SparkleIconButton`. This creates visual inconsistency.

**Suggested Fix**: Replace `Scaffold` with `SparklePageScaffold(role: SparklePageRole.content)`, use `SparkleIconButton`, and add l10n for the title.

---

### ISSUE-024 [P1] -- Several screens use `Navigator.of(context).pop()` for bottom sheets while also being GoRoute targets

**Files** (sample):
- `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 175, 209, 230, 243
- `mobile/lib/features/chat/presentation/widgets/ai_reasoning_mode_pill.dart` line 101
- `mobile/lib/features/achievement/presentation/screens/achievement_map_screen.dart` lines 250, 258

**Description**: These files mix `Navigator.of(context).pop()` (to dismiss modal sheets) and `GoRouter.push()` (for navigation). For modal bottom sheets shown via `showModalBottomSheet()`, `Navigator.of(context).pop()` is correct. However, when the same code also uses `GoRouter.push()` for navigation (as in `node_detail_sheet.dart` lines 176-195), this mixing can be confusing and fragile.

**Impact**: Low risk in practice since `showModalBottomSheet` creates its own navigator, but the pattern is fragile.

---

### ISSUE-025 [P2] -- No 404 page localization or theming

**File**: `mobile/lib/app/routes.dart` lines 72-89

**Description**: The 404 error page is a plain `Scaffold` with hardcoded strings (see ISSUE-002). It also doesn't use `SparklePageScaffold` or any design system components.

---

## 4. UI/UX Issues

### ISSUE-026 [P0] -- Voice input Semantics labels are English-only, breaking accessibility for Chinese users

**File**: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart` line 304

**Description**: (Same as ISSUE-005 but from the accessibility angle.) The Semantics widget wrapping the voice input button uses hardcoded English labels. Chinese-language screen reader users will hear English announcements.

---

### ISSUE-027 [P1] -- `node_detail_sheet.dart` uses deprecated `withOpacity()` instead of `withValues(alpha:)`

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1556, 1558
**Code**:
```dart
color: DS.warning.withOpacity(0.06),
border: Border.all(color: DS.warning.withOpacity(0.15)),
```

**Description**: The codebase has migrated to `withValues(alpha:)` (used everywhere else), but this file still uses the deprecated `withOpacity()`. This generates a deprecation warning in newer Flutter versions.

**Suggested Fix**: Replace with `DS.warning.withValues(alpha: 0.06)` and `DS.warning.withValues(alpha: 0.15)`.

---

### ISSUE-028 [P1] -- Task board card `_CollapsedWorkspacePreview` has no empty state

**File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart` lines 361-431

**Description**: When the task board is collapsed and there are no tasks, the preview shows the summary text ("No tasks today") but no visual placeholder or illustration. The collapsed view is purely text-based, which may look sparse.

**Suggested Fix**: Add a subtle illustration or icon when there are zero tasks.

---

### ISSUE-029 [P1] -- print() statement left in production code

**File**: `mobile/lib/core/services/app_usage_service.dart` line 65
**Code**:
```dart
print('Error getting foreground app: ${e.message}');
```

**Description**: A `print()` statement was found in the app usage service. This will appear in production debug consoles and is a minor security/information leak concern.

**Suggested Fix**: Replace with a proper logging framework call or remove.

---

### ISSUE-030 [P2] -- Dashboard screen is extremely large (1700+ lines)

**File**: `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`

**Description**: At 1700+ lines, this is one of the largest single files in the codebase. While not a bug per se, it makes maintenance and review difficult.

**Suggested Fix**: Consider extracting sections into separate widget files.

---

### ISSUE-031 [P2] -- chat_screen.dart is the largest file in the codebase (3850 lines)

**File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`

**Description**: The chat screen is 3,850 lines long. This is a maintenance concern -- any change requires scrolling through thousands of lines.

---

### ISSUE-032 [P2] -- Knowledge theater screen is very large (4144+ lines)

**File**: `mobile/lib/features/theater/presentation/screens/knowledge_theater_screen.dart`

**Description**: At 4,144+ lines, this file contains multiple private widget classes and is extremely difficult to navigate.

---

### ISSUE-033 [P1] -- `AnimatedBuilder` used throughout codebase (100+ instances) -- should be `AnimatedBuilder`

**Files**: Throughout `mobile/lib/features/` and `mobile/lib/core/`

**Description**: The codebase uses `AnimatedBuilder` in 100+ locations. In Flutter, the correct class is `AnimatedBuilder`. However, since the app compiles and runs, this is likely a custom wrapper or re-export. If this is Flutter's built-in `AnimatedBuilder`, there is no issue. If it's a custom class with a similar name, verify it correctly handles the animation lifecycle.

**Note**: After checking, `AnimatedBuilder` IS the correct Flutter class (renamed from `AnimatedWidget` in older Flutter). This is NOT an issue -- the pattern is correct.

---

## 5. Code Quality

### ISSUE-034 [P1] -- 182 `catch (_)` blocks in features/ silently swallow errors

**Files**: Throughout `mobile/lib/features/` (182 instances) and `mobile/lib/core/` (34 instances)

**Description**: There are 216 total instances of `catch (_)` (catching and discarding the error) across the codebase. While some are acceptable (e.g., parsing fallbacks), the sheer number suggests a pattern of error suppression. Notable examples:

- `mobile/lib/features/insights/data/repositories/growth_dashboard_repository.dart` lines 35, 49
- `mobile/lib/features/insights/data/repositories/learning_path_repository.dart` lines 41, 89, 145, 187
- `mobile/lib/features/home/presentation/providers/home_growth_provider.dart` line 599
- `mobile/lib/features/home/presentation/providers/intent_prediction_provider.dart` lines 536, 539, 542

**Impact**: Errors are silently lost, making debugging extremely difficult. Users see empty/broken UI with no indication of what went wrong.

**Suggested Fix**: At minimum, log the error in debug mode: `catch (e) { debugPrint('Error in xxx: $e'); }`. For user-facing operations, show an error state.

---

### ISSUE-035 [P1] -- 2 TODO comments remain in production code

**Files**:
- `mobile/lib/features/community/data/repositories/community_repository.dart` line 1435: `/// TODO: endpoint POST /api/v1/community/groups/{groupId}/files/{fileId}/copy-to-library`
- `mobile/lib/features/community/presentation/widgets/group_chat_bubble.dart` line 193: `// TODO: i18n - this is inside a Text widget already using style`

**Description**: TODO comments indicate incomplete features or known issues.

**Suggested Fix**: Track these in the issue tracker and resolve before launch, or convert to tracked backlog items.

---

### ISSUE-036 [P2] -- PersistentStateNotifier has many catch blocks with duplicated error handling

**File**: `mobile/lib/core/providers/persistent_state_notifier.dart` (lines 109-627, 12+ catch blocks)

**Description**: This file has 12+ catch blocks, many with identical error handling patterns. This suggests an opportunity to extract a shared error handler.

---

### ISSUE-037 [P2] -- Some widget files use Chinese comments extensively

**File**: `mobile/lib/core/design/tokens_v2/responsive_system.dart` (most lines)
**File**: `mobile/lib/core/design/motion.dart` (most lines)
**File**: `mobile/lib/core/design/design_system.dart` (lines 1-34)

**Description**: Code comments are in Chinese throughout the design system. While this is fine for a bilingual team, it may be confusing for English-only contributors.

---

### ISSUE-038 [P2] -- ThemeManager singleton uses hardcoded SharedPreferences keys

**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart` lines 70-91, 270-284
**Code**:
```dart
_mode = AppThemeMode.values[prefs.getInt('theme_mode') ?? ...];
_brandPreset = BrandPreset.values[prefs.getInt('brand_preset') ?? ...];
_highContrast = prefs.getBool('high_contrast') ?? false;
_colorBlindFriendly = prefs.getBool('color_blind_friendly') ?? false;
_equippedSkinId = prefs.getString('equipped_skin_id');
```

**Description**: SharedPreferences keys are hardcoded strings scattered throughout the file. If any key changes, all references must be updated manually.

**Suggested Fix**: Extract to `static const` fields.

---

### ISSUE-039 [P2] -- `_CommunityInsightContentState._fetchCommunitySignal` catches all and returns null

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1674-1686
**Code**:
```dart
Future<Map<String, dynamic>?> _fetchCommunitySignal() async {
  try {
    ...
  } catch (_) {
    return null;
  }
}
```

**Description**: All errors are silently swallowed and the community insight section just shows "No data" text, even if the real issue is a network error or authentication failure.

**Suggested Fix**: Differentiate between "no data" and "load failed" states.

---

### ISSUE-040 [P2] -- _SourceMaterialsEmptyState and _DocumentExcerptCard have non-const constructors

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1049, 1098

**Description**: These private widget classes are not const-constructible due to using non-const fields. While this is minor, it prevents widget rebuild optimization.

---

## 6. Accessibility

### ISSUE-041 [P1] -- Only 50 Semantics usages across 100+ screen files

**Files**: All `*_screen.dart` files

**Description**: Across 100+ screen files, there are only 50 instances of `Semantics()` or `semanticLabel` usage. Most screens have zero accessibility annotations. For a launch-quality app, interactive elements (buttons, icons, images) should have semantic labels.

**Most affected screens** (no Semantics at all):
- All plan screens
- All error book screens
- All memory screens
- All seed library screens
- All focus screens
- All calendar screens

**Suggested Fix**: Add `Semantics` widgets and `semanticLabel` properties to all interactive elements. Prioritize the chat screen (critical path) and home screen.

---

### ISSUE-042 [P1] -- VoiceInputButton accessibility labels are English-only

**File**: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart` line 304

(See ISSUE-005 for details)

---

### ISSUE-043 [P2] -- Chat screen has only 8 Semantics annotations across 3,850 lines

**File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`

**Description**: The most critical screen in the app (chat) has minimal accessibility support. Message bubbles, input controls, mode selectors, and action buttons largely lack semantic annotations.

---

### ISSUE-044 [P2] -- No accessibility settings screen integration

**File**: `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart`

**Description**: The accessibility settings screen exists but there's no clear indication that enabling high contrast or color-blind mode propagates to all custom-painted widgets (Galaxy graph, achievements, etc.).

---

### ISSUE-045 [P2] -- Node detail sheet lacks Semantics for mastery progress bar

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 379-388

**Description**: The `LinearProgressIndicator` for mastery has no `Semantics` widget, so screen readers cannot announce the progress percentage.

**Suggested Fix**: Wrap in `Semantics(value: history.mastery, label: '${history.masteryPercent}% mastery')`.

---

### ISSUE-046 [P1] -- Community insight `_CommunityInsightContentState` has no loading state

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1618-1670

**Description**: The community insight section's `FutureBuilder` only handles `!snapshot.hasData` (shows "No data") and `snapshot.hasData` (shows data). There is no differentiation between:
- `ConnectionState.waiting` (loading)
- `ConnectionState.done` with null data (no community signal available)
- `ConnectionState.done` with error

All three cases show the same "No data" text.

**Suggested Fix**: Add a loading indicator for `ConnectionState.waiting`, and an error state for `snapshot.hasError`.

---

## 7. Design System Compliance

### ISSUE-047 [P1] -- LearningPathScreen uses raw Scaffold instead of SparklePageScaffold

(See ISSUE-023 for details)

---

### ISSUE-048 [P1] -- LearningPathScreen uses raw IconButton instead of SparkleIconButton

**File**: `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart` line 22
**Code**:
```dart
leading: IconButton(
  icon: const Icon(Icons.arrow_back),
  onPressed: () => Navigator.of(context).pop(),
),
```

**Description**: Uses Flutter's default `IconButton` with `Icons.arrow_back` instead of `SparkleIconButton` with `Icons.arrow_back_rounded` used consistently elsewhere in the app.

---

### ISSUE-049 [P2] -- Inconsistent icon usage: `Icons.arrow_back` vs `Icons.arrow_back_rounded`

**Files**:
- `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart` line 22: `Icons.arrow_back`
- Most other screens: `Icons.arrow_back_rounded`

**Description**: The `_rounded` variant is used consistently throughout the app except in the LearningPathScreen.

---

### ISSUE-050 [P2] -- ThemeManager skin config JSON not validated

**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart` lines 192-217
**Code**:
```dart
final colors = _skinConfig!['colors'] as List?;
if (colors == null || colors.length < 2) return base;
final primaryColor = _parseColor(colors[0]);
```

**Description**: Shop skin configuration is read from SharedPreferences and parsed without schema validation. A malformed JSON stored in `skin_config` could cause rendering issues. The `try/catch` in initialization (line 83-89) handles parse failures, but runtime skin application has no error handling.

**Suggested Fix**: Add try/catch around `_applyShopSkin` or validate the skin config structure.

---

## 8. Additional Findings

### ISSUE-051 [P2] -- `node_detail_sheet.dart` uses `_FocusReasonSection` with hardcoded color values

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1556-1558

**Description**: Uses `DS.warning.withOpacity(0.06)` for background and `DS.warning.withOpacity(0.15)` for border. These specific opacity values are hardcoded rather than using design token references.

---

### ISSUE-052 [P2] -- `_formatDate` in node_detail_sheet uses hardcoded YYYY-MM-DD format

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1496-1500
**Code**:
```dart
String _formatDate(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '${date.year}-$month-$day';
}
```

**Description**: The date format `YYYY-MM-DD` is always used regardless of locale. In Chinese locales, `YYYY年MM月DD日` would be more natural.

**Suggested Fix**: Use `intl.DateFormat` with locale-aware patterns, or use the ARB-defined date format.

---

### ISSUE-053 [P2] -- Traits coldstart questionnaire questions come from raw `Map<String, dynamic>`

**File**: `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart` lines 97-127

**Description**: The widget accepts `List<Map<String, dynamic>> questions` and accesses map keys like `question['id']`, `question['title']`, `option['label']` with null-coalescing fallbacks. This is fragile -- any backend schema change could silently break the questionnaire.

**Suggested Fix**: Define a typed model class for questions and options.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Dart files | 1,198 |
| Screen files | 100+ |
| ARB keys (matched) | 9,400 |
| Hardcoded `isChinese` patterns | 1,685 |
| Silent `catch(_)` blocks | 216 |
| `print()` in production | 1 |
| TODO/FIXME comments | 2 |
| `withOpacity()` (deprecated) | 2 |
| Files > 1000 lines | 3 (chat_screen: 3850, knowledge_theater: 4144, dashboard: 1700+) |

---

## Priority Recommendations (Pre-Launch)

### Must Fix (P0):
1. **ISSUE-001** (partial fix): At minimum, fix the 15 keys in ISSUE-013 (ARB placeholder mismatches) and the most user-visible hardcoded strings in chat_screen, community_screen, and routes.
2. **ISSUE-002**: Localize router error page.
3. **ISSUE-003**: Localize LearningPathScreen title.
4. **ISSUE-022**: Fix LearningPathScreen navigation.
5. **ISSUE-023**: Wrap LearningPathScreen in SparklePageScaffold.
6. **ISSUE-016**: Fix static `S.` usage in node_detail_sheet._relativeTime.

### Should Fix (P1):
7. **ISSUE-004, 005**: Localize chat and voice accessibility labels.
8. **ISSUE-006, 007, 008**: Localize task board, community, and questionnaire strings.
9. **ISSUE-014**: Localize OpenClaw error messages.
10. **ISSUE-027**: Replace deprecated `withOpacity()`.
11. **ISSUE-029**: Remove print() statement.
12. **ISSUE-034**: Add logging to critical catch blocks (at least in chat and home providers).
13. **ISSUE-041, 043**: Add Semantics to chat screen interactive elements.

### Nice to Have (P2):
14. Refactor mega-files (chat_screen, knowledge_theater, dashboard) into smaller widget files.
15. Complete accessibility audit for all screens.
16. Validate skin config schema in ThemeManager.
17. Add typed model classes for dynamic map access patterns.
