# R11 / R3A11: Offline, Error Recovery & Edge Case Audit

**Date**: 2026-05-07  
**Auditor**: Claude Opus 4.7  
**Scope**: Pre-launch final audit of offline, error recovery, graceful degradation, and edge case handling  
**Layers**: Flutter (mobile/lib), Go Gateway (backend/gateway), Python Engine (backend/app)  
**Severity**: P0 = Must-fix before launch, P1 = High priority, P2 = Moderate, P3 = Nice-to-have  

---

## Executive Summary

The Sparkle codebase demonstrates strong error recovery and offline resilience across all three layers. The offline sync system is a real implementation (not a shell) with outbox pattern, exponential backoff, ACK tracking, and CRDT merge support. Circuit breakers exist in both Go and Python. Error sanitization is thorough. The primary gaps are: missing Flutter ErrorWidget.builder override, no centralized offline connectivity indicator, and the chat orchestrator accepting WebSocket connections without first checking the gRPC circuit breaker state.

**Summary**: 1 P0, 3 P1, 6 P2, 3 P3 findings.

---

## FINDINGS

---

### Finding O-01 [P0] — Missing ErrorWidget.builder Override

**File**: `mobile/lib/main.dart` lines 30–46, `mobile/lib/app/app.dart` line 92  
**Area**: Error Boundary Testing / Flutter  

**Current code** (`main.dart` lines 30–46):
```dart
FlutterError.onError = (details) {
  FlutterError.presentError(details);
  PerformanceMonitor().reportCrash(...);
};
PlatformDispatcher.instance.onError = (error, stack) {
  PerformanceMonitor().reportCrash(...);
  return true;
};
```

**Current code** (`app.dart` line 92 — builder closure):
```dart
builder: (context, child) {
  // No ErrorWidget.builder override
  return _ThemeTransitionShell(...);
},
```

**Problem**: `FlutterError.onError` and `PlatformDispatcher.instance.onError` capture exceptions but `ErrorWidget.builder` is NOT overridden. A widget build error (RenderFlex overflow, null check on a late variable, etc.) in production will show the Flutter default red error screen rather than a branded recovery UI. Sentry will capture the crash, but the user sees an unhelpful red box.

**Expected**: `ErrorWidget.builder` should be set in the MaterialApp.router builder to render a `CustomErrorWidget.page()` or similar branded recovery screen.

**Fix recommendation**: In `app.dart`, inside the MaterialApp.router builder, set:
```dart
ErrorWidget.builder = (details) => Material(
  child: CustomErrorWidget.page(
    message: AppLocalizations.of(context)?.errorUnexpected ?? 'Something went wrong',
    context: context,
    onRetry: () => ...,
  ),
);
```

---

### Finding O-02 [P1] — Chat Orchestrator Does Not Check Circuit Breaker Before Accepting WS

**File**: `backend/gateway/internal/handler/chat_orchestrator.go` lines 204–232  
**Area**: Graceful Degradation / Go→Python gRPC  

**Current code** (lines 204–207):
```go
func (h *ChatOrchestrator) HandleWebSocket(c *gin.Context) {
    if h.IsDraining() {
        c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": "Server shutting down"})
        return
    }
    // Proceeds to upgrade WebSocket without checking h.agentClient.AllowRequest()
```

**Reference** (`backend/gateway/internal/agent/client.go` lines 316–320):
```go
func (c *Client) StreamChatWithFallback(...) (..., error) {
    if c.healthChecker != nil && !c.healthChecker.AllowRequest() {
        return nil, ErrCircuitOpen  // Circuit protection only inside gRPC call
    }
```

**Problem**: The WebSocket is upgraded and the user session begins before the circuit breaker is checked. When the user sends a chat message, the gRPC call to Python will fail with `ErrCircuitOpen`. The user's WS connection is established but immediately useless — they will see a "Stream interrupted" error after the first message. Pre-flight circuit breaker check would allow rejecting the WS upgrade with a clear "Service temporarily unavailable" message.

**Expected**: `HandleWebSocket` should call `h.agentClient.AllowRequest()` before upgrading. If the circuit is open, return HTTP 503 with a translated message.

**Fix recommendation**: Add at line 204:
```go
if h.agentClient != nil && !h.agentClient.AllowRequest() {
    msg := i18n.T(c.Request.Context(), "errors.upstream")
    c.AbortWithStatusJSON(http.StatusServiceUnavailable, gin.H{"error": msg, "error_code": "service_unavailable"})
    return
}
```

---

### Finding O-03 [P1] — No Centralized Offline Connectivity Indicator

**File**: `mobile/lib/core/offline/sync_engine.dart` lines 54–58, `mobile/lib/features/chat/presentation/widgets/offline_queue_indicator.dart`, `mobile/lib/features/task/presentation/widgets/task_offline_indicator.dart`  
**Area**: Offline Scenarios / User Feedback  

**Current code** (`sync_engine.dart` lines 54–58):
```dart
_connectivity.onConnectivityChanged.listen((result) {
  if (!result.contains(ConnectivityResult.none)) {
    _processOutbox();
  }
});
```

**Problem**: Connectivity changes are detected by `SyncEngine` and used to trigger sync, but there is no centralized, app-wide offline banner or toast. The `offline_queue_indicator.dart` and `task_offline_indicator.dart` are per-screen widgets that must be voluntarily included. A user on the home screen or settings screen will not know they lost connectivity. The offline message queue silently buffers messages without telling the user their messages haven't been sent.

**Expected**: A `Riverpod` provider that watches `Connectivity().onConnectivityChanged` and exposes `isOffline` state. A `MaterialBanner` or `SnackBar` in the app shell (`app.dart`) that shows when offline. Per-screen widgets are fine for extended context but the global state is missing.

**Fix recommendation**: Add `connectivityProvider` as a `StreamProvider<bool>` in `offline_providers.dart`, then add an offline banner to the app shell in `app.dart`.

---

### Finding O-04 [P1] — Task Create Screen Lacks Unsaved-Data Warning

**File**: `mobile/lib/features/task/presentation/screens/task_create_screen.dart` line 121  
**Area**: Data Loss Prevention / Form Protection  

**Current code** (line 121):
```dart
if (context.canPop()) {
  // Just pops without checking for dirty form state
}
```

**Reference** (task_execution_screen.dart lines 230–253): The execution screen has `_onWillPop()` with celebration protection, time-based quick exit, and focus confirmation dialog. The create screen has none of this.

**Problem**: If a user types a long task description and accidentally swipes back or taps the back button, all entered data is lost with no warning.

**Expected**: The task create screen should use `PopScope` with `onPopInvokedWithResult` that checks for unsaved form data and shows a confirmation dialog.

**Fix recommendation**: Wrap the create screen in a `PopScope` that checks whether the title or description fields are non-empty and shows a "Discard changes?" dialog.

---

### Finding O-05 [P2] — No Flutter Image Cache Eviction on Memory Pressure

**File**: (no file found)  
**Area**: Edge Cases / Memory Pressure  

**Problem**: A search for `imageCache`, `ImageCache`, `didReceiveMemoryWarning`, `memory_pressure`, or `clearCache` in `mobile/lib/core/` found only statistics data cache eviction (LRU-based). There is no `WidgetsBindingObserver` handler that calls `PaintingBinding.instance.imageCache.clear()` or `imageCache.clearLiveImages()` on memory pressure. On low-memory devices with large chat histories and galaxy graphs, this could cause OOM crashes.

**Expected**: A `WidgetsBindingObserver` in the app shell that listens for `didHaveMemoryPressure` (Flutter 3.22+) or `didChangeAppLifecycleState(AppLifecycleState.paused)` and trims the image cache.

**Fix recommendation**: Add to `app.dart` lifecycle observer or in `main.dart`:
```dart
void didHaveMemoryPressure() {
  PaintingBinding.instance.imageCache.clear();
  imageCache.clearLiveImages();
}
```

---

### Finding O-06 [P2] — Rapid-Tap Protection Inconsistent Across Forms

**File**: (multiple) `mobile/lib/features/task/presentation/screens/task_create_screen.dart`  
**Area**: Edge Cases / Double-Submit Prevention  

**Problem**: Some forms (thought_capsule_dialog.dart line 19, flash_capsule_tool.dart line 88, calendar_stats_screen.dart line 1419) have `_isSubmitting` guards. The task create screen and several other forms were NOT auditable for this pattern. A rapid double-tap on "Create Task" could send duplicate POST requests.

**Expected**: All form submission buttons should use an `_isSubmitting` boolean flag or a Riverpod `StateProvider<bool>` to disable the button during submission.

**Fix recommendation**: Audit all form screens for double-submit protection. Add `_isSubmitting` guards to task create, goal create, plan create, and any other data-mutating forms.

---

### Finding O-07 [P2] — Go Goroutine Panic Recovery Missing in Background Workers

**File**: `backend/gateway/cmd/server/setup.go` lines 419–437, `backend/gateway/internal/cqrs/worker/base.go` lines 115–145  
**Area**: Error Boundary Testing / Go Panic Recovery  

**Current code** (`setup.go` lines 419–437):
```go
go func() {
    if err := cqrs.commSyncWorker.Run(context.Background()); err != nil {
        log.Error("Community sync worker stopped", zap.Error(err))
    }
}()
```

**Problem**: The goroutines started in `setup.go` for CQRS workers do not have `defer recover()` blocks. If a worker panics (nil pointer dereference in event parsing, etc.), the entire Go process crashes. The BaseWorker.Run() loop catches errors but does not recover from panics. `gin.Recovery()` only protects HTTP handlers, not background goroutines.

**Expected**: All background goroutines should have `defer recover()` at the top level:
```go
go func() {
    defer func() {
        if r := recover(); r != nil {
            log.Error("worker panic recovered", zap.Any("panic", r))
        }
    }()
    ...
}()
```

**Fix recommendation**: Add `defer recover()` to all background goroutines in `setup.go` lines 419–437, and add a `recover()` in `BaseWorker.Run()` around the message processing loop.

---

### Finding O-08 [P2] — Python asyncio Task Exception Silently Swallowed

**File**: `backend/app/main.py` lines 102–175  
**Area**: Error Boundary Testing / Python asyncio  

**Current code** (line 102):
```python
except Exception as exc:
    logger.warning(f"Agent Graph V2 disabled (import failed): {exc}")
```

**Problem**: Multiple background tasks and startup calls use bare `except Exception` blocks that log and continue. While this prevents crashes, unhandled `asyncio.CancelledError` (which inherits from `Exception` in some contexts) or `KeyboardInterrupt` could be caught unintentionally. More critically, `asyncio.Task` exceptions in background tasks that aren't awaited can be lost — there is no `asyncio.Task.add_done_callback` or global exception handler for unhandled task exceptions.

**Expected**: Register a global asyncio exception handler:
```python
loop = asyncio.get_event_loop()
loop.set_exception_handler(custom_exception_handler)
```

**Fix recommendation**: Add a `custom_exception_handler` that logs to both logger and Sentry, then register it with the event loop in `main.py`.

---

### Finding O-09 [P2] — App-Killed-During-Critical-Op Recovery Unclear

**File**: (no single file — spans sync_engine.dart, offline_message_queue_service.dart)  
**Area**: Data Loss Prevention / App Kill  

**Problem**: The outbox pattern protects against app kill by persisting to Isar before sending. The sync engine's `_requeueStuckWaitingAck()` recovers messages stuck in `waitingAck` state. However, for in-progress task execution (timer running, focus session mid-way), if the app is killed, the active session state is lost. The task status may be inconsistent (shown as "in progress" but no active timer on relaunch).

**Expected**: The app should persist active task execution state to Isar on lifecycle change to `paused` or `detached`, and restore it on `resumed`. The `PassiveSignalService` already tracks lifecycle, but only for sending passive signals — it does not persist execution state.

**Fix recommendation**: Enhance `PassiveSignalService` or create a new `ExecutionStateService` that persists the active task ID, start time, and elapsed duration to Isar on `paused`/`detached`, and checks for stale sessions on `resumed`.

---

### Finding O-10 [P2] — First-Time User Sees Chained Loading States

**File**: `mobile/lib/core/design/widgets/empty_state.dart`, `mobile/lib/features/home/`  
**Area**: Edge Cases / Empty States  

**Problem**: While `EmptyState` and `CompactEmptyState` widgets are comprehensive (6 types, i18n, actions), the end-to-end first-time user experience may show multiple loading spinners in sequence (auth → user profile → task list → galaxy → achievements) rather than a skeleton screen or progressive placeholder. Each provider independently shows its loading state, potentially causing layout jumps.

**Expected**: The home screen shell should use `SliverSkeleton` or a coordinated loading orchestration that fades in content areas as they become available.

**Fix recommendation**: Implement a `HomeLoadingOrchestrator` provider that tracks loading states of all critical data providers and renders a coordinated skeleton screen for first-time load.

---

### Finding O-11 [P3] — LLM Service Unavailable Message Is Generic

**File**: `backend/gateway/internal/handler/error_sanitizer.go` line 109, `backend/gateway/internal/handler/chat_orchestrator_protocol.go` line 703  
**Area**: Graceful Degradation / User Messaging  

**Current code** (`error_sanitizer.go` line 109):
```go
case http.StatusBadGateway, http.StatusServiceUnavailable, http.StatusGatewayTimeout:
    return i18n.T(ctx, "errors.upstream")
```

**Problem**: When the Python engine or LLM is unavailable, the user sees "Service temporarily unavailable" (i18n key `errors.upstream`). While correct for security (no internal details leaked), this is not actionable. The user doesn't know whether to retry, wait, or contact support.

**Expected**: Add a more helpful message like "AI service is temporarily unavailable. Your request has been saved and will be processed when the service recovers. You can continue using other features." Combined with the offline queue, this makes the degraded experience clear.

**Fix recommendation**: Add an `errors.upstream_degraded` i18n key with more context, and use it specifically when the circuit breaker is open vs. a generic upstream failure.

---

### Finding O-12 [P3] — No Deep Link Validation on Cold Start From Notification

**File**: `mobile/lib/core/services/app_link_router_service.dart` line 27, `mobile/lib/core/services/deep_link_service.dart`  
**Area**: Edge Cases / Deep Linking  

**Current code** (`app_link_router_service.dart` lines 54–59):
```dart
void _scheduleHandle(Uri uri, {Duration delay = Duration.zero}) {
    Future<void>.delayed(delay, () {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _handleUri(uri);
      });
    });
}
```

**Problem**: The initial delay is 1400ms for cold start. If the user's auth token is expired when the deep link fires, the navigation will fail silently (the route attempts to load data that requires auth, gets 401, token refresh is triggered, but the navigation has already been initiated). The target screen may show an error or loading state without retrying after re-auth.

**Expected**: The deep link handler should check auth state before navigation and retry with backoff if not yet authenticated.

**Fix recommendation**: Verify auth state in `_handleUri()` before navigation. If not authenticated, wait for auth to complete (watch `authProvider`) then navigate.

---

### Finding O-13 [P3] — MinIO Unavailability Fails Open (Missing Failure Test)

**File**: `backend/gateway/cmd/server/setup.go` lines 184–185  
**Area**: Graceful Degradation / External Dependencies  

**Current code** (lines 184–185):
```go
if err != nil {
    return nil, err  // File storage init failure is fatal
}
```

**Problem**: If MinIO is unavailable at startup, the file storage service initialization returns an error, which causes the entire Gateway to fail to start. This is a fail-closed approach — users can't use any feature if file storage is down, even features unrelated to file upload.

**Expected**: MinIO failure should be a warning, not fatal. File upload/download operations should return user-friendly errors when MinIO is unavailable, but the rest of the Gateway should function. Alternatively, implement a lazy initialization pattern with health checks.

**Fix recommendation**: Make file storage init non-fatal. Log a warning and set a `minioUnavailable` flag. File operations check this flag and return a translated error. The health endpoint should report MinIO status.

---

## WHAT IS WORKING WELL (Notable Strengths)

### Offline Infrastructure (Strong)
- **SyncEngine** (`sync_engine.dart`): Real outbox pattern with Isar persistence, exponential backoff (800ms base, 30s max, 5 attempts), ACK-based tracking with 30s TTL, stuck-message requeueing, connectivity-aware processing, batch processing (20 max), dedup key support.
- **TaskOfflineQueue** (`task_offline_queue.dart`): Full offline support for all 5 task lifecycle operations (start/pause/resume/complete/abandon) with idempotent server handling (409 = success).
- **OfflineMessageQueueService** (`offline_message_queue_service.dart`): Persists chat messages during disconnect with status lifecycle (pending → sent → acked/failed), retryable message recovery, 24h cleanup.
- **CRDTSyncManager** (`crdt_sync_manager.dart`): Real CRDT implementation with Lamport timestamps, operation-based merges, local snapshots, actor IDs.
- **Sync metadata tracking** (`sync_metadata.dart`): Last success timestamp, version tracking.

### Circuit Breakers (Strong)
- **Go gRPC Health Checker** (`agent/health_checker.go`): Full Closed/Open/HalfOpen state machine, Prometheus metrics, manual force open/close, reconnection on failure, panic recovery in health checks, exponential backoff reconnection.
- **Python Redis Circuit Breaker** (`services/circuit_breaker.py`): Redis-backed with local in-memory fallback, TTL window failure counting.
- **Flutter Circuit Breaker** (`retry_strategy.dart`): Independent implementation with 5-failure threshold, 30s reset, half-open probing, manual reset.

### Error Sanitization (Strong)
- **Go Error Sanitizer** (`error_sanitizer.go`): Safe messages per HTTP status, i18n keyed, dev mode raw errors, Prometheus metrics for sanitized errors, request ID tracking, error category classification.
- **WebSocket safe writer** (`ws_safe_writer.go`): Mutex-protected writes, write deadlines, context-aware timeouts, sync.Once close protection.
- **Python FastAPI Exception Handlers** (`main.py` lines 770–822): Three-tier (validation → custom → generic), DEBUG-aware detail exposure, trace ID inclusion.

### Network Resilience (Strong)
- **Go Network Resilience Middleware** (`network_resilience.go`): Upstream retry with exponential backoff, client disconnect detection, state-save signaling, keepalive headers, request timeout enforcement.
- **Go RetryableUpstreamProxy**: Resettable request body for retries, configurable retryable status codes.
- **Python SLO Auto-Degrade** (`auto_degrade.py`): Alertmanager webhook integration, 5 alert types (LLM latency, Redis, DB, Event Bus, GW), kill switch bindings, audit trail events, ClientDisconnectGuard for streaming state save.
- **Python ClientDisconnectGuard**: Context manager for intermediate state saves during streaming disconnects.

### WebSocket Reconnection (Strong)
- **Flutter WebSocket Service** (`websocket_service.dart`): 6 attempts with progressive backoff (800ms to 12.2s), manual vs auto disconnect tracking, cancellation of reconnect timer on manual disconnect.
- **Go WebSocket Hardening** (`ws_hardening.go`): Per-message rate limiting, safe public error messages.
- **Go WebSocket Lifecycle** (`chat_orchestrator.go`): Ping/pong (90s/30s write/read deadlines), idle timeout (5 min), connection registry with max connection limits.

### Session Expiry (Strong)
- **Flutter API Interceptor** (`api_interceptor.dart`): Token refresh with concurrent request dedup (Completer-based), demo mode handling, logout on refresh failure, 401 path exclusion for auth endpoints.

### Event Processing (Strong)
- **Go CQRS Base Worker** (`worker/base.go`): Idempotency check (in-memory + DB), exponential backoff retry (3 attempts, 100ms base, 30s max), DLQ with payload preservation, consumer group self-healing (NOGROUP→recreate), consumer lag metrics.

### Deep Linking (Strong)
- **AppLinkRouterService** (`app_link_router_service.dart`): Cold start + stream link handling, GoRouter integration, delayed retry when context unavailable.
- **DeepLinkService** (`deep_link_service.dart`): 9 route mappings, sparkle:// protocol parsing, parameterized routes with query parameters.
- **RouteResilience** (`route_resilience.dart`): Fallback route mapping per feature area, graceful navigation failure recovery.

### UI Error States (Strong)
- **CustomErrorWidget** (`error_widget.dart`): Page/banner/inline types, severity levels (error/warning/info), i18n, retry, close, gradient theming, accessibility labels.
- **EmptyState** (`empty_state.dart`): 6 types (noTasks/noChats/noPlans/noErrors/noResults/general), i18n descriptions, action buttons, gradient icons, compact variant.

### Data Loss Prevention (Present)
- **Task execution screen** (`task_execution_screen.dart`): PopScope with canPop:false, exit confirmation dialog, auto-pause on long exit, celebration protection.
- **Task cards** (`task_card.dart`): confirmDismiss for swipe-to-dismiss.

---

## SUMMARY TABLE

| ID | Severity | Area | Finding | Status |
|----|----------|------|---------|--------|
| O-01 | **P0** | Error Boundary | No ErrorWidget.builder override | Missing |
| O-02 | **P1** | Graceful Degradation | Chat orchestrator skips circuit breaker check | Missing |
| O-03 | **P1** | Offline UX | No centralized offline banner | Missing |
| O-04 | **P1** | Data Loss | Task create lacks unsaved-data PopScope | Missing |
| O-05 | **P2** | Memory Pressure | No image cache eviction on low memory | Missing |
| O-06 | **P2** | Double-Submit | Inconsistent _isSubmitting guards | Partial |
| O-07 | **P2** | Panic Recovery | Go goroutine panic recovery missing | Missing |
| O-08 | **P2** | Python Errors | asyncio global exception handler missing | Missing |
| O-09 | **P2** | Data Loss | App-kill during task execution unrecoverable | Gap |
| O-10 | **P2** | Empty States | First-time user sees sequential spinners | UX Gap |
| O-11 | **P3** | User Messaging | LLM unavailable message too generic | Minor |
| O-12 | **P3** | Deep Linking | No auth check before cold-start nav | Edge Case |
| O-13 | **P3** | External Deps | MinIO failure is fatal at startup | Design Gap |

**Total**: 13 findings (1 P0, 3 P1, 6 P2, 3 P3)

---

## VERIFICATION CHECKLIST

- [ ] O-01: Add `ErrorWidget.builder` in `app.dart` builder closure
- [ ] O-02: Add circuit breaker pre-check in `HandleWebSocket()`
- [ ] O-03: Add `connectivityProvider` and global offline banner
- [ ] O-04: Add `PopScope` with dirty-form check to task create screen
- [ ] O-05: Add `didHaveMemoryPressure` handler to app lifecycle observer
- [ ] O-06: Audit all forms for `_isSubmitting` guards
- [ ] O-07: Add `defer recover()` to background goroutines
- [ ] O-08: Register asyncio global exception handler
- [ ] O-09: Persist task execution state to Isar on lifecycle pause
- [ ] O-10: Implement coordinated skeleton loading for home screen
- [ ] O-11: Add `errors.upstream_degraded` i18n key with context
- [ ] O-12: Add auth-state check to cold-start deep link handler
- [ ] O-13: Make MinIO init non-fatal with lazy health check

---

## FILES REFERENCED

| File | Lines | Finding |
|------|-------|---------|
| `mobile/lib/main.dart` | 30–46, 171 | O-01 |
| `mobile/lib/app/app.dart` | 76–118 | O-01, O-03, O-05 |
| `mobile/lib/core/offline/sync_engine.dart` | 1–579 | O-03 (strength) |
| `mobile/lib/core/offline/offline_message_queue_service.dart` | 1–192 | O-09 (strength) |
| `mobile/lib/core/offline/crdt_sync_manager.dart` | 1–267 | (strength) |
| `mobile/lib/core/offline/offline_providers.dart` | 1–117 | O-03 |
| `mobile/lib/features/task/data/services/task_offline_queue.dart` | 1–157 | (strength) |
| `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` | 230–254, 925–934 | O-04 (positive reference) |
| `mobile/lib/features/task/presentation/screens/task_create_screen.dart` | 121 | O-04 |
| `mobile/lib/core/services/websocket_service.dart` | 1–166 | (strength) |
| `mobile/lib/core/services/retry_strategy.dart` | 1–271 | (strength) |
| `mobile/lib/core/services/app_link_router_service.dart` | 1–92 | O-12 |
| `mobile/lib/core/services/deep_link_service.dart` | 1–186 | (strength) |
| `mobile/lib/core/navigation/route_resilience.dart` | 1–113 | (strength) |
| `mobile/lib/core/design/widgets/error_widget.dart` | 1–502 | (strength) |
| `mobile/lib/core/design/widgets/empty_state.dart` | 1–408 | O-10 (strength) |
| `backend/gateway/internal/handler/chat_orchestrator.go` | 204–254 | O-02 |
| `backend/gateway/internal/agent/client.go` | 314–330 | O-02 |
| `backend/gateway/internal/agent/health_checker.go` | 1–506 | (strength) |
| `backend/gateway/internal/handler/error_sanitizer.go` | 1–219 | O-11 (strength) |
| `backend/gateway/internal/handler/ws_hardening.go` | 1–48 | (strength) |
| `backend/gateway/internal/handler/ws_safe_writer.go` | 1–104 | (strength) |
| `backend/gateway/internal/middleware/network_resilience.go` | 1–249 | (strength) |
| `backend/gateway/internal/cqrs/worker/base.go` | 114–145 | O-07 |
| `backend/gateway/cmd/server/setup.go` | 184–185, 419–437 | O-07, O-13 |
| `backend/app/services/circuit_breaker.py` | 1–113 | (strength) |
| `backend/app/api/internal/auto_degrade.py` | 1–318 | (strength) |
| `backend/app/main.py` | 102–175, 770–822 | O-08 (strength) |
| `mobile/lib/core/network/api_interceptor.dart` | 125–205 | (strength) |
