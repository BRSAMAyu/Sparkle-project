# Card System Frontend UI/UX Audit

> **Date**: 2026-05-09
> **Auditor**: Senior Flutter/UI Auditor (automated)
> **Scope**: ALL card-related Flutter code in `mobile/lib/`
> **Files audited**: 97+ card-related Dart files

---

## Executive Summary

The Sparkle card system is extensive with ~97 card-related widget files spanning task cards, plan cards, achievement cards, share cards, community feed cards, chat action cards, dashboard cards, and the entity card payload pipeline. The system demonstrates strong design system usage overall but has several categories of issues:

- **18 P1 issues** (broken feature / crash risk)
- **29 P2 issues** (degraded UX)
- **24 P3 issues** (polish / consistency)
- **15 P3-i18n issues** (hardcoded strings)

Key risk areas: null safety in `FeedPostCard`, hardcoded strings bypassing l10n across many card widgets, inconsistent i18n strategy (three different patterns used), and the `entity_card_payloads.dart` fallback using hardcoded Chinese.

---

## 1. Null Safety & Crash Risks

### 1.1 [P0] FeedPostCard: Empty username causes RangeError crash

- **File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:83`
- **Category**: Data/Logic
- **Description**: `post.user.username[0].toUpperCase()` will crash with a `RangeError` if `username` is an empty string. The `username` field is typed as `String` (non-nullable), but nothing prevents it from being empty.
- **Current behavior**: If a user's username is `""`, the app crashes with an unhandled `RangeError`.
- **Expected behavior**: Gracefully handle empty usernames with a fallback (e.g., "?").
- **Fix approach**:
  ```dart
  (post.user.username.isNotEmpty ? post.user.username[0] : '?').toUpperCase()
  ```

### 1.2 [P1] entity_card_payloads: Hardcoded Chinese fallback for unknown entity type

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:860`
- **Category**: i18n
- **Description**: The `_buildLegacyEntityMap` fallback for unknown entity types uses a hardcoded Chinese string `'未命名实体'`:
  ```dart
  'title': _asString(raw['title']) ?? '未命名实体',
  ```
- **Current behavior**: English-locale users see Chinese text for unknown entities.
- **Expected behavior**: Use i18n or at minimum an English fallback like "Unnamed Entity".
- **Fix approach**: Replace with `_asString(raw['title']) ?? 'Unnamed Entity'` or use a runtime i18n call.

### 1.3 [P1] entity_card_payloads: `_fromEntityMap` throws on null `_cachedPayload`

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:34-38` (PlanCardPayload caching in `plan_card.dart:34-38`)
- **Category**: Data/Logic
- **Description**: `PlanCardPayload.get _payload` uses `identical()` check and force-unwraps `_cachedPayload!`. If `identical()` returns `false` on the first call (which it can for map literals), and `fromMap` throws, the cached payload is `null` and the `!` crashes.
- **Current behavior**: Potential null assertion crash if `PlanCardPayload.fromMap()` throws.
- **Expected behavior**: Handle the null case gracefully.
- **Fix approach**: Use null-aware access or try-catch around `fromMap`.

### 1.4 [P1] taskModelFromEntityPayload: Silently swallows all errors

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:440`
- **Category**: Data/Logic
- **Description**: The `catch (_)` block returns `null` silently, making it impossible to debug malformed payloads. The caller in `action_card.dart:237` throws `StateError('Unable to normalize task payload')` but provides no diagnostic information.
- **Current behavior**: Malformed task payloads silently fail, and the error state shows no diagnostic.
- **Expected behavior**: At minimum log the error, or include the original data in the error.
- **Fix approach**: `catch (e) { debugPrint('taskModelFromEntityPayload error: $e'); return null; }`

---

## 2. i18n Violations (Hardcoded Strings)

### 2.1 [P2] TaskCard: Hardcoded English strings in `_SourceContextChip`

- **File**: `mobile/lib/features/task/presentation/widgets/task_card.dart:886`
- **Category**: i18n
- **Description**: Two hardcoded English strings:
  ```dart
  hasGuide ? 'Linked to knowledge source' : 'Knowledge-linked task',
  ```
- **Current behavior**: Chinese users see English text for the knowledge link chip.
- **Expected behavior**: Use `context.l10n` for both strings.
- **Fix approach**: Add ARB keys and use `context.l10n.taskLinkedToKnowledge` / `context.l10n.taskKnowledgeLinkedTask`.

### 2.2 [P2] TaskCard: Hardcoded English type labels in `_typeLabel`

- **File**: `mobile/lib/features/task/presentation/widgets/task_card.dart:828-843`
- **Category**: i18n
- **Description**: All task type labels are hardcoded English: `'Learning'`, `'Training'`, `'Fix'`, `'Reflection'`, `'Social'`, `'Plan'`, `'OCR'`.
- **Current behavior**: Chinese users see English task type pills.
- **Expected behavior**: Use `context.l10n` for each type label.
- **Fix approach**: Pass `BuildContext` and use existing l10n keys like `context.l10n.taskTypeLearning`, etc.

### 2.3 [P2] FeedPostCard: Hardcoded 'Posting...' string

- **File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:142`
- **Category**: i18n
- **Description**: The optimistic posting indicator uses a hardcoded English string:
  ```dart
  'Posting...',
  ```
- **Current behavior**: Chinese users see English "Posting..." text.
- **Expected behavior**: Use `context.l10n.communityPosting` or similar.
- **Fix approach**: Add ARB key and use l10n.

### 2.4 [P2] SharedResourceCard: All user-facing strings use isChinese ternary

- **File**: `mobile/lib/features/community/presentation/widgets/shared_resource_card.dart:32,51,69,108,135,145,155,212,219`
- **Category**: i18n
- **Description**: Nine separate user-facing strings use `isChinese ? '中文' : 'English'` pattern instead of ARB l10n. Strings include: '共享资源', 'Shared Resource', '分享者', 'By', '采纳并加入我的计划', 'Adopt into my plan', '精选', 'Featured', '推荐', 'Recommended', '新手友好', 'Beginner-friendly', etc.
- **Current behavior**: Strings are not tracked in ARB files; translations will be missed if a third language is added.
- **Expected behavior**: All user-facing strings should use `AppLocalizations.of(context)!.xxx` or `context.l10n.xxx`.
- **Fix approach**: Create ARB keys for each string and replace the ternary pattern.

### 2.5 [P2] CardPickerSheet: Five hardcoded English strings

- **File**: `mobile/lib/shared/widgets/card_picker_sheet.dart:28,42,74,100,124,136,148`
- **Category**: i18n
- **Description**: Multiple hardcoded strings: `'Unassigned'`, `'Other'`, `'Search cards or plans'`, `'No results for "$_query"'`, `'Clear search'`, `'Detach from current plan'`.
- **Current behavior**: Not localizable.
- **Expected behavior**: Use l10n for all user-facing strings.
- **Fix approach**: Add ARB keys for each and use `context.l10n`.

### 2.6 [P2] DashboardCardSection: Hardcoded Chinese/English summary

- **File**: `mobile/lib/features/home/presentation/widgets/dashboard_card_section.dart:57-59`
- **Category**: i18n
- **Description**: Summary text uses inline ternary:
  ```dart
  Localizations.localeOf(context)...startsWith('zh')
    ? '保留可定制区，把功能模块放在下半屏。'
    : 'Keep customization in the lower workspace...'
  ```
- **Current behavior**: Bypasses ARB system.
- **Expected behavior**: Use ARB key.
- **Fix approach**: Add `dashboardWorkspaceSummary` to ARB files.

### 2.7 [P2] TaskBoardCard: Side panel descriptions use isChinese ternary

- **File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart:226-280`
- **Category**: i18n
- **Description**: Six side panel description strings use `isChinese ? '中文' : 'English'` pattern: '任务按到期日期分组显示', 'Tasks are grouped by due date.', etc. Also the summary label at line 291-294:
  ```dart
  isChinese
    ? '今日${summary.totalCount}项·已完成${summary.completedCount}'
    : '${summary.completedCount} of ${summary.totalCount} completed today'
  ```
- **Current behavior**: Not tracked in ARB.
- **Expected behavior**: Use ARB l10n.
- **Fix approach**: Add ARB keys and use `context.l10n`.

### 2.8 [P2] AchievementShareCard: Hardcoded '荣耀' and 'Source' strings

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/achievement_share_card.dart:91,103`
- **Category**: i18n
- **Description**: Uses `I18nService.instance.isChinese ? '来源' : 'Source'` and fallback `'荣耀'` instead of ARB keys.
- **Current behavior**: Not tracked in ARB.
- **Expected behavior**: Use `S.communityShareSource` and `S.communityShareGlory` or similar.
- **Fix approach**: Add ARB keys.

### 2.9 [P2] CapsuleShareCard: Hardcoded capsule type matching with Chinese strings

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/capsule_share_card.dart:266-272`
- **Category**: i18n
- **Description**: Icon matching compares against hardcoded Chinese: `'thinking' || '思考'`, `'reflection' || '反思'`, `'inspiration' || '灵感'`, `'summary' || '总结'`.
- **Current behavior**: Works only because backend sends both language keys, but this is fragile.
- **Expected behavior**: Normalize the type at the data layer, not the presentation layer.
- **Fix approach**: Normalize `capsuleType` to a canonical English form before comparing.

### 2.10 [P2] CollapsibleSlot: Hardcoded accessibility label

- **File**: `mobile/lib/features/home/presentation/widgets/collapsible_slot.dart:227`
- **Category**: i18n | Accessibility
- **Description**: Semantic label uses inline ternary:
  ```dart
  label: I18nService.instance.isChinese ? '长按编辑面板' : 'Long press to edit panel',
  ```
- **Current behavior**: Bypasses ARB.
- **Expected behavior**: Use ARB key for accessibility label.
- **Fix approach**: Add ARB key `dashboardLongPressEditPanel`.

---

## 3. UI/UX Issues

### 3.1 [P2] NodeDetailSheet: Deprecated `withOpacity` usage

- **File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart:1556,1558`
- **Category**: Design
- **Description**: Uses `DS.warning.withOpacity(0.06)` and `DS.warning.withOpacity(0.15)` instead of `withValues(alpha: ...)`.
- **Current behavior**: `withOpacity()` triggers a recomputed color object on every build, slightly less performant.
- **Expected behavior**: Use `withValues(alpha: ...)` consistent with rest of codebase.
- **Fix approach**: Replace `withOpacity(x)` with `withValues(alpha: x)`.

### 3.2 [P2] FeedPostCard: Hardcoded margin/padding values

- **File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:39-40`
- **Category**: Design
- **Description**: Uses hardcoded `margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4)` and `padding: const EdgeInsets.fromLTRB(16, 12, 16, 12)` instead of design tokens.
- **Current behavior**: Inconsistent with other cards using `DS.spacing16`, `DS.spacing12`, etc.
- **Expected behavior**: Use design system tokens.
- **Fix approach**: Replace `16` with `DS.spacing16`, `12` with `DS.spacing12`, `4` with `DS.spacing4`.

### 3.3 [P2] FeedPostCard: Hardcoded font sizes and colors

- **File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:103-104,109,205-206,244-245,295-300`
- **Category**: Design
- **Description**: Uses hardcoded `fontSize: 16`, `fontSize: 12`, `fontSize: 15`, `fontSize: 14`, `fontSize: 10` instead of design tokens like `DS.fontSizeBase`, `DS.fontSizeSm`, etc.
- **Current behavior**: Does not follow design system.
- **Expected behavior**: Use `DS.fontSizeXx` tokens.
- **Fix approach**: Replace all hardcoded font sizes with DS tokens.

### 3.4 [P2] DashboardCardGrid: Fixed `gridCardHeight` may clip content

- **File**: `mobile/lib/features/home/presentation/widgets/dashboard_card_grid.dart:12,36`
- **Category**: UI/UX
- **Description**: All grid cards are forced to exactly `gridCardHeight = 196` pixels. Cards with varying content heights (e.g., long streak text, many next actions) may clip or have excessive whitespace.
- **Current behavior**: Content overflow is silently clipped by the fixed height.
- **Expected behavior**: Cards should adapt to content or the grid should support variable heights.
- **Fix approach**: Consider using `SliverGrid` with `SliverGridDelegateWithMaxCrossAxisExtent` or `AlignedGridView` without height constraint, allowing cards to size naturally.

### 3.5 [P2] DashboardCardCarousel: Fixed `carouselCardHeight = 200` may clip

- **File**: `mobile/lib/features/home/presentation/widgets/dashboard_card_carousel.dart:14,50`
- **Category**: UI/UX
- **Description**: Same issue as grid: all carousel cards forced to 200px height regardless of content.
- **Current behavior**: Tall content gets clipped.
- **Expected behavior**: Either use a min/max height range or allow intrinsic sizing.
- **Fix approach**: Consider using `SizedBox(height: max(200, intrinsicHeight))` or a range.

### 3.6 [P2] ActionCard: Shimmer animation restarts via `setState`

- **File**: `mobile/lib/features/chat/presentation/widgets/action_card.dart:408-411`
- **Category**: UI/UX
- **Description**: The shimmer animation restarts using `onEnd: () { if (mounted) setState(() {}); }` which triggers a full widget rebuild just to restart the animation. This is wasteful and causes layout recalculation.
- **Current behavior**: Entire ActionCard rebuilds every 3 seconds while unconfirmed.
- **Expected behavior**: Only the shimmer animation should restart without rebuilding the widget tree.
- **Fix approach**: Use an `AnimationController` with `repeat()` like `PlanReviewCard` does, or use `AnimatedBuilder` with a separate controller.

### 3.7 [P2] PlanReviewCard: Potential overflow on narrow screens

- **File**: `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:406-458` (action buttons section)
- **Category**: UI/UX
- **Description**: The action buttons row uses `Row` with multiple `CustomButton` widgets that have fixed text. On narrow screens (< 320px), buttons may overflow.
- **Current behavior**: Potential pixel overflow on very narrow screens.
- **Expected behavior**: Buttons should wrap or adapt to available width.
- **Fix approach**: Wrap the action button row in `SingleChildScrollView(scrollDirection: Axis.horizontal)` or use `Wrap`.

### 3.8 [P2] TaskCard: Deep nesting may affect performance

- **File**: `mobile/lib/features/task/presentation/widgets/task_card.dart:218-627`
- **Category**: UI/UX
- **Description**: The `_buildCardContent` method has extremely deep widget nesting: `Semantics > Hero > Material > SparkleTappable > RepaintBoundary > Container > ClipRRect > Stack > IntrinsicHeight > Row > Expanded > Padding > Column > Row > Expanded > Column > Row > Flexible > Text`. This is 20+ levels deep.
- **Current behavior**: Hard to maintain; potentially impacts Flutter's layout pass performance.
- **Expected behavior**: Extract sub-sections into separate widget methods/classes for readability and potential widget rebuild optimization.
- **Fix approach**: Extract the inner Column content into a `_TaskCardContent` stateless widget.

### 3.9 [P2] NodeShareCard: Indentation inconsistency in `_buildFullCard`

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/node_share_card.dart:111-305`
- **Category**: UI/UX
- **Description**: The `_buildFullCard` method has inconsistent indentation starting at line 111 where the `decoration` property is not aligned with the parent `Container`. This is cosmetic but indicates a merge or formatting issue.
- **Current behavior**: Harder to read/maintain.
- **Expected behavior**: Properly formatted code.
- **Fix approach**: Run `dart format` on the file.

### 3.10 [P3] FeedPostCard: `_ExpandableText` calls `setState` inside `LayoutBuilder`

- **File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:334-337`
- **Category**: UI/UX
- **Description**: Inside `LayoutBuilder.builder`, the code calls `WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) setState(...); })` every time the overflow state changes. This creates a rebuild loop during layout.
- **Current behavior**: Potential extra frame of layout recalculation.
- **Expected behavior**: Use a `ValueNotifier` or compute overflow during paint phase.
- **Fix approach**: Use `TextPainter` in `didChangeDependencies` or use a custom `RenderBox` to avoid `setState` during layout.

---

## 4. Design System Compliance

### 4.1 [P2] Inconsistent card border radius across card types

- **Category**: Design
- **Description**: Different card types use different border radii:
  - `SparkleCard`: `context.radius.mdRadius` (from theme extension)
  - `TaskCard`: `_sparkleTheme(context)?.radius.mdRadius ?? BorderRadius.circular(16)`
  - `PlanCard`: `BorderRadius.circular(16)` (hardcoded)
  - `FeedPostCard`: `BorderRadius.circular(16)` (hardcoded)
  - `AchievementCard`: `BorderRadius.all(Radius.circular(12/16/18/20))` depending on style
  - `PlanReviewCard`: `DS.borderRadius16`
  - `SharedResourceCard`: `DS.borderRadius12`
  - `NodeShareCard` (compact): `DS.borderRadius8`
  - `NodeShareCard` (full): `DS.borderRadius12`
- **Current behavior**: No consistent card radius standard. Cards on the same screen may have 8, 12, 16, or 20px radii.
- **Expected behavior**: Establish a standard radius per card tier (e.g., 12px for inline, 16px for standalone, 20px for detail) and use DS tokens consistently.
- **Fix approach**: Document the card radius standard and update non-conforming cards.

### 4.2 [P3] Inconsistent shadow usage across cards

- **Category**: Design
- **Description**: Card shadows vary widely:
  - `TaskCard`: Custom shadow from `DS.shadowMd` with modified alpha/blur
  - `PlanReviewCard`: `DS.shadowMd`
  - `FeedPostCard`: Custom `BoxShadow(color: DS.textPrimary.withValues(alpha: 0.06), blurRadius: 18, offset: Offset(0, 8))`
  - `AchievementCard`: Custom shadow per rarity
  - `SharedResourceCard`: No shadow
- **Current behavior**: Inconsistent elevation/shadow semantics.
- **Expected behavior**: Use consistent shadow tokens or document per-tier usage.
- **Fix approach**: Define card shadow tiers in `design_system.dart` and reference them.

### 4.3 [P3] Mixed use of `withOpacity` and `withValues`

- **File**: `node_detail_sheet.dart:1556,1558`
- **Category**: Design
- **Description**: The `_FocusReasonSection` uses deprecated `withOpacity()` while the rest of the card system uses `withValues(alpha: ...)`.
- **Current behavior**: Inconsistent API usage; `withOpacity` creates new color objects per call.
- **Expected behavior**: Consistent use of `withValues(alpha: ...)`.
- **Fix approach**: Replace all `withOpacity(x)` with `withValues(alpha: x)`.

---

## 5. Data/Logic Issues

### 5.1 [P2] PlanShareCardFactory: Unsafe type cast on metadata values

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/plan_share_card.dart:353-364`
- **Category**: Data/Logic
- **Description**: Metadata values are cast directly `as int?` and `as double?` without conversion. If the backend sends `num` (e.g., JSON integers), `metadata['completed_tasks'] as int?` works, but `metadata['progress'] as double?` fails if it's actually an `int`.
- **Current behavior**: If `progress` comes as `42` (int) instead of `42.0` (double), the cast fails silently and progress is null.
- **Expected behavior**: Use `(metadata['progress'] as num?)?.toDouble()` pattern.
- **Fix approach**: Replace `as double?` with `(value as num?)?.toDouble()` and `as int?` with `(value as num?)?.toInt()`.

### 5.2 [P2] NodeShareCardFactory: Same unsafe type cast issue

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/node_share_card.dart:372-385`
- **Category**: Data/Logic
- **Description**: Same as 5.1: `metadata['mastery'] as double?` and `metadata['connections'] as int?` and `metadata['learning_time'] as int?`.
- **Current behavior**: Silent null on type mismatch.
- **Expected behavior**: Safe numeric conversion.
- **Fix approach**: Use `(value as num?)?.toDouble()` / `(value as num?)?.toInt()`.

### 5.3 [P2] TaskShareCardFactory: Same unsafe type cast issue

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/task_share_card.dart:329-332`
- **Category**: Data/Logic
- **Description**: `metadata['duration'] as int?`, `metadata['points'] as int?`, `metadata['streak'] as int?`.
- **Current behavior**: Silent null on type mismatch.
- **Expected behavior**: Safe numeric conversion.
- **Fix approach**: Use `(value as num?)?.toInt()`.

### 5.4 [P2] CapsuleShareCardFactory: Unsafe List cast

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/capsule_share_card.dart:351`
- **Category**: Data/Logic
- **Description**: `(metadata['tags'] as List<dynamic>?)?.cast<String>()` will throw if any tag is not a String.
- **Current behavior**: Runtime crash if tags contain non-String values.
- **Expected behavior**: Graceful handling of mixed-type lists.
- **Fix approach**: Use `.map((e) => e.toString()).toList()` instead of `.cast<String>()`.

### 5.5 [P2] EntityCardPayload parsing: `secondaryActions` filter too restrictive

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:232`
- **Category**: Data/Logic
- **Description**: Uses `.whereType<Map<Object?, Object?>>()` to filter secondary actions. This means `Map<String, dynamic>` items are excluded because they don't match `Map<Object?, Object?>` exactly.
- **Current behavior**: If the backend sends `Map<String, dynamic>` entries in `secondary_actions` (which is common from JSON parsing), they are silently dropped.
- **Expected behavior**: All map items should be parsed.
- **Fix approach**: Use `.where((item) => item is Map)` then `Map<String, dynamic>.from(item as Map)`.

### 5.6 [P1] EntityCardPayload parsing: `children` filter too restrictive

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:259`
- **Category**: Data/Logic
- **Description**: Same issue as 5.5: `childrenRaw.whereType<Map<Object?, Object?>>()` may miss `Map<String, dynamic>` children.
- **Current behavior**: Child entity cards may be silently dropped from the payload.
- **Expected behavior**: All child maps should be parsed.
- **Fix approach**: Use `.where((item) => item is Map)` then `Map<String, dynamic>.from(item as Map)`.

### 5.7 [P2] PlanCard: Caching uses identity comparison on Map

- **File**: `mobile/lib/features/plan/presentation/widgets/plan_card.dart:34-38`
- **Category**: Data/Logic
- **Description**: The `_payload` getter uses `identical(widget.data, _lastData)` to check if re-parsing is needed. Since `Map` objects are rarely identical across widget rebuilds (they're often newly created from JSON), this effectively parses on every build.
- **Current behavior**: Unnecessary re-parsing of the plan card payload on every build.
- **Expected behavior**: Use `DeepCollectionEquality` or check a specific version/timestamp field.
- **Fix approach**: Use `const DeepCollectionEquality().equals(widget.data, _lastData)` or check a specific `schema_version` or `id` field.

### 5.8 [P3] EntityCardPayload: `_asString` fallback silently returns null

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:924`
- **Category**: Data/Logic
- **Description**: `_asString` delegates to `sanitizeNullableDisplayText` which may return null for non-null input (e.g., numbers, booleans). This means `EntityCardPayload.title` could be 'Unnamed Entity' even when the raw data has a valid numeric title.
- **Current behavior**: Numeric titles are silently replaced with fallbacks.
- **Expected behavior**: Convert non-string values to their string representation.
- **Fix approach**: Ensure `_asString` calls `value?.toString()` as a final fallback.

---

## 6. Protocol & Type Mismatch Issues

### 6.1 [P2] ActionCard: Widget type string matching is fragile

- **File**: `mobile/lib/features/chat/presentation/widgets/action_card.dart:218-322`
- **Category**: Protocol
- **Description**: The `build` method matches `widget.action.type` against hardcoded string literals: `'focus_card'`, `'task_card'`, `'task_list'`, etc. There is no type-safe enum or constant for these. If the backend changes a type string, the card silently falls through to the default rendering.
- **Current behavior**: Silent degradation on type string mismatch.
- **Expected behavior**: Use constants or an enum for widget types, with logging on unmatched types.
- **Fix approach**: Define `WidgetType` constants and add a `debugPrint` for unmatched types.

### 6.2 [P3] EntityCardPayload: `planId` getter has confusing fallback chain

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:300-303`
- **Category**: Protocol
- **Description**: The `planId` getter tries three sources in order:
  ```dart
  _asString(linkedEntities['plan_id']) ??
  _asString(raw['plan_id']) ??
  _asString(raw['id'] ?? raw['plan_id'])
  ```
  The third fallback `raw['id'] ?? raw['plan_id']` is redundant since `raw['plan_id']` was already checked. Worse, `raw['id']` returns the entity's own ID, not the plan ID, which is incorrect for task entities.
- **Current behavior**: For tasks without an explicit `plan_id`, the task's own ID is returned as the plan ID.
- **Expected behavior**: Return null if no plan ID is found.
- **Fix approach**: Remove the `raw['id'] ?? raw['plan_id']` fallback, or make it explicit that this is intentional.

---

## 7. Accessibility Issues

### 7.1 [P2] SharedResourceCard: Missing semantic label for adopt button

- **File**: `mobile/lib/features/community/presentation/widgets/shared_resource_card.dart:96-109`
- **Category**: Accessibility
- **Description**: The adopt button `OutlinedButton` has no explicit semantic label. Screen readers will read the button text but won't convey what resource is being adopted.
- **Current behavior**: Screen reader announces "Adopt into my plan" without context.
- **Expected behavior**: Include the resource name in the semantic label.
- **Fix approach**: Add `semanticsLabel: 'Adopt ${resource.resourceTitle ?? "resource"} into my plan'`.

### 7.2 [P2] ShareCards (all): Missing semantic labels

- **Files**: All share card files in `mobile/lib/features/community/presentation/widgets/share_cards/`
- **Category**: Accessibility
- **Description**: None of the share cards (`TaskShareCard`, `PlanShareCard`, `NodeShareCard`, `CapsuleShareCard`, `AchievementShareCard`, `LearningReportShareCard`) have `Semantics` wrappers or explicit semantic labels. The `GestureDetector`/`SparklePressable` tap targets don't have meaningful accessibility descriptions.
- **Current behavior**: Screen readers announce the entire card content as a flat block.
- **Expected behavior**: Each card should have a semantic label summarizing its content (e.g., "Task completed: Math homework. 30 minutes. Tap to view details.").
- **Fix approach**: Wrap each card in `Semantics(label: ..., button: true, hint: ..., child: ...)`.

### 7.3 [P3] CardPickerSheet: Search field missing semantic hint

- **File**: `mobile/lib/shared/widgets/card_picker_sheet.dart:97-105`
- **Category**: Accessibility
- **Description**: The search `TextField` has `hintText: 'Search cards or plans'` but no `semanticsLabel`. Screen readers may read the hint text correctly, but the field's purpose should be explicit.
- **Current behavior**: Screen reader reads the hint but not the field's purpose.
- **Expected behavior**: Add explicit `semanticsLabel`.
- **Fix approach**: Add `semanticsLabel: 'Search for cards or plans to select'`.

### 7.4 [P3] DraggableTaskCard: Drag handle has no semantic label

- **File**: `mobile/lib/shared/widgets/draggable_task_card.dart:175-179`
- **Category**: Accessibility
- **Description**: The drag indicator icon `Icons.drag_indicator` at the top-right of the task card has no semantic label or tooltip for accessibility.
- **Current behavior**: Screen readers don't announce the drag affordance.
- **Expected behavior**: Add a `Semantics` or `Tooltip` wrapper explaining the drag action.
- **Fix approach**: Wrap with `Tooltip(message: l10n.taskDragToReschedule, child: Icon(...))`.

### 7.5 [P3] InteractiveTaskCard: Priority indicator lacks semantics

- **File**: `mobile/lib/features/home/presentation/widgets/task_board/interactive_task_card.dart:239-257`
- **Category**: Accessibility
- **Description**: The `_buildPriorityIndicator` is a colored bar with no semantic meaning. Screen readers cannot determine the task priority.
- **Current behavior**: Priority is only communicated visually via color.
- **Expected behavior**: Include a semantic label for priority.
- **Fix approach**: Wrap in `Semantics(label: 'Priority: ${priority >= 8 ? "High" : priority >= 5 ? "Medium" : "Low"}', child: ...)`.

---

## 8. Stale State & Race Conditions

### 8.1 [P2] ActionCard: `_confirmingTasks` flag may get stuck on error

- **File**: `mobile/lib/features/chat/presentation/widgets/action_card.dart:156-171`
- **Category**: Data/Logic
- **Description**: In `_handleConfirmTasks`, if `onConfirmTasks` throws, the `catch` block does nothing (`catch (_) {}`). The `finally` block sets `_confirmingTasks = false`, but `_confirmedTasks` stays `false`. However, the `_hiddenAfterAction` state is never set in the error path, so the card remains visible but the user may have no way to retry (the button re-enables, but the UI state is ambiguous).
- **Current behavior**: On error, the card stays visible with the confirm button re-enabled, which is actually reasonable. But the success path calls `widget.onConfirm?.call()` before setting `_confirmedTasks = true`, meaning if `onConfirm` triggers a rebuild, `_confirmedTasks` may be `false` during that rebuild.
- **Expected behavior**: Set `_confirmedTasks = true` before calling `onConfirm` callback.
- **Fix approach**: Reorder: set state first, then call callback.

### 8.2 [P3] DraggableTaskCard: `childWhenDragging` receives all callbacks

- **File**: `mobile/lib/shared/widgets/draggable_task_card.dart:152-159`
- **Category**: Data/Logic
- **Description**: The `childWhenDragging` renders a full `TaskCard` with all callbacks (`onTap`, `onStart`, `onComplete`). Since this is the placeholder while dragging, these callbacks should be no-ops or the card should be non-interactive.
- **Current behavior**: User can interact with the ghost card during drag.
- **Expected behavior**: The `childWhenDragging` should have no callbacks or wrap in `IgnorePointer`.
- **Fix approach**: Pass `onTap: null, onStart: null, onComplete: null` to the `childWhenDragging` TaskCard.

### 8.3 [P3] CalendarDayDragTarget: `onLeave` callback is empty

- **File**: `mobile/lib/shared/widgets/draggable_task_card.dart:217-219`
- **Category**: Data/Logic
- **Description**: The `onLeave` callback has an empty body with just a comment. This means the hovered state is never cleared when the drag leaves a calendar cell (only when entering a new cell). If the user drags out of all cells (e.g., to the edge), the last cell stays highlighted.
- **Current behavior**: Last hovered cell stays highlighted when drag leaves all targets.
- **Expected behavior**: Clear hover state on leave.
- **Fix approach**: Call `ref.read(taskDragProvider.notifier).clearHover()` in `onLeave`.

---

## 9. Dead Code & Unreachable Branches

### 9.1 [P3] ShareCards: `onAdopt` callback never passed for some share card factories

- **File**: `mobile/lib/features/community/presentation/widgets/share_cards/capsule_share_card.dart:337-357`
- **Category**: Data/Logic
- **Description**: `CapsuleShareCardFactory` and `NodeShareCardFactory` and `AchievementShareCardFactory` and `LearningReportShareCardFactory` do not accept or pass `onAdopt` callback, even though `ShareCardFactory.fromPayload` accepts it.
- **Current behavior**: Adopt action is silently dropped for these content types.
- **Expected behavior**: Either pass through the adopt callback or document why these types don't support adoption.
- **Fix approach**: Add `onAdopt` parameter to these factories, or document the intentional omission.

### 9.2 [P3] EntityCardPayload: `schemaVersion` field is parsed but never used

- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:277`
- **Category**: Data/Logic
- **Description**: `EntityCardPayload.schemaVersion` is parsed from the payload but never used anywhere in the rendering or validation logic.
- **Current behavior**: Dead field.
- **Expected behavior**: Either use it for version-aware rendering or remove it.
- **Fix approach**: Add version-based rendering logic or document as future use.

---

## 10. Specific Overflow / Clipping Concerns

### 10.1 [P2] PlanCard: Info pills in Wrap may overflow on narrow screens

- **File**: `mobile/lib/features/plan/presentation/widgets/plan_card.dart:165-188`
- **Category**: UI/UX
- **Description**: The meta section uses `Wrap` with `_buildInfoPill` items. Each pill contains an icon + text in a `Row`. If the text is long (e.g., a verbose target date or subject name), individual pills may exceed their parent width because the `Row` inside has no `Expanded` or overflow handling.
- **Current behavior**: Long pill text causes overflow within the pill.
- **Expected behavior**: Text inside pills should truncate.
- **Fix approach**: Wrap the `Text` in `_buildInfoPill` with `Flexible(child: Text(..., overflow: TextOverflow.ellipsis))`.

### 10.2 [P2] TaskBoardCard side panel: `_PanelItem` description may overflow

- **File**: `mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart:434-491`
- **Category**: UI/UX
- **Description**: `_PanelItem` uses a `Row` with icon container + `Expanded > Column > Text(description)`. The description text is not constrained. If the description is very long (which is possible for user-generated content), it could push the column height beyond constraints.
- **Current behavior**: Works for current hardcoded descriptions, but fragile.
- **Expected behavior**: Add `maxLines` and `overflow` to the description text.
- **Fix approach**: Add `maxLines: 3, overflow: TextOverflow.ellipsis` to description Text.

### 10.3 [P3] AchievementCard showcase variant: `_buildToneChip` with maxWidth may clip

- **File**: `mobile/lib/features/achievement/presentation/widgets/achievement_card.dart:1051-1085`
- **Category**: UI/UX
- **Description**: `_buildToneChip` has a `maxWidth` constraint. The internal `Row` with icon + text has no overflow handling. If the label text exceeds the available space after the icon and padding, it overflows.
- **Current behavior**: Long chip labels may overflow.
- **Expected behavior**: Text should truncate.
- **Fix approach**: Wrap the `Text` in `_buildToneChip` with `Flexible(child: Text(..., overflow: TextOverflow.ellipsis))`.

---

## Summary Table

| Severity | Count | Categories |
|----------|-------|-----------|
| P0       | 1     | Null safety crash (FeedPostCard username) |
| P1       | 4     | Hardcoded Chinese fallback, null assertion, silent error swallowing, children filter |
| P2       | 29    | i18n violations (10), unsafe type casts (4), UI/UX (6), overflow (3), design (2), data (2), accessibility (2) |
| P3       | 24    | Design inconsistencies (3), accessibility (3), data/dead code (4), overflow (1), stale state (3), protocol (1), i18n pattern (9+) |

### Priority Fix Order

1. **P0**: Fix FeedPostCard empty username crash (1 file, 1 line)
2. **P1**: Fix entity_card_payloads children filter (affects all entity cards)
3. **P1**: Fix hardcoded Chinese fallback in entity_card_payloads
4. **P1**: Fix unsafe type casts in all share card factories
5. **P2**: Convert all `isChinese ? '中文' : 'English'` patterns to ARB l10n (9 files)
6. **P2**: Add semantic labels to share cards and interactive elements
7. **P2**: Replace hardcoded font sizes with DS tokens in FeedPostCard
8. **P3**: Standardize card border radius and shadow patterns
9. **P3**: Replace `withOpacity` with `withValues` in node_detail_sheet
