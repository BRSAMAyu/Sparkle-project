# R13-R3A11: Offline + Error Recovery Audit

**Audit date**: 2026-05-07  
**Auditor**: Claude (fresh independent audit)  
**Scope**: Flutter (mobile/), Go Gateway (backend/gateway/), Python Engine (backend/app/)  
**Verdict**: PASS with 3 P1 and 4 P2 findings

---

## Summary Table

| # | Area | Verdict | P0 | P1 | P2 | Key Evidence |
|---|------|---------|----|----|----|-------------|
| 1 | ErrorWidget Override | PASS | 0 | 1 | 0 | main.dart:41-48, error_widget.dart |
| 2 | CRDT Sync System | PASS | 0 | 0 | 1 | crdt_sync_manager.dart, sync_engine.dart |
| 3 | Offline Queue | PASS | 0 | 1 | 0 | offline_message_queue_service.dart, task_offline_queue.dart |
| 4 | Network State Visibility | PASS | 0 | 0 | 0 | connectivity_provider.dart, task_offline_indicator.dart |
| 5 | WebSocket Disconnect Handling | PASS | 0 | 1 | 1 | websocket_chat_service_v2.dart, websocket_proxy.go |
| 6 | Error States for Common Scenarios | PASS | 0 | 0 | 0 | error_messages.dart, retry_strategy.dart |
| 7 | Data Integrity | PASS | 0 | 0 | 1 | outbox_dedupe_key.dart, sync_engine.dart, websocket_proxy.go |
| 8 | Edge Case Handling | PASS | 0 | 0 | 1 | websocket_chat_service_v2.dart, file_upload_service.dart |
| **TOTAL** | | **PASS** | **0** | **3** | **4** | |

---

## 1. ErrorWidget Override — PASS (1 P1)

### Verified Working

**ErrorWidget.builder override exists**: `mobile/lib/main.dart:41-48`
```dart
ErrorWidget.builder = (details) => Material(
  color: DS.surfacePrimary,
  child: custom.CustomErrorWidget(
    type: custom.ErrorType.page,
    severity: custom.ErrorSeverity.error,
    message: details.exceptionAsString(),
  ),
);
```

**Branded CustomErrorWidget**: `mobile/lib/core/design/widgets/error_widget.dart`
- Three display types: `page` (full-screen), `banner` (top bar), `inline` (inline card) — lines 9-14
- Three severity levels: `error` (red), `warning` (orange), `info` (blue) — lines 17-21
- Recovery actions: `onRetry` callback renders a gradient-styled retry button (lines 283-292)
- Localized titles and messages via `AppLocalizations` (lines 196-201)
- Sensory feedback on retry (line 207) and close (line 212)
- Semantics annotations: `liveRegion: true`, `container: true` (lines 220-223)

**Specialized error pages** (same file):
- `NetworkErrorPage` (lines 425-445): wifi_off icon, retry button, i18n message
- `NotFoundErrorPage` (lines 448-477): search_off icon, "Go back" action
- `ServerErrorPage` (lines 480-502): cloud_off icon, retry button

**CompactErrorCard**: `mobile/lib/core/design/widgets/compact_error_card.dart`
- Inline "Tap to retry" indicator for card-level errors (lines 31-36)
- Bilingual EN/ZH (line 14)

**Fatal startup error fallback**: `main.dart:160-181`
- Catch-all error displays minimal Scaffold with scrollable error text

**StaleRecoveryCard**: `mobile/lib/features/chat/presentation/widgets/stale_recovery_card.dart`
- Time-aware recovery card for >60min absence (divine moment #4)
- Animated entry with 4 resume options

### P1 Finding: OER-01 — Raw exception text shown to users without sanitization

**Location**: `mobile/lib/main.dart:46`
```dart
message: details.exceptionAsString(),
```
**Risk**: Flutter framework errors often contain stack traces, file paths, and internal type names. Showing `exceptionAsString()` directly may expose implementation details (e.g., `Null check operator used on a null value` with stack trace) that are confusing or alarming to end users.

**Recommendation**: Wrap in a user-friendly message and log the raw exception separately:
```dart
message: l10n?.unexpectedError ?? 'Something went wrong',
// Log: PerformanceMonitor().reportCrash(details.exception, details.stack, context: 'error_widget');
```

---

## 2. CRDT Sync System — PASS (1 P2)

### Verified Working

**CRDTSyncManager**: `mobile/lib/core/offline/crdt_sync_manager.dart` — 267 lines
- Real implementation with operation-based CRDT (CmRDT) merges (line 8)
- Lamport clock ordering via `OfflineCrdtDocument.nextLamport(actorId)` (line 97)
- Four sync types: `knowledgeNode`, `chatMessage`, `task`, `userPreference` (lines 25-30)
- Local persistence to Isar via `LocalCRDTSnapshot` collection (lines 221-236)
- Conflict resolution via automatic merge (line 171-176)
- ACK-backed replay: operations enqueued with dedupe key, deleted on successful server ack (sync_engine.dart:225-232)
- `applyKnowledgeMasteryDelta`, `setKnowledgeMastery`, `setTaskState`, `appendChatMessage` — all produce deterministic local merges (lines 85-163)

**OfflineCrdtDocument**: Referenced from `mobile/lib/core/offline/offline_crdt_document.dart`
- Binary serialization, JSON operations payload

**SyncEngine outbox**: `mobile/lib/core/offline/sync_engine.dart` — 579 lines
- Exponential backoff with jitter: `_nextAttempt` base 800ms, max 30s, jitter 0-250ms (lines 438-443)
- Max 5 attempts, then marks as `failed` (lines 244-252)
- CRDT deltas deleted on ack success, other items transition to `synced`
- `_requeueStuckWaitingAck`: detects items stuck in `waitingAck` > 30s and re-queues (lines 519-549)
- `_waitForAck` with 5s timeout per item (lines 286-289)

**Conflict Resolver**: `mobile/lib/core/offline/conflict_resolver.dart`
- 3-tier strategy: Revision priority → Last Writer Wins → Higher Mastery Wins (lines 39-64)

### P2 Finding: CRDT-01 — sync() method body is empty

**Location**: `mobile/lib/core/offline/crdt_sync_manager.dart:166-168`
```dart
Future<void> sync() async {
  // Trigger SyncEngine processing is automatic via Isar watch
}
```
**Risk**: If called directly, does nothing. The comment says it's automatic via Isar watch, but a caller expecting explicit sync (e.g., from a "Sync Now" button) would get a silent no-op. The method should either delegate to `_syncEngine.processNow()` or be removed if truly unnecessary.

**Recommendation**: Implement as `_syncEngine.processNow()` or add `@Deprecated` annotation explaining it's auto-managed.

---

## 3. Offline Queue — PASS (1 P1)

### Verified Working

**OfflineMessageQueueService**: `mobile/lib/core/offline/offline_message_queue_service.dart` — 192 lines
- Persists to Isar `offlineChatMessages` collection (line 38)
- Full lifecycle: `enqueue` → `markSent` → `markAcked` / `markFailed` → `prepareForRetry` → `remove`
- Status tracking: pending → sent → acked/failed (model lines 5-11)
- `loadRetryableForUser`: loads pending + sent (no ack) + failed-with-budget messages (lines 115-133)
- `cleanupOldAcked`: removes acked messages older than 24h (lines 173-191)
- `canRetry` caps at 5 attempts (model line 131)

**TaskOfflineQueue**: `mobile/lib/features/task/data/services/task_offline_queue.dart`
- Offline-queues all 5 task lifecycle operations: start, pause, resume, complete, abandon
- Server-side idempotency: 409 Conflict treated as success (sync_engine.dart:414-419)
- Dedupe keys per operation: `task:$taskId:start`, `task:$taskId:pause`, etc. (lines 26-61)
- Reactive `pendingTaskOpsCountProvider` for UI badges (lines 132-156)

**Chat integration**: `websocket_chat_service_v2.dart`
- `_persistOutgoingMessage`: every outgoing message persisted to Isar before send (lines 1933-1949)
- `_restorePendingFromDb`: on reconnect, restores retryable messages from DB to in-memory queue (lines 2474-2501)
- `_enqueuePendingMessage`: in-memory queue with 50-message limit (line 1910)
- Sink-accept tracking: `markSent` called when socket accepts message (line 2451)
- Server-ack tracking: `markAcked` called on AckEvent (lines 1869-1874)
- Failed message tracking: `markFailed` when socket fails during send (line 1976)

**SyncEngine outbox**: Persists all sync operations to Isar `outboxItems` collection → survives app kill

### P1 Finding: OFQ-01 — In-memory pending queue has limit; offline DB queue does not

**Location**: `websocket_chat_service_v2.dart:1910` and `offline_message_queue_service.dart`

**Risk**: The in-memory `_pendingMessages` has a 50-message limit with overflow dropping (lines 1910-1931). However, the persistent Isar `offlineChatMessages` collection has no size limit. After a long offline period with many messages, on reconnect the system restores ALL retryable messages from DB into the in-memory queue (line 2476-2501), which can exceed the 50-message limit. The in-memory queue could overflow during restore, causing message loss.

**Recommendation**: Apply the same limit to `_restorePendingFromDb` or increase the in-memory limit during restore to match DB capacity.

---

## 4. Network State Visibility — PASS

### Verified Working

**Connectivity Provider**: `mobile/lib/core/offline/connectivity_provider.dart`
- `connectivityStreamProvider`: StreamProvider wrapping `Connectivity().onConnectivityChanged` (lines 9-13)
- `isOnlineProvider`: Derived boolean provider, optimistic default `true` (lines 16-22)

**NetworkMonitor**: `mobile/lib/core/offline/network_monitor.dart`
- 500ms debounce on connectivity changes (line 19)
- Triggers `syncPendingUpdates()` on network restore (line 22)

**TaskOfflineIndicator**: `mobile/lib/features/task/presentation/widgets/task_offline_indicator.dart`
- Shows offline banner with cloud_off icon when `!isOnline` (lines 30-39)
- Shows sync progress with spinner when online and pending > 0 (lines 44-70)
- Bilingual EN/ZH (lines 33-39)
- Auto-hides when online with empty queue (line 27)

**OfflineQueueIndicator in Chat**: `mobile/lib/features/chat/presentation/widgets/offline_queue_indicator.dart`
- Three visible states: `queued` (wifi_off icon), `sending` (spinner), `complete` (check icon) — lines 119-140
- Bilingual copy for all states (lines 150-183)
- Semantics annotations with liveRegion (lines 31-35)
- AnimatedSwitcher for smooth transitions (lines 35-76)
- "All sent" success state auto-dismisses after 2 seconds (chat_screen.dart:3437-3441)

**Chat screen connection state feedback**: `chat_screen.dart:281-312`
- Reconnecting: loading feedback ("Reconnecting...")
- Reconnected: success feedback ("Reconnected") + reloads conversation history
- Failed: error feedback ("Connection failed")

**Sync Center Screen**: `mobile/lib/features/user/presentation/screens/sync_center_screen.dart`
- Tabbed view: All / Failed / Waiting Ack / Pending (lines 60-66)
- "Retry All" action (lines 39-58)
- "Retry Failed" button at bottom (line 80)

**WebSocket connection panel**: `mobile/lib/features/settings/presentation/widgets/openclaw_connection_panel.dart`
- User-configurable connection settings

---

## 5. WebSocket Disconnect Handling — PASS (1 P1, 1 P2)

### Verified Working

**Flutter WebSocketChatServiceV2**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` — 2692 lines

**Reconnection strategy**:
- Exponential backoff schedule: 800ms, 1.2s, 2.2s, 4.2s, 8.2s, 12.2s (lines 1335-1342)
- Jitter: random 0-250ms added to each delay (line 2305)
- Max 6 reconnection attempts, then fails with user notification (lines 2269-2297)
- Reconnection disabled after 401 auth failure (line 2095)

**User notification during reconnection**:
- `WsConnectionState` enum: disconnected / connecting / connected / reconnecting / failed (lines 1279-1285)
- Stream exposed: `connectionStateStream` (line 1423)
- Chat screen listens and shows AppFeedback (loading/success/error) (chat_screen.dart:282-311)
- Failed pending messages notified with count of dropped messages (lines 2262-2296)

**Message queue during disconnect**:
- In-memory `_pendingMessages` list (line 1404), limit 50 (line 1429)
- Persistent Isar backup via `OfflineMessageQueueService` (line 1407)
- Auto-flush on reconnect after DB restore (line 1746)
- DB restore prevents duplicates by tracking queued request IDs (lines 2480-2501)

**Server ACK tracking**:
- `message_ack`/`ack` event handling marks message as delivered (lines 1869-1874)
- `message_nack`/`nack` event propagated as error with retry timing (lines 883-908)

**Heartbeat**:
- 30s ping interval, 60s timeout (lines 1384-1388)
- 3 consecutive failures trigger reconnect (line 1389)
- Stream-active suppression: if receiving data, heartbeats failures are ignored (lines 2401-2412)
- HeartbeatMetrics stream with RTT tracking (lines 1398-1401)
- Pong detection bypasses full JSON parse for speed (line 2007)

**Token refresh on 401**:
- Detects 401 errors via pattern matching (lines 2045-2058)
- Auto-refreshes token, retries once (lines 2061-2178)
- On refresh failure: logs out, disables reconnect, notifies user of lost messages

**App lifecycle**: `WidgetsBindingObserver` (line 1315)
- Background: stops heartbeat, closes WebSocket (lines 2616-2622)
- Resume: reconnects if was disconnected (lines 2625-2632)

**Go Gateway WebSocketProxy**: `backend/gateway/internal/handler/websocket_proxy.go` — 754 lines

**Reconnect rate limiting**:
- 10 attempts per 30s sliding window (lines 33-35)
- Exceeded: 5-minute block with `retry_after` in response (lines 177-182)
- Cleanup goroutine removes expired trackers every 300s (lines 722-753)

**Per-user connection limits**:
- `registerConnection` enforces `WSMaxConnections` per user (lines 502-521)
- `activeByUser` map tracks live connections (line 60)

**Message rate limiting**:
- Token bucket per-connection via `ws_hardening.go` (line 16-30)
- Oversized message rejection (lines 379-385, 445-450)

**Graceful draining**:
- `IsDraining()` checks on all WS endpoints (lines 109, 148, 195, 247)
- Draining sends `CloseTryAgainLater` to both sides (lines 247-260)

**Panic recovery**: goroutine-level recovery with stack logging (lines 344-357)

### P1 Finding: WSD-01 — WebSocketService (simpler version) has no heartbeat and no jitter

**Location**: `mobile/lib/core/services/websocket_service.dart`

**Risk**: The simpler `WebSocketService` used by the sync engine (not chat V2) has:
1. No heartbeat mechanism at all — zombie connections will not be detected
2. No jitter on reconnect schedule (lines 14-21) — all clients following the same schedule thundering-herd on reconnect

The `SyncEngine` in `sync_engine.dart` uses this service (line 17: `final WebSocketService _wsService`). This means CRDT delta sync has no heartbeat keepalive.

**Recommendation**: Either migrate sync engine to use `WebSocketChatServiceV2` or add heartbeat to `WebSocketService`.

### P2 Finding: WSD-02 — Reconnect jitter range is only 0-250ms

**Location**: `websocket_chat_service_v2.dart:2305`
```dart
final jitterMs = math.Random().nextInt(250);
```

**Risk**: The jitter range (250ms) is small relative to the base delays (800ms-12.2s). At the 800ms step, 250ms jitter is ~31% which is reasonable. But at the 12.2s step, 250ms is only 2% — effectively no jitter for the highest-attempt reconnects where thundering herd is most likely (many clients all at max attempt).

**Recommendation**: Use proportional jitter: `jitterMs = Random().nextInt(baseDelay.inMilliseconds ~/ 4)` (25% of base delay).

---

## 6. Error States for Common Scenarios — PASS

### Verified Working

**ErrorMessages utility**: `mobile/lib/core/utils/error_messages.dart` — 203 lines
- `getLocalizedMessage`: maps error codes + technical messages to i18n strings (lines 6-97)
- Dual matching: first checks Chinese content patterns, then error codes
- Supported codes: OFFLINE, CONNECTION_ERROR, TIMEOUT, UNAUTHORIZED, TOKEN_EXPIRED, SERVER_ERROR, RATE_LIMIT, LLM_ERROR, CONTEXT_LENGTH (lines 38-96)
- `getUserFriendlyMessage`: Chinese fallback messages for all codes (lines 102-150)
- `isRetryable`: determines if error is worth retrying (lines 153-172)
- `getActionSuggestion`: user guidance per error type (lines 176-203)

**Error type** | **Handling** | **Evidence**
---|---|---
API error responses | Localized user-friendly message | `error_messages.dart:6-97`
Connection timeout | Retryable, user notification with retry | `retry_strategy.dart:21-22`, `error_messages.dart:48-50`
401 Unauthorized | Auto token refresh, graceful logout with message preservation notice | `websocket_chat_service_v2.dart:2061-2178`
500 Server Error | Safe message "服务端处理这轮请求时出错了" | `error_messages.dart:138-139`
Network error | "Retry" button, retryable flag | `error_messages.dart:153-172`
Rate limiting | User message "请求过于频繁" | `error_messages.dart:77-78`
AI/LLM error | "模型服务这轮没有稳定返回结果" + retry suggestion | `error_messages.dart:81-82`
WebSocket parse error | `ErrorEvent` with PARSE_ERROR code, non-retryable | `websocket_chat_service_v2.dart:1265-1270`

**RetryStrategy**: `mobile/lib/core/services/retry_strategy.dart` — 271 lines
- Configurable: maxAttempts=3, initialDelay=500ms, maxDelay=10s, backoffFactor=1.5 (lines 11-23)
- Retryable by DioExceptionType: connectionTimeout, sendTimeout, receiveTimeout, connectionError (lines 17-21)
- Retryable by HTTP status code: 408, 429, 500, 502, 503, 504 (line 22)
- Auto-retry on SocketException and TimeoutException (lines 114-121)
- `CircuitBreakerRetryStrategy`: closed → open → half-open states (lines 128-218)
  - Opens after 5 consecutive failures (line 130)
  - Resets after 30s (line 131)
  - Half-open: allows 3 probe requests before fully closing (line 132)

**Route resilience**: `mobile/lib/core/navigation/route_resilience.dart`
- `RouteResilienceScope`: wraps screens for pop/go fallback
- `fallbackRouteForExternalRoute`: maps external deep links to safe fallbacks (lines 75-102)
- Graceful GoRouter navigation with try-catch fallback (lines 68-72)

**Go timeout middleware**: `backend/gateway/internal/middleware/timeout.go`
- Configurable request timeout, returns 503 on deadline (lines 34-39)
- Long-running routes excluded (STT transcribe, learning paths, capsule generation, task generation) (lines 43-61)
- WebSocket routes excluded from timeout (lines 44-47)

**Go drain handling**: `websocket_proxy.go`
- All WS endpoints check `IsDraining()` before upgrading
- Returns 503 with "Server shutting down" message

---

## 7. Data Integrity — PASS (1 P2)

### Verified Working

**Transactional writes**: Isar `writeTxn` used extensively for atomic multi-object writes
- `offline_message_queue_service.dart`: all mutations wrapped in `writeTxn` (lines 37-38, 48-50, 62-64, 76-78, 87-89)
- `sync_engine.dart`: item status transitions in `writeTxn` (lines 91-92, 171-174, 225-232, 237-251)
- `sync_queue.dart`: mastery update + pending update + CRDT snapshot in single `writeTxn` (lines 52-116)
- `crdt_sync_manager.dart`: snapshot persistence in `writeTxn` (lines 226-235)

**Duplicate submission prevention (idempotency)**:

Client-side:
- `OutboxDedupeKey`: knowledge updates keyed by `nodeId:opId` (outbox_dedupe_key.dart:5-6)
- Task ops keyed by `task:$taskId:$operation` (task_offline_queue.dart:26-61)
- CRDT deltas keyed by comma-joined operation IDs (crdt_sync_manager.dart:254)
- Request ID generation: `req_${microseconds}_${random20bit}` (websocket_chat_service_v2.dart:2537-2540)
- OfflineChatMessage.requestId has unique Isar index (model line 20)

Server-side (Go Gateway):
- SHA256 content hash dedup per user (websocket_proxy.go:399-413)
- `MessageDedupService.CheckAndMark` with Redis backing (line 402)
- Community WS messages sanitized before dedup (line 396)

Server-side (Python):
- Task ops: 409 Conflict returned for duplicate state transitions (referenced in sync_engine.dart:411-419)
- 409 treated as success by client (line 414)

**Lost data recovery**:
- Chat messages persisted to Isar BEFORE WebSocket send attempt (websocket_chat_service_v2.dart:1933-1949)
- On reconnect: DB messages restored to in-memory queue, deduplicated against already-queued (lines 2474-2501)
- `prepareForRetry`: resets failed/sent messages back to pending (offline_message_queue_service.dart:82-91)
- SyncEngine outbox items survive app kill (Isar persistence)
- `_requeueStuckWaitingAck`: detects and re-queues items stuck in waitingAck > 30s (sync_engine.dart:519-549)
- Last sync success timestamp persisted to SharedPreferences (sync_engine.dart:551-557)

**Message ordering**:
- `loadRetryableForUser` sorts by `createdAt` (offline_message_queue_service.dart:128-132)
- `_processOutbox` sorts by `createdAt` (sync_engine.dart:152)
- Incoming message processing serialized via `_incomingMessageChain` Future chain (websocket_chat_service_v2.dart:1981-1993)

### P2 Finding: DIT-01 — OfflineChatMessage fileIds use unescaped comma join

**Location**: `mobile/lib/core/offline/models/offline_chat_message.dart:95`
```dart
..fileIds = fileIds != null ? fileIds.join(',') : null
```
and line 138:
```dart
List<String> get parsedFileIds =>
    fileIds?.split(',').where((id) => id.isNotEmpty).toList() ?? [];
```

**Risk**: If a file ID contains a comma (unlikely with UUIDs but possible with custom or future ID schemes), the split/join round-trip would corrupt the data.

**Recommendation**: Use JSON encoding for array storage:
```dart
..fileIds = fileIds != null ? jsonEncode(fileIds) : null
// and
List<String> get parsedFileIds { ... jsonDecode(fileIds) ... }
```

---

## 8. Edge Case Handling — PASS (1 P2)

### Verified Working

**App backgrounded during request**:
- `WidgetsBindingObserver` in `WebSocketChatServiceV2` (line 1315)
- `didChangeAppLifecycleState`: on paused/hidden/detached → stops heartbeat, closes WS (lines 2607-2622)
- On resume → reconnects and restores state (lines 2625-2632)
- Inactive state: keeps socket warm, stops heartbeat only (lines 2609-2612)
- Connection generation tracking (`_connGen`) prevents stale operations (line 1357, 2554)

**Request timeout configuration**:
- Dio connectTimeout: 10s (api_client.dart:17)
- Dio receiveTimeout: 30s (api_client.dart:18)
- Dio sendTimeout: default (not explicitly configured in base, but file upload service has 15s/30s)
- File upload Dio: connectTimeout 15s, receiveTimeout 30s (file_upload_service.dart:31-32)
- Go timeout middleware: configurable per-route, 503 response (timeout.go:16-41)
- WS ack wait: 5s timeout per sync item (sync_engine.dart:286-289)

**Large file upload on slow connection**:
- `FileUploadService.uploadDocument` with presigned URL upload (file_upload_service.dart:39-79)
- `_uploadBinaryWithRetry`: retry on network errors (line 58-64)
- Progress callback support: `onProgress` parameter (line 43)
- `UploadInterruptedException`: preserves upload session for resume (lines 67-78)
- Network error detection: `_isNetworkError` (line 66)

**Concurrent requests from multiple app screens**:
- Per-request stream controllers: `_requestControllers` map keyed by requestId (line 1360)
- Incoming message queue serialized via `_incomingMessageChain` Future chain (line 1981-1993)
- Outbox processing guarded by `_isProcessing` mutex (sync_engine.dart:119)
- `DoneEvent`/`ErrorEvent`/`NackEvent` close the per-request controller (lines 1892-1896)
- `_broadcastErrorToActiveRequests`: global errors propagated to all active requests (lines 1899-1907)
- `_connGen` connection generation for request streaming isolation (lines 1357, 2554)
- 401 token refresh guarded by `_isRefreshingToken` mutex (line 2066)

**Empty state**:
- `OfflineQueueSnapshot.empty` static const (offline_providers.dart:53)
- `OfflineQueueIndicatorStatus.hidden` → `SizedBox.shrink()` (offline_queue_indicator.dart:25)
- `TaskOfflineIndicator` returns `SizedBox.shrink()` when online and empty (task_offline_indicator.dart:27)

**Disposed state safety**:
- `_disposed` flag checked before all async operations (websocket_chat_service_v2.dart)
- Timer callbacks check `mounted` before setState (chat_screen.dart:3438)
- Isar operations check `db.isOpen` before access (offline_message_queue_service.dart:26, 45, etc.)

### P2 Finding: EDGE-01 — WS message rate limiter uses single token bucket per connection, no per-message-type differentiation

**Location**: `backend/gateway/internal/handler/ws_hardening.go:16-30`

**Risk**: The message rate limiter applies to all WebSocket message types equally. A burst of ping/pong or small status messages could trigger the rate limit and close the connection, even though the user is not sending excessive chat messages.

**Recommendation**: Consider exempting control messages (ping/pong) and low-priority status messages from the rate limit, or use separate rate limit tiers.

---

## Overall Assessment

The Sparkle offline and error recovery system is **mature and production-ready**. The architecture covers all critical paths:

- **Layered defense**: Client-side offline queue (Isar) → SyncEngine outbox (exponential backoff + jitter) → Go Gateway (dedup + rate limiting + reconnect rate limiting) → Python (409 idempotency)
- **User visibility at every layer**: Connection state stream → banners → indicators → Sync Center → localized error messages
- **Recovery is automatic**: reconnect → DB restore → flush → ack tracking. Manual retry available as fallback via Sync Center.
- **Data integrity is protected**: atomic Isar transactions, dedupe keys, content-hash dedup at gateway, idempotent task operations

The 3 P1 findings (raw exception display, queue limit mismatch, simpler WS service lacking heartbeat) and 4 P2 findings (empty sync method, small jitter range, unescaped comma join, flat rate limiting) are all addressable without architectural changes.

**Final score**: 8/8 areas PASSING. 0 P0 findings. 3 P1 findings. 4 P2 findings.
