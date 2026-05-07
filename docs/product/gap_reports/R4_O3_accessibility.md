# R4-O3: Deep Accessibility Audit of Key Screens

> **Date**: 2026-05-06
> **Auditor**: Automated code-level audit
> **Scope**: 7 primary screens across chat, home, plan, community, insights, goal, and task features
> **Standard**: WCAG 2.1 AA / Material Accessibility Guidelines

---

## Summary Table

| # | Screen | Semantics | Tap Targets | Text Contrast | Reduce Motion | Screen Reader Nav | Score |
|---|--------|-----------|-------------|---------------|---------------|-------------------|-------|
| 1 | Chat Screen | 1/5 | 3/5 | 4/5 | 1/5 | 1/5 | **2.0** |
| 2 | Dashboard Screen | 2/5 | 3/5 | 4/5 | 2/5 | 2/5 | **2.6** |
| 3 | Sprint Review Screen | 4/5 | 4/5 | 4/5 | 3/5 | 4/5 | **3.8** |
| 4 | Accountability Hub Screen | 2/5 | 4/5 | 4/5 | 4/5 | 2/5 | **3.2** |
| 5 | Learning Dashboard Page | 3/5 | 4/5 | 4/5 | 4/5 | 3/5 | **3.6** |
| 6 | Goal Creation Wizard | 4/5 | 4/5 | 5/5 | 2/5 | 4/5 | **3.8** |
| 7 | Task Detail Screen | 1/5 | 2/5 | 4/5 | 1/5 | 1/5 | **1.8** |

**Overall weighted average: 3.0 / 5.0** -- Moderate accessibility baseline, significant gaps in Semantics coverage and Reduce Motion handling.

---

## 1. Chat Screen (`chat_screen.dart`)

**Score: 2.0 / 5.0**

### Semantics Coverage (1/5)

The chat screen is the most complex screen (~4000 lines) and has the worst semantics coverage.

- Only 1 `Semantics()` wrapper found in the entire file (line 3964).
- AppBar icons use `SparkleIconButton` with `semanticLabel`, which is good -- 7 buttons carry semantic labels (back, settings, history, decision timeline, OpenClaw, refresh, close).
- **Critical gap**: Chat bubbles (`ChatBubble` widget) have no visible Semantics wrappers in this file. Each message should be a semantic container with role, sender, and content announced.
- **Critical gap**: The error banner (lines 1954-2083) has no Semantics wrapper. Screen readers cannot announce error state changes.
- **Critical gap**: Quick action cards, comeback banner, divine moment cards (GrowthCard, StrategyInterventionCard, etc.) all lack Semantics.
- **Critical gap**: Status indicators (`AiStatusIndicator`, `AgentReasoningBubble`) are purely visual -- no semantic labels for screen readers.
- The `_ReasoningBreathOverlay` animation is purely decorative but has no `Semantics(excluded: true)`.

### Tap Target Sizes (3/5)

- AppBar `SparkleIconButton` widgets meet 48x48 minimum (the component enforces this).
- Error banner close button uses `InkWell` with `Padding(DS.spacing4)` around a `DS.iconSizeXs` icon -- likely fails 48x48 minimum (approximately 20 + 8 = 28px hit area).
- Chat input area tap targets are handled in a separate widget (`ChatInput`).

### Text Contrast (4/5)

- No `Colors.white70` found. Uses `DS.textSecondary` and `DS.textTertiary` throughout.
- `DS.textTertiary` on surfaces may fail WCAG AA -- needs runtime verification.
- Chat subtitle uses `fontSize: DS.fontSizeXs` with `DS.textSecondary` -- small text + reduced opacity risks low contrast ratio.

### Reduce Motion (1/5)

- **4 AnimationController instances** (lines 3669, 3704, 3799, 3804) with no `reduceMotion` check.
- **1 AnimatedContainer** (line 3884) with no reduce motion guard.
- **TweenAnimationBuilder** (lines 3580, 3726) with no reduce motion guard.
- **AnimatedOpacity** (line 3589) with no reduce motion guard.
- **AnimatedSize** (line 3598) with no reduce motion guard.
- The platform-level `MediaQuery.disableAnimations` is not consulted anywhere in this file.
- `_ReasoningBreathOverlay` uses continuous animation with no disable mechanism.

### Screen Reader Navigation (1/5)

- No logical grouping with `Semantics(container: true)`.
- No headers marked with `Semantics(header: true)`.
- No `Semantics(sortKey:)` to guide reading order.
- Chat messages list uses reverse `ListView.builder` -- the visual order is correct but the semantic traversal order is not customized.
- Multiple status bars, banners, and overlay cards compete for screen reader attention without grouping.

---

## 2. Dashboard Screen (`dashboard_screen.dart`)

**Score: 2.6 / 5.0**

### Semantics Coverage (2/5)

- Only 2 `Semantics()` wrappers found:
  - `_UnderstandingExpansionSlot` has a proper `Semantics(button: true, label: ...)` around the toggle (line 1465).
  - `_AccountabilityMiniCard` has `Semantics(label: title)` (line 1675).
- **Critical gap**: No Semantics on `_CommandCenterRiskBanner` (InkWell without semantic label).
- **Critical gap**: No Semantics on `_GoalChip` (GestureDetector without semantic label).
- **Critical gap**: No Semantics on `DashboardSectionShell` headers -- section titles are not announced as headers.
- **Critical gap**: No Semantics on error state (lines 1152-1232) -- failure icons and messages are invisible to screen readers.
- **Critical gap**: No Semantics on skeleton loading states.
- The Aurora correction dialog (lines 67-123) has no `Semantics` -- the text field and buttons rely on Flutter defaults.

### Tap Target Sizes (3/5)

- `_GoalChip` uses `ConstrainedBox(constraints: BoxConstraints(minHeight: 44))` -- meets 44px minimum but not the recommended 48px.
- `SparkleIconButton` with `size: 34` appears in several places (briefing toggle, updates toggle, accountability trailing) -- these are 34x34, well below the 48x48 minimum.
- `_CommandCenterRiskBanner` uses `InkWell` without explicit sizing -- may meet minimum via padding.
- `_SectionCountPill` and `_DashboardChip` are display-only (no onTap), so tap target is not required.

### Text Contrast (4/5)

- Uses `DS.textSecondary` and `DS.textTertiary` throughout. No hardcoded `Colors.white70`.
- `_DashboardChip` uses `DS.textSecondary` on `DS.surfaceOverlay` background -- may be borderline.
- Error state text uses inline `TextStyle(color: DS.textSecondary, fontSize: 14)` -- relies on DS token contrast.

### Reduce Motion (2/5)

- **AnimatedSize** used in 3 places (lines 1514, 2450, 2961) -- no reduce motion check.
- **AnimatedSwitcher** (line 1932) -- no reduce motion check.
- **AnimatedRotation** (lines 2439, 2944) -- no reduce motion check.
- Positive: `dashboard_motion.dart` (used by `SparkleStaggerItem`) does check `platformDispatcher.accessibilityFeatures.disableAnimations`. The stagger animations are properly guarded.
- `ScrollEdgeHaptics` does not check reduce motion before triggering haptic feedback.

### Screen Reader Navigation (2/5)

- `_UnderstandingExpansionSlot` provides a labeled button -- good.
- No `Semantics(container: true)` to group dashboard sections.
- No `Semantics(header: true)` on section titles.
- The scrollable content has dozens of sections with no semantic structure -- screen reader users get a flat list.

---

## 3. Sprint Review Screen (`sprint_review_screen.dart`)

**Score: 3.8 / 5.0**

### Semantics Coverage (4/5)

This is the most accessibility-aware screen in the audit.

- `_ProgressHero` wraps its content in `Semantics(container: true, explicitChildNodes: true, label: ...)` with a meaningful label including sprint name, progress, and days left (line 155-158).
- `_StatChip` wraps its content in `Semantics(container: true, label: '$label: $value')` (line 275-278).
- `_BottleneckCard` insight rows each have `Semantics(container: true, label: '${i.title}: ${i.detail}')` (line 394-396).
- `_ReviewNotesCard` wraps in `Semantics(container: true, explicitChildNodes: true, label: ...)` (line 478-481).
- `_ReviewStatusBanner` wraps in `Semantics(container: true, label: ...)` (line 587-589).
- **Gap**: `_SectionHeader` has no `Semantics(header: true)` -- section titles are not announced as headers.
- **Gap**: The continue/adjust buttons have no explicit semantic labels beyond their text content.

### Tap Target Sizes (4/5)

- All buttons use `FilledButton` or `OutlinedButton` which enforce minimum 64x36 via Material defaults.
- `SparkleIconButton` for back button meets 48x48.
- `TextButton` in error banner meets Material defaults.
- **Minor gap**: No explicit `minimumSize` constraint on action buttons, relying on Material defaults which are adequate.

### Text Contrast (4/5)

- No `Colors.white70` or low-alpha hardcoded colors.
- `DS.textSecondary` used for secondary text, `DS.textTertiary` for hints.
- Urgent text uses `DS.error` color which should have adequate contrast.
- `DS.warning.withValues(alpha: 0.1)` as background is fine (not text).

### Reduce Motion (3/5)

- **TweenAnimationBuilder** in `_ProgressHero` (line 176) -- no reduce motion check. The progress bar animates from 0 to actual value.
- No `AnimationController` instances in this screen.
- Positive: The animation is subtle (progress indicator fill) and not disorienting.
- `SparkleCardSkeleton` may include animations but no controllers visible.

### Screen Reader Navigation (4/5)

- Good use of `Semantics(container: true)` for logical grouping.
- `explicitChildNodes: true` used correctly where inner content should be individually accessible.
- Meaningful semantic labels that combine multiple data points (name + progress + days).
- **Gap**: No `Semantics(header: true)` on section titles.
- **Gap**: Reading order is linear (top-to-bottom ListView) which is logical, but no `sortKey` customization.

---

## 4. Accountability Hub Screen (`accountability_hub_screen.dart`)

**Score: 3.2 / 5.0**

### Semantics Coverage (2/5)

- `_HubHeader` uses `Semantics(header: true)` -- the only screen in the audit that marks a header (line 115).
- **Gap**: No Semantics on `_PartnerProgressCard` -- the circular progress indicator, partner name, goal summary, and check status are all visual.
- **Gap**: No Semantics on `_SharedGoalCard` -- progress bar and member chips are not announced.
- **Gap**: No Semantics on `_MetricTile` -- icon, value, and label are visual-only.
- **Gap**: No Semantics on `_Section` titles -- section labels are not announced as headers.
- **Gap**: No Semantics on `_HelpRow` items.
- `IconButton` in AppBar has a `Tooltip` but no explicit `semanticLabel` -- Flutter propagates tooltip as semantics, which is adequate.
- Refresh button has `Tooltip(message: context.l10n.cahRetry)` which provides semantic meaning.

### Tap Target Sizes (4/5)

- All `FilledButton`, `OutlinedButton`, and `TextButton` widgets meet Material defaults.
- `IconButton` in AppBar meets 48x48 via Material defaults.
- `Chip` widgets (member chips) are display-only.
- `ActionChip` for nudge meets Material defaults.
- **Minor gap**: `_MetricTile` is display-only but has no `onTap` -- not interactive, so tap target is not required.

### Text Contrast (4/5)

- Uses `colorScheme.onSurfaceVariant` for secondary text -- follows Material theming.
- No hardcoded low-alpha text colors.
- `colorScheme.error` used for error state with adequate contrast.

### Reduce Motion (4/5)

- No `AnimationController` instances.
- No `AnimatedContainer`, `AnimatedOpacity`, or `TweenAnimationBuilder`.
- `RefreshIndicator` uses platform-standard animation (properly respects system settings).
- Minimal animation usage -- this screen is mostly static content.

### Screen Reader Navigation (2/5)

- `_HubHeader` is the only Semantics-annotated group.
- All other sections (`_CommitmentsSection`, `_PartnerProgressSection`, `_SharedGoalsSection`, etc.) have no semantic grouping.
- No `Semantics(container: true)` for card boundaries.
- The horizontal `ListView.separated` for commitments is not semantically described.

---

## 5. Learning Dashboard Page (`learning_dashboard_page.dart`)

**Score: 3.6 / 5.0**

### Semantics Coverage (3/5)

- Top-level `Semantics(label: context.l10n.gdDashboardSemantics, container: true)` wraps the entire dashboard content (line 58-59).
- `_SectionCard` titles and icons are visually clear but have no Semantics wrappers.
- `_TimeDistributionChart` -- progress bars and labels are purely visual, no Semantics.
- **Critical gap**: `_RingMetric` (CircularProgressIndicator with percentage label) has no Semantics. Screen readers cannot determine the progress value.
- **Critical gap**: `_WeaknessRadar` (CustomPaint) has no Semantics. The radar chart is completely invisible to screen readers.
- **Critical gap**: `_KnowledgeChanges` direction arrows (up/down) are icon-only with no semantic labels.
- `_InlineEmpty` has no Semantics to indicate empty state.
- `_DashboardError` relies on `EmptyState` widget which may or may not have Semantics.

### Tap Target Sizes (4/5)

- `SparkleIconButton` for back button meets 48x48.
- `RefreshIndicator` provides adequate gesture area.
- No small interactive elements -- chips and metric tiles are display-only.
- `_MetricChip` containers are display-only (no onTap).

### Text Contrast (4/5)

- Uses `colorScheme.onSurfaceVariant` for secondary text.
- `colorScheme.secondaryContainer` + `onSecondaryContainer` for metric chips -- proper Material contrast.
- No hardcoded low-alpha colors.

### Reduce Motion (4/5)

- No `AnimationController` instances.
- No `AnimatedContainer`, `AnimatedOpacity`, or `TweenAnimationBuilder`.
- `LinearProgressIndicator` and `CircularProgressIndicator` do not use explicit animations.
- Minimal animation risk.

### Screen Reader Navigation (3/5)

- Top-level `Semantics(container: true)` provides one logical group.
- Inner sections are not individually grouped.
- The `_SectionCard` pattern provides visual structure but no semantic structure.
- `_RadarPainter` (CustomPaint) needs a `Semantics` wrapper describing the data as text.

---

## 6. Goal Creation Wizard Screen (`goal_creation_wizard_screen.dart`)

**Score: 3.8 / 5.0**

### Semantics Coverage (4/5)

This screen has the most comprehensive Semantics annotations.

- The entire wizard body is wrapped in `Semantics(container: true, explicitChildNodes: true, label: ...)` with a step-by-step description (lines 80-86).
- `_WizardProgress` has `Semantics(container: true, label: ...)` announcing progress (line 419-422).
- Each step is wrapped in `Semantics(container: true, label: currentStepLabel)` (line 98-99).
- `CircularProgressIndicator` has `semanticsLabel: 'Loading'` (line 134).
- Icons have `semanticLabel` for back arrow and forward/create icons (lines 120, 138, 142).
- **Gap**: `ChoiceChip` in `_GoalTypeStep` has no explicit semantic labels beyond the visible text.
- **Gap**: `SegmentedButton` in `_TimeHorizonStep` relies on visible text labels -- adequate but no additional context.
- **Gap**: `_ErrorBanner` close `IconButton` has only `tooltip: 'Close'` -- should use localized string.

### Tap Target Sizes (4/5)

- `FilledButton` and `OutlinedButton` in navigation bar meet Material defaults.
- `ChoiceChip` meets Material defaults (minimum 48x48).
- `SegmentedButton` meets Material defaults.
- `TextFormField` and `TextField` meet Material defaults.
- **Minor gap**: Loading spinner in button is 16x16 -- but parent button provides the tap target.

### Text Contrast (5/5)

- Uses Material `Theme.of(context).textTheme` throughout.
- `DS.textSecondary` used for rationale text.
- No hardcoded low-alpha colors.
- `DS.error100` background + `DS.error` border/text in error banner -- proper contrast.

### Reduce Motion (2/5)

- **AnimatedSwitcher** for step transitions (line 101) -- duration 180ms, no reduce motion check.
- No `AnimationController` instances directly, but `AnimatedSwitcher` uses implicit animation.
- The step transition animation may be disorienting if the content changes significantly.

### Screen Reader Navigation (4/5)

- Step-by-step semantic labels provide clear navigation context.
- `Semantics(container: true, explicitChildNodes: true)` on wizard body provides logical grouping.
- `_WizardProgress` announces current step and total steps.
- **Gap**: No `Semantics(header: true)` on step titles.
- **Gap**: Milestone editor cards have no semantic grouping.

---

## 7. Task Detail Screen (`task_detail_screen.dart`)

**Score: 1.8 / 5.0**

### Semantics Coverage (1/5)

- **Zero** `Semantics()` wrappers in the entire file.
- `SparkleIconButton` widgets in the SliverAppBar have no explicit `semanticLabel` -- unlike the chat screen which properly labels them.
- **Critical gap**: The entire SliverAppBar header area (task title, type chips, status chips) has no Semantics. Screen readers cannot access the task metadata.
- **Critical gap**: `_InfoTileCard` widgets (duration, difficulty, energy, deadline) have no Semantics.
- **Critical gap**: `_StructuredGuideSection` with method steps, key points, and action buttons has no Semantics.
- **Critical gap**: `_GuideInfoRow` items are purely visual.
- **Critical gap**: Subtask section (`ExpansionTile`) relies on Flutter's default semantics -- may be adequate but unverified.
- **Critical gap**: Bottom action bar (edit, start/resume, delete) buttons rely on text labels only -- no additional semantic context.
- **Critical gap**: The move-to-plan picker and share sheet dialogs have no semantic context.
- `SourceLifecycleBadgeGroup` and `WhyThisTodayPanel` are delegated to sub-widgets -- Semantics unknown.

### Tap Target Sizes (2/5)

- **Critical gap**: `_InfoTileCard` uses `GestureDetector` with `ScaleTransition` for a tap animation (line 809). The `GestureDetector` does not enforce minimum tap target size. With `DS.spacing16` padding (16px), the effective hit area depends on content size and may fall below 48px on some rows.
- Delete button uses `SparkleIconButton(size: 40)` wrapped in a `DecoratedBox` -- 40px is below the 48x48 minimum.
- Plan context card uses `InkWell` (line 606) which relies on parent sizing.
- Bottom bar buttons use `CustomButton` which should meet Material defaults.
- The icon in `_InfoTileCard` gradient container is 18x18 with `DS.spacing10` (10px) padding -- the container is about 38x38, below 48px.

### Text Contrast (4/5)

- `DS.neutral600` used for tile titles -- should have adequate contrast.
- `DS.neutral900` used for content values -- high contrast.
- `DS.textSecondary` used for note content -- relies on DS token.
- `Colors.white` used for icons on gradient backgrounds -- may have contrast issues depending on gradient colors.

### Reduce Motion (1/5)

- **1 AnimationController** in `_InfoTileCardState` (line 787) for press-to-scale animation -- no reduce motion check.
- `ScaleTransition` animates between 1.0 and 0.95 on tap -- no reduce motion check.
- `Hero` animation on the SliverAppBar (line 367) -- no reduce motion check.
- `SparkleStaggerList` used for content staggering -- may or may not respect reduce motion (depends on implementation).

### Screen Reader Navigation (1/5)

- No semantic grouping whatsoever.
- No headers marked.
- No logical reading order customization.
- The screen is a complex CustomScrollView with SliverAppBar + SliverToBoxAdapter -- screen readers get a flat, unlabeled traversal.
- Bottom action bar is outside the scroll area -- reading order is: header, content, bottom bar. This is logical but not semantically annotated.

---

## Cross-Cutting Findings

### 1. Semantics Coverage is Sparse

Only 2 of 7 screens (Sprint Review, Goal Wizard) have meaningful Semantics annotations. The other 5 screens have minimal to zero coverage. Key missing patterns:

- **No `Semantics(header: true)`** on section titles across all screens except Accountability Hub.
- **No `Semantics(container: true)`** for logical grouping in most screens.
- **Interactive cards** (PartnerProgressCard, InfoTileCard, DashboardChip) lack semantic context.
- **Charts and data visualizations** (radar chart, ring metric, time distribution) are completely invisible to screen readers.

### 2. Reduce Motion is Almost Universally Ignored

Only `dashboard_motion.dart` and `omnibar.dart` check `MediaQuery.disableAnimations`. The 7 audited screens contain:

- 6 AnimationController instances (chat: 4, task: 1) -- none check reduce motion.
- 5 AnimatedContainer/AnimatedOpacity/AnimatedSize instances -- none check reduce motion.
- 4 TweenAnimationBuilder instances -- none check reduce motion.
- Multiple AnimatedSwitcher and AnimatedRotation instances -- none check reduce motion.

### 3. Tap Targets are Mostly Adequate via Material Defaults

Most interactive elements use Material components (`FilledButton`, `OutlinedButton`, `TextButton`, `Chip`, `IconButton`) which enforce minimum sizes. Exceptions:

- `SparkleIconButton(size: 34)` in dashboard -- 6 instances below 48px.
- `SparkleIconButton(size: 40)` for delete in task detail -- 1 instance below 48px.
- `GestureDetector` without size constraints in dashboard `_GoalChip` (44px) and task `_InfoTileCard`.
- Error banner close buttons use small tap areas (28-32px).

### 4. Text Contrast Relies on Design Tokens

All screens use the DS token system (`DS.textPrimary`, `DS.textSecondary`, `DS.textTertiary`) or Material `colorScheme` tokens. No hardcoded `Colors.white70` or similar low-alpha violations were found. This is a positive finding -- the design system layer handles contrast correctly. The risk is in `DS.textTertiary` which may be too light for WCAG AA at small font sizes. This needs runtime contrast ratio measurement.

### 5. Accessibility Settings Infrastructure Exists

The codebase has an `AccessibilitySettings` provider (`mobile/lib/features/settings/presentation/providers/accessibility_provider.dart`) with `reduceMotion` support, and an accessibility settings screen. However, **no audited screen consumes this provider**. The setting exists but is disconnected from the UI layer.

---

## Recommendations (Priority Order)

### P0 -- Must Fix

| ID | Issue | Screens Affected | Effort |
|----|-------|------------------|--------|
| A11Y-01 | Add Semantics wrappers to all interactive and informational cards | Task Detail, Chat, Dashboard | Medium |
| A11Y-02 | Add Semantics to data visualizations (charts, progress rings, radar) | Learning Dashboard, Accountability Hub | Medium |
| A11Y-03 | Fix tap targets below 48px (SparkleIconButton size:34, size:40) | Dashboard, Task Detail | Small |
| A11Y-04 | Screen reader navigation for Chat messages (role, sender, content per bubble) | Chat | Large |

### P1 -- Should Fix

| ID | Issue | Screens Affected | Effort |
|----|-------|------------------|--------|
| A11Y-05 | Respect reduce motion in AnimationController instances | Chat (4), Task (1) | Small |
| A11Y-06 | Respect reduce motion in AnimatedSwitcher/AnimatedSize/AnimatedRotation | Dashboard, Chat | Small |
| A11Y-07 | Add `Semantics(header: true)` to all section titles | All 7 screens | Small |
| A11Y-08 | Add `Semantics(container: true)` for logical card grouping | All 7 screens | Medium |
| A11Y-09 | Wire `AccessibilitySettings.reduceMotion` provider into animation guards | All animated screens | Medium |

### P2 -- Nice to Have

| ID | Issue | Screens Affected | Effort |
|----|-------|------------------|--------|
| A11Y-10 | Add `Semantics(sortKey:)` for non-linear reading order | Chat, Dashboard | Medium |
| A11Y-11 | Live region announcements for status changes (AI thinking, error states) | Chat | Medium |
| A11Y-12 | Verify DS.textTertiary contrast ratio at all font sizes | System-wide | Small |
| A11Y-13 | Add semantic labels to Hero transitions | Task Detail | Small |
| A11Y-14 | Audit sub-widgets (ChatBubble, EmptyState, etc.) for Semantics | Cross-cutting | Large |

---

## Methodology

This audit was performed by static code analysis of the 7 specified screen files. Each file was read in full and examined for:

1. `Semantics()` widget usage and label quality
2. Interactive element sizes (GestureDetector, InkWell, IconButton dimensions)
3. Hardcoded low-contrast colors (`Colors.white70`, alpha values)
4. AnimationController, Animated*, and Tween* usage with reduce motion checks
5. `Semantics(container: true)`, `Semantics(header: true)`, and `Semantics(sortKey:)` patterns

**Limitations**: This audit does not include runtime testing with TalkBack/VoiceOver, does not measure actual contrast ratios, and does not verify sub-widget Semantics implementations (those would require reading 50+ additional widget files).
