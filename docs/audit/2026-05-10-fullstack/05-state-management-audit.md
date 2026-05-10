# State Management & Data Flow Audit

**Date**: 2026-05-10
**Scope**: Flutter Riverpod providers, WebSocket lifecycle, memory leak patterns, navigation state, offline queue
**Files inspected**: 45+ provider/service/widget files

---

## Summary

| Severity | Count |
|----------|-------|
| P0 Critical | 2 |
| P1 High | 5 |
| P2 Medium | 7 |
| P3 Low | 4 |

---

## 1. Riverpod Provider Audit

### P1-01: SyncEngine connectivity listener never cancelled (memory leak)

**File**: `mobile/lib/core/offline/sync_engine.dart:56`
**Severity**: P1 High

In `SyncEngine.start()`, the connectivity change listener is created inline without storing its subscription:

```dart
// Line 56: This StreamSubscription is never cancelled
_connectivity.onConnectivityChanged.listen((result) {
  if (!result.contains(ConnectivityResult.none)) {
    _processOutbox();
  }
});
```

The `_subscription` field only holds the Isar outbox watch subscription. The connectivity subscription is leaked and will never be cancelled, even after `stop()` is called. This means the listener survives across reconnect cycles and app backgrounding, potentially triggering `_processOutbox()` after the engine is stopped.

**Fix**: Store the connectivity subscription in a field and cancel it in `stop()`:
```dart
StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;

void start() {
  // ... outbox watch ...
  _connectivitySubscription = _connectivity.onConnectivityChanged.listen(...);
}

void stop() {
  _subscription?.cancel();
  _connectivitySubscription?.cancel();
}
```

---

### P1-02: ChatNotifier uses `ref` (not `ref.watch`) internally -- no reactive re-subscription risk, but large coupling surface

**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart` (entire file)
**Severity**: P2 Medium (noted for architecture awareness)

`ChatNotifier` receives `Ref _ref` and uses `_ref.read()` throughout (16 call sites). This is correct for a `StateNotifier` that does not need to reactively re-build when dependencies change. However, it creates a hidden dependency graph: the notifier reads from `authProvider`, `activePlanProvider`, `chatModeProvider`, `guidanceModeProvider`, `chatSeedLibraryEnabledProvider`, `subscriptionsProvider`, `experienceEnvelopeProvider`, `lowYieldBlockProvider`, `taskListProvider`, `notificationCenterProvider`, `planListProvider`, `dashboardProvider`, `achievementProvider`, and more. If any of these providers are auto-dispose, they may be re-created between reads, causing inconsistent state snapshots during a single `sendMessage` call.

**Recommendation**: The providers read via `_ref.read()` should all be either `keepAlive` or verified to not auto-dispose mid-stream. The current wiring file (`chat_provider_wiring.dart`) correctly declares `chatRepositoryProvider` and `chatProvider` as non-autoDispose, but the downstream dependencies are not audited.

---

### P2-01: Future.delayed callbacks mutate state without generation guards

**Files**:
- `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart:605, 661, 710, 792, 816, 945`
- `mobile/lib/features/chat/presentation/providers/chat_notifier_reviews.dart:57, 130, 157`

**Severity**: P2 Medium

Multiple `Future.delayed` calls are used to clear feedback state after 2-3 seconds. All guard with `if (mounted)`, which is correct for `StateNotifier`. However, if the notifier is kept alive (which it is, being non-autoDispose), `mounted` remains true indefinitely. The delayed callbacks clear `lastActionStatus` even if a new action has been set in the interim, potentially eating a newer status message.

**Example** (line 605):
```dart
Future.delayed(const Duration(seconds: 2), () {
  if (mounted) {
    state = state.copyWith(clearActionFeedback: true);
  }
});
```

**Fix**: Track a feedback generation counter (similar to `_streamGeneration`). Before clearing, check if the generation matches the one that scheduled the clear.

---

### P2-02: Inconsistent provider annotation patterns

**Files**: Various under `mobile/lib/`
**Severity**: P3 Low

The codebase uses a mix of:
- Manual `StateNotifierProvider` / `Provider` / `FutureProvider` (majority)
- Codegen `@riverpod` annotations (statistics, error_book, notification_center, settings, document)

No issue today, but the two patterns do not interop cleanly with devtools. The codegen providers get auto-generated families and `.g.dart` files while manual ones do not. Long term, standardizing on one pattern would reduce cognitive load.

---

### P2-03: `offlineQueueCurrentUserIdProvider` is a non-autoDispose `FutureProvider` that may resolve to guest ID when auth is not ready

**File**: `mobile/lib/core/offline/offline_providers.dart:19`
**Severity**: P2 Medium

```dart
final offlineQueueCurrentUserIdProvider = FutureProvider<String>((ref) async {
  final user = ref.watch(authProvider).user;
  if (user != null) {
    return user.id;
  }
  return ref.watch(guestServiceProvider).getGuestId();
});
```

This provider `ref.watch`es `authProvider`, so it will re-resolve when auth state changes. However, because it is not `autoDispose`, the initial resolution (guest ID) may be cached and not re-resolved when a real user logs in if the provider has already completed. The Riverpod cache semantics for non-autoDispose `FutureProvider` mean it resolves once and stays unless one of its watch dependencies changes. Since `authProvider` is watched, it should re-trigger. But if `authProvider` emits the same object identity on login (unlikely but possible with some state management patterns), the queue would remain on the guest ID.

**Recommendation**: Add a unit test verifying that logging in after initial guest resolution re-triggers the provider.

---

### P2-04: `syncEngineProvider` starts processing immediately on creation

**File**: `mobile/lib/core/offline/offline_providers.dart:100-107`
**Severity**: P2 Medium

```dart
final syncEngineProvider = Provider<SyncEngine>((ref) {
  final localDb = ref.watch(localDatabaseProvider);
  final wsService = ref.watch(webSocketServiceProvider);
  final apiClient = ref.watch(apiClientProvider);
  final engine = SyncEngine(localDb, wsService, apiClient)..start();
  ref.onDispose(engine.stop);
  return engine;
});
```

`SyncEngine.start()` begins processing the outbox immediately upon provider creation. This happens even before the user is authenticated, potentially firing API calls that will fail with 401. Combined with P1-01 (leaked connectivity listener), this can cause spurious network requests.

**Fix**: Defer `start()` until connectivity is confirmed and auth state is ready. Alternatively, add an auth gate in `_processOutbox()`.

---

## 2. Chat Provider Deep Dive

### P0-01: `sendMessage` is an ~800-line method with complex closure state

**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:821-2000`
**Severity**: P0 Critical (maintainability / bug surface)

The `sendMessage` method captures 30+ mutable local variables in a closure that processes a streaming response. While the `_streamGeneration` guard correctly prevents stale streams from mutating state, the sheer complexity makes it extremely difficult to reason about edge cases:

- If the WebSocket disconnects mid-stream, the `await for` loop throws, caught by the outer `catch`. But `_streamDebouncer.cancel()` is called in both the catch block (line 1969) and `finalizeRun` (line 1094). This double-cancel is safe but indicates the control flow paths are hard to track.
- The `flushPending` closure captures `pendingStreamingContent`, `pendingAiStatus`, etc. by reference and mutates them. If `flushPending` is called after the stream generation has changed, the `_isDisposed || !isCurrentRequest()` guard prevents state mutation, but the local variables continue being accumulated for no purpose.

**Recommendation**: Refactor `sendMessage` into a dedicated `ChatStreamProcessor` class that encapsulates the stream lifecycle. This would make the control flow explicit and testable.

---

### P0-02: WebSocket reconnect during active stream may cause duplicate messages

**File**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:2243-2261`
**Severity**: P0 Critical

When `_handleConnectionClosed()` is called during an active stream, it broadcasts a `CONNECTION_CLOSED` error to all active request controllers:

```dart
void _handleConnectionClosed() {
  _stopHeartbeat();
  if (_requestControllers.isNotEmpty) {
    _broadcastErrorToActiveRequests(
      ErrorEvent(code: 'CONNECTION_CLOSED', message: '...', retryable: true),
    );
  }
  if (_connectionState != WsConnectionState.disconnected) {
    _triggerReconnect();
  }
}
```

The `_triggerReconnect` then calls `_establishConnection`, which on success calls `_flushPendingMessages`. If the user retries (via `retryLastMessage`), the message is re-sent with `reuseLastUserMessage: true`, which avoids re-adding the user message to the list. However, the original failed stream's accumulated partial content is NOT cleaned up if `finalizeRun` was already called for the `CONNECTION_CLOSED` error. The retry creates a new run ID but appends to the same message list. This is correct behavior, but there is a window where:

1. Stream A receives partial content
2. Connection closes -> error broadcast -> `finalizeRun` with `ChatRunPhase.failed`
3. Retry creates Stream B with new `runId`
4. Stream B succeeds and `finalizeRun` adds a new AI message

The result is the user sees: [user message] -> [partial AI message from failed stream] -> [full AI message from retry]. The partial message should not be rendered because `hasRenderableMessage` is only true if `accumulatedContent.trim().isNotEmpty || accumulatedWidgets.isNotEmpty`, but partial streaming content IS accumulated in `accumulatedContent` before the error.

**Fix**: In the error handler within `sendMessage`, clear `accumulatedContent` if the error is `CONNECTION_CLOSED` and no meaningful content was received. Alternatively, in `finalizeRun` for `failed` phase, do not add a message to `state.messages` if the content is only partial streaming content (check if `accumulatedWidgets.isEmpty && accumulatedUxEnvelope == null`).

---

### P1-03: `cancelActiveRun` does not clean up `_streamDebouncer`

**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:217-223`
**Severity**: P1 High

```dart
void cancelActiveRun({String reason = 'supersed'}) {
  if (!state.isSending && state.activeRunId == null) {
    return;
  }
  _invalidateActiveStreamState();
}
```

`_invalidateActiveStreamState` increments `_streamGeneration` and resets state, but does NOT cancel `_streamDebouncer`. If a pending debounced flush fires after cancellation, it will check `isCurrentRequest()` (which returns false due to incremented generation) and return early. This is safe, but the debouncer timer keeps ticking until it fires, which is a minor resource waste. More importantly, the `_streamDebouncer` is shared across all invocations of `sendMessage` on the same `ChatNotifier` instance. If a new `sendMessage` starts before the old debounced flush fires, the new call's `_streamDebouncer.run()` will cancel the old timer (correct behavior in `_Debouncer.run`).

**Status**: Currently safe but fragile. The shared debouncer makes the control flow non-obvious.

---

### P1-04: `chatProvider` is non-autoDispose -- disposed state not reachable through normal navigation

**File**: `mobile/lib/features/chat/presentation/providers/chat_provider_wiring.dart:16-18`
**Severity**: P1 High (by design, with trade-off)

```dart
final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(ref.watch(chatRepositoryProvider), ref),
);
```

The `chatProvider` and `chatRepositoryProvider` are intentionally non-autoDispose to preserve chat state across tab switches. The `ChatNotifier.dispose()` method is only called when the `ProviderContainer` is disposed (app shutdown). This means:

1. WebSocket connection persists even when user is not on the chat tab
2. Heartbeat timers keep firing
3. All accumulated messages stay in memory

The `_isDisposed` flag in `ChatNotifier` will only be set on app shutdown, so `mounted` checks in `Future.delayed` callbacks will always pass.

**Trade-off**: This is correct for UX (returning to chat tab should show the same conversation), but creates a persistent memory footprint. With 500 max messages retained and complex metadata per message, this can accumulate significant memory.

**Recommendation**: Consider a "soft pause" when navigating away from chat tab -- stop heartbeat, cancel pending debouncer timers, but keep messages in memory. Resume on tab return.

---

## 3. Memory Leak Patterns

### P1-05: `PlanReviewGrpcService` and `ReviewGrpcService` are never disposed

**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:92-95`
**Severity**: P1 High

```dart
PlanReviewGrpcService? _planReviewService;
ReviewGrpcService? _reviewService;
```

These are lazily initialized gRPC services that may hold channel resources. They are never disposed in `ChatNotifier.dispose()`. If they create gRPC client channels internally, those channels are leaked.

**Fix**: Add disposal in `ChatNotifier.dispose()`:
```dart
_planReviewService?.dispose();
_reviewService?.dispose();
```

---

### P2-05: `MainNavigationShell._communityEventsSub` cancel is unawaited

**File**: `mobile/lib/core/navigation/shell_navigation.dart:320`
**Severity**: P3 Low

```dart
@override
void dispose() {
  unawaited(_communityEventsSub?.cancel());
  _shellScrollController.dispose();
  super.dispose();
}
```

The `unawaited` cancel is fine for correctness -- the subscription will be cancelled asynchronously. However, if the community event stream emits during the brief window between `dispose` starting and the cancel completing, `_handleCommunityEvent` could be called on a disposed widget. The `_isShowingAchievementDialog` flag and `mounted` checks in dialog code mitigate this, but it is a theoretical race.

**Status**: Low risk in practice.

---

### P2-06: Animation controllers in design system widgets -- audit needed

**Files**: Multiple under `mobile/lib/core/design/`
**Severity**: P2 Medium

The following widgets create `AnimationController` instances in `initState`:
- `sparkle_motion_primitives.dart` (lines 305, 479)
- `sparkle_skeleton.dart` (line 29)
- `flame_indicator.dart` (lines 57, 70)
- `custom_button.dart` (line 162)
- `rarity_visual_wrapper.dart` (lines 97, 103, 109, 115 -- four controllers)
- `expandable_section.dart` (line 38)
- `stepper_indicator.dart` (line 27)

Spot-checking shows these widgets do have corresponding `dispose()` methods that call `_controller.dispose()`. The `rarity_visual_wrapper` creates FOUR controllers which all appear to be disposed. This is well-managed but worth a systematic grep to confirm no widget was missed.

---

### P2-07: `GalaxyNotifier._animationTimer` -- cancelled in dispose, but animation effects may orphan

**File**: `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart:352`
**Severity**: P3 Low

The `_animationTimer` is used for bloom/shrink effects and is cancelled in `dispose()`. This is correct. However, the static `_animationDuration` and `_animationFps` fields are marked `// ignore: unused_field`, suggesting the animation system may be partially deprecated or unused.

---

## 4. Navigation State

### P2-08: Deep link query parameters parsed without null-safety on numeric values

**File**: `mobile/lib/app/routes.dart:241-257`
**Severity**: P2 Medium

```dart
if (double.tryParse(state.uri.queryParameters['mastery'] ?? '') != null)
  'mastery': double.parse(state.uri.queryParameters['mastery']!),
```

This double-parses (once for null check, once for value). If the query parameter changes between the two parses (impossible for static URIs but possible if the URI is dynamically constructed), this could throw. More practically, the `!` assertion after a successful `tryParse` is safe, but the pattern is fragile.

**Recommendation**: Use a helper:
```dart
final mastery = double.tryParse(state.uri.queryParameters['mastery'] ?? '');
if (mastery != null) 'mastery': mastery,
```

---

### P2-09: `ChatScreen` receives `initialConversationId` but does not handle stale sessions

**File**: `mobile/lib/app/routes.dart:268`
**Severity**: P2 Medium

When navigating to `/chat?session_id=abc123`, the `ChatScreen` receives `initialConversationId`. If this session ID is expired or invalid on the backend, the chat will attempt to load history for a non-existent session and fail. The error handling in `loadConversationHistory` does handle this by restoring previous messages, but the user experience could be confusing.

**Recommendation**: Validate the session ID with a lightweight API call before loading full history, or fall back gracefully to a new session.

---

### P3-01: `StatefulShellRoute.indexedStack` preserves all branch states

**File**: `mobile/lib/app/routes.dart:151`
**Severity**: P3 Low (by design)

The shell route uses `indexedStack`, meaning all five tab branches (Home, Galaxy, Chat, Community, Profile) have their widget trees preserved in memory simultaneously. Combined with non-autoDispose providers, this means the memory footprint of the app is the sum of all tabs' states at all times.

This is the correct trade-off for preserving scroll position and state across tab switches, but worth documenting as a memory budget consideration.

---

## 5. Offline Queue

### P1-06: `rejectContentReview` fires `requestRegeneration` without awaiting -- error silently lost

**File**: `mobile/lib/features/chat/presentation/providers/chat_notifier_reviews.dart:136-144`
**Severity**: P1 High

```dart
requestRegeneration(
  originalContentId: 'content_from_review_${review.reviewId}',
  reviewId: review.reviewId,
  regenerationType: 'fix_issues',
).then((result) {
  if (result == null || result['success'] != true) {
    debugPrint('...');
  }
});
```

`requestRegeneration` is called with `.then()` (fire-and-forget) without `unawaited()`. Dart analyzer may warn about this. More importantly, if the regeneration fails, the user only gets the initial "regeneration requested" toast but never learns of the failure. The state is already cleared (`clearPendingContentReview: true`), so the user cannot retry.

**Fix**: Either await the regeneration with a loading indicator, or add a retry mechanism with a state rollback on failure.

---

### P2-10: Offline message queue has no conflict resolution for duplicate sends

**File**: `mobile/lib/core/offline/offline_message_queue_service.dart`
**Severity**: P2 Medium

When the app reconnects, `_restorePendingFromDb` loads retryable messages and adds them to the pending queue. If the WebSocket was briefly connected and the message was sent (but not ACKed), the message status is `sent`. The restoration changes it back to `pending` via `prepareForRetry`, which could cause a duplicate send if:
1. Message is sent to server (status = `sent`)
2. App crashes before ACK
3. On restart, message is loaded as retryable
4. `prepareForRetry` sets status back to `pending`
5. Message is sent again

The backend should be idempotent on `request_id`, so this is mitigated by the `request_id` field. But if the backend does not deduplicate on `request_id`, the message will appear twice.

**Recommendation**: Verify backend idempotency on `request_id` for all message types. Document this as a contract.

---

### P2-11: `OfflineSyncQueue.handleServerUpdate` has a "local wins" branch that does not force push

**File**: `mobile/lib/core/offline/sync_queue.dart:200-204`
**Severity**: P2 Medium

```dart
} else {
  // Local wins.
  // Ideally we should force a push here if our revision is higher,
  // but syncPendingUpdates loop will handle it eventually.
}
```

The comment acknowledges the gap. If the local revision is higher, the pending updates will eventually be pushed by the sync loop. But there is no guarantee of ordering or timing. If the server sends another update before the local push completes, another conflict resolution will occur, potentially overwriting the local change.

**Recommendation**: Force an immediate push after local-wins resolution.

---

### P3-02: `OfflineMessageQueueService` null-checks `_isar` on every call

**File**: `mobile/lib/core/offline/offline_message_queue_service.dart:12`
**Severity**: P3 Low

```dart
Isar? get _isar => _localDb.isarOrNull;
```

Every method starts with `final db = _isar; if (db == null || !db.isOpen) return;`. This is defensive but means all operations silently no-op if Isar is not initialized. This could mask initialization bugs in testing.

---

## 6. Cross-Cutting Observations

### `_streamGeneration` / `_runSequence` pattern is well-implemented

The generation counter pattern in `ChatNotifier` (lines 107-109) correctly prevents stale streams from mutating state. This is the single most important guard in the chat system and is implemented correctly.

### WebSocket V2 lifecycle is well-managed overall

The `WebSocketChatServiceV2` class has:
- Proper `WidgetsBindingObserver` lifecycle (pause/resume)
- Connection generation (`_connGen`) to prevent stale teardowns
- Request-scoped stream controllers that clean up on cancel/done/error
- Terminal fallback timers that are properly cancelled
- Heartbeat with consecutive failure tracking and stream-active suppression

The main gaps are the connectivity listener leak (P1-01) and the active-stream reconnect behavior (P0-02).

### `ChatNotifier.dispose()` is comprehensive

The dispose method correctly cancels:
- `_streamDebouncer`
- `_connectionStateSubscription`
- `_historyLoadOperation`
- Sets `_isDisposed = true`

The missing disposal of `_planReviewService` and `_reviewService` (P1-05) is the gap.

---

## Action Items (Prioritized)

| Priority | ID | Action | Files |
|----------|----|--------|-------|
| P0 | P0-01 | Refactor `sendMessage` into a `ChatStreamProcessor` class | `chat_provider.dart` |
| P0 | P0-02 | Fix partial message accumulation on CONNECTION_CLOSED error | `chat_provider.dart` |
| P1 | P1-01 | Store and cancel connectivity subscription in `SyncEngine` | `sync_engine.dart` |
| P1 | P1-05 | Dispose gRPC service instances in `ChatNotifier.dispose()` | `chat_provider.dart` |
| P1 | P1-06 | Await `requestRegeneration` or add failure rollback | `chat_notifier_reviews.dart` |
| P1 | P1-03 | Cancel `_streamDebouncer` in `cancelActiveRun` | `chat_provider.dart` |
| P1 | P1-04 | Add soft pause/resume for chat when navigating away | `chat_provider.dart`, `chat_screen.dart` |
| P2 | P2-01 | Add generation guards to `Future.delayed` feedback clears | `chat_notifier_actions.dart` |
| P2 | P2-04 | Defer `SyncEngine.start()` until auth is ready | `offline_providers.dart` |
| P2 | P2-10 | Verify backend idempotency on `request_id` | Backend contract |
| P2 | P2-11 | Force push after local-wins conflict resolution | `sync_queue.dart` |
