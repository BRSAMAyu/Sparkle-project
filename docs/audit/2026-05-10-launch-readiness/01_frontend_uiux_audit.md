# Frontend UI/UX Launch-Readiness Audit

**Date**: 2026-05-10
**Auditor**: Senior Frontend Architect (automated)
**Scope**: `mobile/lib/features/` -- all screens, widgets, i18n, code quality
**Status**: CRITICAL -- launch blocked by P0 compilation errors

---

## Executive Summary

The Flutter mobile app has **42 compilation errors** concentrated in a single critical file (`chat_screen.dart`), making the app unable to build. Beyond the build-breaker, there are 622 inline i18n string literals using `I18nService.instance.isChinese` instead of the ARB l10n system, 134 analyzer warnings, 358 debug print statements, and numerous hardcoded route paths across the codebase.

**Total findings: 18**

| Severity | Count |
|----------|-------|
| P0 (Blocker) | 2 |
| P1 (Critical) | 6 |
| P2 (Important) | 6 |
| P3 (Minor) | 4 |

---

## P0 -- Blockers (MUST fix before launch)

### [F-001] chat_screen.dart: 42 compilation errors from broken itemBuilder refactor

- **Severity**: P0 (Blocker)
- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart` lines 1437-1763
- **Description**: A recent partial refactor of the `ListView.builder` in `_ChatScreenState.build()` destroyed the `itemBuilder` callback. The old code had proper index-based message resolution (`isStatusShowing`, `isReasoningShowing`, `isSendingShowing`, `msgIndex` arithmetic, `final message = messages[adjustedIndex]`, `final showCorrectionBar = ...`, `final showEnvelopeIndicator = ...`, and an inner `Builder(builder: (ctx) {...})`). The new working-copy code deleted all the index logic and pasted the `ContextualCorrectionBar` widget directly inside `itemBuilder` with unresolved references:

  1. `ctx` at line 1441 -- resolves to `widget.initialExtraContext` (a `Map<String, dynamic>?`, NOT a `BuildContext`). Was previously a `Builder(builder: (ctx) {...})` local.
  2. `message` at line 1450 -- completely undefined in scope. Was previously `final message = messages[adjustedIndex]`.
  3. `showEnvelopeIndicator` at line 1763 -- undefined variable. Was previously `final showEnvelopeIndicator = isLatestAssistant && message.role == MessageRole.assistant`.
  4. The entire index-dispatch logic for status indicator (index 0), reasoning bubble (index 1), streaming bubble, and message rendering is missing.
  5. `ContentConstraint` wrapper was removed from around the main Column, changing layout behavior.

  Flutter analyzer output: 42 errors including `undefined_identifier`, `expected_token`, `missing_identifier`, and `dead_code`.

- **Impact**: The app cannot compile. Chat is the primary user-facing feature and is completely broken. This single issue blocks all testing and deployment.
- **Fix Context**: Revert the broken diff in `chat_screen.dart` or restore the original `itemBuilder` logic. The committed version (`HEAD`) has working code. The specific area is the `itemBuilder: (context, index) { ... }` callback inside `ListView.builder` starting around line 1437. The old code (visible via `git show HEAD:mobile/lib/features/chat/presentation/screens/chat_screen.dart` lines 1360-1620) contains the correct implementation with:
  - Index dispatch for status/reasoning/streaming/message items
  - `final message = messages[adjustedIndex]` with bounds checking
  - `final showCorrectionBar` and `final showEnvelopeIndicator` computed from message
  - `Builder(builder: (ctx) { ... })` wrapping the `ContextualCorrectionBar`
  - `ContentConstraint(child: Column(...))` wrapper

---

### [F-002] chat_screen.dart: Missing AuroraCoreSessionResumeBanner

- **Severity**: P0 (Blocker)
- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart` -- removed during refactor
- **Description**: The committed version of chat_screen.dart includes an `AuroraCoreSessionResumeBanner` widget between the `ChatUnderstandingDrawerButton` and the `_DualCoreModeChip`. The working copy diff removes it entirely. This banner handles session resumption for Aurora's core calibration flow, which is a key user experience feature for the adaptive AI system.
- **Impact**: Users who had an active Aurora core session will have no way to resume it from the chat screen, breaking the adaptive AI feedback loop.
- **Fix Context**: Restore the `AuroraCoreSessionResumeBanner` in the header panels section. It should appear after `ChatUnderstandingDrawerButton` and before the `_DualCoreModeChip`, as it was in the committed version:
  ```dart
  if (!chatPureMode) const ChatUnderstandingDrawerButton(),
  AuroraCoreSessionResumeBanner(
    conversationId: chatState.conversationId,
  ),
  if (chatState.dualCoreMode != null)
    _DualCoreModeChip(mode: chatState.dualCoreMode!),
  ```

---

## P1 -- Critical (SHOULD fix before launch)

### [F-003] 622 inline zh/en string literals bypassing ARB l10n system

- **Severity**: P1 (Critical)
- **File**: 69 files across `mobile/lib/features/`
- **Description**: 622 instances of `I18nService.instance.isChinese ? '中文' : 'English'` pattern are used instead of the proper `context.l10n.keyName` ARB system. Key affected files:
  - `community_main_screen.dart` -- tab labels, page title, subtitle (lines 54-95)
  - `create_post_screen.dart` -- every user-facing string (title, button labels, hints, error messages, dialog text)
  - `dashboard_screen.dart` -- 206 instances (the largest offender)
  - `learning_insights_overview_screen.dart` -- module card titles, subtitles, button labels
  - `shared_resource_card.dart` -- badge labels ("Featured", "Recommended", "Beginner-friendly", "Adopt into my plan")
  - `node_detail_sheet.dart` -- review prompt text
  - `blocked_users_screen.dart` -- all screen text
  - `favorites_screen.dart` -- all screen text
  - `group_members_screen.dart` -- action labels
  - `notification_list_screen.dart` -- title, error message
  - `sprint_view.dart` -- sprint action buttons
  - `marketplace_screen.dart` -- all screen text
  - `growth_dashboard.dart` (data model) -- narrative text, insights
  - `weekly_growth_narrative.dart` (data model) -- all narrative strings
  - `traits_coldstart_questionnaire.dart` -- "Tap to expand/collapse" hint (line 50)
  - `understanding_snapshot_card.dart` -- multiple UI strings
  - `goal_detail_snapshot_card.dart` -- multiple UI strings
  - `growth_quality_card.dart` -- streak labels, insights

  Meanwhile, the ARB files (`app_en.arb` / `app_zh.arb`) have 9,400 keys each and are perfectly synchronized between EN and ZH. The proper l10n system works correctly; these 622 strings simply were never migrated.

- **Impact**: These strings are invisible to the ARB pipeline. They cannot be found by translators, cannot be audited for completeness, and bypass the `AppLocalizations` generation system. If the i18n service logic ever changes, all 622 instances break silently. For a Chinese-student-facing app, inconsistent i18n approach is a launch risk.
- **Fix Context**: Migrate all `I18nService.instance.isChinese ? '中文' : 'English'` patterns to ARB keys. Example for `community_main_screen.dart`:
  ```dart
  // Before (line 56-58):
  final tabLabels = [
    zh ? '伙伴' : 'Partners',
    zh ? '动态' : 'Feed',
    zh ? '群组' : 'Groups',
  ];
  // After:
  final tabLabels = [
    context.l10n.communityTabPartners,
    context.l10n.communityTabFeed,
    context.l10n.communityTabGroups,
  ];
  ```
  Add corresponding keys to both ARB files. Priority: screens first (create_post, community_main, dashboard), then widgets, then data models.

---

### [F-004] 134 analyzer warnings across the codebase

- **Severity**: P1 (Critical)
- **File**: Multiple files
- **Description**: 134 analyzer warnings including:
  - **Unused fields/methods** in `chat_screen.dart`: `_newMessageDividerBeforeId` (line 189), `_messageKeyFor` (line 833), `_buildBottomInputArea` (line 2505), `_attachmentChipLabel` (line 2828), `_attachmentStatusIcon` (line 2850), `_attachmentStatusColor` (line 2864)
  - **Unused variables**: `offlineStatuses` (line 1163), `latestAssistantMessageId` (line 1173), `idleIconColor` in voice_input_button.dart (line 398), `isZh` in goal_detail_page.dart (line 266), `_ref` in dashboard_provider.dart (line 424)
  - **Unused imports**: `i18n_service.dart` in statistics_report_generator.dart, `material.dart` in auth_routes.dart, cognitive_routes.dart, notification_center_routes.dart, photon_routes.dart, `community_accountability_hub_l10n.dart` in partner_observation_control.dart
  - **Deprecated API usage**: `withOpacity` in node_detail_sheet.dart (lines 1556, 1558) -- should use `.withValues(alpha:)`; `getIsolateID` in performance_monitor.dart -- should use `getIsolateId`
  - **Type inference failures**: comment_bottom_sheet.dart lines 71, 101, 125 -- missing generic type arguments on `get`, `post`, `delete`
  - **Null-aware operator on non-nullable**: weather_guide_screen.dart line 173, learning_portfolio_screen.dart line 446

- **Impact**: Code quality signals to reviewers and app stores. Deprecated API usage will become errors in future Flutter versions. Unused code increases binary size.
- **Fix Context**: Run `flutter analyze` and address each warning. Most are trivial fixes (remove unused code, replace `withOpacity` with `withValues(alpha:)`, add type arguments).

---

### [F-005] 358 debug print statements in production code

- **Severity**: P1 (Critical)
- **File**: Multiple files, especially providers in `features/home/presentation/providers/`
- **Description**: 358 `debugPrint()` calls across the features codebase. While `debugPrint` is suppressed in release builds, the sheer volume suggests debugging code that was never cleaned up. Dense clusters:
  - `dashboard_provider.dart` -- 6 instances
  - `home_growth_provider.dart` -- 7 instances
  - `intent_prediction_provider.dart` -- 6 instances
  - `notification_provider.dart` -- 1 instance
  - `create_post_screen.dart` line 98 -- `debugPrint('Post failed: $e')` (should use structured error reporting)

- **Impact**: Performance overhead in debug builds. Indicates incomplete error handling. `debugPrint` in catch blocks often masks real errors that should surface to the user or a crash reporter. The `create_post_screen.dart` usage on line 98 is especially concerning -- it silently logs a post failure instead of showing user feedback (though there is an `AppFeedback.error` call after it).
- **Fix Context**: Replace `debugPrint` in error catch blocks with proper error reporting (user-facing feedback or crash reporting service). Remove debugging-only `debugPrint` calls. Keep only those that serve as legitimate diagnostic output in development.

---

### [F-006] Hardcoded route paths instead of named routes

- **Severity**: P1 (Critical)
- **File**: Primarily `dashboard_screen.dart` (206 instances), also `learning_insights_overview_screen.dart`, `openclaw_hub_screen.dart`
- **Description**: 16+ locations use hardcoded string routes like `context.push('/tasks')`, `context.go('/chat')`, `context.push('/galaxy')`, `context.go('/goals/new')`, `context.push('/plans/new?type=growth')`, `context.push('/exam-sprint/setup')`, `context.push('/focus')`, `context.push('/community/accountability')`, `context.go('/login')`, etc. while named route constants exist in `*_routes.dart` files (31 route definition files found). Some locations correctly use the route constants (`ChatRoutes.chat`, `TaskRoutes.taskCreate`, `GoalRoutes.detailLocation`) while others use raw strings.

  Inconsistent examples from `dashboard_screen.dart`:
  - Line 383: `context.push('/tasks')` -- should be `context.push(TaskRoutes.tasks)`
  - Line 483: `context.go('/chat')` -- should be `context.go(ChatRoutes.chat)`
  - Line 528: `context.go('/goals/new')` -- should be `context.go(GoalRoutes.create)`
  - Line 1314: `context.go('/login')` -- should be `context.go(AuthRoutes.login)`

- **Impact**: Route refactoring becomes fragile -- any path change requires grep across the entire codebase. Mix of named and hardcoded routes creates maintenance burden. Typos in hardcoded paths cause silent navigation failures.
- **Fix Context**: Replace all hardcoded route strings with their corresponding route constants from `*_routes.dart` files. Example:
  ```dart
  // Before:
  context.push('/tasks');
  // After:
  context.push(TaskRoutes.tasks);
  ```

---

### [F-007] Mixed i18n patterns -- I18nService vs context.l10n within same files

- **Severity**: P1 (Critical)
- **File**: Multiple files, notably `dashboard_screen.dart`, `learning_insights_overview_screen.dart`, `community_main_screen.dart`
- **Description**: Some files mix both `context.l10n.xxx` (proper ARB) and `I18nService.instance.isChinese ? '中文' : 'English'` (inline ternary) in the same widget. For example, `learning_insights_overview_screen.dart` uses `context.l10n` for some module cards (lines 117-134) but switches to `I18nService.instance.isChinese` for the "AI Decision Log" section (lines 139-152) and simulation card (lines 174-182). The `dashboard_screen.dart` file has 206 inline ternaries alongside proper `context.l10n` calls.

- **Impact**: Two different i18n approaches coexist, making the codebase confusing for contributors. Strings added via inline ternary are invisible to l10n tooling.
- **Fix Context**: Standardize on `context.l10n` for all presentation-layer strings. The `I18nService.instance.isChinese` pattern should only be used in data/repository layers where `BuildContext` is unavailable.

---

### [F-008] Community create_post_screen: missing max-length enforcement and character limit indicator

- **Severity**: P1 (Critical)
- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart` lines 204-215
- **Description**: The post content TextField shows a character count (line 208: `'${_contentController.text.length}'`) and turns red when over 500 characters (line 211), but there is no actual `maxLength` constraint on the TextField itself. Users can type beyond 500 characters and the "Post" button remains enabled -- `_contentController.text.trim().isEmpty` is the only submit guard (line 142). The post will be submitted with content exceeding 500 chars, likely causing a backend rejection or truncation.

  Additionally, the character count display doesn't show the limit (e.g., "350/500"), just the raw count.

- **Impact**: Users can submit posts that exceed backend limits, receiving a generic error. This creates a frustrating UX loop where the user writes a long post, hits "Post", and gets a cryptic "Post failed, please try again later" error message.
- **Fix Context**: Add `maxLength: 500` to the TextField at line 180, or add explicit validation in `_submit()`:
  ```dart
  if (content.length > 500) {
    AppFeedback.error(context, l10n.postContentTooLong);
    return;
  }
  ```
  Also update the character count to show `'$count/500'` format.

---

## P2 -- Important (SHOULD fix for launch quality)

### [F-009] node_detail_sheet.dart: Deprecated withOpacity usage

- **Severity**: P2 (Important)
- **File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 1556, 1558
- **Description**: Two calls to `.withOpacity()` which is deprecated in current Flutter. Should use `.withValues(alpha: x)` instead.
  ```dart
  color: DS.warning.withOpacity(0.06),   // line 1556
  border: Border.all(color: DS.warning.withOpacity(0.15)),  // line 1558
  ```
- **Impact**: Will become compilation errors in future Flutter stable releases. Currently generates deprecation warnings.
- **Fix Context**: Replace with:
  ```dart
  color: DS.warning.withValues(alpha: 0.06),
  border: Border.all(color: DS.warning.withValues(alpha: 0.15)),
  ```

---

### [F-010] Community screens: ElevatedButton used instead of design system buttons

- **Severity**: P2 (Important)
- **File**:
  - `blocked_users_screen.dart` line 62 -- retry button
  - `skill_management_screen.dart` lines 528, 627 -- action buttons
  - `agent_team_sheet.dart` line 212 -- team action button
  - `interactive_decay_timeline.dart` lines 324, 346 -- timeline action buttons
- **Description**: These screens use raw `ElevatedButton` instead of the design system's `SparkleButton.primary` or `SparkleButton.secondary`. The design system provides `SparkleButton` with consistent theming, border radius, typography, and motion tokens.
- **Impact**: Visual inconsistency with the rest of the app. These buttons will not follow the Sparkle design language (colors, typography, animation).
- **Fix Context**: Replace `ElevatedButton` with `SparkleButton.primary(label: ..., onPressed: ...)` or `SparkleButton.secondary(...)`.

---

### [F-011] Scaffold bare AppBar transparent backgrounds -- visual inconsistency

- **Severity**: P2 (Important)
- **File**: Multiple screens set `backgroundColor: Colors.transparent` and `elevation: 0` on AppBar:
  - `learning_insights_overview_screen.dart` line 85
  - `learning_forecast_screen.dart` line 102
  - `directive_audit_screen.dart` line 40
  - `growth_chronicle_page.dart` line 26
  - `learning_dashboard_page.dart` line 28
  - `dashboard_screen.dart` lines 954, 1058, 1435, 3248
- **Description**: While some screens use `SparklePageScaffold` which provides consistent theming, others use raw `Scaffold` with manually set transparent AppBars. This creates inconsistency in how the status bar and navigation bar area looks across screens.
- **Impact**: Visual inconsistency. Some screens have blurred/frosted AppBar backgrounds while others are fully transparent, causing the content to bleed through differently.
- **Fix Context**: Standardize on `SparklePageScaffold` for all screens, or at minimum ensure consistent AppBar theming through the theme extension.

---

### [F-012] Notification list screen uses inline i18n for all strings

- **Severity**: P2 (Important)
- **File**: `mobile/lib/features/home/presentation/screens/notification_list_screen.dart`
- **Description**: The entire notification screen uses `I18nService.instance.isChinese` for its title ("Notifications"), error message ("Failed to load notifications"), and presumably all other strings, rather than using `context.l10n`.
- **Impact**: Notification strings cannot be audited for completeness in the ARB pipeline.
- **Fix Context**: Migrate all strings to ARB keys with proper `context.l10n` calls.

---

### [F-013] Traits coldstart questionnaire: inline i18n for "Tap to expand/collapse"

- **Severity**: P2 (Important)
- **File**: `mobile/lib/features/user/presentation/widgets/traits_coldstart_questionnaire.dart` line 50
- **Description**: `zh ? '点击展开/收起' : 'Tap to expand/collapse'` -- this is the only inline string in an otherwise well-l10n'd widget (the rest uses `context.l10n.userTraitsColdstart`, `context.l10n.userTraitsColdstartHint`, `context.l10n.userSkip`, `context.l10n.userSave`, `context.l10n.userSubmitting`).
- **Impact**: Inconsistency within the same widget. This specific hint string is not in the ARB pipeline.
- **Fix Context**: Add `userTraitsToggleHint` to both ARB files and use `context.l10n.userTraitsToggleHint`.

---

### [F-014] node_detail_sheet.dart: Inline i18n for review prompt text

- **Severity**: P2 (Important)
- **File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` lines 179-181
- **Description**: The review prompt sent to chat uses inline i18n:
  ```dart
  'prompt': I18nService.instance.isChinese
      ? '带我复习「$label」。请先基于这个知识节点定位我最该补的薄弱点，再给我一组短练习。'
      : 'Help me review "$label". First identify the weakest point around this knowledge node, then give me a short practice set.',
  ```
  This is a user-visible string sent as a chat prompt that bypasses the l10n system.
- **Impact**: The prompt text cannot be maintained through the ARB pipeline. If the prompt format changes, it must be found by grep rather than through a structured key.
- **Fix Context**: Add ARB keys like `galaxyNodeReviewPrompt` with a `{label}` parameter.

---

## P3 -- Minor (NICE to fix)

### [F-015] Unused element warning for _attachmentChipLabel, _attachmentStatusIcon, _attachmentStatusColor in chat_screen.dart

- **Severity**: P3 (Minor)
- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart` lines 2828, 2850, 2864
- **Description**: Three helper methods (`_attachmentChipLabel`, `_attachmentStatusIcon`, `_attachmentStatusColor`) are defined but never called. These appear to be leftover from a previous attachment feature that was refactored or removed.
- **Impact**: Dead code increases file size (chat_screen.dart is already 3,850 lines) and adds maintenance confusion.
- **Fix Context**: Remove the three unused methods if they are truly dead code. If they are planned for future use, add a `// TODO:` comment.

---

### [F-016] Unused field _newMessageDividerBeforeId and unused method _messageKeyFor in chat_screen.dart

- **Severity**: P3 (Minor)
- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart` lines 189, 833
- **Description**: `_newMessageDividerBeforeId` (field at line 189) is set but never read. `_messageKeyFor` (method at line 833) is defined but never called. Both were part of the original message rendering logic that may have been affected by the broken refactor.
- **Impact**: Dead code in an already massive file. Could indicate incomplete feature work.
- **Fix Context**: Remove if confirmed unused. The `_messageKeyFor` may be needed once the itemBuilder is fixed (it was previously used in the message Column key: `key: _messageKeyFor(message.id)`).

---

### [F-017] comment_bottom_sheet.dart: Missing generic type arguments on API calls

- **Severity**: P3 (Minor)
- **File**: `mobile/lib/features/community/presentation/widgets/comment_bottom_sheet.dart` lines 71, 81, 101, 125
- **Description**: API calls in the comment bottom sheet lack explicit generic type arguments:
  - Line 71: `get(...)` without type argument
  - Line 81: `Map` without type arguments (`Map<dynamic, dynamic>`)
  - Line 101: `post(...)` without type argument
  - Line 125: `delete(...)` without type argument

- **Impact**: Reduced type safety. Could lead to runtime type errors if API response format changes.
- **Fix Context**: Add explicit type arguments:
  ```dart
  _apiClient.get<Map<String, dynamic>>(...)
  Map<String, dynamic>.from(...)
  _apiClient.post<Map<String, dynamic>>(...)
  _apiClient.delete<void>(...)
  ```

---

### [F-018] Raw Colors.white usage in openclaw_connection_panel.dart

- **Severity**: P3 (Minor)
- **File**: `mobile/lib/features/settings/presentation/widgets/openclaw_connection_panel.dart` line 1133
- **Description**: Direct use of `Colors.white` instead of a design token. In dark mode, hardcoded white can look harsh.
- **Impact**: Minor visual inconsistency with the design system.
- **Fix Context**: Replace with `DS.neutral0` or `context.sparkleColors.neutral0` depending on the intended semantics.

---

## Summary Table

| ID | Severity | File | Description |
|----|----------|------|-------------|
| F-001 | **P0** | `chat_screen.dart` | 42 compilation errors -- broken itemBuilder refactor (undefined `ctx`, `message`, `showEnvelopeIndicator`) |
| F-002 | **P0** | `chat_screen.dart` | Missing `AuroraCoreSessionResumeBanner` removed during refactor |
| F-003 | **P1** | 69 files | 622 inline zh/en ternary strings bypassing ARB l10n system |
| F-004 | **P1** | Multiple | 134 analyzer warnings (unused code, deprecated APIs, type inference failures) |
| F-005 | **P1** | Multiple | 358 `debugPrint` statements in production code |
| F-006 | **P1** | `dashboard_screen.dart` + others | 16+ hardcoded route paths instead of named route constants |
| F-007 | **P1** | Multiple | Mixed i18n patterns (I18nService vs context.l10n) within same files |
| F-008 | **P1** | `create_post_screen.dart` | Missing 500-char max-length enforcement on post content TextField |
| F-009 | P2 | `node_detail_sheet.dart` | Deprecated `withOpacity` usage (lines 1556, 1558) |
| F-010 | P2 | 5 files | Raw `ElevatedButton` instead of design system `SparkleButton` |
| F-011 | P2 | 6 screens | Inconsistent AppBar theming (transparent vs SparklePageScaffold) |
| F-012 | P2 | `notification_list_screen.dart` | All strings use inline i18n instead of ARB |
| F-013 | P2 | `traits_coldstart_questionnaire.dart` | Single inline string in otherwise l10n'd widget |
| F-014 | P2 | `node_detail_sheet.dart` | Inline i18n for review prompt text sent to chat |
| F-015 | P3 | `chat_screen.dart` | 3 unused helper methods (_attachmentChipLabel etc.) |
| F-016 | P3 | `chat_screen.dart` | Unused field _newMessageDividerBeforeId and method _messageKeyFor |
| F-017 | P3 | `comment_bottom_sheet.dart` | Missing generic type arguments on API calls |
| F-018 | P3 | `openclaw_connection_panel.dart` | Raw Colors.white instead of design token |

---

## Recommended Fix Priority

1. **Immediate** (blocks all other work): Revert `chat_screen.dart` to the committed version (`git checkout HEAD -- mobile/lib/features/chat/presentation/screens/chat_screen.dart`) and re-apply only the intended layout changes without breaking the itemBuilder.
2. **Before launch**: Address F-003 (i18n migration) at minimum for user-facing screens (community, create post, notification, insights overview). Data model files can be post-launch.
3. **Before launch**: Fix F-008 (character limit enforcement) -- simple one-line fix.
4. **Before launch**: Fix F-009 (deprecated withOpacity) and F-004 (analyzer warnings) to ensure clean CI.
5. **Post-launch**: Address F-005 (debugPrint cleanup), F-006 (route constants), F-010 (button consistency), and remaining P2/P3 items.

---

## Test Verification Commands

```bash
# Verify compilation
cd mobile && flutter analyze 2>&1 | grep "error •" | grep -v "third_party_plugins/" | wc -l
# Expected: 0

# Count remaining inline i18n
grep -rn "I18nService\.instance\.isChinese" lib/features --include="*.dart" | wc -l
# Target: 0 (currently 622)

# Count warnings
cd mobile && flutter analyze 2>&1 | grep "warning •" | wc -l
# Target: <10 (currently 134)

# Verify debug prints
grep -rn "debugPrint\|print(" lib/features --include="*.dart" | wc -l
# Target: <20 (currently 358)
```
