# R11-R1A2: Chat + AI Interaction Journey Audit

**Date**: 2026-05-07
**Auditor**: Automated Full-Stack Trace
**Scope**: Flutter Chat UI -> WebSocket -> Go Proxy -> gRPC -> Python Orchestrator -> LLM -> Response Streaming Back
**Verdict**: **CONDITIONAL PASS** -- no P0 blockers found; 3 P1 and 5 P2 issues identified.

---

## Summary

The chat + AI interaction pipeline is architecturally sound and well-defended. The full data flow from Flutter tap to Python orchestrator and back is complete, with robust error handling, race condition guards, and offline resilience. No issues were found that would block launch. Three P1 issues (streaming content loss risk on rapid send, hardcoded English in chat input hint, and potential _Debouncer timer leak) could degrade the user experience under specific conditions and should be addressed in the first post-launch patch.

---

## Critical Issues (P0): 0

None found. The core chat pipeline is complete and functional.

---

## High Issues (P1): 3

### Finding 1: Streaming Content Loss on Rapid Message Send
- **Severity**: P1
- **User Impact**: When a user sends a second message while the first AI response is still streaming, the first response's partial content may be discarded without being saved as a message in the chat history. The `cancelActiveRun(reason: 'new_message')` call at chat_provider.dart:834 triggers `_invalidateActiveStreamState()` which clears `streamingContent` and all accumulated widgets/metadata. If the first response had meaningful partial content (e.g., half a plan), it is silently lost.
- **File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:834-835`
- **Current Code**:
  ```dart
  if (state.isSending) {
    cancelActiveRun(reason: 'new_message');
  }
  ```
- **Expected**: Partial streaming content should be finalized as a message before cancellation, or at minimum the user should be informed that the previous response was interrupted.
- **Fix**: Before calling `cancelActiveRun`, check if `state.streamingContent` is non-empty and call `finalizeRun(phase: ChatRunPhase.cancelled)` to persist the partial response as a message.

### Finding 2: Hardcoded English String in Chat Input Hint
- **Severity**: P1
- **User Impact**: Chinese-language users see an English fallback "Type a message..." in the text field hint when `I18nService.instance.isChinese` evaluates to false during initial build or before localization is loaded.
- **File**: `mobile/lib/features/chat/presentation/widgets/chat_input.dart:454`
- **Current Code**:
  ```dart
  hintText: widget.hintText ?? (I18nService.instance.isChinese ? '输入消息...' : 'Type a message...'),
  ```
- **Expected**: Should use `context.l10n.chatInputHint` or equivalent ARB key, not a runtime boolean check. The i18n system already has localized strings; this bypasses it.
- **Fix**: Replace with `widget.hintText ?? context.l10n.chatInputHint` and ensure the ARB file has a `chatInputHint` key.

### Finding 3: _Debouncer Timer Not Cancelled on Disposal Path
- **Severity**: P1
- **User Impact**: If the ChatNotifier is disposed while a debounced state update is pending (e.g., user navigates away mid-stream), the `_streamDebouncer.cancel()` is called in `dispose()` but the internal Timer may already be scheduled and fire on a disposed StateNotifier, potentially causing a benign but logged state-set-after-dispose error.
- **File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:226-233`
- **Current Code**:
  ```dart
  @override
  void dispose() {
    _isDisposed = true;
    unawaited(_historyLoadOperation?.cancel());
    _historyLoadOperation = null;
    unawaited(_connectionStateSubscription?.cancel());
    _streamDebouncer.cancel();
    _chatRepository.dispose();
    super.dispose();
  }
  ```
- **Expected**: The `_streamDebouncer.cancel()` should be called before `_isDisposed = true` or the debouncer's callback should check `_isDisposed` (which it does in `flushPending` via `isCurrentRequest()`, but `_isDisposed` is set before cancel, and the `finalizeRun` method does not check `_isDisposed`).
- **Fix**: Move `_streamDebouncer.cancel()` before `_isDisposed = true`, or add an `_isDisposed` guard to `finalizeRun`.

---

## Medium Issues (P2): 5

### Finding 4: No Exponential Backoff on History Load Failure
- **Severity**: P2
- **User Impact**: If conversation history loading fails (network error, 404), the user sees an error message but there is no automatic retry. They must manually navigate away and back to trigger another load attempt.
- **File**: `mobile/lib/features/chat/presentation/providers/chat_notifier_history.dart:115-131`
- **Current Code**: Error handler sets `error` and `errorCode` on state but does not schedule a retry.
- **Expected**: For transient errors (timeout, 5xx), schedule an automatic retry with exponential backoff.
- **Fix**: Add a retry counter and schedule a delayed `loadConversationHistory` call for transient failures.

### Finding 5: ListView.builder Not Using AutomaticKeepAlive for Widget Payloads
- **Severity**: P2
- **User Impact**: Plan review cards, expert roundtable widgets, and other rich widget payloads embedded in chat messages may be rebuilt unnecessarily when scrolling up and down in long conversations, causing minor jank on lower-end devices.
- **File**: `mobile/lib/features/chat/presentation/screens/chat_screen.dart:1399-1600`
- **Current Code**: `ListView.builder` with `cacheExtent: 600` but no `AutomaticKeepAliveClientMixin` on ChatBubble.
- **Expected**: Important widget states (plan review card with user decision pending, for example) should be kept alive during scroll.
- **Fix**: Wrap ChatBubble items in `AutomaticKeepAlive` or use `SliverPrototypeExtentList` for more predictable recycling.

### Finding 6: WebSocket Message Parse Runs on Main Thread for Medium Frames
- **Severity**: P2
- **User Impact**: Messages between 0-12KB are parsed synchronously on the main thread via `_parseChatEvent(data)` instead of `compute()`. During heavy multi-agent responses with large metadata, this can cause micro-jank.
- **File**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:2015-2017`
- **Current Code**:
  ```dart
  final event = data.length < 12000
      ? _parseChatEvent(data)
      : await compute(_parseChatEvent, data);
  ```
- **Expected**: Threshold should be lower (e.g., 4KB) or all parsing should go through compute for consistency, especially since the parser handles complex metadata extraction (routing previews, roundtable turns, orchestration traces).
- **Fix**: Lower threshold to 4096 bytes, or always use compute for JSON messages containing "metadata" or "delta" type fields.

### Finding 7: Plan Review Card Rejection Sheet Lacks Minimum Input Validation
- **Severity**: P2
- **User Impact**: When a user rejects a plan, the rejection feedback sheet allows submitting without entering any text, sending an empty `userComment`. The backend receives a rejection with no reason, reducing the value of the feedback loop.
- **File**: `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:331-347`
- **Current Code**: `_handleRejectionFlow` accepts the feedback sheet result even if both `category` and `note` are empty.
- **Expected**: Require at minimum a category selection or short text note before allowing rejection to proceed.
- **Fix**: Add validation in `_handleRejectionFlow` to check if `feedback.note` or `feedback.category` is non-empty before proceeding.

### Finding 8: Go WebSocket Proxy Does Not Forward Client Close Code to Backend
- **Severity**: P2
- **User Impact**: When the Flutter client intentionally closes the WebSocket (e.g., user switches tabs, app goes to background), the Go proxy's `client_to_backend` goroutine detects the close but does not forward the close code/reason to the backend. The backend may interpret this as an abnormal disconnection rather than a graceful one.
- **File**: `backend/gateway/internal/handler/websocket_proxy.go:362-371`
- **Current Code**: Reads message, checks for errors, and closes the done channel. No explicit forwarding of close frame to backend.
- **Expected**: Forward the close frame with its code and reason to the backend so the Python side can distinguish graceful disconnects from network failures.
- **Fix**: Before signaling done, write a close frame to the backend connection with the same code/reason received from the client.

---

## Findings Detail: Verified Architecture

### 1. Chat Screen UI -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| Message input | PASS | ChatInput widget (chat_input.dart) handles text input, max 4 lines, min 1 line, with proper controller lifecycle |
| Send button | PASS | Animated send button with gradient, disabled state when no text, loading indicator when sending |
| Message bubbles | PASS | ChatBubble widget (chat_bubble.dart) renders user/assistant messages with distinct styling, supports delivery status |
| Typing indicator | PASS | `_TypingIndicator` shown when streaming starts with no content yet (chat_screen.dart:1505-1511) |
| Rich message types | PASS | 20+ widget types handled: plan_review_card, action_card, growth_card, divine_moment, stale_recovery, spine_receipt, goal_arbitration, community_insight, etc. |
| Message scrolling | PASS | Reverse ListView.builder with ScrollController, auto-scroll on new messages via listener (chat_screen.dart:206-209), scroll-to-bottom animation 200ms |
| Auto-scroll to bottom | PASS | `_scrollToBottom()` uses `animateTo(0)` with 200ms easeOut (chat_screen.dart:2595-2603) |
| Empty state | PASS | `_buildQuickActions(context)` shown when no messages (chat_screen.dart:1394-1398), displays welcome message with quick action chips |
| Long message handling | PASS | SparkleMarkdown (sparkle_markdown.dart) renders with flutter_markdown, supports code blocks, links, streaming mode |
| Markdown rendering | PASS | SparkleMarkdown supports `isStreaming` mode for partial markdown completion, code blocks, inline code, links, images |
| Voice input | PASS | VoiceInputButton integrated with transcription callback |
| File attachments | PASS | AttachmentPickerSheet with FilePickerWithPresignedUpload |
| Offline queue indicator | PASS | OfflineQueueIndicator widget shows pending message count and delivery status |

### 2. WebSocket Connection -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| Connection lifecycle | PASS | `ensureConnected()` -> `_establishConnectionAsync()` -> IOWebSocketChannel.connect() with auth |
| Reconnect mechanism | PASS | Exponential backoff: 800ms, 1200ms, 2200ms, 4200ms, 8200ms, 12200ms (6 max attempts) with jitter |
| Heartbeat/ping-pong | PASS | 30s interval, 60s timeout, 3 consecutive failures trigger reconnect, stream-active suppression |
| Message queue offline | PASS | `_pendingMessages` list with 50-message cap, overflow drops oldest with error event |
| Offline persistence | PASS | OfflineMessageQueueService backed by Isar DB, restores on reconnect, marks sent/acked/failed |
| Error handling on drop | PASS | `_handleConnectionError` broadcasts error to all active request controllers |
| 401 handling | PASS | Detects 401, refreshes token via auth repository, reconnects on success, logs out on failure |
| App lifecycle | PASS | `WidgetsBindingObserver.didChangeAppLifecycleState`: disconnects on pause, reconnects on resume |
| Concurrent connections | PASS | Go `registerConnection()` enforces per-user limit via `activeByUser` map with mutex |
| Cleanup on disconnect | PASS | Go proxy uses WaitGroup, `draining` atomic flag, `closeConnections` with sync.Once |
| Auth via WS ticket | PASS | `_issueWsTicket()` calls `/ws/ticket` endpoint, falls back to query param token |

### 3. AI Response Flow -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| FSM states | PASS | INIT, THINKING, GENERATING, TOOL_CALLING, DONE, FAILED (orchestrator.py:176-181) |
| Dual-core routing | PASS | `self.dual_core_router = dual_core_router` initialized in ChatOrchestrator.__init__ (orchestrator.py:306) |
| UX envelope adaptation | PASS | Metadata keys: ux_turn, ux_progress, ux_result, ux_followthrough, ux_sources, ux_evolution extracted and forwarded |
| Streaming response | PASS | `_parseChatEvent` handles "delta" type events, accumulated in ChatNotifier, debounced at 50ms for UI updates |
| Tool execution | PASS | ToolStartEvent/ToolResultEvent parsed and displayed with tool name, progress tracking |
| LLM timeout | PASS | 8-minute stream timeout with STREAM_TIMEOUT error code, retryable |
| Response finalization | PASS | `finalizeRun()` persists accumulated content, widgets, metadata as ChatMessageModel |
| Run cancellation | PASS | `_streamGeneration` counter prevents stale streams from mutating current state |
| Agent collaboration | PASS | Expert roundtable, routing preview, agent turns all tracked and rendered |
| Reasoning visualization | PASS | ReasoningStep events accumulated with timing, rendered as AgentReasoningBubble |

### 4. Plan Review Cards -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| Card rendering | PASS | PlanReviewCard with decision gradient, confidence display, comments list, slide-in animation |
| Approve/reject buttons | PASS | Action buttons shown when `!autoApproved && decision != approved`, with delegate toggle |
| Rejection prompts reason | PASS | `_handleRejectionFlow()` shows feedback sheet with category and note (see P2 Finding 7 for gap) |
| Review feedback via WS | PASS | `sendPlanReviewFeedback()` sends typed message with review_id, user_decision, plan_id, user_comment |
| Review status events | PASS | PlanReviewStatusEvent handled in ChatNotifier with `_handlePlanReviewStatus` |
| Submission state | PASS | `_isSubmitting` and `_isSubmitted` flags prevent double-submission, show loading state |
| Delegate toggle | PASS | Auto-resolved from suggested_modifications, user can toggle before approval |

### 5. Context & Memory -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| Context assembly | PASS | ContextBuilderMixin extracts user profile, plan context, task context, episodic memory, cognitive fragments |
| Self-model injection | PASS | Stage 34/39 modes loaded via kill switch services, scaffolding snapshot built |
| Conversation history | PASS | Loaded via REST `/chat/history/{id}`, paginated with 20-message pages, cancelable |
| User preferences | PASS | Chat mode, reasoning mode, guidance mode, document context mode all sent as extra_context |
| Session management | PASS | Session ID maintained in WS, forwarded on reconnect for backend context restoration |
| Memory service | PASS | MemoryService imported and used for episodic/semantic memory retrieval |
| State aggregator | PASS | StateAggregatorService imported for real-time user state aggregation |

### 6. Recall Notifications -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| Spine receipt cards | PASS | SpineReceiptEvent parsed from metadata, stored in state, rendered as SpineReceiptCard |
| Stale recovery | PASS | StaleRecoveryEvent triggers stale_recovery_card widget |
| Community hints | PASS | CommunityHintEvent renders as community_insight_card |
| Growth milestones | PASS | GrowthCardEvent renders as growth_card |
| Divine moments | PASS | DivineMomentEvent renders as divine_moment_card (MAGIC-002 through MAGIC-006) |
| UX warnings | PASS | UXWarningEvent renders as proactive risk warning |
| Goal arbitration | PASS | GoalArbitrationEvent renders multi-goal conflict surface |

### 7. Error States -- VERIFIED WORKING

| Feature | Status | Evidence |
|---------|--------|----------|
| Network error | PASS | CONNECTION_ERROR broadcast to active requests, retryable, reconnect triggered |
| LLM unavailable | PASS | LLM_ERROR/AI_ERROR codes mapped to user-friendly messages via ErrorMessages utility |
| Rate limiting | PASS | RATE_LIMIT_EXCEEDED handled with user-friendly message, Go-side WS message rate limiter |
| Malformed message | PASS | PARSE_ERROR from _parseChatEvent catch, INVALID_FORMAT for missing "type" field |
| Mid-conversation disconnect | PASS | CONNECTION_CLOSED error broadcast, pending messages preserved in offline queue |
| Auth failure | PASS | 401 detection, automatic token refresh, reconnection, logout on permanent failure |
| Stream timeout | PASS | 8-minute inactivity timeout, STREAM_TIMEOUT error event with retryable=true |
| Error auto-clear | PASS | Error message auto-cleared after 10 seconds (chat_screen.dart:249-257) |
| Retry mechanism | PASS | `retryLastMessage()` reuses last pending request content with `reuseLastUserMessage: true` |
| Failure icon mapping | PASS | `_chatFailureIcon()` maps error codes to appropriate icons (wifi_off, lock, cloud_sync, etc.) |

---

## Verified Working: Complete List

1. **Full chat message lifecycle**: User types -> send button -> ChatNotifier.sendMessage -> ChatRepository.chatStream -> WebSocketChatServiceV2.sendMessage -> Go WebSocket proxy -> Python backend -> streaming delta events back through same path -> accumulated in ChatNotifier -> rendered as ChatBubble
2. **WebSocket connection management**: Auto-connect, heartbeat, exponential backoff reconnect, app lifecycle awareness, token refresh, offline queue persistence
3. **Rich widget rendering**: 20+ widget types (plan review, action card, growth card, divine moments, stale recovery, spine receipts, community hints, goal arbitration, expert roundtable, execution suggestions, etc.)
4. **Plan review flow**: Full cycle from PlanReviewWidgetEvent through card rendering to user decision via WS feedback
5. **Error resilience**: Comprehensive error mapping, retry mechanism, auto-clearing errors, graceful degradation
6. **Offline resilience**: Message queue with Isar persistence, restore on reconnect, delivery status indicators
7. **Context assembly**: Multi-source context injection (user profile, plan, tasks, memory, cognitive state, Aurora runtime)
8. **Dual-core routing**: Execution vs cognitive mode detection, UX envelope metadata propagation
9. **Streaming debouncing**: 50ms debounce prevents UI thrashing during rapid delta events
10. **Race condition protection**: `_streamGeneration` counter prevents stale streams from corrupting current state
11. **Concurrent request isolation**: Per-request StreamControllers in WS service prevent event cross-contamination
12. **Go-side hardening**: Connection limits, reconnect rate limiting, message deduplication, panic recovery in goroutines
13. **Accessibility**: Semantics labels on key interactive elements (send button, attachment button, plan review card)
14. **Memory management**: Proper disposal of controllers, subscriptions, timers, and animation controllers

---

## Files Audited

### Flutter (Mobile)
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (2700+ lines)
- `mobile/lib/features/chat/presentation/widgets/chat_input.dart`
- `mobile/lib/features/chat/presentation/widgets/chat_bubble.dart`
- `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart`
- `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
- `mobile/lib/features/chat/presentation/providers/chat_state.dart`
- `mobile/lib/features/chat/presentation/providers/chat_notifier_history.dart`
- `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` (2692 lines)
- `mobile/lib/features/chat/data/repositories/chat_repository.dart`
- `mobile/lib/core/utils/error_messages.dart`
- `mobile/lib/core/widgets/sparkle_markdown.dart`

### Go (Gateway)
- `backend/gateway/internal/handler/websocket_proxy.go`

### Python (Engine)
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/context_builder.py`
