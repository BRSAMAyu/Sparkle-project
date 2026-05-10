# Gateway & Cross-Layer Integration Audit

**Date**: 2026-05-10
**Auditor**: Senior Platform Engineer
**Scope**: Go Gateway, Proto Parity, Cross-Layer Integration, Infrastructure, Security, Database
**Status**: 15 findings (0 P0, 5 P1, 6 P2, 4 P3)

---

## Automated Checks

| Check | Result |
|-------|--------|
| `go build ./...` | PASS |
| `go vet ./...` | PASS (0 issues) |
| `go test ./...` | PASS (all packages, 0 failures) |
| Proto RPC parity (Go client vs Python server) | PASS (17/17 RPCs) |
| Generated Go code matches proto definitions | PASS |
| DB schema indexes | PASS (1,071 indexes, good coverage on hot paths) |

---

## Findings

### [G-001] Production docker-compose missing ENVIRONMENT for gateway services
- **Severity**: P1 (critical)
- **File**: `docker-compose.prod.yml` lines 89-187
- **Description**: The `gateway_blue` and `gateway_green` service definitions do not set `ENVIRONMENT=production`. Without this, the gateway defaults to development mode (`IsDevelopment()` returns true), which disables critical security validations: insecure JWT secret is accepted, `ALLOW_WS_QUERY_TOKEN` defaults to true, `REDIS_FAIL_CLOSED` is forced to false, admin secret validation is skipped, and `AGENT_TLS_INSECURE` is allowed.
- **Impact**: The gateway will run in development mode in production, bypassing all production safety guards. Tokens with insecure secrets will be accepted, WebSocket query-token auth is enabled (token visible in URLs/server logs), and Redis fail-closed is disabled.
- **Fix Context**: Add `ENVIRONMENT=production` to both gateway service blocks in `docker-compose.prod.yml`:

```yaml
  gateway_blue:
    # ... existing config ...
    environment:
      - ENVIRONMENT=production  # ADD THIS LINE
      - PORT=8080
      - DATABASE_URL=${DATABASE_URL}
      # ... rest of env vars ...
```

Repeat for `gateway_green` (around line 139).

---

### [G-002] Production docker-compose missing critical gateway env vars
- **Severity**: P1 (critical)
- **File**: `docker-compose.prod.yml` lines 89-187
- **Description**: The gateway services in production docker-compose are missing several critical environment variables that have production-specific defaults or are required:
  - `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` -- required for RS256 signing/verification
  - `REDIS_FAIL_CLOSED=true` -- without this, token validation fails open on Redis errors
  - `ALLOWED_ORIGINS` -- without this, the gateway uses the dev default (`https://sparkle.app,https://api.sparkle.app`)
  - `TRUSTED_PROXIES` -- the gateway calls `logger.Fatal()` if this is unset in production, causing immediate crash
  - `ENVIRONMENT=production` (covered in G-001)
  - `ALLOW_WS_QUERY_TOKEN=false` -- explicit production override
  - `AGENT_TLS_ENABLED` / `AGENT_TLS_*` -- production should have TLS for gRPC

  The `.env.production.example` file also lacks `TRUSTED_PROXIES` and `ALLOWED_ORIGINS` entries, meaning deployers have no template to follow.
- **Impact**: The gateway will crash on startup with `TRUSTED_PROXIES not set in production`. If it doesn't crash (e.g., if TRUSTED_PROXIES is set but these others aren't), it will accept insecure JWT secrets and skip TLS verification for gRPC.
- **Fix Context**: Add the following to both `gateway_blue` and `gateway_green` environment blocks in `docker-compose.prod.yml`:

```yaml
      - ENVIRONMENT=production
      - REDIS_FAIL_CLOSED=true
      - TRUSTED_PROXIES=${TRUSTED_PROXIES}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - JWT_PRIVATE_KEY=${JWT_PRIVATE_KEY}
      - JWT_PUBLIC_KEY=${JWT_PUBLIC_KEY}
      - JWT_ISSUER=${JWT_ISSUER:-sparkle-gateway}
      - JWT_AUDIENCE=${JWT_AUDIENCE:-sparkle-app}
      - ALLOW_WS_QUERY_TOKEN=false
      - AGENT_TLS_ENABLED=${AGENT_TLS_ENABLED:-true}
      - AGENT_TLS_CA_CERT=${AGENT_TLS_CA_CERT:-}
      - AGENT_TLS_SERVER_NAME=${AGENT_TLS_SERVER_NAME:-}
      - CORS_ENABLED=${CORS_ENABLED:-true}
```

Also add these entries to `.env.production.example`:
```
# Gateway security
TRUSTED_PROXIES=10.0.0.1/32  # Your load balancer IP/CIDR
ALLOWED_ORIGINS=https://sparkle.example.com,https://app.sparkle.example.com
```

---

### [G-003] .env.production.example missing TRUSTED_PROXIES and ALLOWED_ORIGINS
- **Severity**: P1 (critical)
- **File**: `.env.production.example`
- **Description**: The production environment template file does not include `TRUSTED_PROXIES` or `ALLOWED_ORIGINS` variables. The gateway code at `setup.go:448-451` calls `logger.Fatal("TRUSTED_PROXIES not set in production")` when these are missing and environment is production. The config defaults for `ALLOWED_ORIGINS` are `https://sparkle.app,https://api.sparkle.app` which won't match actual production domains.
- **Impact**: Deployers following the template will either get a crash (missing TRUSTED_PROXIES) or have CORS/origin validation that blocks all real clients (wrong ALLOWED_ORIGINS).
- **Fix Context**: Add to `.env.production.example` in the Gateway section:

```
# Gateway Production Configuration
TRUSTED_PROXIES=<your-load-balancer-ip-or-cidr>
ALLOWED_ORIGINS=https://your-production-domain.com
ALLOW_WS_QUERY_TOKEN=false
REDIS_FAIL_CLOSED=true
```

---

### [G-004] WebSocket proxy connection tracking is per-process (multi-instance gap)
- **Severity**: P2 (important)
- **File**: `backend/gateway/internal/handler/websocket_proxy.go` lines 49-66, 500-537
- **Description**: The `activeByUser` map and `reconnectTrackers` are local to each gateway process. In the production setup (`docker-compose.prod.yml`), there are two gateway instances (`gateway_blue` and `gateway_green`) behind nginx. A user could open connections on both instances, each counting separately, effectively doubling the per-user connection limit. The reconnect rate limiter has the same issue.
- **Impact**: In production with blue/green gateway instances, the per-user WebSocket connection limit (`WS_MAX_CONNECTIONS_PER_USER=2`) is only enforced per-instance. A user can hold 4 connections (2 per instance) instead of 2. The reconnect rate limiter is also bypassable across instances.
- **Fix Context**: The code already acknowledges this (comment on line 49-53). For single-instance deployments this is fine. For multi-instance, add Redis-backed atomic counters:

```go
// In registerConnection, use Redis INCR/DECR:
func (p *WebSocketProxy) registerConnection(userID string) bool {
    if p.rdb != nil {
        key := fmt.Sprintf("ws:conn:%s", userID)
        count, err := p.rdb.IncR(ctx, key).Result()
        if err == nil && count > maxConns {
            p.rdb.Decr(ctx, key)
            return false
        }
        p.rdb.Expire(ctx, key, 24*time.Hour)
    }
    // ... existing local tracking ...
}
```

---

### [G-005] Rate limiter cleanup goroutine leak when RateLimiter is created but never stopped
- **Severity**: P2 (important)
- **File**: `backend/gateway/internal/middleware/rate_limit.go` lines 39-57, 182-186, 228-254
- **Description**: `NewRateLimiter` starts a background goroutine (`cleanupVisitors`) that runs indefinitely. The `Stop()` method exists but is never called for any of the rate limiters created by `IPBasedRateLimit`, `UserBasedRateLimit`, `EndpointSpecificRateLimit`, `AdaptiveRateLimitMiddleware`, and `WebSocketRateLimitMiddleware`. Each middleware instantiation leaks one goroutine per unique rate limiter.
- **Impact**: In a long-running production process, these goroutines accumulate (one per middleware instance that creates a local `RateLimiter`). With the adaptive middleware creating 3 rate limiters, and multiple middleware registrations per route group, this could mean 10-20 leaked goroutines that run forever. Each holds a ticker and a map. Not a crash risk, but a slow resource leak.
- **Fix Context**: Either call `Stop()` during shutdown, or use a singleton pattern for rate limiters that are shared across routes:

```go
// In setup.go, create rate limiters and defer Stop():
apiRL := middleware.NewRateLimiter(rate.Limit(10), 30)
defer apiRL.Stop()
api.Use(middleware.RateLimitMiddleware(apiRL))
```

---

### [G-006] WS ticket stores raw JWT token in Redis
- **Severity**: P2 (important)
- **File**: `backend/gateway/internal/handler/ws_ticket.go` lines 43-46, 57-58
- **Description**: When issuing a WebSocket ticket, the handler stores the raw JWT token in Redis under `ws:ticket:{uuid}`. The ticket is a one-time-use credential (GETDEL in `ws_auth.go` line 19-24), but during its TTL window (default 120 seconds), the JWT is stored in plaintext in Redis. If Redis is compromised or there's a Redis injection vulnerability, all pending WS tickets expose valid JWT tokens.
- **Impact**: A Redis compromise exposes active JWT access tokens for up to 120 seconds. These tokens can be used to impersonate users for any authenticated API call, not just WebSocket connections.
- **Fix Context**: Option A: Don't store the token at all in the ticket, and have the WS auth middleware re-validate via Redis user session instead. Option B: Encrypt the token before storing in Redis:

```go
// Instead of storing raw token:
if authToken != "" {
    encryptedToken, err := encrypt(authToken, cfg.TicketEncryptionKey)
    if err != nil {
        // handle error
    }
    payload["token"] = encryptedToken
}
```

---

### [G-007] Proxy routes: task routes incorrectly nested under errors group scope
- **Severity**: P2 (important)
- **File**: `backend/gateway/internal/handler/proxy_routes.go` lines 117-149
- **Description**: In the `RegisterProxyRoutes` function, lines 125-148 register task-related routes (`tasks.POST("/:id/generate-guide", ...)`, etc.) inside the `errors` group's scope block. In Go, this is functionally correct because the `tasks` variable was defined earlier and these calls still register on the `tasks` group. However, this is confusing and error-prone. The comment on line 117 says "Error Book Extended Routes" but the routes inside are task lifecycle operations.
- **Impact**: Currently functional but misleading. If someone refactors and changes the variable scope (e.g., using `errors.POST` instead of `tasks.POST`), task routes would break silently by being mounted under `/api/v1/errors/` instead of `/api/v1/tasks/`.
- **Fix Context**: Move the task lifecycle routes (lines 125-148) out of the `errors` block and into the `tasks` block (lines 79-115):

```go
// ==================== Tasks Routes ====================
tasks := api.Group("/tasks")
tasks.Use(authMiddleware)
{
    // ... existing routes ...
    // Task lifecycle operations (moved from errors block)
    tasks.POST("/:id/generate-guide", h.proxyWithHeaders)
    tasks.POST("/:id/start", h.proxyWithHeaders)
    tasks.POST("/:id/complete", h.proxyWithHeaders)
    // ... etc ...
}

// ==================== Error Book Extended Routes ====================
errors := api.Group("/errors")
errors.Use(authMiddleware)
{
    errors.GET("/remediable-patterns", h.proxyWithHeaders)
    errors.POST("/patterns/:pattern_id/generate-template", h.proxyWithHeaders)
    errors.POST("/patterns/:pattern_id/accept-template", h.proxyWithHeaders)
}
```

---

### [G-008] Gateway Redis connection not configured with ACL user in production
- **Severity**: P1 (critical)
- **File**: `docker-compose.prod.yml` lines 94-101, `backend/gateway/internal/config/config.go` line 728
- **Description**: In the production compose file, Redis is configured with ACL users (`gateway`, `engine`, `celery`) with different key pattern permissions. The gateway service sets `REDIS_URL` and `REDIS_PASSWORD` but uses the default/gateway password. However, the Go Redis client connects using `redis.NewClient()` with the URL `host:port` format (see config normalization at line 728), which does not specify a username. Redis ACL requires the `gateway` username to access keys prefixed with `gateway:`, `chat:`, `session:`, etc. Without a username, the client authenticates as `default`, which has `~* +@all` access, bypassing the ACL isolation entirely.
- **Impact**: The Redis ACL isolation designed for production is ineffective. The gateway has full access to all Redis keys (including engine keys, celery queues, etc.) instead of being restricted to its own key namespace.
- **Fix Context**: Update the gateway's Redis URL to include the username:

```yaml
# In docker-compose.prod.yml gateway services:
- REDIS_URL=redis://gateway:${SPARKLE_GATEWAY_REDIS_PASSWORD}@redis:6379/0
```

Also update `config.go` normalization to handle `redis://` URLs properly, or add a `REDIS_USERNAME` config field.

---

### [G-009] No request body size limit on proxy routes
- **Severity**: P2 (important)
- **File**: `backend/gateway/cmd/server/setup.go` lines 537-564
- **Description**: The `/api/v1` route group applies rate limiting and timeout middleware but does not set a maximum request body size for proxied routes. The reverse proxy will forward any size request to the Python backend. While individual endpoints (file uploads) have size limits, general proxy routes like `/api/v1/users/*path`, `/api/v1/community/*`, etc. accept unlimited body sizes.
- **Impact**: A malicious or buggy client could send extremely large JSON payloads to any proxy endpoint, consuming gateway memory and potentially causing OOM before the Python backend processes the request.
- **Fix Context**: Add a body size limit middleware to the API group:

```go
// In setup.go, add to the api group:
api.Use(func(c *gin.Context) {
    c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 10*1024*1024) // 10MB
    c.Next()
})
```

---

### [G-010] Development-mode upgrader fallback in ChatOrchestrator
- **Severity**: P3 (minor)
- **File**: `backend/gateway/internal/handler/chat_orchestrator.go` lines 212-223
- **Description**: When `wsFactory` is nil (which shouldn't happen in production), the code falls back to a development upgrader with a warning log. This fallback should never be reached in production, but there's no hard fail -- it just logs a warning and proceeds with an insecure upgrader.
- **Impact**: If the WebSocketFactory is accidentally not initialized, the gateway silently accepts connections without origin checking. The log warning might be missed.
- **Fix Context**: In non-development environments, return an error instead of falling back:

```go
} else {
    if !isDevelopmentEnv() {
        log.Printf("[ERROR] WebSocketFactory missing in non-development environment")
        c.AbortWithStatusJSON(http.StatusInternalServerError, gin.H{"error": "WebSocket configuration error"})
        return
    }
    // ... existing fallback ...
}
```

Note: The existing code at lines 215-218 already does this check, so this is functioning correctly. Downgrading to P3 as the protection is already in place.

---

### [G-011] Local rate limiter maps grow unbounded when Redis is unavailable
- **Severity**: P2 (important)
- **File**: `backend/gateway/internal/middleware/rate_limit.go` lines 258-316, `distributed_rate_limiter.go` lines 289-307
- **Description**: When Redis is unavailable, the hybrid rate limiter falls back to a local `RateLimiter`. Each `HybridRateLimitMiddlewareSimple` call creates a new local `RateLimiter` with `maxVisitors=10000`. With multiple middleware instances, this creates multiple independent maps that each can hold up to 10,000 visitors. Under sustained Redis outage with high traffic, the combined memory usage could grow significantly (worst case: ~10 rate limiters x 10,000 visitors each = 100,000 entries across maps).
- **Impact**: During a Redis outage, memory usage for rate limiting could spike. The eviction policy (`evictOldest`) only triggers when `maxVisitors` is exceeded per individual limiter, so total memory is the sum of all limiters.
- **Fix Context**: Use shared rate limiter instances for fallback instead of creating one per middleware. Or reduce `maxVisitors` for per-endpoint limiters:

```go
const fallbackMaxVisitors = 2000 // Lower than default for shared fallback

func HybridRateLimitMiddlewareSimple(rdb *redis.Client, rps float64, burst int) gin.HandlerFunc {
    localRL := NewRateLimiterWithMax(rate.Limit(rps), burst, fallbackMaxVisitors)
    // ...
}
```

---

### [G-012] CORS middleware doesn't set Vary header when origin is not allowed
- **Severity**: P3 (minor)
- **File**: `backend/gateway/internal/middleware/cors.go` lines 10-30
- **Description**: When the origin is not in the allowed list, the middleware does not set the `Vary: Origin` header. This means a CDN or reverse proxy could cache a response without CORS headers and serve it to a legitimate origin, or vice versa.
- **Impact**: Minimal in practice because nginx handles TLS termination and the gateway is behind it. But it violates HTTP caching best practices.
- **Fix Context**: Always set `Vary: Origin`:

```go
func CORSMiddleware(cfg *config.Config) gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Header("Vary", "Origin")  // Always set
        origin := c.GetHeader("Origin")
        if origin != "" && cfg.IsOriginAllowed(origin) {
            c.Header("Access-Control-Allow-Origin", origin)
            // ... rest of CORS headers ...
        }
        // ...
    }
}
```

---

### [G-013] WsAuth debug logging leaks request metadata in production
- **Severity**: P2 (important)
- **File**: `backend/gateway/internal/middleware/ws_auth.go` line 37-38
- **Description**: The `WsAuthMiddleware` logs every WebSocket connection attempt at `log.Printf` level with client IP, request path, origin, and upgrade header. This logging has no environment check -- it runs in production too. While it doesn't log tokens, it creates verbose logs that could be used for reconnaissance (IP addresses, paths, origins of all WS connections).
- **Impact**: Excessive logging in production. The structured logging (`zap`) is used elsewhere but this middleware uses `log.Printf`. Log volume could be significant under load. IP addresses in logs may have GDPR/privacy implications.
- **Fix Context**: Replace with structured zap logging behind an environment check:

```go
if cfg.IsDevelopment() {
    zap.L().Debug("WS auth request",
        zap.String("path", c.Request.URL.Path),
        zap.String("client_ip", c.ClientIP()),
    )
}
```

---

### [G-014] Production docker-compose gateway uses AGENT_ADDRESS without TLS
- **Severity**: P1 (critical)
- **File**: `docker-compose.prod.yml` lines 89-187
- **Description**: Both `gateway_blue` and `gateway_green` set `AGENT_ADDRESS=agent:50051` without any TLS configuration. The Python agent service sets `GRPC_REQUIRE_TLS=true` in production, which means it will reject plaintext connections. The gateway's gRPC client will fail to connect because it defaults to `insecure.NewCredentials()` when `AGENT_TLS_ENABLED` is not set (defaults to false).
- **Impact**: The gateway cannot communicate with the Python gRPC agent service in production. All chat functionality, plan reviews, memory retrieval, and every other gRPC-dependent feature will fail with connection errors.
- **Fix Context**: Add TLS configuration to the gateway services in `docker-compose.prod.yml`:

```yaml
      - AGENT_ADDRESS=agent:50051
      - AGENT_TLS_ENABLED=true
      - AGENT_TLS_CA_CERT=/run/secrets/grpc_ca.crt
      - AGENT_TLS_SERVER_NAME=sparkle-agent
```

And mount the TLS secrets via Docker secrets or volume mounts.

Alternatively, if using a service mesh (like Istio/Linkerd) that handles mTLS, set `AGENT_TLS_ENABLED=false` but ensure the mesh is configured for automatic mTLS.

---

### [G-015] chat_orchestrator logs raw user ID hash without context
- **Severity**: P3 (minor)
- **File**: `backend/gateway/internal/handler/chat_orchestrator.go` line 307
- **Description**: `log.Printf("WebSocket connected for user: %s", hashUserIDForLog(userID))` uses the standard `log` package instead of the structured `zap` logger used everywhere else. This bypasses the logging infrastructure (no trace IDs, no structured fields, no log level control). Several other places in the handler package use `log.Printf` as well (lines 300, 310, 369, etc.).
- **Impact**: Inconsistent logging makes it harder to correlate logs with traces in production. Standard `log` output doesn't go through the otel/log pipeline and won't appear in Loki/Grafana with proper labels.
- **Fix Context**: Replace all `log.Printf` calls in the handler package with `zap.L().Info/Warn/Error`:

```go
// Before:
log.Printf("WebSocket connected for user: %s", hashUserIDForLog(userID))

// After:
zap.L().Info("WebSocket connected",
    zap.String("user_id_hash", hashUserIDForLog(userID)))
```

---

## Summary Table

| ID | Severity | Title | Component |
|----|----------|-------|-----------|
| G-001 | **P1** | Production compose missing ENVIRONMENT for gateway | docker-compose.prod.yml |
| G-002 | **P1** | Production compose missing critical gateway env vars | docker-compose.prod.yml |
| G-003 | **P1** | .env.production.example missing TRUSTED_PROXIES and ALLOWED_ORIGINS | .env.production.example |
| G-004 | **P2** | WebSocket per-user limits not enforced across instances | websocket_proxy.go |
| G-005 | **P2** | Rate limiter cleanup goroutines never stopped | rate_limit.go |
| G-006 | **P2** | WS ticket stores raw JWT in Redis | ws_ticket.go |
| G-007 | **P2** | Task routes incorrectly scoped under errors group | proxy_routes.go |
| G-008 | **P1** | Gateway Redis connection doesn't use ACL username | docker-compose.prod.yml |
| G-009 | **P2** | No request body size limit on proxy routes | setup.go |
| G-010 | **P3** | Development upgrader fallback in ChatOrchestrator (already guarded) | chat_orchestrator.go |
| G-011 | **P2** | Local rate limiter maps grow unbounded during Redis outage | rate_limit.go |
| G-012 | **P3** | CORS Vary header not set when origin disallowed | cors.go |
| G-013 | **P2** | WsAuth debug logging in production (uses log.Printf) | ws_auth.go |
| G-014 | **P1** | Production gateway uses plaintext gRPC (agent requires TLS) | docker-compose.prod.yml |
| G-015 | **P3** | chat_orchestrator uses log.Printf instead of zap | chat_orchestrator.go |

### Severity Breakdown

| Severity | Count | Blocking? |
|----------|-------|-----------|
| P0 (blocker) | 0 | -- |
| P1 (critical) | 5 | **Yes -- must fix before launch** |
| P2 (important) | 6 | Should fix, tracked post-launch |
| P3 (minor) | 3 | Can defer |

### Critical Path (P1 -- Launch Blockers)

1. **G-001 + G-002**: Production compose must include `ENVIRONMENT=production` and all security-critical env vars for gateway services.
2. **G-003**: Production env template must guide deployers to set `TRUSTED_PROXIES` and `ALLOWED_ORIGINS`.
3. **G-008**: Redis ACL isolation is bypassed without username in connection string.
4. **G-014**: Gateway cannot connect to agent service in production without TLS configuration.

### Positive Findings

- Go Gateway codebase is well-structured with comprehensive test coverage
- All 17 proto RPCs have matching Go client wrappers and Python server implementations
- Authentication middleware has proper fail-closed strategy, JWT RS256 support, and token blacklist checking (JTI, user-level, session-level)
- WebSocket proxy has proper rate limiting, message dedup, size limits, and graceful draining
- Security headers middleware covers CSP, HSTS, X-Frame-Options, and other OWASP recommendations
- Database schema has 1,071 indexes with good coverage on hot paths (user_id, session_id, created_at)
- Nginx configuration properly handles WebSocket upgrades, TLS termination, and upstream failover
- Rate limiter has Redis-backed distributed mode with local fallback
