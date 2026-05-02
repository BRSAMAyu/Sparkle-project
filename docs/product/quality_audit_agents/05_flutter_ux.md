# Quality Audit Agent Report: 05_flutter_ux

Agent ID: af02da637b417f15e

I'll conduct a thorough UX quality audit across all five dimensions. Let me start by reading the key files and searching for patterns in parallel.

---

Now let me read the chat_screen.dart in sections to find the relevant areas, and also read the supporting files.

---

Now let me read key sections of chat_screen.dart for the error/loading/correction patterns, and check for live regions and accessibility details.

---

Let me now check a few more critical items: the chat_design_language_widgets for the AiStatusIndicator, the error bar in chat_screen, and the `_OfflineQueueIndicatorHost` area.

---

Now let me check the calibration_receipt_chip for its dismiss persistence and the `_OfflineQueueIndicatorHost` in chat_screen.

---

I now have comprehensive evidence across all five dimensions. Here is the full audit report.

---

# Flutter UX Quality Audit Report

## Dimension 1: Aurora Status Band Quality

**File:** `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart`

### Visual Hierarchy (Layer 1 -- Collapsed): **EXCELLENT**

The collapsed state is genuinely glanceable. It contains exactly three visual elements in a single row: a colored `_StatusPill` with "Aurora" text, a single-line `AnimatedSwitcher` label (e.g., "calibrated", "risk_found"), and a count fraction "3/5" plus chevron. The `maxLines: 1` with `TextOverflow.ellipsis` ensures no wrapping. The animated color pill communicates state at the pre-attentive level -- users do not need to read to know something changed. The `AnimatedSwitcher` with `easeOutCubic`/`easeInCubic` on the text label makes state transitions legible rather than jarring.

Supporting sub-pills (time context, task health, correction effect) are visually subordinate via smaller 11px text and consistent left padding of `DS.spacing20`, creating clear indentation hierarchy.

### Interaction Quality (Layer 2 -- Correction Chips): **GOOD**

Correction chips in `Wrap` have `BoxConstraints(minHeight: 32, minWidth: 44)` for `_StatusCorrectionChip` and `_PredictedOptionChip`. The minWidth of 44dp meets Apple HIG / Material tap target guidelines. However, the minHeight of 32dp is below the 44dp minimum -- on a real phone, the visual height may pass because of 6px padding + text, but the constraint explicitly allows as short as 32dp. The fallback correction chips at line 1377 use the same 32x44 constraint. The `ContextualCorrectionBar._CorrectionChip` (line 573 of contextual_correction_bar.dart) correctly enforces `minWidth: 44, minHeight: 44`, which is the gold standard. The status bar's own chips should match.

### Layer 3 Depth (Four Cards): **EXCELLENT**

The four cards -- Current Status, Memory References, Next Suggestion, Self-Evaluation -- are genuinely information-dense, not decorative:

1. **Current Status** surfaces `summary` plus up to 5 evidence items from `statusEvidenceChain`, time context, task health, and facet signals.
2. **Memory References** surfaces actual referenced memories or falls back to user_model/goal_model facet summaries.
3. **Next Suggestion** uses backend suggestion or falls back intelligently to predicted options or wake reasons.
4. **Self-Evaluation** shows `selfEvaluation.why` with confidence percentage and risk bullets.

Each card is independently collapsible via `AuroraStatusLayerCard` with `AnimatedCrossFade`. Bullet count is capped at 4, preventing information overload.

### State Transition Animation: **EXCELLENT**

- `AnimatedContainer` with 300ms `easeInOutCubic` on the bar container handles background gradient transition.
- `AnimatedSwitcher` with 300ms handles the text label cross-fade.
- `SizeTransition` with the same `_expandAnimation` controller animates layer 2/3 expansion.
- The `_CorrectionEffectPill` uses `DS.semanticSuccess` color, clearly communicating "correction applied."
- The `_ShimmerDot` uses 1200ms breathing animation for loading state -- appropriate, not distracting.

### Accessibility (All 3 Layers): **GOOD**

- Layer 1: Full `Semantics(button: true, label: collapsedLabel, onTap: ...)` wrapping.
- Layer 2/3: Every `_ActionChip`, `_StatusCorrectionChip`, `_PredictedOptionChip` has `Semantics(button: true, label: ...)` with `ExcludeSemantics` on the visual child to prevent double-announcements.
- `_TimeContextPill`, `_TaskHealthPill`, `_CorrectionEffectPill` all have `Semantics` with meaningful labels.
- `_BarContainer` uses `Semantics(container: true, explicitChildNodes: true)` -- correct for composite controls.
- **Gap:** No `liveRegion: true` on the status bar. When Aurora's state changes (e.g., from "sensing" to "risk_found"), a screen reader user will not be proactively notified.

### Dimension 1 Overall: **GOOD**
The only deductions: 32dp minHeight on some chips (should be 44dp), and no live region for status changes.

---

## Dimension 2: Receipt System Quality

**Files:** `aurora_receipt_chip.dart`, `calibration_receipt_chip.dart`

### Quietness: **EXCELLENT**

- `AuroraReceiptChip`: The collapsed state is a single subtle row -- a 13px icon, one-line summary text, optional count badge, and optional chevron. The container uses `DS.surfaceHigh.withValues(alpha: 0.6)` background with `DS.borderSubtle` border. The margin is only `top: 6, bottom: 2`. This is genuinely unobtrusive.
- `CalibrationReceiptChip`: Even more minimal. Same alpha level, a tune icon, one-line summary, and tiny chevron. Uses `AnimatedOpacity` and `AnimatedSize` for gentle entrance.
- Receipts with no visible data return `SizedBox.shrink()` -- zero visual footprint.

### Discoverability: **GOOD**

- The `AuroraReceiptChip` has a chevron icon (`Icons.chevron_right`) on the right when `_hasDetail` is true, signaling tappability. The `InkWell` with `BorderRadius.circular(8)` provides a tap ripple.
- `CalibrationReceiptChip` uses `Icons.keyboard_arrow_down_rounded` that flips to up, which is a universal "expand" affordance.
- **Concern:** There is no explicit "tap for details" hint for sighted users unfamiliar with the pattern. The discoverability relies entirely on the chevron convention.

### Information Density: **EXCELLENT**

Three well-separated levels:
1. **Collapsed**: One-line summary with type icon and count badge. Precise.
2. **Expanded (CalibrationReceiptChip)**: What changed, why, and next-time effect -- each in its own `_ReceiptDetailLine` with icon, label, and value.
3. **Detail sheet (AuroraReceiptChip)**: Full bottom sheet with memory cards (each with content, metadata, confidence, and a "Not right" correction button), source lists, tool summaries, excluded sources, and action chips.

The `_MemoryReceiptRow` is particularly well-designed: content, metadata line (time, source, confidence, confirmed status), and a correction action -- all in a compact card.

### Dismiss Behavior: **ADEQUATE**

- `CalibrationReceiptChip`: Has an explicit dismiss `IconButton` with close icon, `SensoryFeedbackService.emit(SensoryFeedbackEvent.selection)`, and `setState(() => _dismissed = true)`. The dismiss is immediate and replaces the chip with `SizedBox.shrink()`.
- **Problem:** `_dismissed` is local state. When the chat is scrolled away and back, or the widget is rebuilt by Riverpod, the dismissed state is lost. There is no persistence (no SharedPreferences, no provider state). The receipt reappears on widget rebuild. This is a meaningful UX gap -- users will notice dismissed receipts coming back.
- `AuroraReceiptChip`: Has no dismiss mechanism at all. There is no close button. The chip is always present in the chat.

### Dimension 2 Overall: **GOOD**
Strong quietness and information architecture, but dismiss persistence is a real problem.

---

## Dimension 3: Chat Screen Polish

**File:** `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/chat/presentation/screens/chat_screen.dart`

### Message Delivery States: **EXCELLENT**

The offline delivery pipeline is thorough:
- Four states are mapped: `OfflineMessageStatus.pending -> ChatBubbleDeliveryStatus.queued`, `sent -> sending`, `failed -> failed`, `acked -> normal`.
- The `_offlineDeliveryStatusesByMessageId` method matches queue entries to messages by requestId, then by content+sessionId+time proximity fallback. This is robust.
- The `OfflineQueueIndicator` (a separate widget) shows contextual UI for each state: wifi-off icon for queued, spinner for sending, checkmark for complete. Each state has distinct color coding (warning, info, success).
- The `ChatBubble` receives `deliveryStatus` and `onRetryDelivery` callback -- failed messages can be retried directly.

### Comeback Banner: **EXCELLENT**

The `ComebackBanner` is well-crafted:
- Shows context-aware title (uses `contextData.title`, falls back to `topicSummary`, falls back to l10n default).
- Has an explicit dismiss `IconButton` with the standard close tooltip.
- Shows unfinished items as tappable chips (`_ComebackItemChip`) with type-specific icons.
- Has both "Resume" (for core session) and "Continue in chat" actions.
- Uses `SparkleStaggerItem` for entrance animation with `reduceMotion` respect.
- The banner hydration is signature-gated (`_hydratedComebackSignature`) to avoid re-showing the same context on rebuild.

### Correction Entry: **EXCELLENT**

Correction is deeply integrated:
- `ContextualCorrectionBar` appears below the latest assistant message.
- When `predictedReplyGroups` are available, shows AI-predicted correction chips with semantic values. Otherwise falls back to static chips ("Not right direction", "Make shorter", "Give practice", "Recalibrate").
- Each chip selection shows a `_CorrectionAcknowledgement` with a 4-second auto-dismiss timer -- providing clear feedback without cluttering.
- The freeform correction path opens a dialog with text input (`_promptForAuroraCorrection`).
- Corrections are structured as `AuroraCorrectionPayload` with telemetry tracking.

### Loading States: **GOOD**

- Empty state: When `messages.isEmpty && streamingContent.isEmpty`, shows `_buildQuickActions()` -- quick action chips for the user. Good.
- AI thinking: Shows `AgentReasoningBubble` with steps and duration.
- AI status: Shows `AiStatusIndicator` with status, details, and start time.
- Streaming: Shows streaming content bubble with routing preview and roundtable turns.
- Daily startup failure: Shows `DailyStartupRetryBanner` with retry button.
- **Error state:** Full error bar at the bottom with icon, title, message, retry button (for retryable errors), and dismiss button. The error bar uses `SparkleExitTransition` for animated entry/exit. Failure types are categorized (offline, auth, general) with appropriate icons and action labels.
- **Gap:** The error bar's dismiss action just clears error state (`copyWith(clearError: true)`) -- if the underlying error persists (e.g., network still down), it may reappear immediately, creating a flashing effect.

### Dimension 3 Overall: **EXCELLENT**
Comprehensive state coverage. The correction flow is particularly well-designed.

---

## Dimension 4: Accessibility Coverage

### Semantics Label Coverage: **GOOD**

Quantitative findings:
- **chat/widgets**: 38 `Semantics(` calls across 13 files, paired against 471 interactive element instances (GestureDetector/InkWell/IconButton/etc.) across 58 files. This gives an approximate coverage ratio of **8% by count**, but this raw ratio is misleading:
  - Many of those 471 instances are inside widgets that already have a parent `Semantics` wrapper. For example, the 30 interactive elements in `action_card.dart` may be covered by a small number of `Semantics` wrappers at the card level.
  - The core conversation-flow widgets (status_awareness_bar, contextual_correction_bar, aurora_receipt_chip, calibration_receipt_chip, comeback_banner, offline_queue_indicator, chat_bubble) all have comprehensive `Semantics` coverage with `ExcludeSemantics` to prevent double-counting.
- **aurora**: 4 `Semantics(` calls in `aurora_core_session_sheet.dart` -- but this is a large, complex sheet.
- **home**: 3 `Semantics(` calls across `aurora_status_band.dart` and `unified_omni_bar.dart`.

### Quality of Semantics Labels: **EXCELLENT**

The labels are genuinely meaningful, not placeholder text:
- `"${widget.title}. ${widget.collapseLabel}"` -- contextual, includes state.
- `context.l10n.calibrationReceiptDismiss` -- localized, specific.
- `"${summary}. $semanticLabel"` -- combines content summary with action context.
- `l10n.auroraCorrectionRiskFalsePositive` -- semantic, not "button".
- The offline queue indicator provides richer `semanticLabel` than visual `label` (e.g., visual: "3 messages waiting to send" vs semantic: "Offline queue has 3 messages waiting to send").
- `_BarContainer` passes `collapsedLabel` as `semanticLabel` -- this is the full status description, not just "Aurora".

### Live Regions: **ADEQUATE**

Only 2 live regions found across all three feature areas:
1. `offline_queue_indicator.dart:34` -- `liveRegion: true` for offline queue status changes.
2. `chat_design_language_widgets.dart:220` -- `liveRegion: true` for daily startup retry banner.

**Missing live regions:**
- Aurora status bar state changes (sensing -> risk_found is a critical state change).
- Correction acknowledgment pill appearance.
- Error bar appearance/disappearance.
- Comeback banner appearance.
- Calibration receipt dismissal.

### Keyboard/Focus: **GOOD**

The home-screen `aurora_status_band.dart` (line 73-84) implements `FocusableActionDetector` with keyboard shortcuts (Enter, Space) and `ActivateIntent` -- full keyboard navigation support. The chat-screen status bar lacks this explicit keyboard support, relying on `Semantics.onTap`.

### Dimension 4 Overall: **ADEQUATE**
Label quality is excellent. The main gap is live regions for dynamic content. Only 2 live regions exist where there should be 6-8 for critical state changes. The home-screen band has full keyboard support; the chat-screen band does not.

---

## Dimension 5: Design System Compliance

### Hardcoded Colors in chat/: **EXCELLENT**

Zero instances of `Colors.white` or `Colors.black` in the entire chat feature directory. All colors route through `DS.*` design tokens.

### Hardcoded Colors in aurora/: **GOOD**

3 instances of `Colors.white`, all in `aurora_core_session_sheet.dart`:
- Line 993: `foregroundColor: Colors.white`
- Line 1082: `foregroundColor: Colors.white`
- Line 1248: `foregroundColor: Colors.white`

These are all `foregroundColor` on button/chip elements -- likely used as text/icon color on primary-colored backgrounds. They should use `DS.textOnPrimary` or similar token to support theme inversion.

### Hardcoded Colors in home/: **NEEDS_WORK**

23 instances across 7 files. Many are justified (particle effects, weather highlights blending with accent colors), but some are genuine violations:

- `openclaw_automation_panel.dart:164` -- `Colors.white` (background)
- `openclaw_automation_panel.dart:324` -- `Colors.white` (background)
- `openclaw_node_management_panel.dart:220` -- `Colors.white` (background)
- `openclaw_hub_card.dart:149` -- `Colors.white` (icon color)
- `insight_hub_card.dart:323` -- `Colors.white` (color)
- `exam_sprint_dashboard_card.dart` -- 10 instances including text colors, background colors, and border colors, all using `Colors.white` with various alpha values. These should use `DS.surfacePrimary`, `DS.textPrimary`, etc.

The `weather_presentation.dart` and `background_layer.dart`/`particle_layer.dart` usages are arguably acceptable since they are visual-effect layers where `Colors.white` is a blending component, not a design token.

### Dimension 5 Overall: **GOOD** (for the audited chat/aurora scopes specifically)

The chat feature is completely clean. The aurora feature has 3 minor violations. The home feature has significant hardcoded color usage.

---

## Summary Ratings

| Dimension | Rating | Key Strength | Key Gap |
|-----------|--------|-------------|---------|
| 1. Aurora Status Band | **GOOD** | Layer 3 cards are genuinely useful, not decoration | 32dp minHeight on chips; no live region for state changes |
| 2. Receipt System | **GOOD** | Exceptional quietness and information architecture | CalibrationReceiptChip dismiss is not persisted; AuroraReceiptChip has no dismiss |
| 3. Chat Screen Polish | **EXCELLENT** | Comprehensive state coverage; correction flow is best-in-class | Error bar may flash if underlying error persists |
| 4. Accessibility | **ADEQUATE** | Semantics labels are meaningful and specific | Only 2 live regions across all features; chat status bar lacks keyboard support |
| 5. Design System | **GOOD** | Chat feature is 100% clean; aurora has 3 violations | Home feature has 23 hardcoded `Colors.white` instances |

### Critical Action Items (Priority Order)

1. **Add `liveRegion: true`** to the status bar container in `status_awareness_bar.dart` -- screen reader users are currently silent on Aurora state transitions.
2. **Change `minHeight: 32` to `minHeight: 44`** on `_StatusCorrectionChip` (line 1377) and `_PredictedOptionChip` (line 1433) in `status_awareness_bar.dart`.
3. **Persist dismissed state** for `CalibrationReceiptChip` -- either via a provider or SharedPreferences to prevent re-appearance on rebuild.
4. **Add a dismiss affordance** to `AuroraReceiptChip` -- currently there is no way to dismiss it.
5. **Replace 3 `Colors.white` instances** in `aurora_core_session_sheet.dart` (lines 993, 1082, 1248) with `DS.textOnPrimary` or equivalent.
6. **Add `FocusableActionDetector`** to the chat-screen status bar, matching the pattern already in the home-screen `aurora_status_band.dart`.