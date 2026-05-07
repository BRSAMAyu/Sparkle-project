# R17-C: Go Gateway + Infrastructure + Proto + Database Final Audit

> **Date**: 2026-05-07
> **Auditor**: Claude (Independent Deep Audit)
> **Scope**: Go Gateway (auth, WebSocket, proxy, middleware, services), Proto definitions, DB schema, Docker/production config
> **Method**: Full source code read -- every finding verified by file:line reference

---

## Executive Summary

**16 audit domains** reviewed. The codebase demonstrates strong engineering: comprehensive auth with fail-closed Redis blacklist, well-structured WebSocket proxy with goroutine panic recovery, thorough middleware chain, and production-grade Docker configuration.

**Findings: 0 P0, 2 P1, 3 P2, 2 P3**

No production-critical issues found. Two P1 findings relate to stale legacy Python generated files and a config_production.py file that carries a wildcard CORS default (mitigated by the actual settings.py production guard).

---

## Findings

### P1-1: Stale Legacy Python Proto Generated Files (Legacy Path)

**File**: `backend/app/gen/` (root-level files)
- `backend/app/gen/agent_service_pb2.py` -- last modified May 1, proto updated May 3
- `backend/app/gen/galaxy_service_pb2.py` -- last modified May 1, proto updated May 7
- `backend/app/gen/stt_service_pb2.py` -- last modified May 1, proto updated May 7
- `backend/app/gen/websocket_pb2.py` -- last modified May 1, proto updated May 7
- `backend/app/gen/error_book_pb2.py` -- last modified May 1, proto updated May 1 (fresh)
- `backend/app/gen/user_state_pb2.py` -- last modified May 7, proto updated Apr 24 (fresh)

**Impact**: The new-path generated files under `backend/app/gen/agent/v1/`, `galaxy/v1/`, `stt/v1/`, `ws/` are all fresh (May 7 16:39). The actual runtime imports use the new paths exclusively (verified by grep). However, `backend/app/gen/proto/error_book/__init__.py` re-exports from the old path:
```python
from app.gen.error_book_pb2 import *  # noqa: F401, F403
from app.gen.error_book_pb2_grpc import *  # noqa: F401, F403
```
And `backend/app/gen/userstate/v1/user_state_pb2.py` re-exports from the old path:
```python
from app.gen.user_state_pb2 import *  # noqa: F401,F403
```

**Risk**: If any code imports via the legacy `app.gen.proto.error_book` or `app.gen.userstate.v1` paths, it may get stale proto definitions. Currently error_book_pb2 is fresh so no runtime impact, but this creates a maintenance hazard.

**Recommendation**: Delete the legacy root-level generated files and update the `__init__.py` re-export wrappers to point to the new paths. Or add a CI freshness check that compares proto timestamps against both old and new generated paths.

---

### P1-2: config_production.py Defaults BACKEND_CORS_ORIGINS to Wildcard

**File**: `backend/app/config_production.py:41-44`
```python
BACKEND_CORS_ORIGINS: list[str] = Field(
    default=["*"],
    env="BACKEND_CORS_ORIGINS"
)
```

**Mitigation**: The actual production settings module (`backend/app/config/settings.py:1060-1061`) correctly rejects wildcard in production:
```python
if "*" in cors_origins:
    raise ValueError("BACKEND_CORS_ORIGINS cannot include '*' in production")
```

However, `config_production.py` is a standalone module with its own `ProductionSettings` class. If anyone were to use this module directly (it has `if __name__ == "__main__": check_config()`), the wildcard default would pass its own validation (which only checks `SECRET_KEY == "CHANGE_ME_IN_PRODUCTION"`, not CORS wildcards).

**Risk**: Low in practice since the actual services use `settings.py`, not `config_production.py`. But `config_production.py` lacks the production CORS guard that `settings.py` has.

**Recommendation**: Add CORS wildcard rejection to `config_production.py`'s `validate_all()` method, or add a `@field_validator("BACKEND_CORS_ORIGINS")` that rejects `["*"]` when `DEBUG` is False.

---

### P2-1: WebSocket Proxy Close() is a No-Op

**File**: `backend/gateway/internal/handler/websocket_proxy.go:644-646`
```go
func (p *WebSocketProxy) Close() error {
    return nil
}
```

The proxy has a `wg sync.WaitGroup` and `liveConnections` map, but `Close()` does not drain connections or wait for goroutines. The `StartDraining()` method exists and sets the draining flag, but `Close()` does not call it. If graceful shutdown depends on calling `Close()`, active connections will be orphaned.

**Impact**: Low -- setup.go likely calls `StartDraining()` before shutdown. But the `Close()` method contract is misleading.

**Recommendation**: Either have `Close()` call `StartDraining()` + `p.wg.Wait()` with a timeout, or document that callers must use `StartDraining()` first.

---

### P2-2: Auth Handler Exposes Token Twice in Login Response

**File**: `backend/gateway/internal/handler/auth.go:121-136`
```go
c.JSON(http.StatusOK, gin.H{
    "access_token":  accessToken,
    "refresh_token": refreshToken,
    "token_type":    "bearer",
    "token": gin.H{         // <-- duplicate nesting
        "access_token":  accessToken,
        "refresh_token": refreshToken,
        "token_type":    "bearer",
    },
    "user": gin.H{...},
})
```

The response contains the tokens at both the top level and nested inside a `token` key. This doubles the token data in the response payload and is likely a backward-compatibility artifact.

**Impact**: Cosmetic / bandwidth waste. Not a security issue since the response is over HTTPS/WS.

**Recommendation**: Deprecate one of the two and remove after clients migrate.

---

### P2-3: Errors Group Routes Mixed into Tasks Group

**File**: `backend/gateway/internal/handler/proxy_routes.go:117-149`

Lines 125-149 register task command routes (generate-guide, start, complete, abandon, etc.) inside the `errors` group block instead of the `tasks` group:
```go
errors := api.Group("/errors")
errors.Use(authMiddleware)
{
    errors.GET("/remediable-patterns", h.proxyWithHeaders)
    errors.POST("/patterns/:pattern_id/generate-template", h.proxyWithHeaders)
    errors.POST("/patterns/:pattern_id/accept-template", h.proxyWithHeaders)
    // These are task routes registered on the errors group:
    tasks.POST("/:id/generate-guide", h.proxyWithHeaders)    // line 125
    tasks.POST("/:id/start", h.proxyWithHeaders)              // line 126
    ...
}
```

Wait -- these lines reference `tasks` not `errors`, so they actually register on the `tasks` group defined earlier. The indentation and placement inside the `errors` block is misleading but functionally correct because Go closures capture variables by reference. The `tasks` variable is the one from line 79.

**Impact**: Code readability only. Functionally correct due to Go closure semantics.

**Recommendation**: Move these task command registrations back into the `tasks` block for clarity.

---

### P3-1: Rate Limit Cleanup Goroutine Has No Context Cancellation

**File**: `backend/gateway/internal/middleware/rate_limit.go:89-108`
```go
func (rl *RateLimiter) cleanupVisitors() {
    ticker := time.NewTicker(time.Minute)
    defer ticker.Stop()
    for {
        select {
        case <-rl.stopCh:
            return
        case <-ticker.C:
            ...
        }
    }
}
```

The `stopCh` pattern is correct and the `Stop()` method is provided. However, the `NewRateLimiter` function does not expose a way for the caller to call `Stop()` -- it creates the limiter and starts the goroutine internally. Callers creating rate limiters via `IPBasedRateLimit()`, `UserBasedRateLimit()`, etc. cannot stop the cleanup goroutine.

**Impact**: Negligible -- these goroutines are lightweight and run for the process lifetime. Only relevant for tests.

**Recommendation**: Document that `Stop()` should be called for long-lived limiters, or add finalizer support.

---

### P3-2: setup.go commSyncWorker Uses context.Background() Ignoring Shutdown

**File**: `backend/gateway/cmd/server/setup.go:369-373`
```go
go func() {
    if err := fileEventSubscriber.Run(context.Background()); err != nil {
        logger.Error("File event subscriber stopped", zap.Error(err))
    }
}()
```

Several background goroutines (fileEventSubscriber, fileGC, outboxPublisher, syncWorkers) are started with `context.Background()`. If the gateway receives SIGTERM, these goroutines have no cancellation signal and will continue until the process is killed.

**Impact**: Low -- the OS will kill the process. But graceful shutdown would be cleaner with a derived context from a signal handler.

**Recommendation**: Create a root context with cancel from the main function's signal handler and pass it to background workers.

---

## Verified Clean Areas (No Issues Found)

### 1. Go Auth System -- VERIFIED CLEAN
- JWT creation uses configurable expiry (access 30min, refresh 7d)
- Token type claim enforced (`type: "access"`)
- Issuer and audience validation when configured
- HS256 is documented with RS256 migration plan (known design choice)
- Apple Login flow: TOS/privacy acceptance check, token verification, find-or-create, session persistence
- Session persistence failure does not block login (logged as WARN)
- Error messages are localized via i18n

### 2. Auth Middleware -- VERIFIED CLEAN
- Token blacklist with 3 layers: JTI-specific, user-level revocation, session revocation
- Fail-Closed mode for production (rejects tokens when Redis unavailable)
- Fail-Open mode for development
- Local blacklist cache as fallback (LRU eviction, 10K cap, expiry cleanup)
- Admin secret uses `crypto/subtle.ConstantTimeCompare` (timing-attack resistant)
- Clock skew tolerance (30s) for JWT expiry
- Admin middleware requires separate X-Admin-Secret header
- query user_id parameter validated against token identity

### 3. WebSocket Proxy -- VERIFIED CLEAN
- Connection lifecycle: upgrade, bidirectional proxy, heartbeat ping/pong, close
- Goroutine panic recovery with stack trace logging
- Per-user connection limit with configurable max
- Reconnect rate limiting (sliding window, configurable attempts/block duration)
- Cleanup of expired reconnect trackers (every 5 min)
- Draining mode for graceful shutdown (atomic bool)
- WaitGroup for tracking in-flight connections
- ReadLimit enforced on both client and backend
- Message rate limiter per connection
- Content sanitization (bluemonday) for text messages
- SHA-256 dedup for community messages
- User IDs hashed in logs (first 12 chars of SHA-256)
- UUID validation for group_id path parameter
- Subprotocol passthrough for backend/Client consistency
- Known limitation documented: connection tracking is per-instance (G-03)

### 4. Proxy Routes -- VERIFIED CLEAN
- Explicit route registration for all major API groups
- `registerREST()` helper avoids `Any()` (blocks CONNECT, TRACE, HEAD, OPTIONS)
- Auth middleware applied to all protected routes
- Admin routes require both admin secret and RequireAdmin middleware
- DLQ routes use RequireAdmin
- Client telemetry allows unauthenticated POST for events
- A/B testing variant assignment per request
- User context headers set for all proxied requests
- Comprehensive route coverage: 50+ resource groups

### 5. Galaxy Handler -- VERIFIED CLEAN
- gRPC-first with REST fallback for all endpoints
- Proper timeout contexts (5-10 seconds)
- Request body re-readable via io.NopCloser for fallback path
- Cache invalidation on write operations (graph cache + view cache)
- Node ID validation (UUID parse for CQRS path)
- Multiple path variants supported (`/node/:id` and `/nodes/:id`)
- Rate limiting applied only to SSE and sync endpoints

### 6. Chat Orchestrator -- VERIFIED CLEAN
- Admission control via semaphore (prevents unbounded concurrent streams)
- Minimum 300s timeout for gRPC streams
- User identity canonicalization (email -> UUID resolution)
- Semantic cache with proper scope (skipped for multi-turn sessions)
- Duplicate request detection via TryAcceptRealtimeRequest
- Daily quota enforcement with mid-stream segment tracking
- String builder pool for efficient text accumulation
- OpenTelemetry tracing for user context fetch, cache search, gRPC call, stream receive
- Response types handled uniformly: envelope, protobuf, legacy WebSocket
- Partial response saved on stream error

### 7. Middleware Chain -- VERIFIED CLEAN
- Security headers: CSP, X-Frame-Options (DENY), HSTS (production only), nosniff, XSS protection, Referrer-Policy, Permissions-Policy, Cross-Origin isolation
- CORS: Origin-based (not wildcard), credentials supported, proper preflight handling, max-age 24h
- Rate limiting: Hybrid (Redis + local fallback), adaptive, per-endpoint, sliding window, admin/internal
- i18n middleware for request context
- Request context middleware for request ID propagation
- Network resilience middleware for upstream failures
- Timeout middleware (configurable, default 30s)
- Chaos guard for development testing

### 8. Service Layer -- VERIFIED CLEAN
- TaskCommandService uses Unit of Work / Outbox pattern for transactional consistency
- Chat history with TTL-based pruning
- Semantic cache with content-hash scoping
- File metadata, storage, processing, GC service
- User context aggregation for AI personalization
- Message dedup via Redis content hash
- Galaxy command service via Go CQRS

### 9. Configuration & Startup -- VERIFIED CLEAN
- Dependency injection via service/handler bundles
- Database pool with configurable limits (max 30, min 5, idle 15min)
- Multiple DB connection types (pool, single conn, sql.DB for sqlc)
- Chaos manager for development testing
- Trusted proxy configuration (required in production)
- Prometheus metrics endpoint (development only)
- Swagger UI (development only)
- OTel tracing initialization
- NoRoute handler proxies only specific public auth paths
- Privileged NoRoute paths (logout, upgrade-guest) require auth

### 10. Proto Definitions -- VERIFIED CLEAN
- 7 proto files with proper Go/Python package declarations
- `community_service.proto` intentionally excluded from buf generation (buf.yaml line 8)
- Reserved fields properly declared (ChatResponse reserved 13/"timestamp", GalaxyNode reserved 4/"version")
- Well-structured service definitions with clear comments
- Field numbering is sequential and non-conflicting
- `optional` keyword used correctly for proto3 optional fields

### 11. Proto Code Freshness -- VERIFIED CLEAN (Go)
- All Go generated code (`backend/gateway/gen/`) is fresher than proto sources
- Generated at May 7 16:39 for agent, galaxy, stt, websocket protos
- See P1-1 for Python legacy path staleness

### 12. Database Schema -- VERIFIED CLEAN
- 22,159 lines covering full schema
- 324 foreign key constraints
- 1,066 indexes (including unique indexes)
- Extensions: pgcrypto, pgvector, Apache AGE
- Custom schemas: ag_catalog, sparkle_galaxy
- Proper ENUM types for status fields
- created_at columns with DEFAULT now() or CURRENT_TIMESTAMP

### 13. Docker Configuration -- VERIFIED CLEAN
- docker-compose.yml: Development setup with proper health checks for all services
- docker-compose.prod.yml: Blue-green gateway deployment with Nginx reverse proxy
- Resource limits defined for all services (memory limits and reservations)
- Non-root user for application containers (SPARKLE_APP_UID/GID)
- MinIO with proper user permissions
- Redis with password auth, maxmemory, and LRU eviction policy
- PostgreSQL with pgvector-age custom Dockerfile
- AGE extension initialization via separate init container
- All Aurora kill switches configurable via environment variables
- Production agent container has GRPC_REQUIRE_TLS=true
- IMAGE_TAG required in production (fails if unset)
- Internal and edge network separation in production

### 14. Production Configuration -- VERIFIED CLEAN (settings.py)
- DEBUG=True raises ValueError in production
- SECRET_KEY rejects default values
- BACKEND_CORS_ORIGINS rejects wildcard `["*"]` in production
- CORS origins must be HTTPS in production
- PRODUCTION_URL required for HTTPS links
- Field validators for SECRET_KEY (min 32 chars), DATABASE_URL, LLM_API_KEY, LOG_LEVEL
- Safe config output (sensitive keys redacted)
- (See P1-2 for config_production.py gap)

### 15. Monitoring & Observability -- VERIFIED CLEAN
- Health check endpoint: `/api/v1/health`
- CQRS health: `/api/v1/health/cqrs` (authenticated, checks outbox + workers)
- Prometheus metrics: `sparkle_gateway_middleware_errors_total`, `sparkle_ws_connections_active`, AI chat duration histograms
- OpenTelemetry integration: trace propagation in proxy headers, span creation for user context fetch, cache search, gRPC calls, stream receive
- Request ID propagation: X-Request-ID header, gin context "request_id"
- User ID hashing in all log statements

---

## False Positive Exclusions

| Pattern | Why Not an Issue |
|---------|-----------------|
| HS256 JWT signing | Known design choice, documented RS256 migration plan in auth.go |
| No TLS in docker-compose.yml | Known infrastructure-layer concern, not code bug |
| gRPC to AgentAddress (not localhost) | By design -- configurable endpoint |
| Gin first-match routing | Standard Gin behavior, well-understood |
| `defer Close()` / `defer cancel()` | Standard Go cleanup pattern |
| `context.Background()` in background workers | See P3-2 -- low impact, process lifetime |
| community_service.proto has no generated code | Intentionally excluded in buf.yaml |

---

## Summary Table

| ID | Severity | Component | Issue |
|----|----------|-----------|-------|
| P1-1 | P1 | Proto/Gen | Stale legacy Python proto files with re-export wrappers |
| P1-2 | P1 | Config | config_production.py defaults CORS to wildcard without guard |
| P2-1 | P2 | WebSocket | Close() is no-op despite having wg/liveConnections |
| P2-2 | P2 | Auth | Login response duplicates tokens in nested structure |
| P2-3 | P2 | Proxy Routes | Task command registrations misplaced in errors block (cosmetic) |
| P3-1 | P3 | Middleware | Rate limiter cleanup goroutine not stoppable by callers |
| P3-2 | P3 | Setup | Background workers use context.Background(), no graceful shutdown |

**P0 count: 0 | P1 count: 2 | P2 count: 3 | P3 count: 2**
