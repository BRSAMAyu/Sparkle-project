# Flutter Chat System Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Flutter Chat system is architecturally solid with comprehensive WebSocket lifecycle management, robust error recovery, and well-structured state management via Riverpod StateNotifier. The codebase demonstrates strong engineering discipline in areas like connection lifecycle, race condition guards (`_streamGeneration`, `isSwitchingPlan`, `loadingConversationId`), message bounding, and offline queue persistence. However, there are i18n violations (62 `isChinese` ternary patterns that bypass ARB), a static map leak in `CollapsibleWidgetWrapper`, and several `Future.delayed` callbacks in the provider that could fire after dispose. None of the issues are crash-inducing P0s, but the i18n pattern is a systemic violation that should be tracked.

## Critical Issues (P0)

None found. The system handles disconnection, reconnection, error states, and dispose paths correctly.

## High Issues (P1)

### P1-1. Systematic i18n violation: `isChinese` ternary bypasses ARB l10n

**Files affected**: 62 instances across chat feature files.

The `isChinese ? '中文' : 'English'` pattern is used extensively instead of ARB-based `l10n.*` calls. This violates the project's bilingual strategy and the "never hardcode Chinese or English in user-facing code" rule from CLAUDE.md.

Key concentrations:
- `websocket_chat_service_v2.dart`: 6 instances (lines 169, 1916, 1988, 2237, 2256, 2301) -- user-facing error messages like "网络连接失败" / "Network connection failed"
- `agent_message_renderer.dart`: 5 instances (lines 54, 66, 82, 87, 319) -- widget labels "任务"/"Task", "计划"/"Plan", "成就"/"Achievement", "错题"/"Error"
- `assistant_message_metadata_tray.dart`: 5 instances (lines 107, 309, 312, 314, 434) -- timing labels "耗时"/"Time", "档位"/"Tier", "缓存"/"Cache", source count formatting
- `agent_team_sheet.dart`: ~15 instances -- form labels, button text, tier names
- `chat_screen.dart`: ~6 instances
- `status_awareness_bar.dart`: 4 instances
- `group_chat_screen.dart`: 4 instances
- Multiple other widget files

**Impact**: Adding a third language would require code changes across 62 call sites instead of just ARB file updates. The `isChinese` ternary also means translations cannot be managed by translators via ARB files.

**Recommendation**: Migrate to `context.l10n.*` calls. The project already has `AppLocalizations` with many of these keys defined. Each `isChinese` ternary should be replaced with a proper ARB key.

### P1-2. Static unbounded `Map` in `CollapsibleWidgetWrapper` grows without limit

**File**: `presentation/widgets/collapsible_widget_wrapper.dart:47`
```dart
static final Map<String, bool> _persistedState = {};
```

This static map stores the expanded/collapsed state for every collapsible widget instance ever created in the app's lifetime. Entries are never removed. For a chat system where users may receive hundreds of messages with multiple widgets each, this map grows unboundedly.

**Impact**: Memory leak proportional to the number of unique widget types and messages seen across the entire app session.

**Recommendation**: Use an LRU cache with a bounded size (e.g., 100 entries), or tie persistence to the current session's conversation ID and clear on conversation switch.

### P1-3. `Future.delayed` callbacks in `ChatNotifier` may fire after dispose

**File**: `presentation/providers/chat_notifier_actions.dart`
Lines: 605, 661, 710, 792, 816, 945, 1031

Multiple `Future.delayed` calls use `if (mounted)` guards, but `mounted` on a `StateNotifier` does not behave the same as `State.mounted` on a `StatefulWidget`. In Riverpod, `StateNotifier.mounted` becomes false after `dispose()`, so the guard technically works, but the pattern is fragile and the delayed callbacks hold a closure reference to the notifier.

**Impact**: Non-critical -- the `mounted` check prevents state mutation. However, the closures hold references to the notifier and its dependencies until the timer fires, delaying GC.

**Recommendation**: Track delayed operations with a `Timer` list and cancel all in `dispose()`, similar to how `_streamDebouncer` is handled.

## Medium Issues (P2)

### P2-1. `_Debouncer.run()` can silently swallow the last state update if a new event arrives during the debounce window

**File**: `presentation/providers/chat_provider_wiring.dart:25-28`

The `_Debouncer.run()` method cancels the previous timer and schedules a new one. In `flushPending()`, each event sets `pendingStreamingContent`, `pendingAiStatus`, etc., then calls `flushPending()` which debounces. If two events arrive within the 50ms debounce window, only the second one's state is applied. This is likely intentional for performance, but means the first event's intermediate state is never rendered.

**Impact**: Minor visual artifact -- the UI may skip an intermediate status indicator. Acceptable for streaming text, but could miss a brief status transition like THINKING -> GENERATING.

### P2-2. `_messageKeys` `GlobalKey` map in `ChatScreen` grows until `_pruneMessageKeys` is called

**File**: `presentation/screens/chat_screen.dart:192,814-820`

`_messageKeys` stores a `GlobalKey` per message ID for scroll-to-message functionality. Keys are pruned in `_pruneMessageKeys()` which is called during build, but if messages are rapidly added (streaming), the map can temporarily hold keys for all messages. Since `ChatState.maxRetainedMessages` is 500, this is bounded.

**Impact**: Low -- bounded by `maxRetainedMessages` (500). Acceptable but worth noting.

### P2-3. `ChatScreen` is 4,016 lines -- single file complexity

**File**: `presentation/screens/chat_screen.dart`

The main chat screen is extremely large with many inline widget builders, hydration logic, and state listeners. This makes the file hard to maintain and review.

**Recommendation**: Extract hydration logic (`_hydrateInitialConversationAndPrompt`, `_hydrateDailyStartupIfNeeded`, `_hydrateComebackContextIfNeeded`, `_hydrateChatOpeningIfNeeded`) into a separate mixin or helper class. Extract inline widget builders into standalone widgets.

### P2-4. Accessibility semantics labels are generic placeholders

**File**: `presentation/widgets/collapsible_widget_wrapper.dart:67,144`
```dart
label: 'Chat collapsible widget wrapper control 1',
label: 'Chat collapsible widget wrapper control 2',
```

**File**: `presentation/widgets/agent_message_renderer.dart:231`
```dart
label: 'Chat agent message renderer control 1',
```

These generic semantics labels do not convey meaningful information to screen reader users. A screen reader would announce "Chat collapsible widget wrapper control 1" which is unhelpful.

**Impact**: Poor accessibility experience for users relying on screen readers.

**Recommendation**: Use descriptive labels that include the widget's purpose, e.g., "Expand task details" or "Collapse plan card". Use l10n keys.

### P2-5. `_parseChatEvent` function is a 1,100-line top-level function with deep nesting

**File**: `data/services/websocket_chat_service_v2.dart:161-1272`

The event parser is a single massive function with a large `switch` statement and many nested `if` blocks checking metadata fields. While it correctly handles all event types, it is difficult to test individual branches and prone to merge conflicts.

**Recommendation**: Extract each `case` branch into a named factory method on the event class (e.g., `TextEvent.fromPayload(data)`) or use a registry pattern.

### P2-6. Duplicate metadata extraction logic in `sendMessage`'s TextEvent and FullTextEvent handlers

**File**: `presentation/providers/chat_provider.dart`

Lines 1299-1449 (TextEvent handler) and lines 1495-1632 (FullTextEvent handler) contain nearly identical code for extracting collaboration data, routing preview, roundtable turns, agent activities, etc. This ~300-line duplication is a maintenance burden.

**Recommendation**: Extract a shared `_extractCollaborationMetadata(metadata, ...)` method.

## Low Issues (P3)

### P3-1. `chat_stream_events.dart` is 1,986 lines in a single file

**File**: `data/models/chat_stream_events.dart`

Contains 40+ event classes. Consider splitting into `chat_stream_events_core.dart`, `chat_stream_events_spine.dart`, `chat_stream_events_review.dart`, etc.

### P3-2. `SSE` fallback code is marked `@Deprecated` but still present

**File**: `data/repositories/chat_repository.dart:478-619`

The `chatStreamSSE` method and `_startSSEConnection` / `_parseEvent` methods are deprecated but still take up ~140 lines. If WebSocket is the only transport, these can be removed.

### P3-3. `voiceInputProvider` uses `Logger()` instance directly

**File**: `presentation/providers/voice_input_provider.dart:24`

Creates a `Logger()` instance per notifier. The project should use a centralized logging approach. Minor inconsistency.

### P3-4. `InAppNotificationOverlay` uses a try-catch for focus mode provider

**File**: `data/services/message_notification_service.dart:109-115`

```dart
final _focusModeProviderOrFalse = Provider<bool>((ref) {
  try {
    return ref.watch(focusModeProvider);
  } catch (_) {
    return false;
  }
});
```

This silently swallows provider dependency errors. If `focusModeProvider` is not available, the root cause should be addressed rather than catching.

### P3-5. `MessageBadge` hardcoded "99+" string

**File**: `data/services/message_notification_service.dart:297`
```dart
unreadCount > 99 ? '99+' : '$unreadCount',
```

Minor -- "99+" should ideally be localized.

### P3-6. `_SourceSummaryContent` hardcodes source count format

**File**: `presentation/widgets/assistant_message_metadata_tray.dart:517-519`
```dart
zh ? '${citations.length} 个来源' : '${citations.length} sources',
```

Should use an ARB key with a plural parameter.

## Positive Findings

1. **WebSocket lifecycle is excellent**: Connection, reconnection with exponential backoff + jitter, heartbeat with RTT metrics, graceful disconnect on background, and automatic reconnect on resume are all well-implemented. The `_connGen` mechanism prevents stale teardowns.

2. **Race condition guards are thorough**: `_streamGeneration` prevents stale stream events from corrupting current UI, `isSwitchingPlan` blocks sends during plan transitions, `loadingConversationId` prevents duplicate history loads, and `CancelableOperation` supports cancellation of in-flight history requests.

3. **Offline resilience**: `OfflineMessageQueueService` persists unsent messages to Isar DB, restores them on reconnect, and properly tracks acked/failed/sent states. The pending message queue has a 50-item limit with proper overflow handling.

4. **Stream debouncing**: The `_Debouncer` with 50ms window prevents excessive state mutations during rapid streaming, keeping the UI responsive.

5. **Message bounding**: `ChatState._boundedMessages` caps retained messages at 500, preventing unbounded memory growth in long conversations.

6. **Error recovery**: The `ErrorMessages.getUserFriendlyMessage` / `getActionSuggestion` / `isRetryable` system provides consistent, user-friendly error handling. The retry mechanism via `_retryableRequest` preserves the original request for easy re-submission.

7. **Terminal fallback**: The `_terminalDoneFallbackDelay` mechanism ensures that streams missing a `DoneEvent` still get properly cleaned up, preventing stuck "sending" states.

8. **401 handling**: Automatic token refresh with `Completer`-based deduplication, max retry tracking, and graceful logout on permanent failure.

9. **App lifecycle awareness**: `WidgetsBindingObserver` integration correctly disconnects on background and reconnects on resume, preserving battery and network resources.

10. **Heartbeat suppression during active streams**: The `_isStreamActive` check with 120-second grace period prevents false-positive heartbeat timeouts from interrupting active AI responses.

11. **Large message parsing in isolate**: Messages > 12KB are parsed via `compute()` to avoid blocking the UI thread.

12. **State cleanliness**: `ChatState.copyWith` uses explicit `clear*` flags instead of nullable sentinel values, making state transitions explicit and auditable.

## Files Audited

### Data Layer
- `mobile/lib/features/chat/data/models/chat_message_model.dart` (701 lines)
- `mobile/lib/features/chat/data/models/chat_message_model.g.dart` (193 lines)
- `mobile/lib/features/chat/data/models/chat_response_model.dart` (26 lines)
- `mobile/lib/features/chat/data/models/chat_response_model.g.dart` (29 lines)
- `mobile/lib/features/chat/data/models/chat_mode.dart` (286 lines)
- `mobile/lib/features/chat/data/models/chat_stream_events.dart` (1,986 lines)
- `mobile/lib/features/chat/data/models/expert_catalog_model.dart` (188 lines)
- `mobile/lib/features/chat/data/models/reasoning_step_model.dart` (171 lines)
- `mobile/lib/features/chat/data/models/reasoning_step_model.g.dart` (61 lines)
- `mobile/lib/features/chat/data/repositories/chat_repository.dart` (620 lines)
- `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` (2,699 lines)
- `mobile/lib/features/chat/data/services/agent_session_store.dart` (41 lines)
- `mobile/lib/features/chat/data/services/audio_recording_service.dart` (312 lines)
- `mobile/lib/features/chat/data/services/chat_cache_service.dart` (123 lines)
- `mobile/lib/features/chat/data/services/message_notification_service.dart` (310 lines)
- `mobile/lib/features/chat/data/services/plan_review_grpc_service.dart` (154 lines)
- `mobile/lib/features/chat/data/services/review_grpc_service.dart` (919 lines)

### Provider Layer
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart` (2,032 lines)
- `mobile/lib/features/chat/presentation/providers/chat_state.dart` (466 lines)
- `mobile/lib/features/chat/presentation/providers/chat_provider_wiring.dart` (39 lines)
- `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart` (1,073 lines)
- `mobile/lib/features/chat/presentation/providers/chat_notifier_history.dart` (231 lines)
- `mobile/lib/features/chat/presentation/providers/chat_notifier_reviews.dart` (543 lines)
- `mobile/lib/features/chat/presentation/providers/agent_session_provider.dart` (8 lines)
- `mobile/lib/features/chat/presentation/providers/aurora_status_provider.dart` (669 lines)
- `mobile/lib/features/chat/presentation/providers/chat_mode_provider.dart` (110 lines)
- `mobile/lib/features/chat/presentation/providers/context_decision_provider.dart` (29 lines)
- `mobile/lib/features/chat/presentation/providers/expert_catalog_provider.dart` (9 lines)
- `mobile/lib/features/chat/presentation/providers/guidance_mode_provider.dart` (40 lines)
- `mobile/lib/features/chat/presentation/providers/low_yield_block_provider.dart` (228 lines)
- `mobile/lib/features/chat/presentation/providers/source_explanation_provider.dart` (316 lines)
- `mobile/lib/features/chat/presentation/providers/voice_input_provider.dart` (170 lines)

### Presentation Layer - Screens
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (4,016 lines)
- `mobile/lib/features/chat/presentation/screens/chat_settings_screen.dart` (316 lines)
- `mobile/lib/features/chat/presentation/screens/group_chat_screen.dart` (955 lines)
- `mobile/lib/features/chat/presentation/screens/private_chat_screen.dart` (785 lines)

### Presentation Layer - Key Widgets
- `mobile/lib/features/chat/presentation/widgets/agent_message_renderer.dart` (593 lines)
- `mobile/lib/features/chat/presentation/widgets/assistant_message_metadata_tray.dart` (563 lines)
- `mobile/lib/features/chat/presentation/widgets/collapsible_widget_wrapper.dart` (204 lines)
- `mobile/lib/features/chat/presentation/widgets/chat_input.dart` (697 lines)
- `mobile/lib/features/chat/presentation/widgets/chat_bubble.dart` (3,462 lines -- audited patterns)
- `mobile/lib/features/chat/presentation/widgets/action_card.dart` (3,857 lines -- audited patterns)
- `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart` (512 lines)
- `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart` (1,388 lines)
- `mobile/lib/features/chat/presentation/widgets/content_review_card.dart` (1,390 lines)
- `mobile/lib/features/chat/presentation/widgets/status_awareness_bar.dart` (1,542 lines)

### Other Files
- `mobile/lib/features/chat/chat.dart` (13 lines)
- `mobile/lib/features/chat/chat_routes.dart` (154 lines)
- `mobile/lib/features/chat/widgets/agent_status_indicator.dart` (393 lines)
- `mobile/lib/features/chat/widgets/quick_reply_chips.dart` (363 lines)
- `mobile/lib/features/chat/widgets/typing_text.dart` (334 lines)
