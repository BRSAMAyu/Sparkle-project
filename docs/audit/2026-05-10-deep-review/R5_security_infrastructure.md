# R5: Security & Infrastructure Deep Audit

**Date**: 2026-05-10
**Auditor**: Claude Code (automated deep review)
**Scope**: Authentication, Authorization, Input Validation, Secrets, CORS, Rate Limiting, Docker, Database, Redis, gRPC, Error Leakage, Production Guards

---

## Executive Summary

The Sparkle project demonstrates **mature security engineering** with multi-layered defenses. The audit identified **0 P0 (critical)** issues, **2 P1 (vulnerability)** issues, **8 P2 (hardening)** issues, and **5 P3 (best practice)** findings. The most significant findings relate to gRPC message size bounds, plaintext gRPC in development docker-compose, and a minor variable ordering bug in the gRPC server TLS setup.

**Overall Security Posture: STRONG** -- production guards are comprehensive, JWT handling follows best practices, error sanitization is systematic, and the docker-compose.prod.yml implements proper network isolation.

---

## Findings Index

| # | Severity | Category | Short Description |
|---|----------|----------|-------------------|
| S-01 | P1 | Network | gRPC server has variable ordering bug for `_ca_cert_path` |
| S-02 | P1 | Network | gRPC message size limits are very large (50MB) without per-RPC deadline |
| S-03 | P2 | Config | Dev docker-compose exposes Redis, PostgreSQL, MinIO, gRPC ports publicly |
| S-04 | P2 | Secrets | Dev .env file contains real API keys (tracked correctly in .gitignore) |
| S-05 | P2 | Auth | Client-telemetry POST endpoints accept unauthenticated events |
| S-06 | P2 | Config | Redis in dev docker-compose has no ACL -- single password model |
| S-07 | P2 | Network | Docker socket mounted read-only in promtail (acceptable, but noted) |
| S-08 | P2 | Auth | WebSocket query-token auth allowed in development mode |
| S-09 | P2 | Network | cAdvisor runs privileged in production |
| S-10 | P3 | Config | gRPC reflection guard could be stricter for staging environments |
| S-11 | P3 | Best Practice | JWT token stored in gin context unencrypted (`auth_token`) |
| S-12 | P3 | Best Practice | WsAuthMiddleware logs user ID hashes in production |
| S-13 | P3 | Best Practice | Some rate-limit error responses expose `endpoint` and `remaining` fields |
| S-14 | P3 | Config | Dev docker-compose has `postgres_data` as a bind mount, not a named volume |
| S-15 | P2 | Config | Dev docker-compose does not mirror prod Redis ACL model |

---

## Detailed Findings

---

### S-01: gRPC Server `_ca_cert_path` Variable Ordering Bug

- **Severity**: P1 (Vulnerability)
- **Category**: Network / Config
- **File**: `backend/grpc_server.py`, lines 202-226

**Description**: The variable `_ca_cert_path` is referenced at line 212 (`if _ca_cert_path:`) **before** it is defined at line 226 (`_ca_cert_path = getattr(settings, "GRPC_TLS_CA_CERT_PATH", "")`). In Python, this will raise a `NameError` at runtime, causing the gRPC server to crash when TLS is enabled. This means mTLS configuration (`GRPC_TLS_CA_CERT_PATH`) is currently broken -- the server will fail to start if TLS is enabled with a CA cert path.

**Attack Scenario**: If an operator sets `GRPC_TLS_CA_CERT_PATH` in production believing mTLS is active, the server crashes on boot. If they work around the crash by removing the CA cert path, the server runs with TLS but without client certificate verification, weakening the security model.

**Fix**: Move the `_ca_cert_path` assignment before the TLS credential creation block.

```python
# Line 226 should be moved before line 202
_ca_cert_path = getattr(settings, "GRPC_TLS_CA_CERT_PATH", "")
use_tls = settings.GRPC_REQUIRE_TLS or (
    settings.GRPC_TLS_CERT_PATH and settings.GRPC_TLS_KEY_PATH
)
if use_tls:
    ...
    if _ca_cert_path:
        ...
```

**Context Needed**: The TLS configuration block in `serve()` function.

---

### S-02: gRPC Unbounded Message Sizes (50MB) Without Per-RPC Deadlines

- **Severity**: P1 (Vulnerability)
- **Category**: Network / DoS
- **File**: `backend/grpc_server.py`, lines 153-154

**Description**: The gRPC server accepts messages up to 50MB (`grpc.max_receive_message_length = 50 * 1024 * 1024`). Combined with a `max_concurrent_streams` of 1000, an attacker with valid credentials could send oversized messages to exhaust server memory. There is no per-RPC deadline propagation from the Go gateway.

**Attack Scenario**: An authenticated user sends 50MB gRPC messages concurrently, consuming up to 50GB of server memory (1000 streams * 50MB), causing OOM and denial of service for all users.

**Fix**:
1. Reduce `max_receive_message_length` to a reasonable limit (e.g., 4MB for most RPCs, 10MB for STT).
2. Add per-RPC deadline enforcement in the Go gateway client.
3. Consider streaming upload patterns for large payloads.

---

### S-03: Dev docker-compose Exposes Service Ports Publicly

- **Severity**: P2 (Hardening)
- **Category**: Network / Config
- **File**: `docker-compose.yml`, lines 11, 59, 83-84, 114, 216

**Description**: The development docker-compose exposes PostgreSQL (5432), Redis (6379), MinIO (9000/9001), API (8000), and gRPC (50051) on all interfaces (`0.0.0.0`). These ports are accessible from any network the host is connected to.

**Attack Scenario**: On a public WiFi or shared network, anyone can connect to Redis (no password if REDIS_PASSWORD env is empty) or PostgreSQL with default credentials.

**Fix**: Bind ports to `127.0.0.1` in development:
```yaml
ports:
  - "127.0.0.1:5432:5432"
  - "127.0.0.1:6379:6379"
```

**Note**: The production docker-compose already follows best practice -- internal services have no `ports` directive at all (only nginx exposes 80/443). Monitoring ports are correctly bound to `127.0.0.1`.

---

### S-04: Dev .env Contains Real API Keys

- **Severity**: P2 (Secrets)
- **Category**: Secrets
- **File**: `backend/.env`, lines 37, 42, 48, 59, 72

**Description**: The `.env` file contains real API keys for LLM providers (DeepSeek, DashScope, SiliconFlow, Xiaomi). While `.env` is correctly excluded from git via `.gitignore` (verified: `git ls-files` shows it is not tracked), this creates risk of accidental commits during development.

**Mitigations Already in Place**:
- `.gitignore` correctly excludes `**/.env` (verified)
- `git ls-files --cached` confirms no `.env` files are tracked
- Production config validates required secrets are set

**Fix**: Consider using `.env.example` with placeholder values and a setup script that copies from a secure vault.

---

### S-05: Client Telemetry POST Endpoints Accept Unauthenticated Events

- **Severity**: P2 (Auth)
- **Category**: Auth / Input Validation
- **Files**:
  - Go: `backend/gateway/internal/handler/proxy_routes.go`, lines 729-731
  - Python: `backend/app/api/v1/client_telemetry.py`, lines 116-140

**Description**: The Go gateway registers `/api/v1/client-telemetry/events` and `/api/v1/client-telemetry/events/batch` **without** authMiddleware. The Python endpoint uses `get_optional_current_user` which accepts anonymous submissions. This allows anyone to submit telemetry events, potentially flooding the Redis aggregation keys.

**Attack Scenario**: An unauthenticated attacker submits millions of telemetry events, filling Redis with aggregate keys and causing memory pressure.

**Fix**: Move authMiddleware registration before the telemetry POST routes, or add a separate rate limit for unauthenticated telemetry ingestion.

---

### S-06: Dev Redis Has No ACL -- Single Password Model

- **Severity**: P2 (Config)
- **Category**: Config / Secrets
- **File**: `docker-compose.yml`, line 60

**Description**: Development Redis uses a single `--requirepass` password. The production config (`docker-compose.prod.yml`, lines 510-516) correctly implements RBAC with per-user ACLs (gateway, engine, celery with restricted command sets and key patterns). This divergence means security issues in ACL rules would not be caught in development.

**Fix**: Port the ACL configuration to development docker-compose with the same user separation.

---

### S-07: Docker Socket Mounted in Promtail (Monitoring)

- **Severity**: P2 (Network)
- **Category**: Network / Config
- **Files**: `docker-compose.yml` line 590, `docker-compose.prod.yml` line 771

**Description**: Promtail mounts `/var/run/docker.sock:ro` to read container logs. While read-only, this still provides significant visibility into the Docker daemon. This is standard practice for log collection but is documented as a conscious acceptance of risk.

**Mitigation**: Promtail runs in its own container with resource limits. The socket is read-only.

---

### S-08: WebSocket Query-Token Auth Available in Development

- **Severity**: P2 (Auth)
- **Category**: Auth / Config
- **Files**:
  - Go config: `backend/gateway/internal/config/config.go`, lines 58, 694-696, 751-753
  - Go middleware: `backend/gateway/internal/middleware/ws_auth.go`, lines 62-79

**Description**: In development mode, JWT tokens can be passed via WebSocket URL query parameter (`?token=...`). While this is correctly forbidden in production (`ALLOW_WS_QUERY_TOKEN` is forced false in non-dev environments), the tokens appear in server access logs and browser history in development.

**Mitigations**:
- Production guard at `config.go:694` kills the process if `ALLOW_WS_QUERY_TOKEN` is true in production.
- The ticket-based auth flow (`ws_ticket.go`) provides a one-time-use alternative.

---

### S-09: cAdvisor Runs Privileged in Production

- **Severity**: P2 (Config)
- **Category**: Config / Container
- **File**: `docker-compose.prod.yml`, lines 714-739

**Description**: cAdvisor requires `privileged: true` to access host metrics. It also mounts `/var/run/docker.sock` and host filesystem paths. This is a known requirement for cAdvisor, but the container has significant host access.

**Mitigations**: Port binding is `127.0.0.1:8081:8080`, so it is not externally accessible. Resource limits are applied.

**Fix**: Consider using a lighter alternative (e.g., node_exporter with docker metrics) or running cAdvisor in a dedicated monitoring namespace with SELinux/AppArmor policies.

---

### S-10: gRPC Reflection Guard for Staging

- **Severity**: P3 (Best Practice)
- **Category**: Config
- **File**: `backend/grpc_server.py`, lines 187-199

**Description**: gRPC reflection is disabled in production, which is correct. However, the guard allows reflection in any non-production environment when `GRPC_ENABLE_REFLECTION=true`. In staging environments that mirror production data, reflection could expose service metadata.

**Fix**: Consider requiring explicit `GRPC_ENABLE_REFLECTION=true` even in staging, or adding a dedicated `GRPC_REFLECTION_ALLOWED_ENVIRONMENTS` list.

---

### S-11: JWT Token Stored in Gin Context

- **Severity**: P3 (Best Practice)
- **Category**: Auth
- **File**: `backend/gateway/internal/middleware/auth.go`, line 393

**Description**: The raw JWT access token is stored in the gin context via `c.Set("auth_token", tokenString)`. This token is then forwarded to the Python backend via the `Authorization` header. While this is necessary for proxy operations, if any handler or middleware accidentally logs the context values, the token would be exposed.

**Mitigation**: The `logsafe` package (`backend/gateway/internal/logsafe/logsafe.go`) redacts Bearer tokens from log output via the `bearerPattern` regex. This provides defense-in-depth.

---

### S-12: WsAuth Logs User ID Hashes in Production

- **Severity**: P3 (Best Practice)
- **Category**: Privacy
- **File**: `backend/gateway/internal/middleware/ws_auth.go`, lines 38, 51, 67, 72

**Description**: WsAuthMiddleware logs user ID hashes on every WebSocket connection. In high-traffic production deployments, these logs could be correlated to track user activity patterns.

**Fix**: Consider reducing log level from `log.Printf` to debug-level logging, or sampling (log only N% of connections).

---

### S-13: Rate Limit Responses Expose Internal Details

- **Severity**: P3 (Best Practice)
- **Category**: Info Leakage
- **File**: `backend/gateway/internal/middleware/rate_limit.go`, lines 173-174, 298-301

**Description**: The `AdaptiveRateLimitMiddleware` includes the `endpoint` path in the 429 response body (line 301). The `RateLimitMiddleware` exposes `X-RateLimit-Remaining` headers showing exact token counts. While this is useful for debugging, it gives attackers information about rate limit configurations.

**Fix**: Consider removing the `endpoint` field from production 429 responses and rounding `X-RateLimit-Remaining` to buckets.

---

### S-14: Dev Docker Uses Bind Mount for PostgreSQL Data

- **Severity**: P3 (Config)
- **Category**: Config / Infrastructure
- **File**: `docker-compose.yml`, line 17

**Description**: Development docker-compose uses `./postgres_data:/var/lib/postgresql/data` (a bind mount) instead of a named Docker volume. This can cause permission issues and data corruption on some platforms (especially macOS).

**Fix**: Use a named volume (as done in production with `sparkle_prometheus_data`, etc.) for development PostgreSQL data.

---

### S-15: Dev Docker-Compose Does Not Mirror Prod Redis ACL Model

- **Severity**: P2 (Config)
- **Category**: Config / Infrastructure
- **Files**: `docker-compose.yml` vs `docker-compose.prod.yml`

**Description**: The production Redis configuration (`docker-compose.prod.yml`, lines 509-516) implements proper RBAC with separate users (gateway, engine, celery) with scoped key patterns and restricted command sets. The development Redis uses only `--requirepass` with a single password, meaning ACL misconfigurations would not surface during development.

**Fix**: Port the ACL configuration to `docker-compose.yml` with appropriate dev defaults, ensuring parity with production security model.

---

## Positive Security Findings (Worth Highlighting)

The following security measures are well-implemented and deserve recognition:

### 1. Comprehensive JWT Validation (auth.go)
- RS256 asymmetric signing (HS256 backward compat during migration)
- Token type enforcement (`type: access`)
- JTI blacklist with Redis + local fallback
- User-level token revocation (`user_revoked_before`)
- Session-level revocation (device logout)
- Issuer and audience validation
- `nbf` and `exp` with 30-second clock skew tolerance
- Fail-closed mode in production (Redis failure rejects tokens)

### 2. Error Sanitization (error_sanitizer.go)
- Production errors return generic i18n messages
- Raw error text only shown in development mode
- Prometheus metrics track sanitized errors
- Internal messages are logged but never returned to clients
- All handlers use `sanitizeErrorResponse` consistently

### 3. Security Headers (security.go)
- Strict CSP without `unsafe-inline`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- HSTS in production only (`max-age=31536000; includeSubDomains`)
- `Referrer-Policy: strict-origin-when-cross-origin`
- Cross-Origin isolation headers
- `Permissions-Policy` disabling geolocation, camera, microphone, payment

### 4. Production Guards (settings.py, config.go)
- `DEBUG=True` raises `ValueError` in production
- Insecure `SECRET_KEY` values rejected
- CORS `["*"]` rejected in production
- HTTPS-only CORS origins required in production
- RBAC must be enabled in production
- gRPC reflection disabled in production
- `ALLOW_WS_QUERY_TOKEN` forced false in production
- MinIO default credentials rejected
- `MINIO_USE_SSL` forced true in production
- `ADMIN_SECRET` must be set
- `INTERNAL_API_KEY` must be set
- All critical secrets validated non-empty

### 5. Timing-Attack Resistance
- `AdminAuthMiddleware` uses `crypto/subtle.ConstantTimeCompare`
- `InternalAPIKeyMiddleware` uses `crypto/subtle.ConstantTimeCompare`
- Python gRPC interceptor uses `secrets.compare_digest`

### 6. Network Isolation (docker-compose.prod.yml)
- Two separate networks: `sparkle_edge` (nginx only) and `sparkle_app` (internal, `internal: true`)
- Only nginx exposes ports 80/443 to the host
- All backend services communicate on the internal network only
- Monitoring ports bound to `127.0.0.1`

### 7. PII Protection
- `logsafe` package redacts emails, phone numbers, CN IDs, Bearer tokens, API keys from logs
- User IDs are hashed before logging (`UserIDHash`)
- Aurora privacy module redacts PII from LLM prompts
- Differential privacy (Laplace noise) for community intelligence

### 8. WebSocket Security
- Origin checking via `IsOriginAllowed` (no wildcard in production)
- Message deduplication service
- Per-user connection limits (`WS_MAX_CONNECTIONS_PER_USER`)
- Global connection limits (`WS_GLOBAL_MAX_CONNECTIONS`)
- Message rate limiting (10 RPS, 20 burst)
- Reconnection rate limiting with block windows
- Draining mode for graceful shutdown
- UUID validation for group IDs (path traversal prevention)

### 9. SQL Injection Prevention
- All Go SQL queries use parameterized statements (`$1`, `$2`, etc.) via sqlc
- Python uses SQLAlchemy ORM with parameterized queries
- No string interpolation found in SQL queries

### 10. Rate Limiting
- Multi-tier: IP-based, user-based, endpoint-specific, adaptive
- Redis-backed distributed rate limiting with local fallback
- Sliding window and token bucket algorithms
- Separate rate limits for auth (5 RPS), API (15 RPS), admin, WebSocket
- Per-user WebSocket message rate limiting

### 11. File Upload Security
- MIME type validation against extension allowlist
- Filename sanitization
- File size limits (50MB default)
- Per-user upload rate limiting (10/minute)
- Presigned URLs with expiry for MinIO uploads
- Production requires MinIO SSL

### 12. Token Revocation Infrastructure
- JTI-level blacklist (specific token)
- User-level revocation (all tokens before timestamp)
- Session-level revocation (device logout)
- Local cache fallback when Redis unavailable
- Automatic TTL cleanup for expired blacklist entries

### 13. gRPC Identity Verification
- Auth interceptor validates `user-id` metadata matches JWT `sub` claim
- Prevents user impersonation attacks
- Internal API key authentication for service-to-service calls
- Constant-time comparison for secret validation

### 14. Redis ACL (Production)
- Separate users for gateway, engine, celery with scoped key patterns
- Dangerous commands excluded (`-@admin -@dangerous`)
- Connection and pub/sub allowed per service need

---

## Infrastructure Configuration Summary

| Component | Dev Config | Prod Config | Assessment |
|-----------|-----------|-------------|------------|
| **PostgreSQL** | Port 5432 exposed, no TLS | Internal network, port 5432 not exposed | PROD OK |
| **Redis** | Single password, port exposed | ACL with 4 users, internal network | PROD OK |
| **gRPC** | Plaintext, port 50051 exposed | TLS required, internal network | PROD OK |
| **Gateway** | Port 8080 exposed | Internal + edge network, nginx front | PROD OK |
| **MinIO** | Ports 9000/9001 exposed, no SSL | Internal network, SSL required | PROD OK |
| **Monitoring** | Some ports on 0.0.0.0 | All ports on 127.0.0.1 | PROD OK |
| **Network** | Default bridge | Named edge + internal networks | PROD OK |
| **Resource Limits** | Most services have limits | All services have limits | OK |

---

## Recommendations Priority Matrix

| Priority | Finding | Effort |
|----------|---------|--------|
| **Immediate** | S-01: Fix `_ca_cert_path` variable ordering | Low |
| **Immediate** | S-02: Reduce gRPC message size limits | Low |
| **Before Launch** | S-03: Bind dev ports to 127.0.0.1 | Low |
| **Before Launch** | S-05: Add auth to telemetry POST | Low |
| **Before Launch** | S-06: Port Redis ACL to dev | Medium |
| **Post-Launch** | S-08: Document WS query-token risk | Low |
| **Post-Launch** | S-09: Evaluate cAdvisor alternatives | Medium |
| **Post-Launch** | S-15: Dev-prod Redis ACL parity | Medium |
| **Backlog** | S-10 through S-14 | Low |

---

## Audit Methodology

1. **Static code analysis** of all Go middleware (auth.go, cors.go, security.go, rate_limit.go, ws_auth.go, internal_api.go, internal_ip_whitelist.go, timeout.go, distributed_rate_limiter.go)
2. **Static code analysis** of Go handlers (auth.go, error_sanitizer.go, file_handler.go, proxy_routes.go, websocket_proxy.go, ws_hardening.go, ws_ticket.go)
3. **Configuration review** of Go gateway config (config.go), Python settings (settings.py), Python security (security.py)
4. **Docker review** of docker-compose.yml and docker-compose.prod.yml
5. **gRPC review** of grpc_server.py, grpc_auth.py
6. **Infrastructure review** of redis.conf, SQL queries (query.sql)
7. **Secret scanning** via grep patterns for API keys, passwords, tokens
8. **Privacy review** of logsafe.go, aurora/privacy.py
9. **Router review** of setup.go for middleware ordering and auth coverage
