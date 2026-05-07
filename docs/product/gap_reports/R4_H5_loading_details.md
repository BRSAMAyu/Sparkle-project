# R4_H5 Loading State Gap Analysis Report

**Date**: 2026-05-06
**Auditor**: Claude (H4 + H5 verification)
**Scope**: Top 5 worst loading states identified by H2, plus 3 additional flagged screens

## Executive Summary

H2 identified critical loading UX gaps across 8 high-traffic screens. All suffer from bare `CircularProgressIndicator` spinners instead of context-appropriate skeletons. This creates jarring content jumps and poor perceived performance.

**Key Findings:**
- 5/8 screens have NO loading state (missing entirely)
- 3/8 screens use bare spinners
- 0/8 screens use context-matching skeletons
- **Existing assets**: `SparkleCardSkeleton`, `SparkleListSkeleton`, `SparkleChatBubbleSkeleton` are available but unused

**Impact**: High - These are high-traffic screens (task execution, chat, goals, sprints, galaxy, plan creation, groups, calendar). Poor loading UX directly affects user trust and perceived app quality.

---

## Detailed Analysis

### 1. task_execution_screen.dart ⚠️ CRITICAL

**File**: `/mobile/lib/features/task/presentation/screens/task_execution_screen.dart`

**Current Loading State**: **MISSING ENTIRELY**

| Aspect | Details |
|--------|---------|
| **Line #** | N/A - No loading state exists |
| **What loads?** | Task data, subtasks, execution templates, OpenClaw connection status |
| **Loaded Layout** | Complex multi-panel screen: Focus entry card, timer controls, task protocol panel, guide panel, subtasks, quick tools, chat panel, execution assist panel, bottom controls |
| **Current Behavior** | Screen renders immediately with `activeTask == null` check (line 881), showing "No task" error UI if task hasn't loaded yet |

**Skeleton Suggestion**:
```
TaskExecutionSkeleton should show:
- Horizontal shimmer bar for AppBar title
- Card skeleton for Focus Entry section (with icon + feature chips)
- Skeleton timer circle (centered)
- 3-4 horizontal bars for task protocol panel
- Skeleton subtask expansion tile (collapsed state)
- Skeleton card for execution assist panel
- Bottom action bar skeleton (2-3 buttons)
```

**Reusable Components**: Partial - can use `SparkleCardSkeleton` for card sections, but needs custom layout for timer and bottom controls

**Effort**: **L** (Large - complex custom skeleton needed due to multi-panel layout)

---

### 2. chat_screen.dart

**File**: `/mobile/lib/features/chat/presentation/screens/chat_screen.dart`
*(Note: File is 26k+ tokens, analyzed via search for loading patterns)*

**Current Loading State**: **BARE SPINNER**

| Aspect | Details |
|--------|---------|
| **Line #** | Search pattern: `CircularProgressIndicator` in `.when(loading:)` blocks |
| **What loads?** | Chat history, WebSocket connection, agent state |
| **Loaded Layout** | Chat message list with bubbles (user + AI), input area at bottom |
| **Current Behavior** | Bare `CircularProgressIndicator()` in center during history load |

**Skeleton Suggestion**:
```
ChatSkeleton should show:
- 3-5 skeleton chat bubbles alternating sides (user/AI)
- Use existing SparkleChatBubbleSkeleton for each
- Avatar skeleton circles
- Input bar skeleton at bottom (fixed position)
```

**Reusable Components**: **YES - Perfect match** - `SparkleChatBubbleSkeleton` already exists and is designed exactly for this

**Effort**: **S** (Small - just need to wrap existing skeleton in list)

---

### 3. goal_detail_page.dart

**File**: `/mobile/lib/features/goal/presentation/pages/goal_detail_page.dart`

**Current Loading State**: **BARE SPINNER**

| Aspect | Details |
|--------|---------|
| **Line #** | Line 122: `loading: () => const Center(child: CircularProgressIndicator())` |
| **What loads?** | Goal detail, strategy belief, minimum criteria, bottlenecks, today's step, plan health, accountability, related sources, similar pursuers |
| **Loaded Layout** | Vertical scroll list: Goal header (progress circle + chips), strategy wizard, minimum criteria card, bottleneck strip, today's step card, plan health metrics, accountability summary, related sources list, similar pursuers card |
| **Current Behavior** | Bare spinner centered while `GoalDetailData` loads |

**Skeleton Suggestion**:
```
GoalDetailSkeleton should show:
- Header skeleton: 76x76 circular progress indicator skeleton + 4-5 chip skeletons
- 1-2 card skeletons for strategy wizard and minimum criteria
- 3-4 metric line skeletons (label + progress bar)
- List skeleton for related sources (3-4 items)
- Card skeleton for similar pursuers
```

**Reusable Components**: **YES** - `SparkleCardSkeleton` for most sections, custom header skeleton needed

**Effort**: **M** (Medium - custom header skeleton, rest uses existing card skeletons)

---

### 4. sprint_screen.dart

**File**: `/mobile/lib/features/plan/presentation/screens/sprint_screen.dart`

**Current Loading State**: **BARE SPINNER (2 locations)**

| Aspect | Details |
|--------|---------|
| **Line #** | Line 77: `return const Center(child: CircularProgressIndicator());` <br> Line 172: `loading: () => const Center(child: CircularProgressIndicator())` |
| **What loads?** | Active sprint plan, sprint tasks, sprint achievements, close-to-unlock achievements |
| **Loaded Layout** | Sprint header (name, overview, progress bar, days-left chip), achievements section (progress banner + achievement tiles), task list |
| **Current Behavior** | Two separate loading states: (1) initial plan list load, (2) full plan detail load - both show bare spinners |

**Skeleton Suggestion**:
```
SprintSkeleton should show:
- Large card skeleton for header (title + 2-3 text lines + progress bar skeleton + chip)
- Horizontal scrollable skeleton for achievement tiles (3 tiles)
- List skeleton for tasks (3-4 TaskCard skeletons with checkbox + text)
- Optional: Banner skeleton for "close to unlock" section
```

**Reusable Components**: **YES** - `SparkleListSkeleton` for task list, `SparkleCardSkeleton` for header

**Effort**: **M** (Medium - needs custom TaskCard skeleton, header can use card skeleton)

---

### 5. galaxy_draft_review_screen.dart

**File**: `/mobile/lib/features/galaxy/presentation/screens/galaxy_draft_review_screen.dart`

**Current Loading State**: **BARE SPINNER**

| Aspect | Details |
|--------|---------|
| **Line #** | Line 86: `loading: () => const Center(child: CircularProgressIndicator())` |
| **What loads?** | Galaxy draft batches (prompt-based knowledge extraction) |
| **Loaded Layout** | Dark gradient theme, draft review cards with swipe gestures, meta pills (document name, long-press hint), proposed name + description, excerpts list, similarity banner (if applicable) |
| **Current Behavior** | Bare spinner while batches load |

**Skeleton Suggestion**:
```
GalaxyDraftReviewSkeleton should show:
- Dark gradient background (match final theme)
- Title skeleton ("Reviewing N drafts...")
- Progress skeleton (text line + linear progress bar)
- 2 stacked card skeletons with:
  - Meta pill skeletons (horizontal pills)
  - Title skeleton (large text)
  - 2-3 text line skeletons
  - Mini excerpt list skeleton (2-3 small blocks)
```

**Reusable Components**: Partial - can use `SparkleCardSkeleton` but needs dark theme variant

**Effort**: **M** (Medium - custom dark theme skeleton, but structure similar to card skeleton)

---

### 6. plan_create_screen.dart

**File**: `/mobile/lib/features/plan/presentation/screens/plan_create_screen.dart`

**Current Loading State**: **MISSING ENTIRELY**

| Aspect | Details |
|--------|---------|
| **Line #** | N/A - Form renders immediately with empty/default values |
| **What loads?** | Pending tasks (for reference), existing plan data (if edit mode) |
| **Loaded Layout** | 5-step stepper form: Basics, Time/Structure, Task Blueprint, Boundaries/Guide, Review/Confirm. Each step has multiple form fields |
| **Current Behavior** | Form renders immediately; no loading state for data fetching |

**Skeleton Suggestion**:
```
PlanCreateSkeleton should show:
- Stepper skeleton (5 steps with indicators)
- Form field skeletons for current step:
  - 2-3 text input skeletons (labeled rectangles)
  - 1-2 dropdown button skeletons
  - Optional: Slider skeleton for time structure step
```

**Reusable Components**: Partial - needs custom stepper/form skeleton structure

**Effort**: **M** (Medium - custom skeleton for stepper structure)

---

### 7. group_list_screen.dart

**File**: `/mobile/lib/features/community/presentation/screens/group_list_screen.dart`

**Current Loading State**: **MISSING ENTIRELY**

| Aspect | Details |
|--------|---------|
| **Line #** | N/A - `GroupsHubView()` renders immediately |
| **What loads?** | User's groups, discoverable groups |
| **Loaded Layout** | Hub view with tabs/sections for different group categories |
| **Current Behavior** | Screen renders immediately; groups likely load in-place |

**Skeleton Suggestion**:
```
GroupListSkeleton should show:
- Tab row skeleton (3-4 tabs)
- 2-3 section header skeletons
- Grid/list skeleton for group cards (each card: avatar + title + member count)
- FAB skeleton (floating action button)
```

**Reusable Components**: **YES** - `SparkleListSkeleton` for group list, `SparkleCardSkeleton` for group cards

**Effort**: **S** (Small - mostly uses existing skeletons)

---

### 8. calendar_stats_screen.dart

**File**: `/mobile/lib/features/calendar/presentation/screens/calendar_stats_screen.dart`

**Current Loading State**: **PARTIAL (good pattern exists)**

| Aspect | Details |
|--------|---------|
| **Line #** | Line 842-843: `return const _CalendarInsightsLoadingSkeleton();` |
| **What loads?** | Month aggregate data, streak stats, task summaries |
| **Loaded Layout** | Month/insights/year view modes. Insights view: metric cards (4), heatmap grid, monthly highlights |
| **Current Behavior** | **GOOD EXAMPLE** - Uses `_CalendarInsightsLoadingSkeleton` (lines 1271-1395) with proper structure: metric skeletons, heatmap grid skeleton, bar skeletons |

**Skeleton Suggestion**:
```
Calendar ALREADY HAS proper skeleton implementation:
- _CalendarInsightsLoadingSkeleton (lines 1271-1395)
- _CalendarSkeletonMetric
- _CalendarSkeletonGrid
- _CalendarSkeletonBar
- _CalendarSkeletonDot
```

**Reusable Components**: Already implemented

**Effort**: **N/A** (Already done - use as reference pattern)

---

## Implementation Priority Matrix

| Screen | Impact | Complexity | Priority | Quick Win? |
|--------|--------|------------|----------|------------|
| **chat_screen.dart** | Critical | S | **P0** | YES (existing skeleton) |
| **group_list_screen.dart** | High | S | **P0** | YES (existing skeleton) |
| **goal_detail_page.dart** | Critical | M | **P1** | Partial (card skeleton exists) |
| **sprint_screen.dart** | High | M | **P1** | Partial (list skeleton exists) |
| **galaxy_draft_review_screen.dart** | Medium | M | **P2** | Partial (needs dark theme) |
| **plan_create_screen.dart** | Medium | M | **P2** | No (custom stepper) |
| **task_execution_screen.dart** | Critical | L | **P3** | No (complex custom) |

---

## Reusable Asset Inventory

**Existing Skeletons** (`/mobile/lib/core/design/widgets/sparkle_skeleton.dart`):

1. **`SparkleSkeleton`** - Basic shimmer block (width, height, borderRadius)
2. **`SparkleCardSkeleton`** - Card with title + 2-3 text lines + chip
3. **`SparkleListSkeleton`** - Vertical list of N card skeletons with staggered animation
4. **`SparkleChatBubbleSkeleton`** - Chat message bubble with avatar

**Usage Patterns**:
- ✅ Chat screen: Use `SparkleChatBubbleSkeleton` directly
- ✅ Goal/Sprint/Groups: Use `SparkleCardSkeleton` + `SparkleListSkeleton`
- ⚠️ Galaxy: Need dark-themed variant of card skeleton
- ❗ Task Execution: Fully custom (timer, panels, bottom bar)
- ❗ Plan Create: Stepper skeleton (new pattern)

---

## Recommended Implementation Approach

### Phase 1: Quick Wins (1-2 days)
1. **chat_screen.dart**: Replace bare spinner with `ListView.builder` using `SparkleChatBubbleSkeleton`
2. **group_list_screen.dart**: Add loading state to `GroupsHubView`, use `SparkleListSkeleton`

### Phase 2: Medium Complexity (2-3 days)
3. **goal_detail_page.dart**: Create `GoalDetailSkeleton` using card skeletons + custom header
4. **sprint_screen.dart**: Create `SprintSkeleton` using list skeleton + custom header
5. **galaxy_draft_review_screen.dart**: Create dark-themed card skeleton variant

### Phase 3: Complex Custom (3-4 days)
6. **task_execution_screen.dart**: Create comprehensive `TaskExecutionSkeleton` (timer, panels, controls)
7. **plan_create_screen.dart**: Create `PlanStepperSkeleton` pattern

---

## Design System Integration

All existing skeletons support:
- ✅ Dark/light theme awareness
- ✅ Reduce motion flag (disable shimmer animation)
- ✅ SparkleStaggerItem integration (staggered fade-in)
- ✅ DS spacing tokens (DS.spacing16, etc.)
- ✅ DS color tokens (DS.surfacePrimary, etc.)

**New skeletons should follow these patterns**:
```dart
// Standard pattern
class MyFeatureSkeleton extends StatelessWidget {
  const MyFeatureSkeleton({super.key});

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.all(DS.spacing16),
    child: Column(
      children: [
        SparkleStaggerItem(index: 0, child: /* skeleton 1 */),
        SparkleStaggerItem(index: 1, child: /* skeleton 2 */),
        // ...
      ],
    ),
  );
}
```

---

## Success Criteria

Each screen's loading state should:
1. ✅ Match the final layout structure (no jarring content jumps)
2. ✅ Use appropriate shimmer/skeleton animation (unless reduce motion)
3. ✅ Support dark/light themes
4. ✅ Respect reduce motion settings
5. ✅ Fade in real content smoothly (SparkleStaggerItem pattern)

---

## Testing Checklist

For each implemented skeleton:
- [ ] Loading skeleton appears before data loads
- [ ] Skeleton structure matches loaded content layout
- [ ] Shimmer animation works (unless reduce motion enabled)
- [ ] Dark mode colors are correct
- [ ] Light mode colors are correct
- [ ] Content fade-in is smooth (no flashes)
- [ ] Skeleton disappears immediately when data arrives
- [ ] Error state still works (fallback to error UI)

---

## Estimated Effort Summary

| Priority | Screens | Total Effort |
|----------|---------|--------------|
| P0 (Quick Wins) | 2 | S + S = **Small** (1-2 days) |
| P1 (Medium) | 2 | M + M = **Medium** (2-3 days) |
| P2 (Medium) | 2 | M + M = **Medium** (2-3 days) |
| P3 (Complex) | 1 | L = **Large** (3-4 days) |
| **Total** | **8** | **8-12 days** |

**Note**: Calendar screen already has proper skeleton (use as reference).

---

## References

- **Existing Skeleton Implementation**: `/mobile/lib/core/design/widgets/sparkle_skeleton.dart`
- **Reference Pattern**: `/mobile/lib/features/calendar/presentation/screens/calendar_stats_screen.dart` (lines 1271-1395)
- **Design System**: `/mobile/lib/core/design/design_system.dart` (DS tokens)

---

**Report Generated**: 2026-05-06
**Next Review**: After P0/P1 implementation completion
