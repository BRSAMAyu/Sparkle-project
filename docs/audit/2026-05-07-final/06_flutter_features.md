# Flutter Features Audit (Non-Chat)

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Flutter features codebase (717 source files across 41 feature directories) demonstrates solid engineering overall: controllers are consistently disposed, design system tokens are used uniformly, Riverpod providers follow proper patterns, and accessibility semantics are present on interactive elements. The primary concern is a **TextEditingController leak in task_chat_panel.dart** (a widget-level field never disposed) and two dialog-scoped controllers in plan_detail_screen.dart and friend_profile_screen.dart that are not disposed after dialog dismissal. Secondary concerns include hardcoded Chinese strings in share cards that bypass the I18nService pattern used elsewhere in the same files, and a raw exception string leaked to users in create_post_screen.dart.

## Critical Issues (P0)

None identified. No data corruption, security vulnerabilities, or crash-inducing defects found.

## High Issues (P1)

### P1-01: TextEditingController never disposed in TaskChatPanel
- **File**: `mobile/lib/features/task/presentation/widgets/task_chat_panel.dart:31`
- **Detail**: `final TextEditingController _controller = TextEditingController();` is declared as a field on `_TaskChatPanelState` (line 31). The class has `initState` (line 36) but **no `dispose` override**. Every time a `TaskChatPanel` widget is created and destroyed, the controller leaks.
- **Fix**: Add `@override void dispose() { _controller.dispose(); super.dispose(); }` to `_TaskChatPanelState`.

### P1-02: Dialog-scoped TextEditingController leaks in plan_detail_screen.dart
- **File**: `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart:2533,2633`
- **Detail**: Two dialog methods (`_createPhaseDialog` at line 2533 and `_completePhaseDialog` at line 2633) create local `TextEditingController` instances that are never disposed after the dialog closes. While the GC will eventually collect them, the framework attaches listeners to these controllers that may not be cleaned up promptly.
- **Fix**: Call `controller.dispose()` and `reflectionController.dispose()` after reading the final text values (after the dialog returns).

### P1-03: Dialog-scoped TextEditingController leak in friend_profile_screen.dart
- **File**: `mobile/lib/features/community/presentation/screens/friend_profile_screen.dart:270`
- **Detail**: `_showAccountabilityInvite` creates a local `TextEditingController goalController` (line 270) used in a dialog, but it is never disposed after the dialog completes.
- **Fix**: Dispose `goalController` after reading the text value (after line 330).

### P1-04: Raw exception message exposed to user in create_post_screen.dart
- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart:92`
- **Detail**: `AppFeedback.error(context, I18nService.instance.isChinese ? '发布失败：$e' : 'Post failed: $e');` directly concatenates the raw exception `e` into the user-facing error message. This can leak internal server details, stack traces, or implementation specifics to the user.
- **Fix**: Replace with a generic user-facing error message (e.g., `'发布失败，请稍后重试'` / `'Post failed, please try again later'`). Log the exception internally for debugging.

## Medium Issues (P2)

### P2-01: Hardcoded Chinese strings in node_share_card.dart bypass I18nService
- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/node_share_card.dart:90,288,295`
- **Detail**: The compact card at line 90 has `'掌握度 ${(_masteryPercent!)}%'` with no I18nService wrapper. The full card at line 288 has `'${learningTime}分钟'` and line 295 has `'$connections个'` -- all hardcoded Chinese without `I18nService.instance.isChinese` guard. The same file uses `context.l10n.*` and `S.*` constants elsewhere (lines 191, 287, 294, 324-327), making this inconsistent.
- **Fix**: Wrap all three with `I18nService.instance.isChinese ? '掌握度 ...' : 'Mastery ...%'` pattern, or use ARB keys.

### P2-02: Hardcoded Chinese default value in achievement_share_card.dart
- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/achievement_share_card.dart:103`
- **Detail**: `metadata['rarity']?.toString() ?? '荣耀'` -- the fallback `'荣耀'` is hardcoded Chinese. English-speaking users would see Chinese text when no rarity metadata is provided.
- **Fix**: Use `I18nService.instance.isChinese ? '荣耀' : 'Glorious'` or an ARB key.

### P2-03: Hardcoded Chinese strings in capsule_share_card.dart
- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/capsule_share_card.dart:216,297`
- **Detail**: Line 216: `'${wordCount}字'` (should be `'words'` in English). Line 297: `'深度 Lv.$depth'` (should be `'Depth Lv.$depth'` in English). Both are guarded by `I18nService.instance.isChinese` ternaries, so they are functionally correct but the capsule type icons at lines 270-275 match Chinese strings (`'思考'`, `'反思'`, `'灵感'`, `'总结'`) without I18n -- these are server-provided values used in a switch statement, so they correctly handle both languages.

### P2-04: Hardcoded Chinese strings in task_share_card.dart
- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/task_share_card.dart:93,221-240,313-317`
- **Detail**: Multiple instances of `I18nService.instance.isChinese ? '...' : '...'` are present and functional, but the pattern is used inconsistently. Lines 221-240 use it for stat labels (Duration, Points, Streak) which is correct. Lines 313-317 use it for relative time which is correct. Line 93 compact card `'完成 · ${duration}分钟'` is correctly I18n-wrapped.

### P2-05: Multiple screens use `_t(zh, en)` helper instead of ARB keys in goal_creation_wizard_screen.dart
- **File**: `mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart` (multiple lines)
- **Detail**: The entire wizard screen uses a private `_t(String zh, String en)` helper function rather than ARB-based l10n. While functional per the project's bilingual strategy, this means all ~30+ user-facing strings in this screen cannot be updated via ARB files without code changes. This applies to step labels (line 73-77), button labels, error messages, and section titles.
- **Scope**: Also applies to `task_protocol_panel.dart` (lines 28-29, 98, 154, 175, 201), which uses `static String _t()`.

### P2-06: Community main screen tab labels use inline I18n instead of ARB
- **File**: `mobile/lib/features/community/presentation/screens/community_main_screen.dart:56-58,83,93`
- **Detail**: Tab labels `'伙伴'/'Partners'`, `'动态'/'Feed'`, `'群组'/'Groups'`, screen title `'社群'/'Community'`, and subtitle `'和伙伴一起成长'/'Grow together with partners'` all use `I18nService.instance.isChinese` ternaries rather than ARB keys.

### P2-07: Milestone celebration badge labels hardcoded in English only
- **File**: `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart:114-118`
- **Detail**: `badgeLabel` getter returns `'Galaxy Explorer'`, `'Sprint Veteran'`, `'Core Sparkle User'` -- English-only hardcoded strings with no Chinese translation path. Chinese users will see English badge labels.

### P2-08: Error messages in community screens include raw exception via l10n template
- **Files**:
  - `mobile/lib/features/community/presentation/screens/group_detail_screen.dart:421,598`
  - `mobile/lib/features/community/presentation/screens/group_members_screen.dart:710,806,859`
  - `mobile/lib/features/community/presentation/screens/friends_screen.dart:251,349,821`
  - `mobile/lib/features/community/presentation/screens/friend_profile_screen.dart:347`
- **Detail**: Pattern `context.l10n.xxxFailed(e.toString())` passes raw exception text through localized templates. While the template string itself is in ARB, the exception content may contain server internals. This is partially mitigated by the l10n template but the exception detail is still exposed.

## Low Issues (P3)

### P3-01: EvidenceQuickPeek overlay uses 4-second timer without cancellation mechanism
- **File**: `mobile/lib/features/memory/presentation/widgets/memory_evidence_badge.dart:109`
- **Detail**: `Future.delayed(const Duration(seconds: 4), ...)` runs on a global timer. If the user rapidly triggers multiple peeks, multiple timers and overlay entries coexist. The `mounted` check protects against double-removal, but there is no mechanism to cancel the timer if the overlay is manually dismissed before 4 seconds.
- **Risk**: Low. In practice, users rarely trigger rapid sequential peeks, and `entry.mounted` guards against double-removal crashes.

### P3-02: `_segmentIntersectsRect` in star_map_painter.dart uses conservative bounding-box check
- **File**: `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart:2492-2498`
- **Detail**: `Rect.fromPoints(a, b).overlaps(rect)` checks bounding-box overlap rather than true line-segment intersection. This may over-draw edges whose bounding box overlaps the viewport but the actual line does not.
- **Risk**: Very low. This is a performance optimization for viewport culling; over-drawing is preferable to missing edges. The visual impact is negligible.

### P3-03: Legal document screen has hardcoded date and version string
- **File**: `mobile/lib/features/auth/presentation/screens/legal_document_screen.dart:58,66`
- **Detail**: `'当前版本：v1'` / `'Current version: v1'` and the last-updated date `'2026年5月1日'` are hardcoded via I18nService rather than ARB keys. These would need code changes to update.

### P3-04: `create_post_screen.dart` has dead-code conditional on icon color
- **File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart:178-179,188-189`
- **Detail**: Both `SparkleIconButton` widgets use identical color logic: `color: _selectedImage != null ? DS.brandPrimary : DS.brandPrimary`. The ternary is redundant since both branches return the same value.

### P3-05: Community WebSocket service does not implement heartbeat/ping
- **File**: `mobile/lib/features/community/data/services/community_websocket_service.dart`
- **Detail**: The service connects to WebSocket endpoints but does not send periodic ping frames or implement application-level heartbeats. Idle connections may be dropped by intermediate proxies without the client detecting it until the next send attempt. The reconnection mechanism (with exponential backoff) mitigates this.
- **Risk**: Low. The reconnection logic handles dropped connections gracefully.

## Positive Findings

1. **Consistent dispose patterns**: All StatefulWidget classes that declare controller fields (TextEditingController, TabController, AnimationController, PageController, ScrollController) properly override `dispose()` to clean up. The single exception (task_chat_panel.dart) is the only confirmed leak.

2. **Design system adherence**: All audited files consistently use `DS.*` tokens for colors, spacing, border radius, font sizes, and font weights. No raw `Colors.*` or hardcoded numeric values found in presentation code.

3. **Star map painter quality**: The `StarMapPainter` (2785 lines) is an exceptionally well-structured `CustomPainter` with:
   - Proper LOD (Level of Detail) system with 5 levels
   - Node and edge budgets to cap draw calls
   - Picture caching for backdrop and parallax star layers
   - Spatial index for viewport culling
   - Label caching with LRU eviction (maxEntries = 600)
   - `shouldRepaint` covers all 27 state variables
   - Timeline instrumentation for performance profiling
   - `performanceDegraded` mode that reduces particle counts and disables effects

4. **Accessibility semantics present**: Interactive elements include `Semantics` widgets with proper labels (e.g., evidence cards line 343-344, goal wizard line 86-92, onboarding page dots). The milestone celebration screen respects `reduceMotion` (line 172-174).

5. **Riverpod patterns are clean**: Provider usage follows recommended patterns -- `ref.watch` for UI, `ref.read` for callbacks, `ref.listenManual` for side effects, `ref.invalidate` for refresh. Error states are properly surfaced through `AsyncValue.when()`.

6. **UnsavedChangesGuard**: Applied to form screens (create_post_screen, add_error_screen, create_library_screen) to prevent accidental data loss.

7. **Share card factory pattern**: All four share card factories (Capsule, Node, Plan, Task) follow a consistent `fromPayload` factory pattern that gracefully handles missing/optional metadata with null-safe extraction.

8. **Onboarding lifecycle management**: `InteractiveOnboardingScreen` correctly persists/restores page state via SharedPreferences, disposes its `PageController`, and guards all async operations with `mounted` checks.

9. **Community WebSocket service**: Proper resource cleanup in `dispose()` method -- cancels reconnect timers, cancels subscriptions, closes channels, closes stream controllers. Reconnection uses exponential backoff with max attempts cap. Message deduplication via nonce-based cache with size limit.

10. **Proper `mounted` guards**: All async operations across audited files check `if (!mounted) return;` before calling `setState`, preventing the common Flutter "setState after dispose" exception.

## Files Audited

### Share Cards (explicitly requested)
- `mobile/lib/features/community/presentation/widgets/share_cards/capsule_share_card.dart`
- `mobile/lib/features/community/presentation/widgets/share_cards/node_share_card.dart`
- `mobile/lib/features/community/presentation/widgets/share_cards/plan_share_card.dart`
- `mobile/lib/features/community/presentation/widgets/share_cards/task_share_card.dart`
- `mobile/lib/features/community/presentation/widgets/share_cards/achievement_share_card.dart`

### Galaxy (explicitly requested)
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart`

### Memory (explicitly requested)
- `mobile/lib/features/memory/presentation/widgets/evidence_cards.dart`
- `mobile/lib/features/memory/presentation/widgets/evidence_drawer.dart`
- `mobile/lib/features/memory/presentation/widgets/memory_evidence_badge.dart`

### Plan
- `mobile/lib/features/plan/presentation/widgets/plan_card.dart`
- `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`
- `mobile/lib/features/plan/presentation/screens/plan_create_screen.dart`
- `mobile/lib/features/plan/presentation/screens/learning_portfolio_screen.dart`

### Task
- `mobile/lib/features/task/presentation/widgets/task_protocol_panel.dart`
- `mobile/lib/features/task/presentation/widgets/task_chat_panel.dart`
- `mobile/lib/features/task/presentation/screens/task_list_screen.dart`
- `mobile/lib/features/task/presentation/widgets/task_feedback_dialog.dart`

### Community
- `mobile/lib/features/community/presentation/screens/community_main_screen.dart`
- `mobile/lib/features/community/presentation/screens/create_post_screen.dart`
- `mobile/lib/features/community/presentation/screens/friend_profile_screen.dart`
- `mobile/lib/features/community/presentation/screens/friends_screen.dart`
- `mobile/lib/features/community/presentation/screens/group_detail_screen.dart`
- `mobile/lib/features/community/presentation/screens/group_members_screen.dart`
- `mobile/lib/features/community/data/services/community_websocket_service.dart`

### Goal
- `mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart`
- `mobile/lib/features/goal/presentation/pages/goal_detail_page.dart`
- `mobile/lib/features/goal/presentation/widgets/goal_intent_input.dart`

### Onboarding
- `mobile/lib/features/onboarding/presentation/screens/interactive_onboarding_screen.dart`
- `mobile/lib/features/onboarding/presentation/widgets/architecture_animation.dart`

### Achievement
- `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart`

### User (Profile)
- `mobile/lib/features/user/presentation/screens/edit_profile_screen.dart`

### Auth
- `mobile/lib/features/auth/presentation/screens/legal_document_screen.dart`

### Error Book
- `mobile/lib/features/error_book/presentation/screens/add_error_screen.dart`

### Pattern scans (grep-based, all 717 files)
- All files with `TextEditingController`, `AnimationController`, `ScrollController`, `StreamSubscription` -- checked for paired `dispose()`
- All files with `initState` -- checked for corresponding `dispose`
- All files in share_cards/ -- checked for hardcoded strings vs I18nService/ARB usage
- All files in memory/ -- checked for hardcoded strings
- All files in community/presentation/screens/ -- checked for raw error message exposure
