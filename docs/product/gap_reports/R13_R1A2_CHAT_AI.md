# R13 / R1A2 -- Chat + AI Deep Audit
**Date**: 2026-05-07
**Scope**: WebSocket chat, streaming, rich cards, dual-core routing, history
**Layers**: Flutter -> Go Gateway -> Python Engine -> PostgreSQL / Redis

## Summary
| Category | Count |
|----------|-------|
| P0 | 0 |
| P1 | 3 |
| P2 | 5 |
| Verified | 22 |

---

## P1 Findings

### P1-1: No client-side message length limit in Flutter chat input
**File**: `mobile/lib/features/chat/presentation/widgets/chat_input.dart:186-188`
**Evidence**: The `_handleSend()` method trims text and checks for empty, but never enforces a character limit. The Go gateway enforces `maxMessageLength = 4000` chars (`backend/gateway/internal/handler/chat_orchestrator.go:130,532`), so the user gets an opaque server-side error rather than immediate client feedback. The `TextField` has no `maxLength` property set.
**Impact**: Users typing long messages get a server-side rejection (`message_length_exceeded`) with no prior warning. Wasted user effort; poor UX.
**Fix**: Add `maxLength: 4000` to the `TextField` in `ChatInput`, and show a character count near the limit.

### P1-2: Chat history persistence loses AI assistant responses in multi-turn streams
**File**: `backend/gateway/internal/service/chat_history_persister.go:220-224`
**Evidence**: The persister writes to `chat_messages` with columns `(id, session_id, user_id, role, content, created_at)`. However, it does NOT persist `widgets`, `tool_results`, `reasoning_steps`, or `ux_envelope` data. The `ChatHistoryMessage` struct at `chat_history.go:70-80` does define `Widgets`, `ToolResults`, and other fields, but the SQL INSERT at line 220-224 only writes `(id, session_id, user_id, role, content, created_at)`. Rich metadata from AI responses (plan review cards, action cards, collaboration data) is lost on reload.
**Impact**: When a user reloads a conversation, all rich card data is gone -- only plain text survives. PlanReviewCards, ToolResult cards, AgentCollaboration panels, and reasoning steps are all stripped.
**Fix**: Add columns for `widgets`, `tool_results`, `metadata` (JSONB) to `chat_messages` table and include them in the INSERT.

### P1-3: No AI chat session search functionality
**File**: Searched all of `mobile/lib/features/chat/` -- no search implementation found.
**Evidence**: Community group chat has search (`group_chat_screen.dart:847`), but the primary AI chat screen (`chat_screen.dart`) has no search capability. There is no search endpoint in the Go chat history service, and no search UI. The `getRecentConversations` method in `chat_repository.dart:248` lists sessions but offers no full-text search.
**Impact**: Users cannot find previous conversations or specific AI advice. With daily usage over weeks, conversation history becomes un-navigable.
**Fix**: Add full-text search endpoint to Go history service using PostgreSQL `ts_vector` on `chat_messages.content`, and add a search bar UI to the conversation list.

---

## P2 Findings

### P2-1: Concurrent rapid messages may interleave streaming events
**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:833-835,864-865`
**Evidence**: When `isSending` is true and the user sends a new message, `cancelActiveRun(reason: 'new_message')` is called (line 833-835). The `_streamGeneration` counter (line 864) prevents stale events from corrupting state via `isCurrentRequest()`. However, the WS service uses per-request controllers (`_requestControllers` map at `websocket_chat_service_v2.dart:1360`) keyed by `requestId`. The Go gateway's `HandleWebSocket` at `chat_orchestrator.go:344` processes messages sequentially in a single loop, so the second `StreamChat` gRPC call blocks until the first completes. The cancel mechanism in Flutter is sound, but there is a brief window where the first stream's `DoneEvent` may arrive after cancellation, causing a stale `isCurrentRequest()` check to reject it silently. The user sees no error but may miss a partial response.
**Impact**: Low-probability edge case; mostly mitigated by generation counter. No data corruption, but occasional lost partial responses.
**Fix**: Consider sending an explicit cancel signal to the Go gateway when the client cancels a stream, allowing the gateway to abort the in-flight gRPC call.

### P2-2: Dual-core mode chip only updates on `FullTextEvent`, not `TextEvent`
**File**: `mobile/lib/features/chat/presentation/providers/chat_provider.dart:1514-1519`
**Evidence**: The `dual_core_mode` is extracted from `ux_turn` only in the `FullTextEvent` handler (line 1514-1519). The `TextEvent` handler (line 1299-1450) does NOT extract `dual_core_mode`. Since most streaming responses use `TextEvent` (delta chunks), the dual-core mode chip only updates when a `FullTextEvent` arrives (typically near the end of a stream). During streaming, the chip shows stale data.
**Impact**: The dual-core routing indicator lags behind the actual mode during streaming. Minor visual inconsistency.
**Fix**: Also extract `dual_core_mode` from the `TextEvent` metadata handler.

### P2-3: FileMessageBubble uses hardcoded "View" label bypassing i18n
**File**: `mobile/lib/features/chat/presentation/widgets/file_message_bubble.dart:229`
**Evidence**: `label: I18nService.instance.isChinese ? '...' : 'View'` uses the ternary pattern rather than the proper `context.l10n` system. The "Save to library" button (line 239) correctly uses `context.l10n.chatFileSaveToLibrary`, but "View" does not.
**Impact**: Minor i18n inconsistency. The view button label is not translatable through the standard l10n system.
**Fix**: Add a `chatFileView` key to the l10n strings and use `context.l10n.chatFileView`.

### P2-4: Chat history persister generates new UUID per message, no request_id correlation
**File**: `backend/gateway/internal/service/chat_history_persister.go:196-197`
**Evidence**: Each message gets `messageID := uuid.New().String()` on insert. There is no correlation with the original `request_id` from the client or the `response_id` from the AI. The `ChatHistoryMessage` struct does not include a `request_id` field. This means there is no way to link a user's sent message with the AI's response across reloads.
**Impact**: No request-response correlation in persisted history. Cannot verify response integrity or trace issues.
**Fix**: Add `request_id` and `response_id` columns to `chat_messages` and include them in the INSERT.

### P2-5: WebSocket reconnection does not replay in-flight request state
**File**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:2238-2258`
**Evidence**: When `_handleConnectionClosed()` fires during an active stream, it broadcasts `CONNECTION_CLOSED` errors to all active request controllers (line 2242-2252). These are non-retryable from the WS service's perspective. The `ChatNotifier` in `chat_provider.dart:1633-1660` does show a retryable error to the user via `ErrorMessages.isRetryable('CONNECTION_CLOSED')`, but the WS-level stream is already torn down. The user must manually tap "retry" -- there is no automatic reconnection-and-replay of the in-flight message.
**Impact**: Users lose their AI response mid-stream on network glitches and must manually retry. No automatic resumption.
**Fix**: On reconnect, check if there was an in-flight request and automatically replay it, or at minimum show a one-tap "resend" option.

---

## Verified Working

### 1. WebSocket Connection Lifecycle
- **Authentication**: JWT token resolved from `AuthRepository` (`websocket_chat_service_v2.dart:1755-1772`), or WS ticket exchange via `/ws/ticket` (line 1774-1790). Token passed as query param on connection. Go gateway requires `user_id` from auth middleware (`chat_orchestrator.go:298-304`). VERIFIED.
- **Reconnection**: Exponential backoff with jitter, 6 max attempts (`websocket_chat_service_v2.dart:1335-1343`). Go gateway has reconnect rate limiting (`websocket_proxy.go:31-37`). Session_id forwarded on reconnect for context restoration (`websocket_chat_service_v2.dart:1694-1697`). VERIFIED.
- **Heartbeat**: Client sends `{"type": "ping"}` every 30s (`websocket_chat_service_v2.dart:1384,2328`), expects pong within 60s (line 1386-1387). 3 consecutive failures triggers reconnect (line 1389). Stream-active suppression prevents false reconnects during active streaming (line 2400-2414). Go gateway sends its own pings at configurable interval with configurable pong wait (`chat_orchestrator.go:236-252`). VERIFIED.
- **Connection state visibility**: `WsConnectionState` enum exposed as stream (`websocket_chat_service_v2.dart:1279-1285,1422-1424`). Chat screen subscribes and shows in `chat_state.wsConnectionState` (`chat_provider.dart:72-75`). VERIFIED.
- **App lifecycle**: Background disconnects WS (`websocket_chat_service_v2.dart:2615-2621`), resume reconnects with reset attempt counter (line 2625-2631). VERIFIED.

### 2. Message Send/Receive Full Path
- **Flutter sends**: `ChatInput._handleSend()` -> `onSend` callback -> `ChatNotifier.sendMessage()` -> `ChatRepository.chatStream()` -> `WebSocketChatServiceV2.sendMessage()` -> WS JSON payload. VERIFIED.
- **Go receives**: `ChatOrchestrator.HandleWebSocket()` reads from WS channel (`chat_orchestrator.go:344-362`), parses JSON, validates empty message (line 521-526), enforces length limit (line 532-540), sanitizes with bluemonday (line 543), forwards to Python gRPC via `handleChatMessage()`. VERIFIED.
- **Python processes**: gRPC `StreamChat` call, orchestrator FSM, LLM streaming. Response flows back via gRPC stream.
- **Go forwards**: Streams gRPC response chunks back to WS client as JSON events. VERIFIED.
- **Flutter receives**: `_queueIncomingMessage()` serializes processing (`websocket_chat_service_v2.dart:1982-1994`), `_parseChatEvent()` handles 30+ event types, routes to per-request controller. VERIFIED.

### 3. Streaming Response Rendering
- **Token-by-token rendering**: `TextEvent` content accumulated character by character (`chat_provider.dart:1448`), debounced at 50ms (`chat_provider.dart:84`), rendered in `_StreamingBubble` using `SparkleMarkdown` with `isStreaming: true` (`chat_screen.dart:3617-3626`). VERIFIED.
- **Blinking cursor**: `_BlinkingCursor` widget shown during streaming (`chat_screen.dart:3629`). VERIFIED.
- **Markdown rendering**: `SparkleMarkdown` handles markdown, code blocks, links in both streaming and final bubbles. VERIFIED.
- **Typing indicator**: `_TypingIndicator` shown when `isSending && !isStatusShowing && !isReasoningShowing` (`chat_screen.dart:1498-1503`). VERIFIED.
- **Stream timeout**: 8-minute hard timeout on stream (`chat_provider.dart:1243`). VERIFIED.
- **Stream interruption**: On error/close, `finalizeRun()` called with `failed` phase, error shown to user with retry option (`chat_provider.dart:1633-1660`). VERIFIED.

### 4. Rich Media / Action Cards
- **PlanReviewCard**: All three decisions (approve/reject/modify) wired with callbacks (`plan_review_card.dart:910-1004`). Rejection flow shows feedback sheet with category selection (line 1147-1387). Delegate toggle for auto-execution (line 1006-1055). Plan review feedback sent via WS `sendPlanReviewFeedback()` (`websocket_chat_service_v2.dart:1577-1599`). VERIFIED.
- **ContextReceiptBar**: Parses from `rawMetadata` including `aurora_receipts`, `session_adaptation`, `memory_reference_receipt`, `social_context_receipt`, `context_receipt`, `spine_receipt` (`context_receipt_bar.dart:59-123`). Deduplication by composite key (line 161-188). CalibrationReceiptChip and AuroraReceiptChip rendered with action support. VERIFIED.
- **SourceExplanationCard**: Exists and renders used/unused sources with confidence pill. Submit correction action wired (`source_explanation_card.dart:192-227`). Supports both inline metadata and provider-based fallback (line 30-48). VERIFIED.
- **FileMessageBubble**: File upload supported via `AttachmentPickerSheet` -> `FilePickerWithPresigned`. Files sent via `file_ids` in WS payload (`websocket_chat_service_v2.dart:1493`). `FileMessageBubbleWithThumbnail` renders with thumbnail, file info, view/save actions (`file_message_bubble.dart`). VERIFIED.

### 5. Dual-Core Routing Frontend Behavior
- **Mode chip**: `_DualCoreModeChip` renders execution (amber), cognitive (indigo), or balanced (teal) mode (`chat_screen.dart:3865-3909`). Mode extracted from `ux_turn.dual_core_mode` in `FullTextEvent` metadata. VERIFIED (with P2-2 lag issue).
- **UX envelope**: `_extractUxEnvelope()` pulls `ux_turn`, `ux_progress`, `ux_result`, `ux_followthrough`, `ux_sources`, `ux_evolution`, `adaptation_summary`, `continuity_banner`, `mode_explanation` from metadata (`chat_provider.dart:423-455`). Widgets appended via `_appendUxWidgets()` (line 457-549). VERIFIED.

### 6. Chat History
- **Pagination**: `loadConversationHistory()` with `historyPageSize = 20` (`chat_notifier_history.dart:78`). `loadMoreHistory()` with offset-based pagination and deduplication (line 161-230). VERIFIED.
- **Cancel-on-switch**: `CancelableOperation` wraps history load, cancelled on conversation switch (`chat_notifier_history.dart:83-99`). Race condition guard with `loadingConversationId` (line 57-59). VERIFIED.
- **Message persistence**: Go gateway enqueues to Redis `queue:persist:history` via `ChatHistoryService`. `ChatHistoryPersister` batch-writes to PostgreSQL with retry and exponential backoff (`chat_history_persister.go`). Circuit breaker with local retry buffer at `chat_history.go:46-67`. VERIFIED.
- **Infinite scroll**: `loadMoreHistory()` triggered by scroll position in chat screen. `hasMoreMessages` flag managed correctly. VERIFIED.

### 7. Edge Cases
- **Empty message**: Blocked in Flutter (`chat_input.dart:188: if (text.isEmpty || _isSending) return`). Also blocked server-side (`chat_orchestrator.go:521-526`). VERIFIED.
- **Message length limit**: Server enforces 4000 chars (`chat_orchestrator.go:130,532`). Client does NOT enforce (see P1-1).
- **Message deduplication**: Go gateway uses SHA-256 content hash per user via `MessageDedupService` (`websocket_proxy.go:399-413`). VERIFIED.
- **Concurrent sessions**: Go gateway enforces `WSMaxConnections` per user (`websocket_proxy.go:508-519`). VERIFIED.
- **Rate limiting**: `wsMessageRateLimiter` applied at message level (`chat_orchestrator.go:338,383`). VERIFIED.
- **XSS filtering**: `bluemonday` sanitizer applied to all messages (`chat_orchestrator.go:543`). VERIFIED.
- **Oversized messages**: `SetReadLimit` on both client and backend connections (`websocket_proxy.go:291-292`). Default 256KB. VERIFIED.
- **Idle timeout**: Go gateway closes connections after configurable idle timeout (default 5 min) (`chat_orchestrator.go:238,291-293,350-354`). VERIFIED.
- **Plan switch race condition**: `isSwitchingPlan` flag blocks sends during switch (`chat_provider.dart:103,828-831`). VERIFIED.
- **Generation counter**: `_streamGeneration` prevents stale stream events from corrupting state (`chat_provider.dart:109,864-865`). VERIFIED.
- **Offline queue**: `OfflineMessageQueueService` persists messages to Isar DB, restores on reconnect (`websocket_chat_service_v2.dart:1330-1332,2474-2502`). Queue limit of 50 with overflow notification (line 1429,1909-1931). VERIFIED.
- **401 handling**: Token refresh with automatic reconnect (`websocket_chat_service_v2.dart:2061-2179`). Max 1 retry before logout. VERIFIED.
