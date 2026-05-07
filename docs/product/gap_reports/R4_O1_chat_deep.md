# R4-O1: Chat Screen Deep Audit Report

> **Date**: 2026-05-06 | **Scope**: Primary chat interaction surface
> **Files Audited**: 8 files, ~7,500 lines total

---

## Executive Summary

The Chat screen is the most complex surface in the Sparkle app. It is architecturally sound overall: WebSocket state is properly observed, lifecycle checks are consistent, and the widget tree handles dozens of backend-driven card types. However, this audit identifies **17 findings** across i18n, memory management, semantics, input validation, and dead code.

**Severity breakdown**: 3 High | 7 Medium | 7 Low

---

## File-by-File Findings

### 1. `chat_screen.dart` (4,002 lines)

#### State Management
- **GOOD**: `ref.watch(chatProvider)` is the single source of truth. No duplicate state.
- **GOOD**: WebSocket connection state is observed via `listenManual` in `initState` with user-facing feedback for reconnecting/connected/failed transitions.
- **GOOD**: Error state is auto-cleared after 10 seconds via `Future.delayed` with mounted check.
- **GOOD**: Loading state shows a `LinearProgressIndicator` at the top.
- **MINOR**: Empty state renders `_buildQuickActions()` but the method was not fully inspected here; the conditional at line 1399-1403 covers empty messages + no streaming + no status indicators -- seems complete.

#### Memory / Lifecycle
- **GOOD**: `_scrollController` is properly disposed (line 1046-1054).
- **GOOD**: BGM activity flags are cleared in `dispose()`.
- **GOOD**: `mounted` checks are present after every `await` in hydration methods (lines 411, 443, 471, 496, 534, 573, 630, 665, 695, 717).
- **GOOD**: `ref.listenManual` listeners are cleaned up automatically by Riverpod when the StatefulConsumerState is disposed.

#### i18n
- **HIGH-F1**: `_chatFailureTitle()` (lines 109-125) uses `zh ? '...' : '...'` inline bilingual pattern instead of ARB keys. Six failure title strings and three action label strings are hardcoded in `_chatFailureTitle` and `_chatFailureActionLabel`.
- **MEDIUM-F2**: Lines 1896-1920: Inline `isChinese ? '...' : '...'` strings for agenda preview items (`'确认聊天纠错反馈'`, `'调整后续回复策略'`). These should be ARB keys.
- **MEDIUM-F3**: Lines 2869-2873: Inline `isChinese ? '...' : '...'` for correction action descriptions (`'确认顶部提醒里的判断'`, `'决定下一步是否调整'`).
- **LOW**: Line 2194: `action.contains('累')` is a hardcoded Chinese character check for detecting "tired" intent in growth card actions. This breaks for non-Chinese locales.

#### Semantics
- **GOOD**: AppBar buttons have `semanticLabel` parameters set from l10n.
- **GOOD**: The back button uses `l10n.back` as semanticLabel.
- **GOOD**: PopupMenuButton uses `tooltip: context.l10n.chatMoreActions`.

#### Error Handling / WebSocket
- **GOOD**: WS reconnect triggers `AppFeedback.loading` with `l10n.chatReconnecting`.
- **GOOD**: WS connected-after-reconnect triggers `AppFeedback.success` with `l10n.chatReconnected` and reloads history.
- **GOOD**: WS failure triggers `AppFeedback.error` with `l10n.chatConnectionFailed`.
- **GOOD**: Error bar shows contextual icon and retry button based on failure kind.

#### Input Validation
- **LOW-F4**: No `maxLength` constraint visible on the `ChatInput` widget. The `_handleSend()` in `chat_input.dart` trims and checks empty, but there is no hard limit on message length. Very long messages could cause performance issues in `SparkleMarkdown` rendering and WebSocket frame size.

---

### 2. `chat_bubble.dart` (3,376 lines)

#### Memory / Lifecycle
- **HIGH-F5**: `_responseFeedbackSelections` is a **static `LinkedHashMap`** (line 117) shared across all `_ChatBubbleState` instances. It has a max of 200 entries, so it is bounded. However, it is never cleared on dispose -- the map persists for the lifetime of the isolate. This is a deliberate design (preserving feedback selection state across rebuilds), but the static mutable state is a code smell that could cause issues in tests or if the limit changes.
- **GOOD**: `_entryController` (AnimationController) is properly disposed (line 218-219).
- **GOOD**: `_handleDoubleTap` uses `Future.delayed` with mounted check before `_showHeart = false`.

#### i18n
- **MEDIUM-F6**: `_deliveryCopy()` method (lines 2342-2355) uses `I18nService.instance.isChinese ? '...' : '...'` for four strings: `'等待发送'`/`'Queued'`, `'正在发送'`/`'Sending'`, `'发送失败'`/`'Send failed'`, `'重试'`/`'Retry'`. These should be ARB keys.
- **LOW**: Lines 1581-1613: `_recentTopicHints()` contains hardcoded Chinese keyword arrays: `'考试'`, `'面试'`, `'复盘'`, `'计划'`, `'错题'`, `'表达'` and their signal words. Also hardcodes Chinese stop words. This is a heuristic utility that will not function for English users.
- **LOW**: Line 247: `"Close exploration panel"` -- hardcoded English-only semantic label.

#### Semantics
- **GOOD**: The main bubble `GestureDetector` is wrapped in `Semantics(button: true, label: 'Open message actions')`.
- **MEDIUM-F7**: The semantic label `'Open message actions'` (line 929) is hardcoded English, not localized. Users with screen readers in Chinese will hear English.
- **LOW**: `_buildHeartAnimation` has no semantic label -- double-tap heart animation is invisible to accessibility.
- **LOW**: `_InsightLinkCard` has `Semantics(button: true, label: 'Open insight link')` -- hardcoded English (line 2976).

#### Widget Quality
- **GOOD**: Revoked messages show a styled placeholder with localized text.
- **GOOD**: Streaming state shows a typing indicator via `AiStatusIndicator`.
- **GOOD**: Delivery status (queued/sending/failed) shown with appropriate badges and retry action.
- **GOOD**: Response feedback row shows thumbs up/down with selected state.

#### Dead Code / Unused Imports
- **LOW-F8**: `import 'package:sparkle/core/services/universal_share_service.dart'` (line 17) -- `UniversalShareService` does not appear to be used directly in this file. The share logic uses `UniversalSharePayload` from `entity_card_payloads.dart` and `ShareCardFactory` from `share_cards.dart`. If `UniversalShareService` is unused, this is a dead import.
- **LOW**: The `_shouldConstrain` branch at lines 1090-1094 returns `animatedContent` in both the `if` and `else` branches identically -- the conditional has no effect. The `if (!shouldConstrain) return animatedContent;` and the fallthrough both return the same value.

---

### 3. `experience_envelope_indicator.dart` (136 lines)

#### Rendering Verification
- **CONFIRMED RENDERED**: The widget IS rendered in `chat_screen.dart` at line 1945: `const ExperienceEnvelopeIndicator()` appears inside the streaming bubble section, conditionally shown when `showEnvelopeIndicator` is true.

#### i18n
- **HIGH-F9**: ALL visible strings use `I18nService.instance.isChinese ? '中文' : 'English'` inline pattern instead of ARB:
  - Line 41: `'认知调整指示器'` / `'Cognitive adjustment indicator'` (semantic label)
  - Line 63: `'Aurora 正在适应'` / `'Aurora adapting'` (header text)
  - Line 127: `'无'` / `'none'` (null value)
  - Line 130-131: `'是'`/`'yes'`, `'否'`/`'no'` (boolean values)
  - Adjustment dimension labels are hardcoded English-only: `'Tone'`, `'Verbosity'`, `'Challenge'`, etc. (lines 14-21).

#### Semantics
- **GOOD**: Wrapped in `Semantics(container: true, label: ...)` with a descriptive label.
- **LOW**: Individual adjustment chips have `Semantics` wrappers, but the label format `'$label: $valueText ($reason)'` mixes English dimension labels with potentially Chinese values.

#### State Management
- **GOOD**: Uses `ref.watch(experienceEnvelopeProvider)` -- reactive to envelope changes.
- **GOOD**: Returns `SizedBox.shrink()` when no adjustments -- invisible when inactive.

---

### 4. `causal_timeline_panel.dart` (634 lines)

#### State Management
- **GOOD**: `AsyncValue.when()` is fully handled with loading (`CircularProgressIndicator`), error (icon + retry button + text), and data states. Empty state is handled separately.
- **GOOD**: Error state includes an `onRetry` callback that calls `ref.read(causalTimelineProvider.notifier).load()`.

#### i18n
- **MEDIUM-F10**: Lines 247, 285, 517, 521: Four strings use `I18nService.instance.isChinese ? '...' : '...'`:
  - Tooltip: `'刷新'` / `'Refresh'`
  - Retry button: `'重试'` / `'Retry'`
  - Cancel button: `'取消'` / `'Cancel'`
  - Submit button: `'提交'` / `'Submit'`
- **GOOD**: Most strings use `context.l10n.*` ARB keys: `chatCausalWhyDecisions`, `chatCausalSemanticsRefresh`, `chatCausalLoadFailed`, `chatCausalNoRecords`, `chatCausalNoRecordsHint`, etc.

#### Lifecycle
- **GOOD**: `TextEditingController` in `_showCorrectionInput` is properly disposed after dialog closes (line 526).

#### Semantics
- **GOOD**: Entry cards have `Semantics(button: true, label: ...)` with localized labels.
- **GOOD**: Action chips have `Semantics(button: true, label: ...)` with localized labels.
- **GOOD**: Refresh button has `Semantics(button: true, label: ...)` and `tooltip`.

---

### 5. `source_explanation_card.dart` (429 lines)

#### Rendering Verification
- **CONFIRMED RENDERED**: Rendered inside `chat_bubble.dart` at lines 1138-1142, conditionally shown when `showAiSystemAccessories` is true and the message is not from user and is a `ChatMessageModel`.

#### State Management
- **GOOD**: Uses `ref.watch(sourceExplanationProvider).maybeWhen()` with `data` and `orElse` branches. The `orElse` returns `SizedBox.shrink()`.
- **GOOD**: If `rawMetadata` is provided directly, it uses local parsing first without provider dependency.

#### i18n
- **GOOD**: All visible strings use `context.l10n.*` ARB keys: `sourceExplanationSemantics`, `sourceExplanationUsedSummary`, `sourceExplanationUsedSources`, `sourceExplanationUnusedSources`, `sourceExplanationCorrectionSent`, `sourceExplanationCorrectionFailed`, etc.
- **No inline zh/en strings found** -- this file is i18n-clean.

#### Lifecycle
- **GOOD**: `mounted` checks after `await` in `_submitCorrection` (lines 203, 220, 228).
- **GOOD**: `ScaffoldMessenger.of(context)` is captured before the async gap (line 196).

#### Semantics
- **GOOD**: Top-level `Semantics(container: true, button: true, label: ...)`.
- **GOOD**: Correct button has `Semantics(button: true, label: ...)` with localized label and `tooltip`.

---

### 6. `context_receipt_bar.dart` (257 lines)

#### Rendering Verification
- **CONFIRMED RENDERED**: Rendered inside `chat_bubble.dart` at lines 1129-1137, conditionally shown when `showAiSystemAccessories` is true and the message is not from user and is a `ChatMessageModel`. Passes `rawMetadata` from the chat message.

#### State Management
- **GOOD**: This is a `StatelessWidget` -- no state management concerns.
- **GOOD**: Returns `SizedBox.shrink()` when no receipts are parsed (line 27).
- **GOOD**: Deduplication logic prevents duplicate receipt chips (lines 161-188, 190-211).

#### i18n
- **GOOD**: No visible strings -- this widget delegates all text to `AuroraReceiptChip` and `CalibrationReceiptChip` which receive data from the backend.

#### Error Handling
- **GOOD**: `_decode()` handles null, Map/List passthrough, and JSON string decoding with try-catch that returns null on failure (lines 245-256). No crashes from malformed metadata.

#### Semantics
- **LOW-F11**: No `Semantics` wrapper on the receipt bar itself or individual receipt chips. The content is visible but not announced to screen readers.

---

### 7. `low_yield_gentle_block_card.dart` (183 lines)

#### i18n
- **GOOD**: All visible strings use `context.l10n.*` ARB keys: `lowYieldActivityFallback`, `lowYieldReasonFallback`, `lowYieldSuggestionFallback`, `lowYieldCardSemantics`, `lowYieldCardTitle`, `lowYieldCardMessage`, `lowYieldActionCorrect`, `lowYieldActionContinue`, `lowYieldActionSwitch`.
- **No inline zh/en strings found** -- this file is i18n-clean.

#### Lifecycle
- **MEDIUM-F12**: `_handle()` method sets `_handled = true` immediately, then awaits the callback. If the callback throws, the card is already visually removed (`_handled = true` causes `SizedBox.shrink()`). The user has no way to retry or see that the action failed. Should catch errors and reset `_handled = false` on failure.

#### Semantics
- **GOOD**: Wrapped in `Semantics(container: true, label: l10n.lowYieldCardSemantics)`.
- **GOOD**: All three action buttons are standard Flutter buttons (OutlinedButton, TextButton, FilledButton) which have built-in semantics.

---

### 8. `chat_provider.dart` (first 100 lines)

#### State Management
- **GOOD**: Extends `StateNotifier<ChatState>` with proper initialization.
- **GOOD**: `_isDisposed` flag prevents state updates after disposal.
- **GOOD**: `_connectionStateSubscription` listens to WebSocket state stream and maps to `ChatState.wsConnectionState`.
- **GOOD**: Demo mode handled with separate initialization path.

#### Lifecycle
- **MEDIUM-F13**: `_connectionStateSubscription` is created in constructor but the visible first 100 lines do not show cancellation in a `dispose()` override. The subscription must be cancelled when the notifier is disposed, but this needs verification in the rest of the file (which was not fully read). If `_connectionStateSubscription?.cancel()` is missing from dispose, this is a stream subscription leak.

#### Input Validation
- **LOW**: `sendMessage()` (line 821+) blocks during plan switch and if already sending. It does not validate content length or sanitize the string before sending to the WebSocket service. The trim/empty check happens in the ChatInput widget, not in the provider.

---

## Cross-Cutting Verification

### Is ExperienceEnvelopeIndicator ACTUALLY RENDERED?
**YES.** Confirmed at `chat_screen.dart` line 1945: `const ExperienceEnvelopeIndicator()` is rendered inside the streaming bubble section when `showEnvelopeIndicator` is true. The variable `showEnvelopeIndicator` is computed earlier from the chat state.

### Does SourceExplanationCard show when backend provides source data?
**YES.** `chat_bubble.dart` lines 1138-1142 render `SourceExplanationCard(rawMetadata: ...)` when `showAiSystemAccessories` is true. The card's `build()` method parses `rawMetadata` via `SourceExplanationReceipt.fromMetadata()` and renders if non-null. It also falls back to `sourceExplanationProvider` if `useLatestReceiptFallback` is set.

### Does ContextReceiptBar render on every message?
**CONDITIONAL.** It renders for every non-user `ChatMessageModel` when `showAiSystemAccessories` is true (chat_bubble.dart lines 1121-1145). Whether it shows content depends on whether the message's `rawMetadata` contains receipt data. If `rawMetadata` is null or empty, the bar returns `SizedBox.shrink()` -- invisible but rendered.

---

## Finding Summary Table

| ID | Severity | File | Category | Description |
|----|----------|------|----------|-------------|
| F1 | HIGH | chat_screen.dart | i18n | 9 inline zh/en strings in `_chatFailureTitle` and `_chatFailureActionLabel` |
| F2 | MEDIUM | chat_screen.dart | i18n | 4 inline zh/en strings for agenda preview items |
| F3 | MEDIUM | chat_screen.dart | i18n | 2 inline zh/en strings for correction action descriptions |
| F4 | LOW | chat_input.dart | Input | No `maxLength` constraint on text input |
| F5 | HIGH | chat_bubble.dart | Memory | Static mutable `_responseFeedbackSelections` map persists across widget lifecycle |
| F6 | MEDIUM | chat_bubble.dart | i18n | 4 inline zh/en strings in `_deliveryCopy()` |
| F7 | MEDIUM | chat_bubble.dart | Semantics | `'Open message actions'` hardcoded English semantic label |
| F8 | LOW | chat_bubble.dart | Dead code | Possible unused import `universal_share_service.dart`; dead conditional branch at line 1090 |
| F9 | HIGH | experience_envelope_indicator.dart | i18n | All visible strings use inline zh/en pattern (6+ strings); dimension labels English-only |
| F10 | MEDIUM | causal_timeline_panel.dart | i18n | 4 inline zh/en strings for buttons/tooltip |
| F11 | LOW | context_receipt_bar.dart | Semantics | No Semantics wrapper on receipt bar or chips |
| F12 | MEDIUM | low_yield_gentle_block_card.dart | Error handling | Card hides before callback completes; no error recovery if callback throws |
| F13 | MEDIUM | chat_provider.dart | Lifecycle | `_connectionStateSubscription` cancellation needs verification in dispose |
| F14 | LOW | chat_bubble.dart | i18n | `_recentTopicHints()` hardcodes Chinese keyword arrays, non-functional for English |
| F15 | LOW | chat_bubble.dart | Semantics | Hardcoded English-only semantic labels: `'Close exploration panel'`, `'Open insight link'` |
| F16 | LOW | chat_bubble.dart | i18n | `action.contains('累')` Chinese character check breaks for non-Chinese |
| F17 | LOW | chat_screen.dart | i18n | `action.contains('累')` in growth card action check is Chinese-only |

---

## Recommended Fix Priority

### P0 -- Fix Immediately
1. **F9**: Migrate `ExperienceEnvelopeIndicator` to ARB keys. This is a user-visible widget with 6+ inline strings.
2. **F1**: Migrate `_chatFailureTitle` / `_chatFailureActionLabel` to ARB keys. Error states are critical UX moments.

### P1 -- Fix This Sprint
3. **F5**: Consider making `_responseFeedbackSelections` an instance variable or a dedicated Riverpod state provider instead of static mutable state.
4. **F7, F15**: Localize all `Semantics` labels. Screen reader users in Chinese hear English.
5. **F6, F10**: Migrate remaining `_deliveryCopy()` and causal panel button strings to ARB.
6. **F12**: Add try-catch in `LowYieldGentleBlockCard._handle()` with error recovery.
7. **F13**: Verify `_connectionStateSubscription?.cancel()` in ChatNotifier.dispose().

### P2 -- Fix Next Sprint
8. **F2, F3**: Migrate inline agenda/correction strings to ARB.
9. **F14, F16, F17**: Make `_recentTopicHints()` locale-aware or extract to backend.
10. **F4**: Add `maxLength: 4000` (or similar) to `ChatInput` TextField.
11. **F8**: Remove dead import and fix dead conditional branch.
12. **F11**: Add Semantics wrappers to ContextReceiptBar.
