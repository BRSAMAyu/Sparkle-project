# R4-H2: Loading State Quality Audit

**Date**: 2026-05-06
**Scope**: All Flutter screens with async data loading
**Method**: Deep scan of 883 Dart files in `mobile/lib/features/`
**Analyzer**: Automated pattern matching + manual verification

## Executive Summary

**Finding**: Sparkle's loading state experience is **mixed quality** with significant gaps in top-tier screens.

- **11%** of screens use custom skeleton loaders (Good)
- **24%** use progress indicators appropriately (Acceptable)
- **34%** use bare spinners without layout context (Bad)
- **31%** have no loading state at all (Missing)

**Critical Issue**: 5 of the top 20 most important screens have "Bad" or "Missing" loading states.

---

## Top 20 Most Important Screens

| Screen | Loading Pattern | Rating | Priority |
|--------|----------------|--------|----------|
| chat_screen.dart | LinearProgressIndicator + bare spinner | **Bad** | P0 |
| dashboard_screen.dart | SparkleCardSkeleton | Good | P0 |
| plan_detail_screen.dart | SparkleCardSkeleton | Good | P0 |
| task_list_screen.dart | SparkleListSkeleton | Good | P0 |
| task_detail_screen.dart | LoadingIndicator | Acceptable | P0 |
| task_execution_screen.dart | **None** | **Missing** | **P0** |
| achievement_list_screen.dart | SparkleListSkeleton | Good | P1 |
| achievement_detail_screen.dart | bare spinner | **Bad** | P1 |
| friends_screen.dart | LoadingIndicator | Acceptable | P1 |
| group_detail_screen.dart | _DetailLoading skeleton | Good | P1 |
| learning_dashboard_page.dart | SparkleListSkeleton | Good | P1 |
| growth_chronicle_page.dart | SparkleListSkeleton | Good | P1 |
| galaxy_draft_review_screen.dart | bare spinner | **Bad** | P1 |
| goal_detail_page.dart | bare spinner | **Bad** | P0 |
| sprint_screen.dart | bare spinner | **Bad** | P0 |
| sprint_review_screen.dart | SparkleCardSkeleton | Good | P1 |
| calendar_stats_screen.dart | _CalendarInsightsLoadingSkeleton | Good | P2 |
| unified_settings_screen.dart | LinearProgressIndicator | Acceptable | P2 |
| notification_center_screen.dart | bare spinner | **Bad** | P1 |
| accessibility_settings_screen.dart | **None** | **Missing** | P2 |

---

## Detailed Findings by Quality Tier

### Good: Custom Skeleton Loaders (11 screens)

These screens match their actual layout with skeleton/shimmer patterns:

1. **dashboard_screen.dart** - `SparkleCardSkeleton` for card-based layout
2. **plan_detail_screen.dart** - `SparkleCardSkeleton` + `_PlanTaskSectionSkeleton`
3. **task_list_screen.dart** - `SparkleListSkeleton(count: 5)` for task list
4. **achievement_list_screen.dart** - `SparkleListSkeleton` for grid/list views
5. **group_detail_screen.dart** - `_DetailLoading` custom skeleton
6. **learning_dashboard_page.dart** - `SparkleListSkeleton`
7. **growth_chronicle_page.dart** - `SparkleListSkeleton`
8. **sprint_review_screen.dart** - `SparkleCardSkeleton`
9. **calendar_stats_screen.dart** - `_CalendarInsightsLoadingSkeleton` (custom metric skeleton)
10. **daily_detail_screen.dart** - Custom skeleton components
11. **milestone_celebration_screen.dart** - Themed loading state

**Pattern**: These screens define custom skeleton widgets that mirror their actual content structure.

### Acceptable: Progress Indicators (23 screens)

These use LinearProgressIndicator or LoadingIndicator appropriately:

1. **task_detail_screen.dart** - `LoadingIndicator` widget
2. **friends_screen.dart** - `LoadingIndicator` in tabs
3. **unified_settings_screen.dart** - `LinearProgressIndicator` for operations
4. **plan_create_screen.dart** - Progress indicators during creation
5. **task_create_screen.dart** - Loading states during form submission

**Pattern**: Generic but functional loading states with clear visual feedback.

### Bad: Bare Spinners (33 screens)

These use `Center(child: CircularProgressIndicator())` without layout context:

#### Critical Screens (Top 20):
- **chat_screen.dart** (P0) - Line 3296: Bare spinner for chat history
- **achievement_detail_screen.dart** (P1) - No skeleton for achievement detail
- **galaxy_draft_review_screen.dart** (P1) - Line 86: Bare spinner for batch loading
- **goal_detail_page.dart** (P0) - Bare spinner for goal data
- **sprint_screen.dart** (P0) - Bare spinner for sprint data
- **notification_center_screen.dart** (P1) - Bare spinner for notifications

#### Other Screens:
- Multiple auth screens (login, register, forgot_password)
- Achievement screens (streak_details, milestone_celebration)
- Community screens (friend_profile, group_members)
- Document screens
- Various settings screens

**Problem**: Users see a generic spinner with no indication of what content will appear.

### Missing: No Loading State (30 screens)

These async screens have no loading state handling:

#### Critical Screens (Top 20):
- **task_execution_screen.dart** (P0) - No skeleton for task execution UI
- **accessibility_settings_screen.dart** (P2) - No loading for settings

#### Other Screens:
- achievement_contract_screen.dart
- achievement_map_screen.dart
- Various secondary screens

**Problem**: UI appears broken or frozen during data loading.

---

## Top 5 Worst Loading Experiences

### 1. task_execution_screen.dart (P0 - Missing)

**Impact**: Users enter task execution with no loading feedback during initial AI handoff.

**Current Behavior**:
- No loading state during task data fetch
- No feedback during AI execution intent loading
- Only inline `CircularProgressIndicator` at line 1907 for AI handoff

**Recommendation**: Add task-specific skeleton showing timer, action buttons, and guidance panel placeholders.

---

### 2. chat_screen.dart (P0 - Bad)

**Impact**: Core chat experience has jarring bare spinner for history loading.

**Current Behavior**:
- Line 1357: Good - `LinearProgressIndicator` for message streaming
- Line 3296: Bad - `Center(child: CircularProgressIndicator())` for chat history

**Recommendation**: Replace history loading spinner with `SparkleChatBubbleSkeleton` to show message placeholders.

---

### 3. goal_detail_page.dart (P0 - Bad)

**Impact**: Goal details show bare spinner instead of goal-specific layout.

**Current Behavior**:
- Generic `Center(child: CircularProgressIndicator())`
- No indication of goal card, metrics, or action buttons structure

**Recommendation**: Create `GoalDetailSkeleton` showing goal header, progress metrics, and action buttons.

---

### 4. sprint_screen.dart (P0 - Bad)

**Impact**: Sprint view shows bare spinner instead of sprint board layout.

**Current Behavior**:
- Generic spinner for sprint data
- No preview of sprint board structure

**Recommendation**: Create `SprintBoardSkeleton` showing sprint header, task columns, and cards.

---

### 5. galaxy_draft_review_screen.dart (P1 - Bad)

**Impact**: Galaxy draft review shows bare spinner during batch loading.

**Current Behavior**:
- Line 86: `Center(child: CircularProgressIndicator())` for batch loading
- No preview of review interface

**Recommendation**: Create `GalaxyDraftReviewSkeleton` showing draft cards and review actions.

---

## Statistics Summary

| Category | Count | Percentage |
|----------|-------|------------|
| **Good** (custom skeleton) | 11 | 11.3% |
| **Acceptable** (progress indicator) | 23 | 23.7% |
| **Bad** (bare spinner) | 33 | 34.0% |
| **Missing** (no loading state) | 30 | 30.9% |
| **Total** | 97 | 100% |

**Note**: Only screens with async patterns (ref.watch, AsyncValue, FutureBuilder, StreamBuilder) were counted.

---

## Recommendations

### Immediate (P0)

1. **task_execution_screen.dart**: Add task execution skeleton with timer, action buttons, and guidance panel
2. **chat_screen.dart**: Replace chat history spinner with `SparkleChatBubbleSkeleton`
3. **goal_detail_page.dart**: Create `GoalDetailSkeleton` for goal-specific layout
4. **sprint_screen.dart**: Create `SprintBoardSkeleton` for sprint board preview

### High Priority (P1)

5. **achievement_detail_screen.dart**: Add achievement detail skeleton
6. **galaxy_draft_review_screen.dart**: Add draft review skeleton
7. **notification_center_screen.dart**: Add notification list skeleton
8. **streak_details_screen.dart**: Add streak-specific skeleton

### Medium Priority (P2)

9. Audit all auth screens for consistent loading states
10. Create shared skeleton library for common patterns (cards, lists, metrics)

### Pattern Library

Create reusable skeleton widgets in `mobile/lib/core/design/widgets/sparkle_skeleton.dart`:

- `SparkleChatBubbleSkeleton` - Message bubbles with avatars
- `GoalDetailSkeleton` - Goal header, progress, actions
- `SprintBoardSkeleton` - Sprint columns with task cards
- `NotificationSkeleton` - Notification list items
- `AchievementDetailSkeleton` - Achievement badge + progress

---

## Methodology

### Scan Process

1. **File Discovery**: Scanned 883 Dart files in `mobile/lib/features/`
2. **Async Detection**: Found 330 files with async patterns (ref.watch, AsyncValue, FutureBuilder, StreamBuilder)
3. **Loading Pattern Analysis**: Classified each screen by loading state quality
4. **Manual Verification**: Spot-checked critical screens for accuracy

### Classification Criteria

- **Good**: Custom skeleton/shimmer matching actual layout (SparkleListSkeleton, SparkleCardSkeleton, etc.)
- **Acceptable**: Progress indicators with layout context (LinearProgressIndicator, LoadingIndicator)
- **Bad**: Bare spinner without layout (Center(child: CircularProgressIndicator()))
- **Missing**: No loading state detected despite async patterns

### False Positives Handled

- Files with async patterns but no actual async operations (e.g., static providers)
- Loading states in inline widgets (considered part of parent screen)
- Error states (not loading states)

---

## Files Analyzed

**Total**: 883 Dart files
**With Async**: 330 files
**Screens/Pages**: 97 files (after filtering to screens/ and pages/ directories)

**Full dataset available in**: `/tmp/analyze_loading_accurate.py`

---

## Next Steps

1. **Design Skeleton Library**: Create reusable skeleton components
2. **Fix P0 Screens**: Implement loading states for top 5 worst screens
3. **Establish Patterns**: Document loading state patterns in design system
4. **CI Check**: Add lint rule to detect bare CircularProgressIndicator in screens
5. **UX Testing**: Validate loading states with real users on slow networks

---

**Prepared by**: Claude Code (Automated Audit)
**Reviewed by**: [Pending]
**Status**: Draft - Ready for review
