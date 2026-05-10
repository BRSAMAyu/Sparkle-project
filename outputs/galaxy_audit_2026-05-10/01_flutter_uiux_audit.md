# Flutter UI/UX Audit: Knowledge Galaxy & Community Sharing Widgets

> **Date**: 2026-05-10
> **Auditor**: Claude Code (automated audit)
> **Scope**: Galaxy core UI, node detail sheet, community knowledge widgets, share cards, learning path screens

---

## Summary

| Severity | Count |
|----------|-------|
| P0 (crash/data loss) | 1 |
| P1 (broken feature) | 4 |
| P2 (degraded UX) | 7 |
| P3 (minor/cosmetic) | 5 |
| **Total** | **17** |

---

## 1. i18n Violations (Hardcoded Strings)

### Issue #1 -- P1: SharedResourceCard uses hardcoded Chinese/English strings via I18nService instead of l10n ARB

**File**: `mobile/lib/features/community/presentation/widgets/shared_resource_card.dart`
**Lines**: 29, 33, 50-51, 69, 108, 130-163, 206-223

**Issue**: `SharedResourceCard` uses `I18nService.instance.isChinese ? 'Chinese' : 'English'` pattern throughout instead of ARB l10n. This is a direct violation of the project's i18n bilingual strategy documented in CLAUDE.md. There are at least 10 hardcoded string pairs:
- Line 33: `'Shared Resource'`
- Line 50-51: `'Shared Resource'` (fallback)
- Line 69: `'By'` prefix for sharer name
- Line 108: `'Adopt into my plan'`
- Line 130-162: Quality badge labels `'Featured'`, `'Recommended'`, `'Beginner-friendly'`
- Line 206-223: Stats strings like `'$adoption adoptions'`, `'Avg rating...'`

**Context**:
```dart
// Line 29-33
final isChinese = I18nService.instance.isChinese;
return Semantics(
  button: true,
  label: resource.resourceTitle ?? (isChinese ? '共享资源' : 'Shared Resource'),
```

```dart
// Line 108
child: Text(
  isChinese ? '采纳并加入我的计划' : 'Adopt into my plan',
),
```

**Fix**: Replace all `I18nService.instance.isChinese` ternaries with proper `context.l10n.*` calls. Add missing ARB keys for quality badges, stats labels, and action button text.

---

### Issue #2 -- P2: LearningPathScreen has hardcoded fallback title

**File**: `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart`
**Line**: 19

**Issue**: AppBar title uses hardcoded `'Learning Path'` as fallback instead of l10n.

**Context**:
```dart
title: Text(
  nodeName.isNotEmpty ? nodeName : 'Learning Path',
),
```

**Fix**: Use `context.l10n.learningPathTitle` or similar ARB key.

---

### Issue #3 -- P2: _GalaxyDraftPendingIndicator missing const constructor qualification

**File**: `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`
**Lines**: 3498-3499

**Issue**: `_GalaxyDraftPendingIndicator` line 3498 uses `context.l10n.galaxyDraftPendingIndicator(batchCount, draftCount)` correctly for the text, but the widget class itself is declared at line 3452 with `const` constructor. The l10n method call inside `build()` is fine. This is not an issue -- I verified it uses l10n properly. Removing from findings.

---

### Issue #4 -- P2: SharedResourceCard `_typeLabel` strings are not localized

**File**: `mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`
**Lines**: 757-772 (in `_GroupKnowledgeBaseViewState`), 959-974 (in `_KnowledgeBaseListCard`), 1100-1115 (in `_KnowledgeBaseGridCard`)

**Issue**: File type labels `'PDF'`, `'PPTX'`, `'DOCX'`, `'IMAGE'`, `'TXT'`, `'FILE'` are hardcoded in English across three duplicated `_typeLabel` methods. While these are technical acronyms that may not need localization, the fallback `'FILE'` should arguably use l10n.

**Context**:
```dart
// Line 762
if (normalizedMime.contains('pdf')) return 'PDF';
// ...
return extension.isEmpty ? 'FILE' : extension;
```

**Fix**: These are borderline. `'FILE'` and `'IMAGE'` could be localized; `'PDF'`/`'PPTX'`/`'DOCX'` are universally understood technical terms. Low priority.

---

## 2. State Management Bugs

### Issue #5 -- P1: FutureBuilder in _CommunityInsightContent re-fetches on every rebuild

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`
**Lines**: 1619-1621

**Issue**: `_CommunityInsightContent` creates a new `_fetchCommunitySignal()` Future in every `build()` call and passes it to `FutureBuilder`. This means every time the widget rebuilds (e.g., when parent state changes), a new API call fires. The future is not cached or stored in a state field.

**Context**:
```dart
Widget build(BuildContext context) {
  return FutureBuilder<Map<String, dynamic>?>(
    future: _fetchCommunitySignal(),  // NEW FUTURE EVERY BUILD
    builder: (context, snapshot) {
```

**Fix**: Cache the future in `initState()` or use a Riverpod provider (like `nodeSourceMaterialsProvider` pattern already used above it in the same file). Store the future in a late field:
```dart
late final Future<Map<String, dynamic>?> _communityFuture;

@override
void initState() {
  super.initState();
  _communityFuture = _fetchCommunitySignal();
}
```

---

### Issue #6 -- P2: _KnowledgeBaseViewState reload creates duplicate Futures on rapid category switches

**File**: `mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`
**Lines**: 60-69

**Issue**: `_reload()` replaces `_filesFuture` and `_categoriesFuture` every time it's called. If the user rapidly switches categories, previous futures are abandoned but there's no cancellation mechanism. The `_categoriesFuture` is fetched every `_reload()` call even though categories rarely change.

**Context**:
```dart
void _reload() {
  final repo = ref.read(fileRepositoryProvider);
  setState(() {
    _filesFuture = repo.listGroupFiles(
      widget.groupId,
      category: _selectedCategory,
      limit: 200,
    );
    _categoriesFuture = repo.getGroupFileCategories(widget.groupId);
  });
}
```

**Fix**: Categories should be fetched once in `initState()` and not re-fetched on category filter changes. Only `_filesFuture` needs refreshing.

---

### Issue #7 -- P2: Galaxy provider `deselectNode()` bypasses copyWith pattern

**File**: `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart`
**Lines**: 806-833

**Issue**: `deselectNode()` manually constructs a new `GalaxyState` instead of using `copyWith()`. This is fragile -- if any new field is added to `GalaxyState`, it must be added here too. There's already a `copyWith` with special `_noChange` sentinel for nullable fields.

**Context**:
```dart
void deselectNode() {
  if (state.selectedNodeId == null) return;
  state = GalaxyState(
    nodes: state.nodes,
    edges: state.edges,
    // ... 20+ fields manually listed
  );
```

**Fix**: Use `state.copyWith(selectedNodeId: ..., draggingNodeId: ..., expandedEdgeNodeIds: ...)` with the sentinel pattern already in place.

---

## 3. Null Safety Issues

### Issue #8 -- P0: GalaxyRoutes.knowledgeDetail accesses path parameter without null check

**File**: `mobile/lib/features/galaxy/galaxy_routes.dart`
**Line**: 50

**Issue**: `state.pathParameters['id']!` uses force-unwrap. If the route is somehow matched without an `:id` parameter, this crashes.

**Context**:
```dart
final nodeId = state.pathParameters['id']!;
```

**Fix**: Add a null check with fallback navigation:
```dart
final nodeId = state.pathParameters['id'];
if (nodeId == null) {
  return buildSparkleTransitionPage(
    state: state,
    child: const Scaffold(body: Center(child: Text('Invalid node ID'))),
  );
}
```

---

### Issue #9 -- P1: GalaxyNodeModel.fromJson can crash on null 'id'

**File**: `mobile/lib/shared/entities/galaxy_model.dart`
**Line**: 193

**Issue**: `json['id'] as String` will throw a `TypeError` if the backend returns null or missing `id`. All other fields have null-coalescing defaults but `id` does not.

**Context**:
```dart
id: json['id'] as String,  // NO null safety
```

**Fix**: Use `json['id']?.toString() ?? ''` pattern consistent with other fields, or validate before constructing.

---

### Issue #10 -- P2: GalaxyGraphResponse.fromJson crashes if 'nodes' key is missing

**File**: `mobile/lib/shared/entities/galaxy_model.dart`
**Line**: 526

**Issue**: `json['nodes'] as List<dynamic>` will throw if the key is missing or null. The edges field has a fallback `?? const <dynamic>[]` but nodes does not.

**Context**:
```dart
nodes: (json['nodes'] as List<dynamic>)
    .map((e) => GalaxyNodeModel.fromJson(e as Map<String, dynamic>))
    .toList(),
// vs edges which has fallback:
final rawEdges = (json['edges'] ?? json['relations'] ?? const <dynamic>[])
    as List<dynamic>;
```

**Fix**: Add a null fallback:
```dart
nodes: ((json['nodes'] ?? const <dynamic>[]) as List<dynamic>)
```

---

## 4. Error Handling Gaps

### Issue #11 -- P1: _openFile in group_knowledge_base_view does not handle getDownloadUrl failure

**File**: `mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`
**Lines**: 121-132

**Issue**: `_openFile` calls `getDownloadUrl` without try/catch. If the API call fails (network error, 404, etc.), the error propagates unhandled and shows a generic red error screen.

**Context**:
```dart
Future<void> _openFile(GroupFileInfo file) async {
  if (!file.canDownload) {
    AppFeedback.info(context, context.l10n.communityNoDownloadPermission);
    return;
  }
  final presigned = await ref
      .read(fileRepositoryProvider)
      .getDownloadUrl(file.fileId, groupId: widget.groupId);
  // NO try/catch - unhandled error
  final uri = Uri.tryParse(presigned.url);
  if (uri == null) return;
  await launchUrl(uri, mode: LaunchMode.externalApplication);
}
```

**Fix**: Wrap in try/catch with user-facing error feedback:
```dart
try {
  final presigned = await ref.read(fileRepositoryProvider)...
  ...
} catch (e) {
  if (!mounted) return;
  AppFeedback.error(context, context.l10n.communityOpenFileFailed);
}
```

---

### Issue #12 -- P2: NodeShareCardFactory._parseMasteryFromSubtitle can throw on non-numeric match

**File**: `mobile/lib/features/community/presentation/widgets/share_cards/node_share_card.dart`
**Lines**: 391-397

**Issue**: `int.parse(match.group(1)!)` can throw if the regex matches something that's not a valid integer. The `!` force unwrap on `match.group(1)` is safe since the regex guarantees a capture group, but `int.parse` is not guarded.

**Context**:
```dart
static double? _parseMasteryFromSubtitle(String subtitle) {
  final match = RegExp(r'(\d+)%').firstMatch(subtitle);
  if (match != null) {
    return int.parse(match.group(1)!) / 100.0;
  }
  return null;
}
```

**Fix**: Use `int.tryParse`:
```dart
final value = int.tryParse(match.group(1) ?? '');
return value != null ? value / 100.0 : null;
```

---

## 5. Dead Code / Duplication

### Issue #13 -- P2: _iconForMime, _typeLabel, _formatSize are duplicated 3 times in group_knowledge_base_view.dart

**File**: `mobile/lib/features/community/presentation/widgets/group_knowledge_base_view.dart`
**Lines**: 734-772, 936-983, 1077-1115

**Issue**: The methods `_iconForMime()`, `_typeLabel()`, and `_formatSize()` are copy-pasted into three different widget classes (`_GroupKnowledgeBaseViewState`, `_KnowledgeBaseListCard`, `_KnowledgeBaseGridCard`). Any fix to one copy must be applied to all three.

**Fix**: Extract these utility methods into a shared static helper class or top-level functions.

---

### Issue #14 -- P3: GalaxyNotifier has unused _animationDuration, _animationStep fields

**File**: `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart`
**Lines**: 354-357

**Issue**: `_animationDuration` and `_animationStep` are declared with `// ignore: unused_field` suppression comments. Dead code.

**Context**:
```dart
// ignore: unused_field
static const double _animationDuration = 300; // ms
static const int _animationFps = 60;
// ignore: unused_field
static const double _animationStep = 1000 / _animationFps; // ~16.67ms
```

**Fix**: Remove these unused fields entirely, including `_animationFps`.

---

### Issue #15 -- P3: GalaxyNotifier._mapPerformanceTier is an identity function

**File**: `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart`
**Line**: 422

**Issue**: `_mapPerformanceTier` just returns its input unchanged. This is a no-op identity function.

**Context**:
```dart
PerformanceTier _mapPerformanceTier(PerformanceTier tier) => tier;
```

**Fix**: Remove and use the value directly, or document why this indirection exists (e.g., planned future mapping).

---

## 6. UI/UX Issues

### Issue #16 -- P2: Node detail sheet nodeId displayed in tertiary text is a UUID

**File**: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`
**Lines**: 343-349

**Issue**: The raw `nodeId` (a UUID like `abc123-def456...`) is displayed to users as secondary text. This is meaningless to users and clutters the UI.

**Context**:
```dart
Text(
  nodeId,
  maxLines: 1,
  overflow: TextOverflow.ellipsis,
  style: Theme.of(context).textTheme.labelSmall?.copyWith(
        color: DS.textTertiary,
      ),
),
```

**Fix**: Either remove this text entirely or replace with a human-readable identifier like sector name or a short hash.

---

### Issue #17 -- P3: LearningReportShareCard chip uses DS.neutral0 with alpha 0.7 on light theme

**File**: `mobile/lib/features/community/presentation/widgets/share_cards/learning_report_share_card.dart`
**Lines**: 123-124

**Issue**: In light mode, chip background is `DS.neutral0.withValues(alpha: 0.7)`. `DS.neutral0` is typically white (#FFFFFF), so a white chip on a light surface has almost no visual contrast. This makes the chip content hard to read in light mode.

**Context**:
```dart
color: isDark
    ? DS.neutral0.withValues(alpha: 0.08)
    : DS.neutral0.withValues(alpha: 0.7),  // White on white/light background
```

**Fix**: Use a contrasting color for light mode chips, such as `DS.surfaceSecondary` or a tinted background with proper text contrast.

---

## Findings by File

| File | Issues |
|------|--------|
| `galaxy_screen.dart` | (No issues found -- well-implemented) |
| `node_detail_sheet.dart` | #5 (FutureBuilder re-fetch), #16 (UUID shown to user) |
| `galaxy_provider.dart` | #7 (bypass copyWith), #14 (dead fields), #15 (identity fn) |
| `galaxy_model.dart` | #9 (null id crash), #10 (missing nodes fallback) |
| `galaxy_routes.dart` | #8 (force-unwrap crash) |
| `group_knowledge_base_view.dart` | #4 (type labels), #6 (duplicate futures), #11 (no error handling), #13 (code duplication) |
| `shared_resource_card.dart` | #1 (hardcoded strings) |
| `node_share_card.dart` | #12 (parseMasteryFromSubtitle crash) |
| `learning_report_share_card.dart` | #17 (light mode contrast) |
| `learning_path_screen.dart` | #2 (hardcoded title) |
| `learning_path_dialog.dart` | (No issues found -- well-implemented) |
| `insights_routes.dart` | (No issues found) |
| `share_resource_sheet.dart` | (No issues found -- well-implemented) |
| `enhanced_galaxy_repository.dart` | (No issues found -- robust error handling) |
| `compact_knowledge_node.dart` | (No issues found -- well-optimized) |
| `node_history_model.dart` | (No issues found) |

---

## Positive Observations

1. **Galaxy screen (galaxy_screen.dart)**: Extremely thorough implementation. Proper disposal of all 15+ animation controllers, tickers, timers, and subscriptions. `mounted` checks are consistently used before `setState`. Frame timing monitoring with performance degradation fallback. The `_sanitizeGraph` method defensively filters invalid nodes.

2. **Enhanced galaxy repository**: Excellent error handling with circuit breaker, retry strategy, smart cache, and stale-cache-on-error fallback.

3. **Node detail sheet**: Good separation of loading/error/data states. Uses `showSensoryModalBottomSheet` consistently. Proper l10n usage via `_SourceMaterialsCopy` helper.

4. **Learning path dialog**: Comprehensive loading state management with `_isBusy` gate. Uses inline feedback instead of modal dialogs for async operations. Good error handling with mounted checks.

5. **Share resource sheet**: Clean tab-based UI with proper friend/group state management. Core partner auto-preselection is a nice UX touch.

---

## Priority Fix Order

1. **#8** (P0) -- GalaxyRoutes force-unwrap crash
2. **#9** (P1) -- GalaxyNodeModel null id crash
3. **#1** (P1) -- SharedResourceCard hardcoded strings (i18n violation)
4. **#5** (P1) -- CommunityInsight re-fetching on every rebuild
5. **#11** (P1) -- Group knowledge base missing error handling
6. **#10** (P2) -- GalaxyGraphResponse missing nodes fallback
7. **#2** (P2) -- LearningPathScreen hardcoded title
8. **#6** (P2) -- Duplicate category fetch on reload
9. **#7** (P2) -- deselectNode bypasses copyWith
10. **#12** (P2) -- Mastery parse crash
11. **#13** (P2) -- Code duplication in knowledge base view
12. **#16** (P2) -- UUID shown to user
13. **#17** (P3) -- Light mode contrast issue
14. **#4** (P3) -- Type labels not localized
15. **#14** (P3) -- Dead fields in GalaxyNotifier
16. **#15** (P3) -- Identity function
