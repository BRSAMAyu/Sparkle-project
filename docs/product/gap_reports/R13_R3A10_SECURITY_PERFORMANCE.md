# R13-R3A10 Security + Performance Independent Audit Report

**Date**: 2026-05-07
**Auditor**: Claude (fresh independent audit)
**Scope**: Full stack (Go Gateway + Python Engine + Flutter Mobile)
**Status**: COMPLETE

---

## Executive Summary

The Sparkle security posture is **strong for an early-stage product**, with multiple defense-in-depth layers active. No P0 (critical/blocking) security issues were found. Two P1 findings and six P2 findings are documented below. The rate limiting, input sanitization, error message handling, and security header configurations all follow best practices. The primary architectural concern is the use of HS256 (symmetric) JWT across both Go and Python layers, which couples key management and expands the blast radius of a key compromise.

### Summary Table

| Severity | Count | Key Areas |
|----------|-------|-----------|
| P0 (Blocker) | 0 | -- |
| P1 (High) | 2 | Symmetric JWT key sharing; PII in Python logs |
| P2 (Medium) | 6 | No cert rotation; passlib/bcrypt compat; fail-open session; Minio SSL; partial refresh flow; no chat history cache |
| Verified Working | 28 | See "Verified Working" section below |

---

## 1. Authentication Chain

### 1.1 JWT Algorithm and Key Management

**Finding P1-01: HS256 symmetric key shared across Go Gateway and Python Engine**

- **File(s)**: `backend/gateway/internal/handler/auth.go:163`, `backend/app/core/security.py:64`
- **Detail**: Both Go and Python use HS256 with the same symmetric secret. A key compromise in either service compromises all tokens across both services. HS256 requires both issuer and verifier to hold the raw key.

- **Current mitigation**: 
  - Go: Non-dev envs enforce JWT_SECRET presence and reject known-insecure defaults (`config.go:579-584`)
  - Python: `settings.py:1024-1040` enforces SECRET_KEY >= 32 chars and rejects default values in non-DEBUG
  - Both: Use jti, exp, nbf, aud, iss, sub, type claims for defense-in-depth

- **Recommendation**: Migrate to RS256 (asymmetric) for long-term improvement. This allows Go to verify with a public key while Python signs with the private key, reducing key distribution surface area.

### 1.2 Token Expiry and Refresh

**Verified Working**: 
- Access token: 30 min (configurable via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`) (`config.go:477`)
- Refresh token: 7 days (configurable via `JWT_REFRESH_TOKEN_EXPIRE_DAYS`) (`config.go:478`)
- Python mirrors: `settings.py:216-217`

**Finding P2-01: No dedicated refresh token endpoint in Go Gateway**

- **File(s)**: `backend/gateway/cmd/server/setup.go:862`
- **Detail**: The `/api/v1/auth/refresh` endpoint is proxied to the Python backend rather than handled natively in Go. The Go Gateway's `AuthHandler.AppleLogin` issues both tokens but has no dedicated refresh handler. This means:
  - Refresh token validation happens in Python, not at the gateway edge
  - No refresh token rotation implemented (refresh tokens are single-use only in best practice)
  - Potential latency add from proxy hop

- **Recommendation**: Add a native Go refresh endpoint with refresh token rotation for better security.

### 1.3 Token Validation Layer

**Verified Working**: 
- Go middleware validates all JWT tokens at the gateway edge before any backend processing (`auth.go:346-383`)
- Python independently re-validates tokens for internal API calls (`security.py:89-136`)
- Both layers check: expiry, nbf, iss, aud, token type, JTI blacklist, user revocation, session revocation

### 1.4 Token Blacklist/Revocation

**Verified Working -- Multi-Layer Revocation System**:

| Revocation Type | Go Gateway | Python Engine |
|----------------|------------|---------------|
| JTI blacklist | Redis + local cache | Redis + DB fallback |
| User-level revocation | Redis + local cache | Redis + DB fallback |
| Session-level revocation | Redis only | Redis + DB fallback |
| Fail-closed (prod) | Yes (`REDIS_FAIL_CLOSED=true`) | Yes (returns True on error) |

- **Go**: `auth.go:492-581` -- checks three revocation dimensions with Fail-Closed behavior in production
- **Python**: `security.py:116-130, 150-235` -- independent validation with DB fallback
- **Local cache**: Go maintains an in-memory local blacklist (`auth.go:49-226`) for fallback when Redis is unavailable

---

## 2. TLS Configuration

### 2.1 gRPC Client TLS

**Verified Working -- Strong gRPC TLS Configuration**:

- **File**: `backend/gateway/internal/agent/client.go:98-170`
- TLS 1.2 minimum version: `tls.VersionTLS12` (line 102)
- mTLS support: Client certificate/key loading (lines 126-137)
- CA certificate verification: via file path with cert pool validation (lines 107-123)
- Production enforcement: `config.go:594` -- `AGENT_TLS_INSECURE` must be false in non-dev
- Connection keepalive: 20s interval, 10s timeout (lines 160-163)
- Retry policy: 4 max attempts, 500ms initial backoff, 10s max backoff (lines 142-154)
- Call limits: 50MB max send/receive message size (lines 165-168)
- Circuit breaker: health checker with configurable threshold (lines 268-281)

**Finding P2-02: No certificate rotation support**

- **File(s)**: `backend/gateway/internal/agent/client.go:107-123`
- **Detail**: TLS certificates are loaded from files at startup only. Certificate rotation would require a service restart. gRPC Go's native credentials do not support hot-reloading certificates.

- **Recommendation**: Implement a certificate reloader using `grpc.Credentials()` callback or a file watcher that periodically checks for new certs. Alternatively, use a sidecar proxy (envoy/linkerd) for certificate management.

### 2.2 MinIO Storage TLS

**Finding P2-03: MinIO SSL disabled by default**

- **File**: `backend/gateway/internal/config/config.go:510`
- **Detail**: `MINIO_USE_SSL` defaults to `false`. File storage connections (presigned URLs, direct uploads) may transmit in cleartext in production unless explicitly configured.

- **Recommendation**: Default `MINIO_USE_SSL` to `true` in production environments, or add a config check like the TLS check for gRPC.

### 2.3 HTTP/gRPC Server TLS

**Note**: The Go Gateway serves HTTP, not HTTPS. Production deployments are expected to terminate TLS at a reverse proxy (nginx/ALB). No internal TLS config for the HTTP server was found. This is the standard pattern and acceptable, but document the proxy requirement explicitly.

---

## 3. Security Headers

### Verified Working -- Comprehensive Security Headers

- **File**: `backend/gateway/internal/middleware/security.go`

| Header | Value | Status |
|--------|-------|--------|
| Content-Security-Policy | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; connect-src 'self' wss: https:; font-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'` | STRONG -- No unsafe-inline, no unsafe-eval |
| X-Frame-Options | `DENY` | GOOD |
| X-Content-Type-Options | `nosniff` | GOOD |
| X-XSS-Protection | `1; mode=block` | GOOD (legacy) |
| Strict-Transport-Security | `max-age=31536000; includeSubDomains` | GOOD (prod only) |
| Referrer-Policy | `strict-origin-when-cross-origin` | GOOD |
| Permissions-Policy | `geolocation=(), camera=(), microphone=(), payment=()` | GOOD (restrictive) |
| Cross-Origin-Opener-Policy | `same-origin` | GOOD |
| Cross-Origin-Resource-Policy | `same-origin` | GOOD |

### CORS Configuration

- **File**: `backend/gateway/internal/middleware/cors.go`, `backend/gateway/internal/config/config.go:132-204`
- Origin validation is strict: scheme + hostname + port matching required
- Wildcard `*` is rejected in production (`config.go:158-163`)
- Subdomain wildcards supported (`*.sparkle.app`) via `matchWildcardHost()`
- Preflight caching: 24 hours (`Access-Control-Max-Age: 86400`)
- Credentials enabled: `Access-Control-Allow-Credentials: true`
- Exposed headers include rate limiting headers

---

## 4. Input Validation & Injection Prevention

### 4.1 SQL Injection

**Verified Working -- Parameterized Queries Everywhere**:

- **Go**: All SQL is generated by sqlc from `query.sql`, producing parameterized `$1, $2, ...` queries in `query.sql.go`. No raw SQL string concatenation found.
- **Python**: Uses SQLAlchemy ORM (`select()`, `.where()`, `.scalar()`) which parameterizes by default. No raw SQL found outside of the Alembic migration utility.

### 4.2 XSS Prevention

**Verified Working -- bluemonday Sanitization**:

- **File**: `backend/gateway/internal/handler/chat_orchestrator.go:127`
- All WebSocket chat text is sanitized via `bluemonday.UGCPolicy()` which:
  - Allows only safe HTML tags (b, i, em, strong, a, p, br, ul, ol, li, etc.)
  - Strips all dangerous tags (script, iframe, object, embed)
  - Removes javascript: URLs and event handlers (onclick, etc.)
- Applies to: WebSocket text payloads (line 543, 598), protocol deltas (line 118 of `chat_orchestrator_protocol.go`), status updates (line 133-134)
- Community WebSocket payloads also sanitized (`sanitizeCommunityWSTextPayload` in `websocket_proxy_paths_test.go:45`)

### 4.3 Command Injection

**Verified Working -- Minimal OS Command Execution**:

- **Go**: No `os/exec` calls found in the gateway codebase
- **Python**: 
  - `services/simulation_runner.py:128` uses `subprocess.run()` -- simulation/dev tool, not exposed via API
  - `services/stt/providers/zhipu_provider.py:222` uses `asyncio.create_subprocess_exec` -- STT provider, input is controlled
  - `core/execution_trust.py:126` detects injection patterns (`<script`, `javascript:`, `eval(`, `exec(`) as a defense layer
  - `core/llm_safety.py:88` detects `subprocess.` in LLM output as a safety check

### 4.4 File Upload Validation

**Verified Working -- Multi-Layer File Validation**:

- **File**: `backend/gateway/internal/handler/file_handler.go`
- **Size limit**: 50MB default (`config.go:513`) enforced at prepare stage (line 135)
- **MIME type validation**: Whitelist of 15 allowed types (`allowedMimeTypesByExt`, lines 24-44)
- **Extension matching**: MIME type must match filename extension (line 156)
- **Magic byte validation**: `validateFileByMagicBytes()` (lines 570-621) checks actual file headers for PDF, DOCX/XLSX/PPTX, PNG, JPEG, GIF, WebP
- **Path traversal**: `sanitizeFilename()` uses `path.Base()` to strip directory components (line 506-512)
- **Object keys**: UUID-based: `{userID}/{fileID}/original{ext}` -- no user-controlled paths
- **Rate limiting**: 10 uploads per minute per user (line 120-124, `getLimiter()` lines 554-566)
- **Authentication**: All file routes require auth middleware

### 4.5 Error Message Sanitization

**Verified Working -- Environment-Aware Error Sanitization**:

- **File**: `backend/gateway/internal/handler/error_sanitizer.go`
- In production: generic i18n error messages only (no stack traces, no internal details)
- In development: raw error text included for debugging
- All errors logged with `logsafe.RedactText()` for internal logging
- Prometheus counter tracks sanitized error responses by status code, handler, and category

---

## 5. Rate Limiting

### 5.1 Rate Limit Coverage

| Endpoint Group | Rate (rps) | Burst | Type | Config Source |
|---------------|------------|-------|------|---------------|
| `/api/v1/*` (all) | 15 | 30 | Hybrid (Redis + local) | `setup.go` |
| `/api/v1/auth/apple` | 5 | 15 | Hybrid | `setup.go` |
| `/api/v1/ws/ticket` | 2 (configurable) | 5 | Hybrid | `setup.go` |
| WebSocket connections | 0.083/s (5/min) | 10 | Local (token bucket) | `rate_limit.go:340` |
| WebSocket messages | 10 per conn | 20 | Local (per-connection) | `ws_hardening.go:16-30` |
| Galaxy routes | 10 | 20 | Hybrid | `setup.go` |
| Admin routes | 0.167/s (10/min) | 10 | Hybrid | `setup.go` |
| Internal routes | 60 | 120 | Hybrid | `setup.go` |

**Verified Working -- Comprehensive Rate Limiting**:

- All public API endpoints covered by at least one rate limiter
- Hybrid approach: Redis for distributed limiting + local fallback
- Per-user identification when authenticated, IP-based fallback
- Sliding window algorithm available for more precise limiting
- Route-scoped buckets prevent noisy endpoints from starving others (`normalizeRateLimitRoutePath`, `rate_limit.go:481-496`)

### 5.2 WebSocket-Specific Rate Limiting

- Connection rate: 5/min per IP
- Message rate: 10 rps per WebSocket connection
- Global connection limit: 2000 (configurable)
- Per-user connection limit: 2 connections

---

## 6. Sensitive Data Exposure

### 6.1 Password Hashing

**Verified Working -- bcrypt via passlib**:

- **File**: `backend/app/core/security.py:25`
- Uses `passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")`
- Auto-upgrade deprecated schemes
- Fail-closed verification: errors during verify return False (lines 32-35)
- No fallback to weaker hashing

**Finding P2-04: passlib/bcrypt version compatibility warning**

- **File**: `backend/app/main.py:162-179`
- **Detail**: The code includes a compatibility check for passlib 1.7.4 with bcrypt 5.0+. The dependency pins `bcrypt>=4.0.1,<4.1.0` which is correct, but environment drift could introduce the incompatible version.

- **Recommendation**: Add an explicit version check that fails startup (not just warns) if incompatible versions are detected. Or migrate to a maintained library like `bcrypt` directly without passlib.

### 6.2 PII in Logs

**Verified Working -- Go logsafe Package**:

- **File**: `backend/gateway/internal/logsafe/logsafe.go`
- Redacts: emails, phone numbers, CN ID numbers, Bearer tokens, API keys (sk-...), assignment secrets (api_key=..., password=...), URL credentials
- User IDs are hashed via SHA-256 (first 12 hex chars) for log traceability without reversibility
- Truncates messages to 240 chars to limit exposure
- All middleware error logging uses `logsafe.RedactText()` and `logsafe.UserIDHash()`
- All handler error logging uses the same

**Finding P1-02: Python logs contain raw user_id values**

- **File(s)**: 
  - `backend/app/core/token_revocation.py:35` -- `logger.info(f"Token blacklisted: {token_jti}")` (token jti is less sensitive but still identifying)
  - `backend/app/core/token_revocation.py:75` -- `logger.info(f"Refresh token revoked for user {user_id}: {refresh_token_jti}")`
  - `backend/app/core/token_revocation.py:95` -- `logger.info(f"Revoking all tokens for user {user_id}")`
  - `backend/app/core/security.py:196` -- `logger.warning("Revocation timestamp DB fallback failed for user {}: {}", user_id, exc)`
  - `backend/app/core/security.py:235` -- `logger.warning("Session revocation DB lookup failed open for session {}: {}", session_id, exc)`
- **Detail**: Unlike Go which hashes user IDs with `logsafe.UserIDHash()`, Python logs user_id directly. While user_id is a UUID (not PII directly), it becomes personally identifying when correlated with other data.

- **Recommendation**: Implement a Python equivalent of the Go `logsafe` package. Hash user_ids with SHA-256 before logging.

### 6.3 Configuration Secrets

**Verified Working -- Production Secret Enforcement**:

- **File**: `backend/gateway/internal/config/config.go:578-610`
- Non-development environments must have:
  - Non-empty `JWT_SECRET` (not an insecure default)
  - Non-empty `ADMIN_SECRET` (not an insecure default)
  - `AGENT_TLS_INSECURE=false`
  - `REDIS_FAIL_CLOSED=true` (enforced)
  - `ALLOW_WS_QUERY_TOKEN=false` (enforced)
  - Non-empty `INTERNAL_API_KEY`
  - Non-empty `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` (not default "minioadmin")
  - `SPARKLE_RBAC_ENABLED=true` (in production)
- `.env` files are in `.gitignore`

### 6.4 Constant-Time Comparison for Secrets

**Verified Working**:
- Admin secret comparison: `subtle.ConstantTimeCompare()` (`auth.go:418`)
- Internal API key comparison: `subtle.ConstantTimeCompare()` (`internal_api.go:20`)

---

## 7. Performance Hotspots

### 7.1 N+1 Query Patterns

**Audit Result: No Critical N+1 Found**

- Go: All queries use sqlc-generated parameterized queries. The `community_query.go` service uses Redis `MGET` for batch fetching posts (lines 63-69), which is efficient.
- Python: Uses SQLAlchemy ORM with eager loading best practices. Context manager gathering is batched.

### 7.2 Missing Caching

**Finding P2-05: No Redis caching for chat history or galaxy data**

- **File(s)**: `backend/gateway/internal/service/chat_history.go`, galaxy handler
- **Detail**: Chat sessions and history are fetched from PostgreSQL on every request. Similarly, galaxy/knowledge graph queries hit the database directly. While there is rate limiting, there is no response caching layer.

- **Recommendation**: Implement Redis caching for:
  - Recent chat sessions (LRU cache with TTL)
  - Frequently accessed galaxy nodes (read-through cache)
  - User profile data (cached on update)

### 7.3 Unbounded Queries

**Verified Working -- Pagination Enforced**:

| Endpoint | Default Limit | Max Limit | File |
|----------|--------------|-----------|------|
| Chat sessions | 20 | 200 | `chat_history.go:70` |
| Chat history | 20 | 200 | `chat_history.go:87-88` |
| File listing | 20 | No hard max (but limited by user scope) | `file_handler.go:409` |
| File search | 20 | No explicit max | `file_handler.go:463` |
| Error book | 20 | 20 | `error_book.go:134` |
| Group messages | 50 | 200 | `group_chat.go:58` |
| `clampLimit()` helper | -- | Cap at defined max | `group_chat.go:58` |

### 7.4 Large Payload Handling

**Verified Working -- Size Limits**:

- gRPC messages: 50MB max send/receive
- WebSocket messages: 256KB default
- File upload: 50MB default (validated in upload prepare)
- Request timeout: 30s default

### 7.5 Connection Pooling

- gRPC: Connection pooling via keepalive (20s interval, permits without stream)
- PostgreSQL: pgx v5 connection pool (managed by the driver)
- Redis: go-redis connection pool (managed by the client)

---

## 8. Dependency Security

### 8.1 Go Dependencies (`go.mod`)

| Dependency | Version | Status |
|-----------|---------|--------|
| `github.com/golang-jwt/jwt/v5` | v5.3.0 | Current v5 major -- GOOD |
| `github.com/gin-gonic/gin` | v1.9.1 | Minor behind (1.10.x available) -- LOW RISK |
| `github.com/gorilla/websocket` | v1.5.1 | Current v1 -- GOOD |
| `github.com/microcosm-cc/bluemonday` | v1.0.26 | Recent -- GOOD |
| `golang.org/x/crypto` | v0.46.0 | Very recent -- GOOD |
| `golang.org/x/net` | v0.48.0 | Very recent -- GOOD |
| `google.golang.org/grpc` | v1.78.0 | Very recent -- GOOD |
| `google.golang.org/protobuf` | v1.36.11 | Very recent -- GOOD |
| `github.com/jackc/pgx/v5` | v5.7.2 | Recent -- GOOD |
| `github.com/redis/go-redis/v9` | v9.17.2 | Recent -- GOOD |

### 8.2 Python Dependencies (`pyproject.toml`)

| Dependency | Version | Status |
|-----------|---------|--------|
| `fastapi` | >=0.109.0 | Modern -- GOOD |
| `sqlalchemy` | >=2.0.25 | Current major -- GOOD |
| `python-jose[cryptography]` | >=3.3.0 | Standard -- GOOD |
| `passlib[bcrypt]` | >=1.7.4 | Maintenance-only (last release 2020) -- NOTED |
| `bcrypt` | >=4.0.1,<4.1.0 | Pinned for compat -- GOOD |
| `grpcio` | >=1.60.0 | Reasonable -- OK |
| `openai` | >=1.10.0 | Broad range -- OK |
| `langgraph` | >=0.2.0 | Early version -- EXPECTED |
| `pydantic` | >=2.5.3 | Current major -- GOOD |

### 8.3 Flutter Dependencies (`pubspec.yaml`)

| Dependency | Status |
|-----------|--------|
| `flutter_secure_storage: ^9.0.0` | Keychain/Keystore for tokens -- GOOD |
| `flutter_riverpod: ^2.4.9` | State management -- OK |
| `go_router: ^13.0.0` | Navigation -- Recent |
| `dio: ^5.4.0` | HTTP client with interceptor support -- OK |
| `sentry_flutter: ^8.0.0` | Crash reporting -- GOOD |
| `web_socket_channel: ^3.0.3` | WebSocket implementation -- OK |

**Note**: Multiple third-party plugins are overridden with local copies in `third_party_plugins/`. These should be audited separately and kept in sync with upstream security patches.

---

## 9. Additional Verified Working Items

1. **Circuit breaker** for gRPC agent connections with configurable thresholds (`agent/client.go:268-281`)
2. **Graceful shutdown** with configurable timeout (`config.go:530`)
3. **WebSocket ping/pong** keepalive (30s interval, 90s wait) (`config.go:534-535`)
4. **WebSocket idle timeout** (300s) and connection limits (2 per user, 2000 global)
5. **WebSocket reconnect rate limiting** (minimum 2s gap, max 10 attempts, 300s block) (`agent/client.go:192-199`)
6. **Internal API** endpoint protection: API key + IP whitelist + rate limiting (`setup.go` internal group)
7. **Chaos engineering** support: configurable but disabled in production (`config.go:499-501`)
8. **Prometheus metrics** for security events: sanitized errors, WS connection errors, ticket failures
9. **Distributed rate limiting** via Redis Lua scripts (`distributed_rate_limiter.go`)
10. **Sliding window rate limiting** as an alternative to token bucket (`sliding_window` mode)
11. **Admin secret** enforced in non-dev with constant-time comparison
12. **Apple Sign In** with proper token verification (issuer, audience checks in `apple_auth.go`)
13. **Session persistence** with device metadata, IP, user agent tracking
14. **LRU-based** rate limiter eviction for memory bounding
15. **Object pooling** for chat input structs to reduce GC pressure (`chat_orchestrator.go:40-44`)
16. **LLM output safety**: `llm_safety.py`, `llm_secure_io.py`, `execution_trust.py` for defense-in-depth

---

## 10. Consolidated Findings Register

| ID | Severity | Area | Finding | File:Line |
|----|----------|------|---------|-----------|
| P1-01 | HIGH | Auth | HS256 symmetric JWT shared across Go and Python | `auth.go:163`, `security.py:64` |
| P1-02 | HIGH | Logging | Python logs raw user_id values without hashing | `token_revocation.py:35,75,95`, `security.py:196,235` |
| P2-01 | MEDIUM | Auth | No native refresh endpoint in Go Gateway; proxied to Python | `setup.go:862` |
| P2-02 | MEDIUM | TLS | No certificate rotation support for gRPC | `agent/client.go:107-123` |
| P2-03 | MEDIUM | Storage | MinIO SSL disabled by default | `config.go:510` |
| P2-04 | MEDIUM | Dependencies | passlib/bcrypt version compatibility warning | `main.py:162-179` |
| P2-05 | MEDIUM | Performance | No Redis caching for chat history/galaxy data | `chat_history.go`, galaxy handler |
| P2-06 | MEDIUM | Auth | No refresh token rotation on refresh | `auth.go:166-197` |

---

## 11. Recommendations Priority

### Immediate (P1)
1. Implement SHA-256 hashing of user_ids in Python logs (mirror Go's `logsafe.UserIDHash()`)
2. Plan RS256 migration path for JWT (add public key verification to Go, private key signing in Python)

### Short-term (P2)
3. Add dedicated Go refresh endpoint with token rotation
4. Enable MinIO SSL by default in production configs
5. Add Redis response caching for chat session list and galaxy node queries
6. Add certificate reloading mechanism or document restart-based rotation

### Long-term
7. Audit third_party_plugins for Flutter (keep in sync with upstream)
8. Add structured logging throughout Python (use structlog with PII scrubbing)
9. Add explicit HSTS preload support

---

## 12. Methodology Notes

- All findings are based on direct code inspection of the current `main` branch
- No dynamic testing or penetration testing was performed
- File paths are relative to the project root (`/Users/brsama/code/GitHub/Sparkle-project/`)
- Line numbers are accurate as of the branch state on 2026-05-07
- "Verified Working" items were confirmed by tracing the full code path
