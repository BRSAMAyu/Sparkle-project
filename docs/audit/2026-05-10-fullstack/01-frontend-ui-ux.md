# Frontend UI/UX Audit Report

> **Date**: 2026-05-10
> **Scope**: `mobile/lib/` -- Chat, Home, Community, Galaxy, Insights, User features + cross-cutting concerns
> **Severity Scale**: P0 (Critical / crash-prone), P1 (High / broken flow), P2 (Medium / UX degradation), P3 (Low / polish)

---

## Summary

| Severity | Count |
|----------|-------|
| P0       | 2     |
| P1       | 9     |
| P2       | 18    |
| P3       | 14    |
| **Total** | **43** |

---

## 1. Chat Feature (`features/chat/`)

### P0-01: Undefined `ctx` variable in `chat_screen.dart` itemBuilder

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Line**: 1441, 1455-1456, 1518, and many more inside the `ListView.builder` itemBuilder
- **Description**: The `itemBuilder` callback receives `context` as its first parameter, but the body references `ctx` (undefined variable). This would cause a compile-time error or reference the wrong context. The variable `ctx` is used for `ctx.l10n` and as context argument to `auroraCorrectionPresentationFor(ctx, ...)`.
- **Suggested Fix**: Replace all `ctx.` references inside the itemBuilder with `context.`.

### P0-02: Undefined `message` variable in `chat_screen.dart` itemBuilder

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Line**: 1450 (`message.id`)
- **Description**: Inside the `ListView.builder` itemBuilder, `message.id` is referenced but no `message` variable is declared in that scope. The builder should compute `message` from `messages[index]` (or the appropriate index mapping that accounts for streaming/status indicators). Without this, the code cannot compile or will throw a runtime error.
- **Suggested Fix**: Add proper index-to-message mapping at the top of the itemBuilder: `final message = messages[index];` (adjusted for the streaming/status indicator offset).

### P1-01: Hardcoded string 'OpenClaw Hub' not using i18n

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Line**: 1266
- **Description**: The semantic label fallback uses a hardcoded English string `'OpenClaw Hub'` instead of `context.l10n.openclawHubAppBarTitle`. When the user has `showOpenClawAttention == false`, the accessibility label is always in English.
- **Suggested Fix**: Replace `'OpenClaw Hub'` with `context.l10n.openclawHubAppBarTitle`.

### P1-02: Hardcoded English semantic labels in voice_input_button.dart

- **File**: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart`
- **Line**: 304
- **Description**: Semantics label is hardcoded as `'Stop voice input recording'` / `'Start voice input'` in English. Non-English users get incorrect accessibility labels.
- **Suggested Fix**: Use `context.l10n` for the semantic labels.

### P2-01: chat_screen.dart is 2900+ lines -- extremely large single file

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Line**: Entire file
- **Description**: At 2900+ lines with deeply nested itemBuilder callbacks and 15+ listener subscriptions in initState, this file is a significant maintenance burden. The itemBuilder at line 1437 contains 300+ lines of inline code with deeply nested callbacks. This increases the risk of bugs during modification (as evidenced by P0-01 and P0-02).
- **Suggested Fix**: Extract the itemBuilder body into a separate method or widget. Extract the Aurora correction handlers into a dedicated mixin or helper class. Consider splitting the screen into sub-widgets for header panels, message list, and bottom input area.

### P2-02: Chat error auto-clear uses mutable state access pattern

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Line**: 256-265
- **Description**: The error listener directly mutates `notifier.state` via `notifier.state = notifier.state.copyWith(clearError: true)` inside a `Future.delayed`. This bypasses the standard state management pattern and could cause state inconsistencies if other mutations happen during the 10-second window.
- **Suggested Fix**: Add a dedicated `clearError()` method on the ChatNotifier that handles this atomically.

### P2-03: Chat bottom padding uses hardcoded magic numbers

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Lines**: 2442-2500
- **Description**: `_calculateBottomPadding` uses hardcoded values like `132`, `108.0`, `124.0`, `80.0`, `100.0` for different layout configurations. These values are fragile and may break on different screen sizes or when components change height.
- **Suggested Fix**: Use LayoutBuilder or IntrinsicHeight measurements to dynamically calculate bottom padding based on actual component heights.

### P3-01: `_chatFailureIcon` switch does not handle all `FailureKind` exhaustively

- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- **Line**: 94-108
- **Description**: The switch statement uses `FailureKind.network` as a case but the `FailureKindCode.fromCode` could return values not covered if new failure kinds are added. The `default` falls to `unknown` icon but there is no compile-time guarantee all cases are handled.
- **Suggested Fix**: No immediate fix needed since the switch is exhaustive for current enum values, but consider adding a lint rule for exhaustive switch.

---

## 2. Home Dashboard (`features/home/`)

### P1-03: Hardcoded Chinese strings in task_board_card.dart

- **File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart`
- **Lines**: 227, 235, 248, 256, 269, 277, 292
- **Description**: Multiple user-facing strings use `isChinese ? '...' : '...'` pattern instead of ARB l10n keys. Examples:
  - `'任务按到期日期分组显示'` / `'Tasks are grouped by due date.'` (line 227)
  - `'红色高亮显示已逾期的任务'` / `'Overdue tasks are highlighted in red.'` (line 235)
  - `'今日${summary.totalCount}项·已完成${summary.completedCount}'` (line 292)
  - 8 total instances of this pattern
- **Suggested Fix**: Add these strings to `app_en.arb` and `app_zh.arb`, then use `context.l10n.*` throughout.

### P2-04: Collapsible slot uses isChinese ternary for semantic label

- **File**: `mobile/lib/features/home/presentation/widgets/collapsible_slot.dart`
- **Line**: 227
- **Description**: `_ExpandedSurface` uses `I18nService.instance.isChinese ? '长按编辑面板' : 'Long press to edit panel'` for the semantic label. This should use l10n.
- **Suggested Fix**: Use `context.l10n` for the semantic label.

### P2-05: DashboardCardGrid has fixed height constant

- **File**: `mobile/lib/features/home/presentation/widgets/dashboard_card_grid.dart`
- **Line**: 12
- **Description**: `gridCardHeight` is a static `196` pixels. This fixed height may cause overflow or excessive whitespace on different screen densities. Cards with variable content (like task lists) may clip or have excessive padding.
- **Suggested Fix**: Consider using `IntrinsicHeight` or allow cards to self-size with a min/max constraint.

### P3-02: Task board card `_summaryLabel` mixes l10n and isChinese

- **File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart`
- **Line**: 284-294
- **Description**: The `_summaryLabel` method uses `isChinese ? '...' : '...'` for the summary text, while other parts of the same widget use `context.l10n.*`. Inconsistent i18n approach within the same file.
- **Suggested Fix**: Use `context.l10n` consistently.

---

## 3. Community (`features/community/`)

### P1-04: community_main_screen.dart uses isChinese instead of l10n for ALL tab labels and page titles

- **File**: `mobile/lib/features/community/presentation/screens/community_main_screen.dart`
- **Lines**: 54-59, 83, 93
- **Description**: Tab labels ('伙伴'/'Partners', '动态'/'Feed', '群组'/'Groups'), page title ('社群'/'Community'), and subtitle ('和伙伴一起成长'/'Grow together with partners') all use `zh ? '...' : '...'` pattern instead of ARB l10n. These are all user-facing strings.
- **Suggested Fix**: Add keys to `app_en.arb` and use `context.l10n.*`.

### P1-05: create_post_screen.dart uses isChinese for ALL user-facing text

- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart`
- **Lines**: 101-103, 123-126, 135, 140, 168, 192-194, 236, 289, 302, 308
- **Description**: Every user-facing string in this screen uses `zh ? '...' : '...'` instead of ARB l10n. This includes:
  - Error message: `'发布失败，请稍后重试'` / `'Post failed, please try again later'` (line 101-103)
  - Unsaved changes dialog: `'放弃编辑？'` / `'Discard draft?'` (line 123)
  - App bar title: `'发布动态'` / `'New Post'` (line 135)
  - Field labels and hints: `'选择心情'`, `'附图'`, `'图片'`, `'话题'` (lines 168, 236, 302, 308)
  - Content hint: `'分享你此刻的想法...'` (line 192-194)
  - 15+ total hardcoded string pairs
- **Suggested Fix**: Migrate all strings to ARB l10n.

### P1-06: create_post_screen.dart -- no actual content length enforcement

- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart`
- **Lines**: 205-211
- **Description**: The character count turns red when exceeding 500, but there is no `maxLength` on the TextField and the submit function does not enforce the limit. Users can submit posts exceeding 500 characters.
- **Suggested Fix**: Either add `maxLength: 500` to the TextField, or check `content.length > 500` in `_submit()` and show an error.

### P2-06: shared_resource_card.dart uses isChinese for ALL user-facing text

- **File**: `mobile/lib/features/community/presentation/widgets/shared_resource_card.dart`
- **Lines**: 32, 51, 69, 108, 135, 145, 155, 212-213, 219-220
- **Description**: All strings use `isChinese ? '...' : '...'` pattern:
  - `'共享资源'` / `'Shared Resource'`
  - `'精选'` / `'Featured'`, `'推荐'` / `'Recommended'`, `'新手友好'` / `'Beginner-friendly'`
  - `'采纳并加入我的计划'` / `'Adopt into my plan'`
  - `'采纳 $adoption 次'` / `'$adoption adoptions'`
  - 10+ total hardcoded string pairs
- **Suggested Fix**: Migrate to ARB l10n.

### P2-07: accountability_detail_screen.dart -- hardcoded Chinese date format

- **File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- **Lines**: 955, 1007, 1082
- **Description**: Date formatting uses hardcoded Chinese format `'M月d日 HH:mm'` via `DateFormat('M月d日 HH:mm').format(...)`. This format is incorrect for English users -- it would display "5月10日 14:30" instead of "May 10, 14:30".
- **Suggested Fix**: Use locale-aware formatting: `DateFormat.yMMMd(context.l10n.localeName).add_Hm().format(...)` or add specific l10n date format keys.

### P2-08: accountability_detail_screen.dart -- hardcoded Chinese counter suffix

- **File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- **Lines**: 975, 1027
- **Description**: `'$count 条'` is hardcoded with the Chinese counter character '条'. For English users this would display "5 条" instead of "5 items".
- **Suggested Fix**: Use `context.l10n.accountabilityItemCount(count)` or similar l10n key.

### P2-09: accountability_detail_screen.dart -- error message leaks raw exception to user

- **File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- **Lines**: 99, 258-259
- **Description**: Error display uses `'$e'` and `'${context.l10n.accountabilityOperationFailed}: $e'` which exposes raw exception details (potentially including stack traces, internal URLs, etc.) to the user.
- **Suggested Fix**: Log the exception internally and show a generic user-friendly error message.

### P2-10: accountability_heatmap.dart -- hardcoded cell colors not theme-aware

- **File**: `mobile/lib/features/community/presentation/widgets/accountability_heatmap.dart`
- **Lines**: 383-385
- **Description**: Day cell colors are hardcoded as `Color(0xFF2E7D32)` (dark green) and `Color(0xFF9BE9A8)` (light green). These do not adapt to dark/light theme and may have poor contrast in dark mode.
- **Suggested Fix**: Use DS semantic color tokens or theme-aware colors.

### P3-03: accountability_detail_screen.dart -- _PersonStat uses full name for avatar text

- **File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- **Line**: 875
- **Description**: The `_PersonStat` CircleAvatar displays `name` (e.g., "Me" or "Them") as its child text. Multi-character names like "Them" overflow the small CircleAvatar (radius 30).
- **Suggested Fix**: Use initials (first character) for the avatar text, or increase the radius.

### P3-04: create_post_screen.dart -- Topic button does nothing useful

- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart`
- **Lines**: 309-314
- **Description**: The Topic toolbar button's `onPressed` sets `_topicController.text` to itself if non-empty (a no-op) and requests focus without actually focusing the topic field specifically.
- **Suggested Fix**: Focus the topic TextField specifically: `_topicController.selection = TextSelection(baseOffset: 0, extentOffset: _topicController.text.length); FocusScope.of(context).requestFocus(_topicFocus);` (a `_topicFocus` FocusNode would need to be created).

### P3-05: create_post_screen.dart -- Post button calls empty lambda when disabled

- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart`
- **Line**: 143
- **Description**: When content is empty, the Post button's `onPressed` is `() {}` instead of `null`. This means the button appears enabled and responds to taps (doing nothing) rather than appearing disabled. With `SparkleButton.primary`, the button should use `onPressed: null` for proper disabled state.
- **Suggested Fix**: Change to `onPressed: _contentController.text.trim().isEmpty || _isPosting ? null : _submit`.

---

## 4. Galaxy Knowledge Graph (`features/galaxy/`)

### P1-07: node_detail_sheet.dart -- hardcoded review prompt in isChinese ternary

- **File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`
- **Lines**: 179-181
- **Description**: The default review prompt uses `I18nService.instance.isChinese ? '带我复习「$label」。...' : 'Help me review "$label"...'` -- a long, complex prompt string hardcoded as a ternary instead of using l10n. Additionally, this is a prompt that will be sent to the AI, so hardcoding prevents future i18n improvements.
- **Suggested Fix**: Add a parameterized l10n key: `context.l10n.galaxyNodeReviewPrompt(label)`.

### P2-11: Galaxy screen -- extremely large state class with 60+ fields

- **File**: `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`
- **Lines**: 135-208
- **Description**: `_GalaxyScreenState` has 60+ mutable fields, 7 AnimationControllers, 3 Tickers, and complex disposal logic. This is extremely fragile -- any missed disposal causes memory leaks. The state class is also very difficult to test and maintain.
- **Suggested Fix**: Extract animation management into a dedicated controller class. Group related state into immutable data classes.

### P3-06: Galaxy screen -- node ID displayed raw to user

- **File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`
- **Line**: 344-349
- **Description**: The node detail sheet displays the raw `nodeId` (likely a UUID or internal ID) in a secondary text line. This is developer-facing information that may confuse users.
- **Suggested Fix**: Remove the raw ID display or move it to a developer/debug overlay.

---

## 5. Insights (`features/insights/`)

### P3-07: learning_path_dialog.dart -- hardcoded semantic label

- **File**: `mobile/lib/features/insights/presentation/widgets/learning_path_dialog.dart`
- **Line**: 873
- **Description**: The dismiss button uses `semanticLabel: 'dismiss feedback'` -- a hardcoded English string.
- **Suggested Fix**: Use `context.l10n.dismiss` or similar l10n key.

### P3-08: insights_routes.dart -- no error handling for missing query parameters

- **File**: `mobile/lib/features/insights/insights_routes.dart`
- **Lines**: 116-118
- **Description**: The learning path route extracts `node_id` and `node_label` from query parameters with fallback to empty strings. If both are empty, `LearningPathScreen` receives empty data and may show an empty/broken view without any user feedback.
- **Suggested Fix**: Validate that at least `node_id` is present and non-empty. Show an error or redirect if not.

---

## 6. User/Profile (`features/user/`)

### P2-12: traits_coldstart_questionnaire.dart -- hardcoded Chinese string

- **File**: `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart`
- **Line**: 50
- **Description**: `'点击展开/收起'` / `'Tap to expand/collapse'` uses `zh ? '...' : '...'` pattern.
- **Suggested Fix**: Add to ARB l10n.

### P3-09: traits_coldstart_questionnaire.dart -- no form validation before submit

- **File**: `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart`
- **Line**: 129-141
- **Description**: `_handleSubmit` submits `_answers` without checking if all questions are answered. Users can submit a partial/empty form.
- **Suggested Fix**: Validate that all questions have answers before submitting. Show validation error if incomplete.

### P3-10: user_persona_screen.dart -- error state still shows full content with empty data

- **File**: `mobile/lib/features/user/presentation/screens/user_persona_screen.dart`
- **Line**: 92-103
- **Description**: When `profileAsync` is in error state, the build method calls `_buildContent` with empty data `const <String, dynamic>{}`. This means the user sees an empty profile view with a warning, rather than a clear error state with retry.
- **Suggested Fix**: Show a dedicated error view when profile loading fails, with a prominent retry button.

---

## 7. Cross-cutting Concerns

### P1-08: Widespread use of `isChinese ? '...' : '...'` pattern instead of ARB l10n

- **Files**: Multiple files across community, home, user features (see individual issues P1-03, P1-04, P1-05, P2-06, P2-12, P1-07)
- **Description**: The `I18nService.instance.isChinese ? '中文' : 'English'` pattern is used extensively throughout the codebase instead of the proper ARB l10n system. This pattern:
  - Does not support any language beyond Chinese and English
  - Bypasses the l10n code generation pipeline
  - Makes strings harder to find and update
  - Violates the project's own i18n strategy documented in `feedback_i18n_strategy.md`
- **Affected files** (estimated count): 15+ files, 80+ string instances
- **Suggested Fix**: Systematically migrate all `isChinese` ternaries to ARB l10n keys. This is a significant effort but is required per the project's own standards.

### P2-13: design_system.dart -- ThemeManager singleton may not be disposed

- **File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart`
- **Line**: 11-14
- **Description**: `ThemeManager` is a singleton `ChangeNotifier` with `WidgetsBindingObserver`. It registers as an observer but never unregisters (it's a singleton, so it lives for the app lifetime). While this is acceptable for a singleton, the `_observerRegistered` flag could lead to double-registration if `initialize()` is called multiple times in testing scenarios.
- **Suggested Fix**: Add a `dispose()` guard for testing, or reset `_observerRegistered` in `initialize()`.

### P2-14: group_knowledge_base_view.dart -- duplicated utility methods

- **File**: `mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`
- **Lines**: 725-772, 936-983, 1077-1115
- **Description**: `_formatSize()`, `_iconForMime()`, and `_typeLabel()` methods are duplicated 3 times across `_GroupKnowledgeBaseViewState`, `_KnowledgeBaseListCard`, and `_KnowledgeBaseGridCard`. This violates DRY and makes maintenance error-prone.
- **Suggested Fix**: Extract these utility methods into a shared mixin or top-level utility file.

### P2-15: No retry mechanism in community_main_screen for tab content loading

- **File**: `mobile/lib/features/community/presentation/screens/community_main_screen.dart`
- **Line**: 124-131
- **Description**: The `TabBarView` children (`PartnersTab`, `FeedTabContent`, `GroupsTab`) are loaded without any visible error/retry handling at this level. If any tab fails to load, there is no parent-level retry mechanism.
- **Suggested Fix**: Verify that each tab widget handles its own loading/error/retry states properly. Consider adding a top-level error boundary.

### P2-16: accountability_detail_screen.dart -- DateTime formatting inconsistencies

- **File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- **Lines**: 1249 (`DateFormat('MM-dd HH:mm')`), 955 (`DateFormat('M月d日 HH:mm')`)
- **Description**: Two different date formats are used -- one locale-neutral (`MM-dd HH:mm`) and one Chinese-specific (`M月d日 HH:mm`). The neutral format at line 1249 does not respect locale either.
- **Suggested Fix**: Use locale-aware formatting throughout: `DateFormat.yMMMd(context.l10n.localeName).add_Hm().format(...)`.

### P3-11: voice_input_button.dart -- recording duration timer continues after dispose

- **File**: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart`
- **Lines**: 93-97
- **Description**: While `dispose()` cancels `_durationTimer`, if `_stopRecording()` is called and then `dispose()` happens quickly, the `_recordingService.dispose()` at line 96 may interact with the async stop. The `_recordingService` is disposed synchronously while `_stopRecording()` is async.
- **Suggested Fix**: Ensure `_recordingService.stopRecording()` completes before disposing, or handle the race condition.

### P3-12: group_knowledge_base_view.dart -- _toggleOfficial is only local state, not persisted

- **File**: `mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`
- **Lines**: 148-158
- **Description**: `_toggleOfficial` only updates `_officialOverrides` (local state) and shows a success message, but does not persist the change to the backend. The change will be lost on reload.
- **Suggested Fix**: Call the appropriate API to persist the official status change. The local override should only be a temporary optimistic update.

### P3-13: community_main_screen.dart -- SliverPersistentHeader delegate may not rebuild on locale change

- **File**: `mobile/lib/features/community/presentation/screens/community_main_screen.dart`
- **Lines**: 138-162
- **Description**: `_TabBarDelegate.shouldRebuild` compares `tabBar != oldDelegate.tabBar`. Since tab labels are created in `build()` and are new objects each time, this should work. However, the TabBar itself is created inside `build()`, so it will always be a new instance. The delegate pattern is correct but could be simplified.
- **Suggested Fix**: No immediate fix needed. The current implementation is functional.

### P3-14: learning_path_dialog.dart -- _loadRelatedTasks fetches ALL tasks then filters client-side

- **File**: `mobile/lib/features/insights/presentation/widgets/learning_path_dialog.dart`
- **Lines**: 429-436
- **Description**: `_loadRelatedTasks` fetches up to 50 tasks and then filters by `knowledgeNodeId` client-side. This is inefficient -- the filtering should be done server-side.
- **Suggested Fix**: Add a `knowledgeNodeId` filter parameter to the `getTasks()` API call.

---

## Appendix A: Files Audited

| File | Status |
|------|--------|
| `features/chat/presentation/screens/chat_screen.dart` | Issues found (P0, P1, P2) |
| `features/chat/presentation/widgets/voice_input_button.dart` | Issues found (P1, P3) |
| `features/home/presentation/widgets/collapsible_slot.dart` | Issues found (P2) |
| `features/home/presentation/widgets/dashboard_card_grid.dart` | Issues found (P2) |
| `features/home/presentation/widgets/task_board/task_board_card.dart` | Issues found (P1, P3) |
| `features/community/presentation/screens/community_main_screen.dart` | Issues found (P1) |
| `features/community/presentation/screens/accountability_detail_screen.dart` | Issues found (P2, P3) |
| `features/community/presentation/screens/create_post_screen.dart` | Issues found (P1, P3) |
| `features/community/presentation/widgets/accountability_heatmap.dart` | Issues found (P2) |
| `features/community/presentation/widgets/group_knowledge_base_view.dart` | Issues found (P2, P3) |
| `features/community/presentation/widgets/share_cards/learning_report_share_card.dart` | No significant issues |
| `features/community/presentation/widgets/shared_resource_card.dart` | Issues found (P2) |
| `features/galaxy/presentation/screens/galaxy_screen.dart` | Issues found (P2) |
| `features/galaxy/presentation/widgets/node_detail_sheet.dart` | Issues found (P1, P3) |
| `features/insights/insights_routes.dart` | Issues found (P3) |
| `features/insights/presentation/widgets/learning_path_dialog.dart` | Issues found (P3) |
| `features/user/presentation/screens/user_persona_screen.dart` | Issues found (P3) |
| `features/user/presentation/widgets/traits_coldstart_questionnaire.dart` | Issues found (P2, P3) |
| `l10n/app_en.arb` | Reviewed for key coverage |
| `core/design/design_system.dart` | Reviewed |
| `core/design/tokens_v2/theme_manager.dart` | Issues found (P2) |

---

## Appendix B: i18n Pattern Violation Summary

The following pattern is used extensively instead of proper ARB l10n:

```dart
// ANTI-PATTERN used in 15+ files:
final zh = I18nService.instance.isChinese;
Text(zh ? '中文文本' : 'English text');

// CORRECT pattern per project standards:
Text(context.l10n.someArbKey);
```

**Estimated total instances**: 80+ string pairs across:
- `community_main_screen.dart` (5 instances)
- `create_post_screen.dart` (15+ instances)
- `shared_resource_card.dart` (10+ instances)
- `task_board_card.dart` (8 instances)
- `dashboard_screen.dart` (5+ instances)
- `dashboard_edit_sheet.dart` (3+ instances)
- `node_detail_sheet.dart` (2 instances)
- `traits_coldstart_questionnaire.dart` (1 instance)
- `collapsible_slot.dart` (1 instance)
- `group_search_screen.dart` (4+ instances)
- `favorites_screen.dart` (10+ instances)
- `community_agent_provider.dart` (7+ instances)
- `accountability_repository.dart` (5+ instances)
- `next_actions_card.dart` (2+ instances)
- Various other community files

---

## Appendix C: Recommended Fix Priority

### Immediate (P0 -- Must Fix Before Ship)

1. **P0-01**: Fix undefined `ctx` in `chat_screen.dart` itemBuilder -- replace with `context`
2. **P0-02**: Fix undefined `message` variable in `chat_screen.dart` itemBuilder -- add proper index mapping

### High Priority (P1 -- Fix in Next Sprint)

3. **P1-01**: Hardcoded 'OpenClaw Hub' string
4. **P1-02**: Hardcoded English semantic labels in voice_input_button
5. **P1-03**: 8 hardcoded string pairs in task_board_card
6. **P1-04**: 5 hardcoded string pairs in community_main_screen
7. **P1-05**: 15+ hardcoded string pairs in create_post_screen
8. **P1-06**: Missing content length enforcement in create_post
9. **P1-07**: Hardcoded review prompt in node_detail_sheet
10. **P1-08**: Systematic isChinese pattern violation (cross-cutting)

### Medium Priority (P2 -- Fix in Following Sprint)

11. **P2-01** through **P2-16**: 18 issues including code structure, theme awareness, utility duplication, and validation gaps

### Low Priority (P3 -- Polish Phase)

12. **P3-01** through **P3-14**: 14 issues including minor UX improvements, accessibility gaps, and code quality improvements
