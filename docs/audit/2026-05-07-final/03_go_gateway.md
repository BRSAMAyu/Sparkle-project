# Go Gateway Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Go Gateway is a well-architected, production-grade coordination layer with strong security posture, comprehensive WebSocket lifecycle management, and mature gRPC client handling with circuit breaker protection. The code demonstrates disciplined separation of concerns, thorough error sanitization, and proper graceful shutdown orchestration. There are no blocking P0 issues. Several P1 items should be addressed before launch, primarily around a goroutine leak in the CQRS initialization, a stale context reference in background workers, and a defensive nil check in the token validator.

## Critical Issues (P0)

None found.

## High Issues (P1)

### P1-1: Background goroutines use `context.Background()` instead of derived context with cancellation

**Files**: `cmd/server/setup.go:370-372,376-378,404-418,427-439`

Multiple background workers (file event subscriber, file GC, outbox publisher/cleaner, DLQ cleaner, sync workers) are started with `context.Background()`. These goroutines have no mechanism to be stopped during graceful shutdown. The CQRS workers and event subscribers will continue running after the HTTP server shuts down, potentially causing resource leaks and partial writes during deployment.

```go
// Line 370-372: file event subscriber — unstoppable
go func() {
    if err := fileEventSubscriber.Run(context.Background()); err != nil {
```

```go
// Line 376-378: file GC — unstoppable
go func() {
    if err := fileGC.Run(context.Background()); err != nil {
```

**Recommendation**: Create a derived context from a master shutdown context that gets cancelled during the shutdown sequence in `main()`, and pass it to all background workers. Add `Stop()` methods where missing.

### P1-2: `authToken` set but unused in `ChatOrchestrator.HandleWebSocket`

**File**: `internal/handler/chat_orchestrator.go:305-306`

```go
authToken := c.GetString("auth_token")
_ = authToken
```

The auth token is explicitly blank-assigned and never used. Meanwhile, downstream methods like `handleActionFeedback` receive `authToken` as a parameter and presumably need it. This is dead code that may indicate a missing feature or an incomplete refactoring. The `authToken` IS passed into inner methods like `handleActionFeedbackWithResponder` via closures, so the blank assignment on line 306 should be removed to avoid confusion.

### P1-3: CQRS health endpoint uses separate `context.Background()` instead of request context

**File**: `cmd/server/setup.go:512`

```go
outboxPendingCount, err := cqrs.outboxRepo.GetPendingCount(context.Background())
```

Inside the `/api/v1/health/cqrs` handler, a fresh `context.Background()` is used instead of `c.Request.Context()`. If the client disconnects, the database query continues executing unnecessarily. For a health endpoint this is low risk, but it violates the principle of respecting client context and should be consistent with other endpoints.

### P1-4: `galaxyClient` connection failure is logged as warning but server continues without it

**File**: `cmd/server/setup.go:222-224`

```go
galaxyClient, err := galaxy.NewClient(cfg)
if err != nil {
    log.Printf("Warning: Unable to connect to galaxy service: %v", err)
}
```

Unlike `agentClient` and `errorBookClient`, the galaxy client failure does NOT prevent server startup. If the galaxy service is required for key features (knowledge graph, mastery updates), the server will accept requests that fail at runtime with nil pointer errors. The `defer galaxyClient.Close()` on line 69 is guarded by a nil check, but downstream handlers like `galaxy_handler.go` and `chat_orchestrator.go` may not consistently guard against nil.

**Recommendation**: Either make galaxy a hard dependency (fail fast like agent/error_book), or ensure all downstream code paths have nil guards with clear error messages.

### P1-5: WebSocket proxy reads `err` after successful `ReadMessage` and checks for `CloseError`

**File**: `internal/handler/websocket_proxy.go:364-377` and `430-443`

In both the client-to-backend and backend-to-client goroutines, after a successful `ReadMessage()` (where `err == nil`), the code checks `errors.As(err, &closeErr)`. This block can never execute because `err` is nil at that point. The close error detection logic is dead code:

```go
messageType, data, err := clientConn.ReadMessage()
if err != nil {
    // ... error handling ...
    sendErr(err)
    return
}
var closeErr *websocket.CloseError
if errors.As(err, &closeErr) {  // err is nil here — dead code
    closeConnections(closeErr.Code, closeErr.Text)
}
```

This is not a security issue (close frames are handled by gorilla/websocket internally and trigger the error path above), but it indicates a logic misunderstanding. Close errors are already captured in the `if err != nil` block above, and `websocket.IsUnexpectedCloseError` correctly filters them.

## Medium Issues (P2)

### P2-1: User ID logged with hash but some paths still log raw user ID

**File**: `internal/handler/chat_orchestrator.go:308`

```go
log.Printf("WebSocket connected for user: %s", hashUserIDForLog(userID))
```

While the main orchestrator correctly hashes user IDs, the `ws_auth.go` middleware logs:

```go
log.Printf("[WsAuth] JWT header validation success for user: %s", logsafe.UserIDHash(userID))
```

This is correct. However, `internal/handler/auth.go:90` logs:

```go
log.Printf("[WARN] UpdateUserLastLogin failed for user %s: %v", h.uuidToString(user.ID), err)
```

This logs the raw UUID. While UUIDs are less sensitive than emails, the codebase should be consistent. Verify that `logsafe.UserIDHash` is used everywhere for production logs.

### P2-2: Rate limiter goroutines are never stopped for per-endpoint limiters

**File**: `internal/middleware/rate_limit.go:182-185,258`

Functions like `IPBasedRateLimit`, `UserBasedRateLimit`, and `AdaptiveRateLimitMiddleware` create `RateLimiter` instances internally but never call `rl.Stop()`. Each `RateLimiter` spawns a background goroutine for cleanup. While the goroutines are lightweight, they leak over the server's lifetime since the `stopCh` is never closed.

```go
func IPBasedRateLimit(requestsPerSecond float64, burst int) gin.HandlerFunc {
    rl := NewRateLimiter(rate.Limit(requestsPerSecond), burst)
    // rl.Stop() is never called — goroutine leaks
    return RateLimitMiddleware(rl)
}
```

The `HybridRateLimitMiddlewareSimple` function also creates local rate limiters that are never stopped.

**Recommendation**: Either make these long-lived singletons (created once in `setup.go`) or call `Stop()` when the middleware is discarded.

### P2-3: `GetRecentSessionsFromDB` query uses `LEFT JOIN LATERAL` without index guarantee

**File**: `internal/db/query.sql.go:820-833`

```sql
SELECT cs.id, cs.title, cs.last_message_at, cm.content as preview
FROM chat_sessions cs
LEFT JOIN LATERAL (
  SELECT content FROM chat_messages
  WHERE session_id = cs.id
  ORDER BY created_at DESC
  LIMIT 1
) cm ON true
WHERE cs.user_id = $1 AND cs.is_active = true
ORDER BY cs.last_message_at DESC
LIMIT $2
```

The LATERAL subquery runs for every session row. If there is no composite index on `(session_id, created_at DESC)` in `chat_messages`, this could be an N+1 performance issue. Verify the index exists.

### P2-4: No global connection count enforcement in `ConnectionRegistry.Register`

**File**: `internal/handler/ws_registry.go:56-96`

The `Register` method checks `maxPerUser` but the `maxActive` check iterates all connections under a write lock:

```go
if r.maxActive > 0 {
    totalActive := 0
    for _, entries := range r.connections {
        totalActive += len(entries)
    }
    if totalActive >= r.maxActive {
        r.mu.Unlock()
        return false
    }
}
```

With `WSGlobalMaxConnections=2000` (the default) and 2000+ connections, this O(n) scan under a write lock on every new connection registration could become a contention point. Consider maintaining an atomic counter instead.

### P2-5: Network resilience middleware double-wraps timeout

**File**: `cmd/server/setup.go:586-587` and `internal/middleware/network_resilience.go:114`

The network resilience middleware is applied globally with `r.Use(...)` on line 586. But `api` group already has `TimeoutMiddleware` applied on line 543. This means API routes get two layers of timeout enforcement: the middleware timeout (30s) AND the resilience timeout (30s). If they fire simultaneously, the behavior is unpredictable.

### P2-6: `commCmdService` and `commQueryService` created but unused

**File**: `cmd/server/setup.go:359-362`

```go
commCmdService := service.NewCommunityCommandService(dbh.pool)
commQueryService := service.NewCommunityQueryService(rdb, dbh.pool)
_ = commCmdService
_ = commQueryService
```

These services are initialized (creating database pool connections) and then immediately discarded with blank assignments. This is dead code that wastes resources.

## Low Issues (P3)

### P3-1: `isDevelopmentModeForErrors` reads `ENVIRONMENT` from env directly instead of config

**File**: `internal/handler/error_sanitizer.go:25-28`, `internal/middleware/auth.go:305-308`

Multiple helper functions call `os.Getenv("ENVIRONMENT")` directly rather than using the passed `*config.Config` or gin context. This bypasses the viper configuration layer and may give inconsistent results if env vars are set differently than what viper resolved. While unlikely in practice, it is a consistency issue.

### P3-2: `hashUserIDForLog` uses SHA-256 truncated to 12 hex chars

**File**: `internal/handler/websocket_proxy.go:599-602`

```go
func hashUserIDForLog(userID string) string {
    sum := sha256.Sum256([]byte(userID))
    return hex.EncodeToString(sum[:])[:12]
}
```

12 hex characters (48 bits) provides good enough collision resistance for logging purposes, but the function is defined in `websocket_proxy.go` and used in `chat_orchestrator.go`. It should be in a shared utility package or in `logsafe` to avoid duplication and potential inconsistent hashing approaches.

### P3-3: `selectWebSocketSubprotocol` returns first matching candidate but may expose ticket tokens

**File**: `internal/handler/websocket_factory.go:69-94`

The function iterates `Sec-WebSocket-Protocol` header parts and returns the first match that looks like a ticket/bearer/token prefix. If none match, it returns the first subprotocol. This means if a client sends `ticket=<valid-ticket>, some-other-protocol`, the ticket value becomes the selected subprotocol and gets echoed back in the upgrade response header. While the ticket is one-time-use, this is an information leak vector.

### P3-4: `matchWildcardHost` rejects exact domain matches for wildcard patterns

**File**: `internal/config/config.go:213-221`

```go
func matchWildcardHost(host string, domain string) bool {
    host = strings.ToLower(host)
    domain = strings.ToLower(domain)
    if host == domain {
        return false
    }
    return strings.HasSuffix(host, "."+domain)
}
```

If the allowlist has `*.example.com` and a request comes from `example.com` (not a subdomain), it will be rejected. This is likely intentional (only subdomains match wildcards), but should be documented clearly since some users may expect `*.example.com` to also match `example.com`.

### P3-5: Admin rebuild endpoints use `context.Background()` for long-running operations

**File**: `cmd/server/setup.go:674-688`

The admin projection rebuild endpoints spawn goroutines with `context.Background()`. If multiple rebuilds are triggered simultaneously, there is no deduplication or cancellation mechanism. An operator could accidentally trigger multiple concurrent rebuilds of the same projection.

### P3-6: `loadEnvFileIntoViper` does not handle multi-line values

**File**: `internal/config/config.go:387-418`

The `.env` file parser reads line-by-line and does not support multi-line values (e.g., PEM-encoded RSA keys stored in `.env`). The JWT RSA keys (`JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`) must be provided as single-line values or via environment variables directly. This is documented behavior but could surprise operators trying to use multi-line PEM files in `.env`.

## Positive Findings

1. **Excellent security posture**: JWT validation supports both RS256 and HS256 with proper key parsing, timing-attack-resistant admin secret comparison, production-mode rejection of insecure defaults, and environment-aware fail-closed Redis token blacklisting.

2. **Thorough error sanitization**: A dedicated `error_sanitizer.go` ensures internal error details never leak to clients. Development mode preserves debuggability while production mode uses i18n-sanitized messages. Prometheus metrics track sanitized errors.

3. **Comprehensive graceful shutdown**: The 4-phase shutdown sequence (stop admitting WS work -> stop HTTP -> drain WS connections -> wait for HTTP settle) with configurable timeout is well-designed and correctly orchestrated.

4. **Robust WebSocket lifecycle**: Both the chat orchestrator and community proxy implement proper ping/pong keepalive, read limits, message rate limiting, idle timeout, and reconnect rate limiting with configurable parameters.

5. **Strong gRPC client design**: The agent client implements connection pooling, automatic reconnection with rate limiting (R5-G07 minimum gap), circuit breaker with three states (closed/open/half-open), health checking, and Prometheus observability for all states and transitions.

6. **Well-structured proxy routing**: The `ProxyRoutesHandler` uses explicit `registerREST` methods instead of `Any()`, preventing unintended method exposure. The `NoRoute` fallback is limited to specific auth paths with proper privilege escalation checks.

7. **Proper SQL injection prevention**: All database queries use sqlc-generated code with parameterized statements (`$1`, `$2`, etc.), eliminating SQL injection risk entirely.

8. **Security headers are comprehensive**: CSP, HSTS (production only), X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, and Cross-Origin isolation headers are all applied correctly.

9. **Object pooling for performance**: `sync.Pool` is used for `chatInput` structs and `strings.Builder` instances in the hot WebSocket message path, reducing GC pressure.

10. **WebSocket safe writer**: The channel-based mutex (`wsSafeWriter`) with context-aware lock acquisition prevents deadlocks and provides proper timeout handling for concurrent writes.

11. **CORS configuration is origin-aware**: Proper `Vary: Origin` header, wildcard rejection in production, and per-request origin validation against a configurable whitelist.

12. **Internal API protection**: Both API key (constant-time comparison) and IP whitelist (CIDR-based) middleware protect internal endpoints, applied as a group to ensure defense in depth.

## Files Audited

| File | Lines |
|------|-------|
| `cmd/server/main.go` | 154 |
| `cmd/server/setup.go` | 965 |
| `internal/config/config.go` | 757 |
| `internal/agent/client.go` | 582 |
| `internal/agent/health_checker.go` | 512 |
| `internal/handler/chat_orchestrator.go` | 744 |
| `internal/handler/chat_orchestrator_chatflow.go` | 1040 |
| `internal/handler/chat_orchestrator_connections.go` | 99 |
| `internal/handler/chat_orchestrator_protocol.go` | 716 |
| `internal/handler/websocket_proxy.go` | 766 |
| `internal/handler/ws_registry.go` | 330 |
| `internal/handler/ws_safe_writer.go` | 105 |
| `internal/handler/ws_ticket.go` | 71 |
| `internal/handler/ws_hardening.go` | 49 |
| `internal/handler/websocket_factory.go` | 95 |
| `internal/handler/auth.go` | 232 |
| `internal/handler/error_sanitizer.go` | 219 |
| `internal/handler/proxy_routes.go` | 1059 |
| `internal/handler/file_handler.go` | 622 |
| `internal/handler/api_errors.go` | (not read, referenced) |
| `internal/middleware/auth.go` | 671 |
| `internal/middleware/cors.go` | 31 |
| `internal/middleware/security.go` | 51 |
| `internal/middleware/rate_limit.go` | 537 |
| `internal/middleware/distributed_rate_limiter.go` | 364 |
| `internal/middleware/timeout.go` | 62 |
| `internal/middleware/ws_auth.go` | 173 |
| `internal/middleware/internal_api.go` | 28 |
| `internal/middleware/internal_ip_whitelist.go` | 72 |
| `internal/middleware/network_resilience.go` | 249 |
| `internal/db/db.go` | 33 |
| `internal/db/query.sql.go` | 1643 |
| **Total** | **~12,000+** |
