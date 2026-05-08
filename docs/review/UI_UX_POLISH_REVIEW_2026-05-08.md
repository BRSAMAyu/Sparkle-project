# UI/UX Polish Review Document
**Date**: 2026-05-08 | **Phases**: 1-6 | **Files**: 8

---

## Commit History

```
379208058  polish(ui): haptic feedback and micro-interaction consistency
465e4a258  fix(chat): overflow guards for small screens
22dacfeac  feat(profile): UI/UX polish for My page - 5 phases complete
f25fcc585  chore: add startup smoke test + CI/CD workflows + production env template
2b7dc4518  polish(dashboard): context-aware skeletons, snappier animations, wider text scale
79daf30bb  fix(chat): correct gradient fade colors and clean up unused import
8dbb1520c  feat(chat): three-state message height with gradient indicators
63be072ba  fix(chat): improve message detail view with smart thresholds and swipe fix
6e7388915  refactor(chat): cluster accessory widgets into horizontal chip row
```

---

## Phase 1: Chat Accessory Clustering
**Commit**: `6e7388915` | **File**: `chat_bubble.dart`

### Problem
AI message accessories (cards, traces, previews) rendered as individually-padded `CollapsibleWidgetWrapper` in a vertical `Column`. 5-8 chips = 170-270px vertical space, pushing AI text off-screen.

### Solution
Created `_buildAccessoryCluster()` method that groups all disclosure-based accessories into a `Wrap` layout (horizontal flow).

### Key Changes

| Line | Change |
|------|--------|
| ~1188-1538 | Extract all disclosure-based accessories into `_buildAccessoryCluster()` |
| ~1200 | `Wrap(spacing: DS.spacing6, runSpacing: DS.spacing4)` for horizontal chip layout |
| Collapsed chips | Horizontal row (~170px wide) vs 5 rows (~250px tall) |

### Verification Checklist
- [ ] Send message that triggers plan + task + cognitive widgets → chips in horizontal row
- [ ] AI text visible without scrolling after chips populate
- [ ] Expand any chip → content appears below chip row
- [ ] Wrap respects screen width, chips wrap to second row if needed

---

## Phase 2: Message Detail View Polish
**Commit**: `63be072ba` | **Files**: `chat_bubble.dart`, `message_detail_view.dart`

### Problem 1: Swipe vs scroll conflict
`Dismissible` on message detail view conflicted with content scrolling — swiping down would dismiss even when content wasn't at top.

### Solution 1
Converted `MessageDetailView` from `StatelessWidget` to `StatefulWidget` with `ScrollController`. Replaced `Dismissible` with `GestureDetector`:

```dart
// Before (chat_bubble.dart:46)
Dismissible(
  key: Key('message-detail-${widget.message.id}'),
  direction: DismissDirection.down,
  ...
)

// After
GestureDetector(
  onVerticalDragEnd: (details) {
    final velocity = details.primaryVelocity ?? 0;
    final atTop = !_scrollController.hasClients || _scrollController.offset <= 0;
    if (atTop && velocity > 300) {
      Navigator.of(context).pop();
    }
  },
  ...
)
```

### Problem 2: Tap threshold too strict
`content.length < 60` ignored multi-line short messages.

### Solution 2
```dart
final lineCount = '\n'.allMatches(chatMessage.content).length + 1;
if (chatMessage.content.length < 60 && lineCount < 4) return;
```

### Problem 3: No entry animation
Tapping to open detail view had no scale animation.

### Solution 3
Added `ScaleTransition` wrapper in page builder:
```dart
pageBuilder: (context, animation, secondaryAnimation) =>
    FadeTransition(
      opacity: animation,
      child: ScaleTransition(
        scale: Tween<double>(begin: 0.95, end: 1.0).animate(
          CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
        ),
        child: MessageDetailView(...),
      ),
    ),
```

### Verification Checklist
- [ ] Tap 3-line list message → opens detail view
- [ ] Scroll long content → no accidental dismiss
- [ ] Swipe down at content top with velocity > 300 → dismisses
- [ ] Entry animation (fade + scale 0.95→1.0) visible on open
- [ ] Multi-line short message (e.g., "Line 1\nLine 2\nLine 3") opens detail view

---

## Phase 3: Three-State Message Height
**Commit**: `8dbb1520c` | **File**: `chat_bubble.dart`

### Problem
Messages >500 chars were binary: collapsed at `min(screenHeight * 0.5, 280.0)` or full height. No intermediate state.

### Solution
Replaced `Set<String>` with `Map<String, int>` for height state:
- 0 = compact (default): `min(screenHeight * 0.35, 220.0)` — ~10-12 lines
- 1 = comfortable (first tap): `min(screenHeight * 0.55, 350.0)` — most content visible
- 2 = full (second tap): no constraint

Gradient fade at bottom of compact/comfortable states:
```dart
Positioned(
  bottom: 0, left: 0, right: 0, height: 40,
  child: DecoratedBox(
    decoration: BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          isUser ? DS.chatBubbleUser.withValues(alpha: 0) : DS.chatBubbleOther.withValues(alpha: 0),
          isUser ? DS.chatBubbleUser : DS.chatBubbleOther,
        ],
      ),
    ),
  ),
),
```

Gradient colors match actual bubble backgrounds (fixed in `79daf30bb` from review feedback).

### Verification Checklist
- [ ] Long AI message shows compact with gradient fade
- [ ] First tap → comfortable height (more lines visible)
- [ ] Second tap → full height, no gradient
- [ ] Gradient uses correct bubble background color (user=DS.chatBubbleUser, AI=DS.chatBubbleOther)
- [ ] "Read more" text only shown when in compact/comfortable (hidden at full)

---

## Phase 4: Dashboard Visual Refinement
**Commit**: `2b7dc4518` | **Files**: `dashboard_screen.dart`, `collapsible_slot.dart`, `compact_status_bar.dart`

### Change 1: Context-aware skeletons
Replaced generic `SparkleCardSkeleton` with shape-matched variants:
- `_CompactStatusBarSkeleton`: Short wide bar (48px height)
- `_AuroraStatusBandSkeleton`: Thin strip (40px height)
- `_CommandCenterSkeleton`: Horizontal layout (120px height)

### Change 2: Faster collapse animation
`collapsible_slot.dart`:
```dart
AnimatedSize(
  duration: DS.motionDuration(SparkleMotionToken.responsive), // Was DS.durationNormal (250ms)
  curve: DS.curveEaseInOut,
```

### Change 3: Relaxed text scale threshold
`compact_status_bar.dart`:
```dart
// Before: textScale < 1.05
// After:  textScale < 1.2
final showWeatherLabel = width >= 390 && textScale < 1.2;
```

### Verification Checklist
- [ ] Dashboard loads → skeletons match approximate card shapes
- [ ] Skeleton → content transition smooth (AnimatedSwitcher)
- [ ] Collapsing dashboard slot animates faster (180ms vs 250ms)
- [ ] Weather label visible on devices with text scale up to 1.19
- [ ] Weather label hidden when textScale ≥ 1.2

---

## Phase 5: Overflow Guards
**Commit**: `465e4a258` | **File**: `chat_screen.dart`

### Problem
Chat bottom input area overflowed when multiple pills (PlanSelector, ChatMode, AiReasoning, IntentPrediction) stacked vertically on small screens.

### Solution
```dart
return ConstrainedBox(
  constraints: BoxConstraints(
    maxHeight: MediaQuery.of(context).size.height * 0.4,
  ),
  child: SingleChildScrollView(
    physics: const ClampingScrollPhysics(), // Was NeverScrollableScrollPhysics
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [...],
    ),
  ),
);
```

### Verification Checklist
- [ ] iPhone SE / small screen → bottom input area doesn't overflow
- [ ] Many pills stack → scrolls internally instead of overflow
- [ ] Input field still functional when scrolled

---

## Phase 6: Micro-interaction Polish
**Commit**: `379208058` | **Files**: `collapsible_widget_wrapper.dart`, `message_detail_view.dart`

### Change 1: Haptic on collapse button
```dart
onTap: () {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
  _setExpanded(false);
},
```

### Change 2: Content fade-in
```dart
TweenAnimationBuilder<double>(
  tween: Tween(begin: 0.0, end: 1.0),
  duration: const Duration(milliseconds: 120),
  builder: (context, opacity, child) => Opacity(
    opacity: opacity,
    child: child,
  ),
  child: Stack(...) // wrapped content
)
```

### Change 3: Bottom gradient in detail view
```dart
bool _hasScrolledToBottom = false;

// Scroll tracking
NotificationListener<ScrollNotification>(
  onNotification: (notification) {
    if (notification is ScrollEndNotification) {
      setState(() {
        _hasScrolledToBottom = _scrollController.hasClients &&
            _scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 1;
      });
    }
    return false;
  },
  ...
)

// Gradient overlay
if (!_hasScrolledToBottom)
  Positioned(
    bottom: 0, left: 0, right: 0, height: 32,
    child: DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Theme.of(context).colorScheme.surface.withValues(alpha: 0),
            Theme.of(context).colorScheme.surface,
          ],
        ),
      ),
    ),
  ),
```

### Verification Checklist
- [ ] Haptic feedback on collapse button tap
- [ ] Expanded content fades in over 120ms
- [ ] Bottom gradient visible on long content until scrolled to bottom
- [ ] Gradient disappears when scrolled to end

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total commits | 6 |
| Files modified | 8 |
| Lines added | ~400 |
| Errors | 0 |
| Info-level issues | 52 (pre-existing in chat_screen.dart) |

## Test Scenarios

1. **Accessory crowding**: Send message that triggers plan + 3 tasks → chips in horizontal row, AI text visible
2. **Detail view**: Tap multi-line message → opens with scale animation → scroll content → no accidental dismiss → swipe down at top → dismisses
3. **Three-state height**: Long message → compact with gradient → tap → comfortable → tap → full
4. **Dashboard**: Load dashboard → skeletons match shapes → smooth fade to content
5. **Small screen overflow**: iPhone SE → input area scrolls internally, no overflow
6. **Micro-interactions**: Expand/collapse widget → haptic + fade animation → detail view → bottom gradient

---

## Verification Commands

```bash
# Analyze all modified files
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter analyze \
  lib/features/chat/presentation/widgets/chat_bubble.dart \
  lib/features/chat/presentation/screens/chat_screen.dart \
  lib/features/chat/presentation/widgets/collapsible_widget_wrapper.dart \
  lib/features/chat/presentation/widgets/message_detail_view.dart \
  lib/features/home/presentation/screens/dashboard_screen.dart \
  lib/features/home/presentation/widgets/collapsible_slot.dart \
  lib/features/home/presentation/widgets/compact_status_bar.dart

# Run widget tests
flutter test test/widget/

# Visual verification on simulator
flutter run -d <simulator_id>
```
