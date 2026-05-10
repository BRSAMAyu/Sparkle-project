# Community & Accountability Flutter UI/UX Audit

**Date**: 2026-05-10
**Auditor**: Senior Mobile Engineer
**Scope**: `mobile/lib/features/community/` + cross-feature community widgets
**Severity**: P0 (crash/data-loss) > P1 (broken feature) > P2 (poor UX) > P3 (code quality)

---

## Summary

| Severity | Count |
|----------|-------|
| P0       | 0     |
| P1       | 5     |
| P2       | 14    |
| P3       | 12    |
| **Total**| **31**|

**Critical areas**: i18n bypass (hardcoded Chinese in non-l10n paths), null-safety crash in _FriendTile, provider memory leaks, DateFormat locale mismatch, missing error handling in repositories.

---

## P1: Broken Feature / Wrong Data

### [SEVERITY: P1] Hardcoded Chinese format strings in accountability_detail_screen bypass l10n
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart:955,975,1007,1027,1082`
**Category**: i18n
**Description**: The `_PendingPoliciesCard`, `_RecentReflectionsCard`, and `_ForesightHintCard` widgets contain hardcoded Chinese strings that bypass the l10n system. When the app is in English locale, these still render Chinese text like "条" (counter word) and "M月d日 HH:mm" (date format). The DateFormat pattern `M月d日 HH:mm` is a Chinese locale format used unconditionally.
**Context**:
```dart
// Line 975
count <= 0 ? context.l10n.accountabilityZeroItems : '$count 条',
// Line 955
count, DateFormat('M月d日 HH:mm').format(nextTriggerAt));
// Line 1027
count <= 0 ? context.l10n.accountabilityZeroItems : '$count 条',
```
**Suggested Fix**: Add l10n keys for count formatting (`accountabilityCountItems(count)`) and use locale-aware date format via `DateFormat.yMMMd().add_Hm().format()` or an l10n interpolation pattern. Never hardcode "条" or "M月d日".

### [SEVERITY: P1] Null crash in _FriendTile when displayName is empty
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart:697`
**Category**: bug
**Description**: `user.displayName[0].toUpperCase()` will throw a `RangeError` if `displayName` returns an empty string. The `UserBrief.displayName` getter returns `nickname ?? username`, and while username is required, there is no guarantee it is non-empty at runtime (e.g., malformed API response or demo data).
**Context**:
```dart
Text(
  user.displayName[0].toUpperCase(), // CRASH if displayName == ''
```
**Suggested Fix**: Add null/empty guard: `(user.displayName.isNotEmpty ? user.displayName[0] : '?').toUpperCase()`.

### [SEVERITY: P1] Null crash in _PartnershipCard on accountability_screen when partner is null
**File**: `mobile/lib/features/community/presentation/screens/accountability_screen.dart:131-132`
**Category**: bug
**Description**: `partner?.displayName ?? '?'` followed by `.substring(0, 1).toUpperCase()` -- the `?? '?'` ensures non-null, but if partner is null, `'?'` is fine. However, `partner?.displayName ?? '未知用户'` on line 147 also works. The actual issue is that `partner` itself can be null when `partnerGoal` is used without the correct context (the isInitiator logic on line 102-104 swaps initiator/partner, but if the server returns neither populated, partner is null).
**Context**:
```dart
final partner = isInitiator ? partnership.partner : partnership.initiator;
// partner can be null if neither is populated
```
**Suggested Fix**: Add explicit null handling for the `partner` variable and show a fallback state when both initiator and partner are null.

### [SEVERITY: P1] create_post_screen uses isChinese ternary instead of l10n ARB
**File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart:101-103,124-127,135,168-169,194-195,289`
**Category**: i18n
**Description**: The entire CreatePostScreen uses `I18nService.instance.isChinese` ternary pattern instead of going through ARB l10n. This means all strings are invisible to the localization toolchain, cannot be extracted by tools, and will not appear in translation files. Approximately 15+ user-facing strings are affected.
**Context**:
```dart
AppFeedback.error(context, I18nService.instance.isChinese
    ? '发布失败，请稍后重试'
    : 'Post failed, please try again later');
```
**Suggested Fix**: Move all strings to ARB files and use `context.l10n.xxx` pattern. Every string in create_post_screen.dart should go through AppLocalizations.

### [SEVERITY: P1] community_main_screen uses isChinese ternary instead of l10n ARB
**File**: `mobile/lib/features/community/presentation/screens/community_main_screen.dart:54-59,83,93`
**Category**: i18n
**Description**: Same issue as create_post_screen. The community main screen header and tab labels use `I18nService.instance.isChinese` instead of ARB l10n. The tab labels "伙伴"/"Partners", "动态"/"Feed", "群组"/"Groups" and the page title "社群"/"Community" are all hardcoded.
**Context**:
```dart
final tabLabels = [
  zh ? '伙伴' : 'Partners',
  zh ? '动态' : 'Feed',
  zh ? '群组' : 'Groups',
];
```
**Suggested Fix**: Add l10n keys `communityTabPartners`, `communityTabFeed`, `communityTabGroups`, `communityTitle`, `communitySubtitle` to ARB files and use `context.l10n.xxx`.

---

## P2: Poor UX / Missing Edge Case / Accessibility

### [SEVERITY: P2] myPartnershipsProvider lacks autoDispose, may leak memory
**File**: `mobile/lib/features/community/presentation/providers/accountability_provider.dart:7-12`
**Category**: state-mgmt
**Description**: `myPartnershipsProvider` is a `StateNotifierProvider` without `autoDispose`. When the user navigates away from the accountability screens, the provider and its data remain in memory indefinitely. Other similar list providers in the same file (e.g., `partnershipStatsProvider`, `partnershipTimelineProvider`) correctly use `autoDispose`.
**Context**:
```dart
final myPartnershipsProvider = StateNotifierProvider<
    MyPartnershipsNotifier, AsyncValue<List<AccountabilityPartnershipInfo>>>(
  (ref) => MyPartnershipsNotifier(
    ref.watch(accountabilityRepositoryProvider),
  ),
);
```
**Suggested Fix**: Add `.autoDispose` or evaluate whether the partnership list truly needs to persist across navigations. If so, document the rationale.

### [SEVERITY: P2] accountabilityHubProvider lacks autoDispose
**File**: `mobile/lib/features/community/presentation/providers/accountability_hub_provider.dart:7-12`
**Category**: state-mgmt
**Description**: Same issue as myPartnershipsProvider. The `AccountabilityHubNotifier` persists in memory even when no widget is watching it.
**Suggested Fix**: Add `autoDispose` unless there is a specific reason to keep the hub data warm at all times.

### [SEVERITY: P2] _DashboardView uses hardcoded numeric padding/margins instead of design tokens
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart:559,567,577-578,598-600,609,626,637`
**Category**: ux
**Description**: The `_DashboardHero` widget uses raw numeric values like `12`, `18`, `22`, `10`, `4`, `14`, `8` for padding, spacing, and dimensions instead of DS design tokens. This creates visual inconsistency and makes theme updates harder.
**Context**:
```dart
const SizedBox(width: 12),  // should be DS.spacing12
padding: const EdgeInsets.all(18),  // should be DS.spacing18 or similar
```
**Suggested Fix**: Replace all hardcoded numeric spacing values with DS tokens (e.g., `DS.spacing12`, `DS.spacing16`).

### [SEVERITY: P2] _HeroAction touch target too small (40x40 effective area)
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart:684-715`
**Category**: a11y
**Description**: The `_HeroAction` button has padding of `12x10` with 16px icon + text. The total height is approximately 36-40px, which is below the Material Design minimum touch target of 48x48. This affects accessibility, especially on smaller devices.
**Suggested Fix**: Add `minimumSize: MaterialTapTargetSize.shrinkWrap` with `SizedBox(height: 48)` wrapper or increase vertical padding to meet 48px minimum.

### [SEVERITY: P2] PartnersTab has no Semantics labels for accessibility
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart`
**Category**: a11y
**Description**: None of the tappable cards (`_PartnershipCard`, `_CommitmentCard`, `_ProgressCard`, `_RiskCard`, `_HelpableCard`, `_FriendTile`) have Semantics labels. Screen readers will announce generic container content instead of meaningful descriptions like "Partner Lena, 7 day streak, checked in today".
**Suggested Fix**: Wrap each tappable widget with `Semantics(button: true, label: '...')` providing a descriptive announcement string.

### [SEVERITY: P2] accountability_detail_screen DateFormat uses fixed locale pattern
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart:1249`
**Category**: i18n
**Description**: `DateFormat('MM-dd HH:mm')` is hardcoded. This will show "05-10 14:30" regardless of locale. The Chinese sections also use a different pattern `M月d日 HH:mm`. Neither pattern respects the device locale.
**Context**:
```dart
final dateStr = DateFormat('MM-dd HH:mm').format(checkin.createdAt);
```
**Suggested Fix**: Use `DateFormat.yMMMd(context.l10n.localeName).add_Hm()` or add a l10n interpolation for date formatting.

### [SEVERITY: P2] accountability_screen error handler exposes raw error to user
**File**: `mobile/lib/features/community/presentation/screens/accountability_screen.dart:50`
**Category**: ux
**Description**: The error state displays `'加载失败: $e'` / `'Load failed: $e'` which exposes raw exception messages to users. These may contain internal details, stack traces, or English text when the user expects Chinese.
**Context**:
```dart
Text(I18nService.instance.isChinese ? '加载失败: $e' : 'Load failed: $e', ...)
```
**Suggested Fix**: Show a generic user-friendly error message and log the raw error separately.

### [SEVERITY: P2] CommunityAccountabilityHubCard shows SizedBox.shrink on loading
**File**: `mobile/lib/features/experience/presentation/widgets/community_accountability_hub_card.dart:28`
**Category**: ux
**Description**: When the accountability hub data is loading, the widget returns `SizedBox.shrink()`, causing a sudden layout shift when data appears. There is no skeleton or loading indicator.
**Suggested Fix**: Show a shimmer/skeleton placeholder matching the card size to prevent layout jumps.

### [SEVERITY: P2] CommunityAccountabilityHubCard also uses isChinese ternary instead of l10n
**File**: `mobile/lib/features/experience/presentation/widgets/community_accountability_hub_card.dart:49,81-82,89-94,114,119`
**Category**: i18n
**Description**: The entire card uses `I18nService.instance.isChinese` for all user-visible strings, bypassing ARB l10n.
**Context**:
```dart
zh ? '目标责任空间' : 'Accountability space',
```
**Suggested Fix**: Use `context.l10n` with proper ARB keys.

### [SEVERITY: P2] community_accountability_hub_l10n.dart bypasses ARB l10n system entirely
**File**: `mobile/lib/features/community/presentation/l10n/community_accountability_hub_l10n.dart`
**Category**: i18n
**Description**: This file creates a custom extension on AppLocalizations using a private `_zh` flag instead of proper ARB key generation. This means 50+ strings are not tracked in ARB files, cannot be sent to translators, and won't be included in new locale additions. The pattern is inconsistent with the rest of the app.
**Suggested Fix**: Migrate all strings from this extension to the ARB files (`app_en.arb`, `app_zh.arb`) and regenerate localizations.

### [SEVERITY: P2] PartnersTab _PartnershipCard shows initiatorGoal for all partnerships regardless of role
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart:258`
**Category**: bug
**Description**: The partnership card always shows `partnership.initiatorGoal` as the subtitle text, even when the current user is the partner (not the initiator). This means users may see the other person's goal labeled as if it were their own.
**Context**:
```dart
Text(
  partnership.initiatorGoal, // always shows initiator's goal
```
**Suggested Fix**: Determine if the current user is the initiator and show the appropriate goal (similar to accountability_screen.dart logic at lines 105-107).

### [SEVERITY: P2] community_share_repository: rejectResource is client-side only, no server call
**File**: `mobile/lib/features/community/data/repositories/community_share_repository.dart:116-130`
**Category**: bug
**Description**: `rejectResource()` only records the rejection through the event stream and never calls a server endpoint. The TODO comment acknowledges the backend endpoint may not exist yet, but this means rejections are not persisted and have no effect on the recommendation algorithm in production.
**Context**:
```dart
// Server-side endpoint may not exist yet; record rejection through the
// event stream so it still influences personalization.
```
**Suggested Fix**: Either implement the server endpoint or add a clear user-facing indication that the rejection is only local.

### [SEVERITY: P2] accountability_repository static demo state is not thread-safe
**File**: `mobile/lib/features/community/data/repositories/accountability_repository.dart:48-49`
**Category**: state-mgmt
**Description**: `_demoPartnerships` and `_demoTimelineByPartnership` are static mutable fields that are read and modified from async methods without synchronization. While Dart is single-threaded, concurrent async operations could interleave, leading to inconsistent state (e.g., timeline added for a partnership that was just removed).
**Suggested Fix**: Consider making demo state management more robust, or at minimum add a comment documenting the single-thread assumption.

### [SEVERITY: P2] _PartnerAvatar in partners_tab uses "checked in" indicator for "online" status
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart:240,757-791`
**Category**: ux
**Description**: The `_PartnerAvatar` widget has an `isOnline` parameter but is passed `partnerCheckedIn` (whether the partner checked in today). This conflates "online right now" with "checked in today", showing a green online dot when the partner may not actually be online.
**Context**:
```dart
_PartnerAvatar(
  avatarUrl: partner?.avatarUrl,
  name: partner?.nickname ?? partner?.username ?? '?',
  isOnline: partnerCheckedIn, // Misleading: checked-in != online
),
```
**Suggested Fix**: Either pass the actual online status from UserBrief.status or rename the indicator to "checked in today" with a different visual treatment.

### [SEVERITY: P2] No pull-to-refresh on accountability_detail_screen
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
**Category**: ux
**Description**: The accountability detail screen has no pull-to-refresh mechanism. The only refresh option is the retry button on error state. After a check-in or nudge, the user must navigate away and back to see updated data.
**Suggested Fix**: Wrap the ListView in a `SparkleRefreshIndicator` and call `ref.invalidate(accountabilityDashboardProvider(widget.partnershipId))`.

---

## P3: Code Quality / Dead Code / Minor Improvement

### [SEVERITY: P3] AccountabilityCheckinSheet TextEditingController not guarded against widget unmount
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart:1455-1617`
**Category**: state-mgmt
**Description**: The `_submit()` method calls `setState` after an async gap (line 1614) with only an `if (mounted)` check. However, the controller could theoretically be used after dispose in edge cases where the bottom sheet is dismissed during the async operation.
**Suggested Fix**: The current pattern is acceptable but could be made more robust by checking `mounted` before accessing `_contentController.text`.

### [SEVERITY: P3] Unused import: intl in accountability_detail_screen
**File**: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart:6`
**Category**: dead-code
**Description**: `import 'package:intl/intl.dart'` is used, but the DateFormat usage is hardcoded rather than locale-aware. While technically used, the pattern should be refactored for proper l10n (see P2 findings).

### [SEVERITY: P3] community_model.dart has extremely large file (1971 lines)
**File**: `mobile/lib/features/community/data/models/community_model.dart`
**Category**: dead-code
**Description**: At nearly 2000 lines, this single model file contains 30+ model classes, enums, and helper functions. This violates single-responsibility and makes navigation difficult. Similar concerns apply to community_provider.dart (2184 lines) and mock_community_repository.dart (2422 lines).
**Suggested Fix**: Split into separate files by domain: `friendship_models.dart`, `group_models.dart`, `message_models.dart`, `shared_resource_models.dart`, etc.

### [SEVERITY: P3] mock_community_repository.dart is 2422 lines, exceeds maintainability threshold
**File**: `mobile/lib/features/community/data/repositories/mock_community_repository.dart`
**Category**: dead-code
**Description**: The mock repository is enormous, making it hard to maintain and slow to navigate. Demo data generation should ideally be in separate fixture files.
**Suggested Fix**: Extract demo data into separate fixture/data classes and keep the mock repository focused on behavior.

### [SEVERITY: P3] community_provider.dart at 2184 lines has too many providers in single file
**File**: `mobile/lib/features/community/presentation/providers/community_provider.dart`
**Category**: dead-code
**Description**: Contains 10+ providers, notifiers, and WebSocket handling logic. This makes it hard to find specific providers and increases merge conflict risk.
**Suggested Fix**: Split into separate files: `friends_provider.dart`, `group_provider.dart`, `chat_provider.dart`, `search_provider.dart`, etc.

### [SEVERITY: P3] AccountabilityRepository._extractApiError uses isChinese instead of l10n
**File**: `mobile/lib/features/community/data/repositories/accountability_repository.dart:23`
**Category**: i18n
**Description**: The fallback error message uses `I18nService.instance.isChinese` instead of a proper l10n key. While this is a repository layer (not presentation), the fallback messages are ultimately shown to users.
**Context**:
```dart
final fb = fallback ?? (I18nService.instance.isChinese ? '请求失败' : 'Request failed');
```
**Suggested Fix**: Consider returning structured error types and letting the presentation layer handle l10n, or use a centralized error message service.

### [SEVERITY: P3] AccountabilityScreen uses isChinese ternary instead of l10n
**File**: `mobile/lib/features/community/presentation/screens/accountability_screen.dart:35,50-51,53-54,64-65,106-107,147,163,167-168,205,218-219,244`
**Category**: i18n
**Description**: The accountability screen uses the `I18nService.instance.isChinese` pattern extensively instead of ARB l10n. While accountability_detail_screen.dart properly uses `context.l10n`, this screen does not.
**Suggested Fix**: Migrate all strings to ARB l10n using the `context.l10n` pattern.

### [SEVERITY: P3] PartnersTab _buildEmptyIfNeeded uses isChinese ternary
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart:163-174`
**Category**: i18n
**Description**: Empty state strings use `isChinese` ternary instead of l10n ARB.
**Suggested Fix**: Use `context.l10n` for all user-visible strings.

### [SEVERITY: P3] All PartnersTab subsections use isChinese ternary
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart:188-196,280-281,303-304,306-307,393,394-396,546,567,568,602,603,623-624,638,649-651`
**Category**: i18n
**Description**: Every section title and UI label in partners_tab.dart uses the `isChinese` pattern. This is a systemic issue across the entire file.
**Suggested Fix**: Batch-migrate all strings to ARB l10n.

### [SEVERITY: P3] accountability_invite_flow.dart utility file not audited but referenced
**File**: `mobile/lib/features/community/presentation/utils/accountability_invite_flow.dart`
**Category**: dead-code
**Description**: This utility is imported by accountability_screen.dart but was not included in the audit scope. It should be reviewed for the same i18n and error handling patterns.
**Suggested Fix**: Add to next audit cycle.

### [SEVERITY: P3] group_chat_bubble.dart has a TODO for i18n
**File**: `mobile/lib/features/community/presentation/widgets/group_chat_bubble.dart:193`
**Category**: i18n
**Description**: A TODO comment indicates an i18n bypass in the group chat bubble report action text.
**Context**:
```
.communityReport, // TODO: i18n - this is inside a Text widget already using style
```
**Suggested Fix**: Resolve the TODO by adding the string to ARB files.

### [SEVERITY: P3] community_agent_provider.dart has isChinese ternary in prompt generation
**File**: `mobile/lib/features/community/presentation/providers/community_agent_provider.dart:145-173,196-223,233-246,254-279`
**Category**: i18n
**Description**: The AI prompt generation functions use `I18nService.instance.isChinese` to construct Chinese or English prompts. While these are not user-visible strings (they are sent to the LLM), the pattern should be documented as intentional since it controls AI behavior language, not UI text.

---

## Cross-Cutting Concerns

### Systemic i18n Bypass

The community feature has two conflicting i18n patterns:
1. **Proper l10n**: `accountability_detail_screen.dart` uses `context.l10n` via ARB files
2. **Bypass pattern**: Most other files use `I18nService.instance.isChinese ? '中文' : 'English'`

This creates maintenance burden and ensures that translators working with ARB files cannot see the full set of user-facing strings. The following files are affected:
- `community_main_screen.dart`
- `accountability_screen.dart`
- `create_post_screen.dart`
- `partners_tab.dart`
- `community_accountability_hub_card.dart`
- `community_accountability_hub_l10n.dart` (custom extension bypasses ARB entirely)

**Recommendation**: Establish a single policy -- all user-visible strings must go through ARB l10n. Schedule a migration sprint.

### Missing Empty States

Several screens lack proper empty states or loading-to-empty transitions:
- `CommunityAccountabilityHubCard` shows `SizedBox.shrink()` during loading (layout shift)
- `_PartnershipCard` shows `initiatorGoal` regardless of user role (semantic confusion)
- PartnersTab empty state only shows when ALL data sources are empty (good), but individual sections have no empty messages

### Accessibility Gaps

- No Semantics labels on any tappable cards in PartnersTab
- Touch targets below 48px minimum in `_HeroAction` buttons
- No screen reader support for streak counts, check-in status, or progress percentages
- Color-only indicators (green/gray dots for check-in status) without text alternatives for color-blind users
