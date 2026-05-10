# Cross-Layer Integration & Architecture Audit

**Date**: 2026-05-10
**Auditor**: Chief Architect (direct verification)
**Scope**: Go Gateway proxy routes, schema ownership, WebSocket security, CQRS conflicts, API contract verification

---

## Summary

| Severity | Count |
|----------|-------|
| P0       | 1     |
| P1       | 3     |
| P2       | 3     |
| P3       | 1     |
| **Total**| **8** |

---

## P0 Findings

### [P0-01] JWT Token Exposed in WebSocket URL Query String
**File**: `mobile/lib/features/community/data/services/community_websocket_service.dart:144,195`
**Category**: security
**Description**: The JWT access token is passed as a URL query parameter (`?token=$token`) for both group and personal WebSocket connections. This exposes the token in:
1. Server access logs (Nginx/Go Gateway)
2. Browser history (if web)
3. Proxy logs (CDN, load balancer)
4. Referrer headers

The Go Gateway's WebSocket proxy test (`websocket_proxy_test.go:45`) correctly asserts `!contains("token=")`, but the Flutter client still sends it this way. This suggests the proxy strips it server-side, but the token is already in the clear by then.
**Context**:
```dart
final wsUrl = '${ApiConstants.wsBaseUrl}/api/v1/community/groups/$groupId/ws?token=$token';
final wsUrl = '${ApiConstants.wsBaseUrl}/api/v1/community/ws/connect?token=$token';
```
**Suggested Fix**: Pass the token via WebSocket subprotocol negotiation or as an initial auth message after connection. The Go Gateway should accept the token from a header-based upgrade (via `Sec-WebSocket-Protocol` or initial message) rather than query string.

---

## P1 Findings

### [P1-01] Schema.sql Has 1606 Objects Owned by `brsama` vs 754 by `postgres`
**File**: `backend/gateway/internal/db/schema.sql`
**Category**: infrastructure
**Description**: 68% of database objects (tables, indexes, constraints, types, functions) are owned by the local development user `brsama` instead of `postgres`. This includes critical community tables like `accountability_policies`. In production, if the application connects as `postgres`, these objects will be accessible. But if a different DB user is used (e.g., `sparkle_app`), permission errors will occur for all `brsama`-owned objects. Additionally, `make sync-db` (pg_dump) preserves ownership, so this drift will propagate.
**Context**:
```
-- Name: accountability_policies; Type: TABLE; Schema: public; Owner: brsama
-- (1606 more objects with Owner: brsama)
-- Name: accountability_partnership; Type: TABLE; Schema: public; Owner: postgres
-- (754 more objects with Owner: postgres)
```
**Suggested Fix**: Run `REASSIGN OWNED BY brsama TO postgres` on the development database, then regenerate `schema.sql` via `make sync-db`. Add a CI check that rejects schema dumps with non-`postgres` owners.

### [P1-02] Go Gateway CommunityHandler CQRS Routes May Conflict with Proxy Routes
**File**: `backend/gateway/internal/api/v1/community.go:24-33` vs `backend/gateway/internal/handler/proxy_routes.go:528-535`
**Category**: architecture
**Description**: The Go Gateway has TWO separate handlers for community routes:
1. `CommunityHandler` (CQRS): Registers `POST /community/posts`, `POST /community/posts/:id/like`, `GET /community/feed` with local Go handlers that write to PostgreSQL + Redis
2. `ProxyRoutesHandler`: Registers the SAME routes (`GET /community/feed`, `POST /community/posts`, `POST /community/posts/:id/like`) that proxy to Python

However, `CommunityHandler.RegisterRoutes()` is never called in `setup.go` — only the proxy routes are registered. This means the CQRS handler is dead code that could cause confusion. The `CommunityCommandService`, `CommunityQueryService`, and `CommunityProjectionHandler` are all instantiated but only the projection handler is used.
**Context**:
```go
// community.go - CQRS handler (dead code)
func (h *CommunityHandler) RegisterRoutes(router *gin.RouterGroup, authMiddleware gin.HandlerFunc) {
    group := router.Group("/community")
    protected := group.Group("")
    protected.Use(authMiddleware)
    protected.POST("/posts", h.CreatePost)    // Go CQRS
    protected.POST("/posts/:id/like", h.LikePost) // Go CQRS
    group.GET("/feed", h.GetFeed)             // Go CQRS
}

// proxy_routes.go - actual routes used
community.GET("/feed", h.proxyWithHeaders)    // proxies to Python
community.POST("/posts", h.proxyWithHeaders)  // proxies to Python
community.POST("/posts/:id/like", h.proxyWithHeaders) // proxies to Python
```
**Suggested Fix**: Either remove `CommunityHandler`, `CommunityCommandService`, `CommunityQueryService` and their tests (since they are unused), or activate the CQRS path and remove the proxy routes for those endpoints. Document which path is canonical.

### [P1-03] Community Main Routes Not Fully Covered in Go Gateway Proxy
**File**: `backend/gateway/internal/handler/proxy_routes.go:444-569`
**Category**: architecture
**Description**: Comparing Go proxy routes with Python backend routes, several Python endpoints are missing from the Go proxy:
1. `GET /community/goals/{goalId}/similar-pursuers` — present in Flutter `api_endpoints.dart:362` and Python route exists, but NOT in Go proxy
2. `GET /community/recommended-resources` — Python route exists, NOT in Go proxy
3. `GET /community/resources` — Python route exists, NOT in Go proxy
4. `POST /community/shared-resources/{id}/flag-misleading` — Python route exists, NOT in Go proxy
5. `GET /community/messages/search` — present in Flutter `api_endpoints.dart:471`, NOT in Go proxy
6. `POST /community/messages/search/advanced` — NOT in Go proxy
7. `GET /community/admin/reports` — NOT in Go proxy (admin routes are catch-all though)
8. `PUT /community/admin/reports/{id}/resolve` — NOT in Go proxy (admin catch-all covers this)
9. `GET /community/groups/{group_id}/files/{file_id}/copy-to-library` — Flutter TODO, NOT in Go proxy
10. `GET /community/groups/{group_id}/flame` — in Go proxy but NOT in Python backend routes

The `similar-pursuers`, `recommended-resources`, `resources`, and `flag-misleading` endpoints will 404 at the Go Gateway level unless they fall through to the NoRoute handler.
**Suggested Fix**: Add missing proxy routes to `proxy_routes.go` for all Python endpoints that the Flutter client calls. Verify the NoRoute catch-all proxy handles these as a fallback.

---

## P2 Findings

### [P2-01] Proto community_service.proto Marked as Deprecated but Still Referenced
**File**: `proto/community_service.proto:1-10`
**Category**: dead-code
**Description**: The proto file has a comment marking it as deprecated in favor of REST/gateway CQRS, but it still contains 422 lines of service/message definitions. No generated Go or Python code from this proto is used in the actual implementation. The Flutter client communicates via REST (not gRPC) for all community features.
**Suggested Fix**: Either remove the proto file and document the REST API as the canonical contract, or keep it as documentation with a clear `// DEPRECATED` banner and no code generation.

### [P2-02] WebSocket Service Memory Leak: _receivedMessageIds Grows Unbounded to 1000
**File**: `mobile/lib/features/community/data/services/community_websocket_service.dart:89-90,329-331`
**Category**: performance
**Description**: The deduplication cache `_receivedMessageIds` caps at 1000 entries using FIFO removal (`_receivedMessageIds.remove(_receivedMessageIds.first)`). But `Set` in Dart does not guarantee insertion order — `first` returns an arbitrary element. This means the dedup cache may evict recent IDs while keeping old ones, causing false negatives (duplicate messages shown) or false positives (valid messages dropped).
**Context**:
```dart
final Set<String> _receivedMessageIds = {};
// ...
_receivedMessageIds.add(msgId);
if (_receivedMessageIds.length > _maxMessageCacheSize) {
  _receivedMessageIds.remove(_receivedMessageIds.first); // Set.first is arbitrary!
}
```
**Suggested Fix**: Use a `LinkedHashSet` instead of `Set` to maintain insertion order. Or use a `Queue<String>` with a `Set<String>` for O(1) lookup.

### [P2-03] AccountabilityPartnership UniqueConstraint Missing deleted_at Scope
**File**: `backend/app/models/accountability.py:90-95`
**Category**: logic
**Description**: The `UniqueConstraint("initiator_id", "partner_id")` does not exclude soft-deleted rows. After a partnership ends (soft-deleted), the same two users cannot create a new partnership because the unique constraint fails on the deleted row. The `request_partnership` API handler works around this by reusing ended partnerships (lines 940-951 of accountability.py), but this is fragile — it reuses the old row's `id`, breaking audit trails.
**Context**:
```python
UniqueConstraint(
    "initiator_id", "partner_id",
    name="uq_accountability_partnership_pair",
),  # no deleted_at IS NULL filter
```
**Suggested Fix**: Replace with a partial unique index: `Index("uq_partnership_active_pair", "initiator_id", "partner_id", unique=True, postgresql_where=text("deleted_at IS NULL"))`. This allows new partnerships after old ones are soft-deleted.

---

## P3 Findings

### [P3-01] CommunityWebSocketService.dispose() Is Async But Never Awaited
**File**: `mobile/lib/features/community/data/services/community_websocket_service.dart:476-483`
**Category**: dead-code
**Description**: The `dispose()` method is `async` and closes `StreamController`s, but it is likely called from `State.dispose()` which is synchronous. The `StreamController.close()` returns a `Future` but in a sync context, the stream may not be fully closed before the widget is garbage collected.
**Suggested Fix**: Make `dispose()` synchronous and call `streamController.close()` without awaiting (it's safe to not await in dispose).

---

## Architecture Observations

### 1. Dual Route Registration Pattern
The community system has a "belt and suspenders" approach:
- Go Gateway has explicit CQRS handler (`CommunityHandler`) — **unused**
- Go Gateway has proxy routes to Python — **active**
- Go Gateway has CQRS projection handler — **active** (reads events to update Redis read models)

This means community posts go: Flutter → Go Gateway (proxy) → Python (creates post) → Event Bus → Go projection worker (updates Redis). The CQRS read side (Go `CommunityQueryService`) is never called because the proxy routes send everything to Python.

### 2. Token-in-URL Anti-Pattern
Both WebSocket connections pass JWT in the URL. This is a known security anti-pattern. The Go test explicitly checks `!contains("token=")` on the backend URL, suggesting awareness of the issue, but the Flutter client hasn't been updated.

### 3. Missing Go Proxy Routes = Silent Failures
Several Flutter API calls will 404 at the Go Gateway unless the NoRoute handler catches them. This works in practice (NoRoute proxies to Python), but explicit routes provide better observability, rate limiting, and auth middleware guarantees.
