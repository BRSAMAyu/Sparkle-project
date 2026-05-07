# R12 / R1A2 — Chat_AI 二次深度审查
**Date**: 2026-05-08
**Scope**: Chat + AI
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: The vision document (`.claude/plans/wise-tickling-lobster.md`) was not found in the current branch. Compared against `phase3_card_protocol_plan.md` and current implementation state.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 0 |
| P1 (important gap, ship with plan) | 1 |
| P2 (nice to have, post-launch) | 5 |
| Verified working | 2 |

---

## R11 P0 验证
No P0 issues were identified in the R11 audit for this scope.

---

## P0 Findings (Must Fix Before Launch)
None found. The core chat pipeline is robust, supporting both offline persistence and concurrent connection limiting.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Streaming Content Loss on Rapid Message Send (Carryover from R11)
**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
**Lines**: 217-223, 833-835
**Problem**: When a user sends a second message while the first AI response is still streaming, `cancelActiveRun(reason: 'new_message')` is called. This immediately calls `_invalidateActiveStreamState()`, silently discarding any partially streamed response.
**Evidence**:
```dart
  void cancelActiveRun({String reason = 'superseded'}) {
    if (!state.isSending && state.activeRunId == null) {
      return;
    }
    debugPrint('[Chat] cancelActiveRun: $reason');
    _invalidateActiveStreamState(); // Partially streamed content is lost here
  }
```
**Expected**: Partial streaming content should be finalized and persisted into `state.messages` before the state is cleared.
**Fix recommendation**: Before invalidating state, check if `state.streamingContent` is not empty. If so, call `finalizeRun(phase: ChatRunPhase.cancelled)` or manually append a canceled message to the history.

---

## P2 Findings (Post-Launch)

### P2-1: No Exponential Backoff on History Load Failure (Carryover from R11)
**File**: `mobile/lib/features/chat/presentation/providers/chat_notifier_history.dart`
**Lines**: 100-150
**Problem**: The error catch block sets `error` and `errorCode` but does not schedule a retry.
**Evidence**: Catch block sets `isLoading: false` but does not initiate a timer for retry.
**Expected**: For retryable transient errors, a delayed retry should be scheduled.
**Fix recommendation**: Introduce a retry counter and `Future.delayed` call to `loadConversationHistory`.

### P2-2: ListView.builder Not Using KeepAlive for Rich Widget Payloads (Carryover from R11)
**File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
**Lines**: 1392-1550
**Problem**: Rich payloads (PlanReviewCard, AgentReasoningBubble) are rebuilt when scrolled out of view and back, causing slight jank.
**Evidence**: `ListView.builder` returns `ChatBubble` directly without `AutomaticKeepAliveClientMixin`.
**Expected**: Expensive widgets should maintain their state during scroll.
**Fix recommendation**: Wrap the `ChatBubble` or its inner complex payloads with `AutomaticKeepAlive`.

### P2-3: WebSocket Parse Main-Thread Threshold Too High (Carryover from R11)
**File**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`
**Lines**: 2015-2017
**Problem**: Messages up to 12KB are parsed synchronously on the main thread, potentially causing frame drops on lower-end devices during heavy metadata streams.
**Evidence**: `final event = data.length < 12000 ? _parseChatEvent(data) : await compute(_parseChatEvent, data);`
**Expected**: Threshold should be smaller (e.g., 4096 bytes) or metadata-heavy JSON should always use `compute`.
**Fix recommendation**: Lower threshold to `4096`.

### P2-4: Plan Review Rejection Sheet Lacks Input Validation (Carryover from R11)
**File**: `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart`
**Lines**: 332-347
**Problem**: The rejection flow accepts an empty note and category, meaning empty feedback can be sent to the backend.
**Evidence**: `_handleRejectionFlow` processes `feedback` without enforcing non-empty values.
**Expected**: Force the user to either select a category or provide a short text note.
**Fix recommendation**: In `_handleRejectionFlow`, add a check `if (feedback.category.isEmpty && (trimmedNote == null || trimmedNote.isEmpty)) return;`.

### P2-5: Go WebSocket Proxy Does Not Forward Client Close Code (Carryover from R11)
**File**: `backend/gateway/internal/handler/websocket_proxy.go`
**Lines**: 260-400
**Problem**: When the Flutter client gracefully closes the WS, the proxy exits the read loop and implicitly closes both connections via `defer clientConn.Close()` / `defer backendConn.Close()`, but does not forward the close frame to the backend.
**Evidence**: The read loop handles `err != nil` by logging and calling `sendErr(err)`, which signals done, triggering defers. `closeConnections` is only called explicitly on panic.
**Expected**: The proxy should parse the close frame code/reason and write it to `backendConn`.
**Fix recommendation**: Check if `err` is a `CloseError`, extract the code and text, and write a close message to `backendConn` before exiting.

---

## Verified Working (Strengths)

### V-1: Hardcoded English String in Chat Input Hint Fixed
- Verified `mobile/lib/features/chat/presentation/widgets/chat_input.dart` now uses `context.l10n.chatInputPlaceholder` instead of hardcoded ternary string checks.
- **Verdict**: PASS

### V-2: _streamDebouncer Not Cancelled on Disposal Path Fixed
- Verified in `chat_provider.dart:227` that `_streamDebouncer.cancel()` is safely called prior to `_isDisposed = true` and other cleanup logic.
- **Verdict**: PASS

---

## Cross-Route Integration Issues
No major new cross-route issues identified. The Go gateway correctly maps connections to user IDs via token extraction and limits concurrent connections accurately. Message deduplication is functioning.

---

## Code Quality Observations
The Dart codebase uses Riverpod heavily. The `ChatNotifier` is becoming quite large (over 1000 lines including extensions) and may benefit from further decomposition, especially decoupling the WebSocket lifecycle management from the UI presentation state. The Go-side proxy is robust with good use of sync primitives but lacks full proxying of control frames (such as close codes).