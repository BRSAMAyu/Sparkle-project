# R11 / R3A10 -- Pre-Launch Security + Performance + Infrastructure Audit

**Date**: 2026-05-07
**Auditor**: Claude Opus 4.7 (Automated Audit)
**Scope**: Entire Sparkle monorepo -- Go Gateway, Python Engine, Flutter Mobile, Docker, NGINX, Monitoring
**Methodology**: Static analysis of all source files, configuration files, Docker setups, and infrastructure scripts. Grep-based pattern matching for secrets, injection vectors, missing security controls, and performance anti-patterns.

---

## Executive Summary

| Category | P0 | P1 | P2 | Total |
|----------|----|----|----|-------|
| Security | 3 | 7 | 4 | 14 |
| Performance | 0 | 2 | 4 | 6 |
| Infrastructure | 0 | 1 | 5 | 6 |
| **Total** | **3** | **10** | **13** | **26** |

**Overall Assessment**: The codebase shows strong security fundamentals -- parameterized queries everywhere (Go sqlc + Python SQLAlchemy), bluemonday HTML sanitization on all WebSocket messages, comprehensive error sanitization with Prometheus tracking, JWT token blacklisting with Redis fail-closed mode, internal API key authentication with constant-time comparison, IP whitelisting for internal routes, CSP and security headers on all responses, and production guardrails in config validation. **No hardcoded production secrets were found.** The 3 P0 findings are configuration gaps, not active vulnerabilities, and are straightforward to fix.

---

## SECURITY FINDINGS

### P0-1: mTLS Client Certificate Environment Variables Not Bound

**File**: `backend/gateway/internal/config/config.go`, lines 387-450
**Field**: `AgentTLSClientCertPath` (line 41) and `AgentTLSClientKeyPath` (line 42)

**Finding**: The config struct defines `AgentTLSClientCertPath` and `AgentTLSClientKeyPath` fields (used in `backend/gateway/internal/agent/client.go` lines 125-135 for mTLS), but these two environment variables are **not included in the `envKeys` slice** (lines 387-450) that maps environment variables to config fields. The `viper.BindEnv` loop only iterates keys in this slice, so `AGENT_TLS_CLIENT_CERT` and `AGENT_TLS_CLIENT_KEY` can never be set via environment variables -- only via `.env` files or `viper.SetDefault`.

**Risk**: In production Docker/Kubernetes deployments where mTLS is configured via environment variables (the standard approach), the mTLS client certificate paths would silently remain empty strings. The gRPC client would use one-way TLS (server-only) instead of mutual TLS. This means the gRPC connection from Gateway to Python Agent would not authenticate the client, weakening defense-in-depth against internal network compromise.

**Fix**: Add `"AGENT_TLS_CLIENT_CERT"` and `"AGENT_TLS_CLIENT_KEY"` to the `envKeys` slice in `config.go` between `AGENT_TLS_INSECURE` and `GRPC_TIMEOUT_SECONDS` (around line 391). Also add corresponding `viper.SetDefault` calls for consistency.

**Current State**: Broken -- mTLS client certs cannot be loaded from environment.

---

### P0-2: gRPC Client Missing TLS Minimum Version

**File**: `backend/gateway/internal/agent/client.go`, lines 101-103
**Code**:
```go
tlsCfg := &tls.Config{
    ServerName:         cfg.AgentTLSServerName,
    InsecureSkipVerify: cfg.AgentTLSInsecure,
}
```

**Finding**: The `tls.Config` struct does not set `MinVersion`. Go's default `MinVersion` is 0, which allows TLS 1.0 negotiation. TLS 1.0 and 1.1 are deprecated (RFC 8996) and vulnerable to multiple attacks (BEAST, POODLE, Lucky13).

**Risk**: In environments where TLS is enabled but the server supports older protocol versions, the gRPC connection between Gateway and Python Agent could negotiate down to TLS 1.0/1.1, exposing the internal communication channel to known protocol-level vulnerabilities.

**Fix**: Add `MinVersion: tls.VersionTLS12` to the `tls.Config` literal. Optionally add `CurvePreferences` to prefer modern elliptic curves:
```go
tlsCfg := &tls.Config{
    MinVersion:         tls.VersionTLS12,
    ServerName:         cfg.AgentTLSServerName,
    InsecureSkipVerify: cfg.AgentTLSInsecure,
    CurvePreferences:   []tls.CurveID{tls.X25519, tls.CurveP256},
}
```

**Current State**: Missing -- no minimum TLS version enforced.

---

### P0-3: CSP Allows `style-src 'unsafe-inline'`

**File**: `backend/gateway/internal/middleware/security.go`, line 18
**Code**:
```go
"style-src 'self' 'unsafe-inline'; "+
```

**Finding**: The Content-Security-Policy allows inline styles (`'unsafe-inline'`). While the comment on line 16 acknowledges this ("style-src keeps 'unsafe-inline' for framework/runtime-injected styles"), inline styles are a CSS injection / data exfiltration vector. Combined with other weaknesses (e.g., an HTML injection via user content), this allows attackers to extract sensitive data via CSS selectors (CSS Exfil attack).

**Risk**: Medium -- requires a separate HTML injection to exploit, and Flutter web rendering in `canvaskit` mode is less susceptible. However, if the Flutter app is loaded in HTML renderer mode on web or if any admin dashboard pages use server-rendered HTML, this gap is exploitable.

**Fix**: Migrate inline styles to a CSP nonce or hash mechanism. With `gin`, this requires a nonce middleware that generates a unique nonce per request and modifies the CSP header and HTML response accordingly. For the short term, restrict `style-src` to `'self'` and add hashes for any required inline styles in HTML responses. The Flutter app does not need inline styles (it uses its own rendering engine).

**Current State**: Present -- intentional but documented gap.

---

### P1-1: Redis `allkeys-lru` Can Evict Security-Critical Keys

**File**: `docker-compose.yml`, line 60
**Code**:
```
redis-stack-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
```

**Finding**: The Redis maxmemory policy is `allkeys-lru`, which evicts the least-recently-used keys when memory is full. Security-critical keys include:
- `token_blacklist:<jti>` -- JWT token blacklist entries
- `user_revoked_before:<user_id>` -- User-level token revocation timestamps
- `session_revoked:<sid>` -- Session revocation flags
- `ws:ticket:<uuid>` -- WebSocket tickets

If Redis memory fills up, these keys could be evicted before their TTL expires. Eviction of `token_blacklist:*` keys would allow a supposedly-revoked token to be accepted, bypassing JWT revocation. The TTL on blacklist entries is typically short (the remaining lifetime of the token), but during memory pressure this is a real gap.

**Risk**: Under memory pressure, token revocation can silently fail, allowing revoked JWTs to authenticate. This is especially dangerous after a security incident (account takeover, device theft) where immediate revocation was expected to work.

**Fix**: Option A (preferred): Use Redis `volatile-lru` instead of `allkeys-lru`. This only evicts keys that have an explicit TTL, and security keys already have TTLs set -- this protects keys that have no expiry. Option B: Add `--maxmemory-policy noeviction` and increase maxmemory to ensure Redis never needs to evict. Option C: Use a separate Redis instance/database for security-critical keys with `noeviction` policy.

**Current State**: `allkeys-lru` active in development docker-compose.yml; production docker-compose.prod.yml has its own Redis config (line 480+).

---

### P1-2: JWT Algorithm HS256 -- Shared Symmetric Key

**Files**:
- `backend/gateway/internal/handler/auth.go`, lines 162, 191
- `backend/gateway/internal/middleware/auth.go`, line 447
- `backend/app/core/security.py`, line 64
- `backend/app/config/settings.py`, line 134

**Finding**: JWT signing uses HMAC-SHA256 (HS256) with a single shared `SECRET_KEY` across Gateway and Python Engine. HS256 is a symmetric algorithm -- anyone who knows the secret can both create and verify tokens. With multiple services sharing the same secret (Go Gateway + Python gRPC agent), the secret exposure surface is doubled.

**Risk**: If either the Go Gateway or Python Engine is compromised, the attacker can forge JWTs for any user. Asymmetric algorithms (RS256, ES256) would limit the Python Engine to verification-only (public key), reducing blast radius. However, in Sparkle's architecture, both services are containerized and the gRPC channel already has its own auth (internal API key + pending mTLS), so the practical risk is moderate.

**Fix**: For a post-launch improvement, consider migrating to RS256 or ES256 with the Gateway holding the private key and the Python Engine holding only the public key. This requires key generation infrastructure and JWT library changes in both Go and Python. Short-term: ensure the `SECRET_KEY` is a high-entropy 64+ character random string and rotated periodically.

**Current State**: HS256 used everywhere; production guardrail enforces non-default SECRET_KEY.

---

### P1-3: passlib / bcrypt Version Incompatibility Warning

**File**: `backend/app/main.py`, lines 140-157
**Finding**: Startup code detects potential incompatibility between passlib 1.7.x and bcrypt 5.0+:
```python
bcrypt_ver = tuple(map(int, bcrypt.__version__.split(".")[:2]))
if bcrypt_ver >= (5, 0):
    logger.warning("passlib 1.7.4 may be incompatible with bcrypt 5.0.0")
```

**Risk**: If this incompatibility manifests, `passlib` could silently fail to verify passwords or produce incorrect hashes, leading to either authentication failures (denial of service) or accepting invalid passwords (security bypass). The exact behavior depends on how passlib's bcrypt backend handles the version mismatch.

**Fix**: Pin `bcrypt<5.0.0` in `requirements.txt` and `pyproject.toml` to ensure the compatible version. Alternatively, upgrade passlib to a version that supports bcrypt 5.0+ or switch to `bcrypt` library directly for password operations (bypassing passlib's abstraction).

**Current State**: Warning only; no version pin.

---

### P1-4: Nginx TLS Cipher Suite Too Permissive

**File**: `nginx/nginx.conf`, line 35
**Code**:
```
ssl_ciphers  HIGH:!aNULL:!MD5;
```

**Finding**: The `HIGH` cipher string includes ciphers that, while strong at the time, are now considered less than ideal for modern deployments. It does not explicitly disable CBC-mode ciphers (vulnerable to Lucky13 timing attacks) or order preferences for forward-secrecy ciphers. The Mozilla "Intermediate" configuration recommends `ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...` with explicit cipher ordering.

**Risk**: Low-Medium. HSTS is configured (6-month max-age), TLS 1.2+ is enforced via `ssl_protocols TLSv1.2 TLSv1.3`, and the cipher string does disable NULL and MD5 ciphers. The practical attack surface is small, but not zero -- a CBC-mode timing attack could theoretically recover session data if the attacker can make millions of requests.

**Fix**: Use Mozilla's Modern or Intermediate cipher list:
```
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;  # Let client choose modern cipher
```

**Current State**: Functional but uses older HIGH cipher string.

---

### P1-5: Python gRPC Server Defaults to PLAINTEXT

**File**: `backend/grpc_server.py`, lines 191-212
**Finding**: The gRPC server only enables TLS when `GRPC_REQUIRE_TLS` is true or cert paths are set:
```python
use_tls = settings.GRPC_REQUIRE_TLS or (
    settings.GRPC_TLS_CERT_PATH and settings.GRPC_TLS_KEY_PATH
)
```
In development (ENVIRONMENT=development), `GRPC_REQUIRE_TLS` defaults to `None` which resolves to `False`. The production config validates that `GRPC_REQUIRE_TLS=True` (see `backend/app/config/settings.py` line 1021), so production is protected. However, there is no validation that `GRPC_TLS_CERT_PATH` and `GRPC_TLS_KEY_PATH` actually exist and contain valid certificates at startup.

**Risk**: In production: if the cert files are missing, the gRPC server will log an error and crash at best, or silently listen on an insecure port at worst. The Python `grpc_server.py` file reads cert files at lines 195-198 via `open(settings.GRPC_TLS_CERT_PATH, "rb")` which would raise `FileNotFoundError` and crash -- so the harm is limited to startup failure, not silent insecure operation. Still, the pre-flight check should validate cert existence before attempting to start.

**Fix**: Add explicit cert path validation in `config/settings.py` post-validation: if `GRPC_REQUIRE_TLS` is true, verify `GRPC_TLS_CERT_PATH` and `GRPC_TLS_KEY_PATH` are set and point to readable files.

**Current State**: Production guardrail exists; missing file validation.

---

### P1-6: No Automated JWT Key Rotation

**Files**:
- `backend/app/config/settings.py`, lines 156-157
- `backend/gateway/internal/config/config.go`, line 48

**Finding**: The Python config defines `SPARKLE_JWT_KEY_VERSION` (default "v1") and `SPARKLE_JWT_PREVIOUS_KEY` (default "") for key rotation support, but there is no automated rotation mechanism, no key generation script, and no grace-period logic in the Go Gateway's `validateJWT` function. Key rotation is a manual process.

**Risk**: If the JWT signing key is compromised, there is no rapid rotation capability. Manual rotation requires updating both services simultaneously, risking downtime or rejected tokens during the transition window.

**Fix**: Implement grace-period validation in `validateJWT` that tries the current key first, then the previous key. Create a key generation script and rotation SOP. For immediate pre-launch: document the rotation procedure and test it manually.

**Current State**: Fields defined but no automation.

---

### P1-7: Error Details Leaked in Development Mode

**File**: `backend/gateway/internal/middleware/auth.go`, lines 268-279
**Finding**: The `middlewareErrorMessage` function returns detailed error messages when `isDevelopmentModeForMiddlewareErrors()` returns true (ENVIRONMENT is empty, "dev", or "development"):
```go
if isDevelopmentModeForMiddlewareErrors() && message != "" {
    return message
}
```
This means in development, internal error messages like "Redis blacklist check failed" or "session revocation lookup failed" are returned to the client. While this is acceptable for development, it creates a risk if a development configuration is accidentally deployed.

**Risk**: Low -- production guardrails prevent this (ENVIRONMENT must be "prod"/"production" for production). However, if "staging" environment uses detailed errors, it could leak information to testers or attackers probing the staging endpoint.

**Fix**: Add "staging" to the production error message path:
```go
func isDevelopmentModeForMiddlewareErrors() bool {
    env := strings.ToLower(os.Getenv("ENVIRONMENT"))
    return env == "" || env == "dev" || env == "development"
}
```
Consider making "staging" use production error messages.

**Current State**: Development-only gap; production is protected.

---

### P2-1: gRPC Reflection Not Condition-Locked for Production

**File**: `backend/grpc_server.py`, line 184
**Code**:
```python
if settings.DEBUG or settings.GRPC_ENABLE_REFLECTION:
    reflection.enable_server_reflection(tuple(services), server)
```

**Finding**: gRPC reflection is enabled when DEBUG is True. While `DEBUG` is forced to False in production (settings.py line 1008), the condition is an OR -- if `GRPC_ENABLE_REFLECTION` is accidentally set to True in a non-DEBUG environment, reflection would be enabled, exposing service discovery information. The default for `GRPC_ENABLE_REFLECTION` is False (settings.py line 860), so this is safe by default but allows misconfiguration.

**Risk**: Low. Service discovery via reflection enables attackers to enumerate all gRPC methods. Combined with no mTLS, an attacker on the internal network could discover and call any gRPC method.

**Fix**: Change to AND condition in production: `if settings.DEBUG and settings.GRPC_ENABLE_REFLECTION`.

**Current State**: Safe by default; could be hardened.

---

### P2-2: WebSocket Ticket TTL Configurable but No Max Cap

**File**: `backend/gateway/internal/config/config.go`, line 470
**Default**: 120 seconds (2 minutes)
**Configuration**: `WS_TICKET_TTL_SECONDS`

**Finding**: The WebSocket ticket TTL is configurable but there is no maximum cap. If accidentally set to a very high value (e.g., 86400 = 24 hours), the ticket would effectively be a long-lived authentication mechanism, bypassing the intended short-lived ticket design.

**Risk**: Low -- requires operator misconfiguration.

**Fix**: Add a max TTL validation in `Load()`: reject values > 300 (5 minutes) in non-development environments.

**Current State**: Configurable without upper bound.

---

### P2-3: Redis `REDIS_FAIL_CLOSED` Defaults to False in viper, Overridden at Load

**File**: `backend/gateway/internal/config/config.go`, lines 486 and 586
**Two-step logic**:
1. `viper.SetDefault("REDIS_FAIL_CLOSED", false)` (line 486) -- default false
2. `cfg.RedisFailClosed = true` if `!cfg.IsDevelopment()` (line 586) -- forced true in non-dev

**Finding**: The two-step logic is correct for non-development environments (fail-closed is forced). However, if the `IsDevelopment()` check passes (empty string or "dev"/"development"), fail-closed remains false even in "staging". The Redis fail-closed default for staging should also be true.

**Risk**: Low -- staging could operate in fail-open mode, allowing tokens when Redis is unavailable.

**Fix**: Change `IsDevelopment()` check to `IsProduction()` or explicitly add "staging" to the fail-closed enforcement:
```go
if !cfg.IsDevelopment() || env == "staging" {
    cfg.RedisFailClosed = true
}
```

**Current State**: Staging gets fail-open by default.

---

### P2-4: No Automated TLS Certificate Expiry Monitoring

**Finding**: The Prometheus monitoring stack includes comprehensive SLO alerts, Celery alerts, and production baselines, but there is no TLS certificate expiry monitoring. The NGINX reverse proxy uses cert files mounted at `/etc/nginx/ssl/`, but there is no blackbox exporter check or alert for certificate expiration.

**Risk**: Expired TLS certificates cause service outage.

**Fix**: Add a `blackbox_exporter` probe for TLS certificate expiry, or use `ssl_exporter`, or add a simple cron job that checks `openssl x509 -enddate`. Wire into Alertmanager.

**Current State**: Not monitored.

---

## PERFORMANCE FINDINGS

### P1-1: `allkeys-lru` Eviction Policy Also Degrades Cache Performance

**File**: `docker-compose.yml`, line 60 (same as Security P1-1)
**Finding**: Under Redis memory pressure, `allkeys-lru` evicts any key -- including hot cache entries. This can cause cache stampedes where many requests simultaneously miss the cache and hammer the database. For Sparkle's dual-core architecture, this could affect session state, preference lookups, and chat history caching.

**Fix**: Same resolution as Security P1-1. Use `volatile-lru` to prefer evicting keys with TTLs, keeping non-expiring data intact. For cache-specific keys, set appropriate TTLs.

**Current State**: `allkeys-lru` active.

---

### P1-2: Single pgxpool Connection for Go Gateway

**File**: `backend/gateway/cmd/server/setup.go`, lines 115-162
**Config**: MaxConns=30, MinConns=5, MaxConnIdleTime=15min

**Finding**: The Go Gateway uses a single pgxpool with 30 max connections. This pool serves all request types -- chat or stream queries, chat history, user context lookups, CQRS projections, task commands, file metadata, and more. There is no connection pool sharding or prioritization for critical vs. background queries. Under load, background CQRS workers could consume all connections, starving real-time chat requests.

**Risk**: Medium. CQRS workers (outbox publisher, sync workers) could exhaust the connection pool under high event processing load, causing chat request timeouts.

**Fix**: Use separate connection pools for critical-path queries (chat, auth) vs. background workers. Both pools can connect to the same database, just with different sizes and priorities. Example: critical pool (MaxConns=20) + worker pool (MaxConns=10).

**Current State**: Single shared pool.

---

### P2-1: No Query Plan Analysis for Hot Paths

**Finding**: The HNSW indexes exist for pgvector columns (6 indexes across cognitive_fragments, document_chunks, episodic_memories, knowledge_nodes, scenes, seed_items). However, there is no automated EXPLAIN ANALYZE testing for the most frequent queries: chat message insertion, chat history retrieval, user context loading, task state transitions, and plan review submission. Each of these could benefit from specific B-tree indexes on join/filter columns.

**Risk**: Under-reported until production load.

**Fix**: Run `EXPLAIN ANALYZE` on the top 10 most frequent queries (identifiable via pg_stat_statements) and create missing indexes. Pay special attention to composite indexes on `(user_id, created_at)` for chat_messages and `(session_id, created_at)` for history retrieval.

**Current State**: Indexes exist for vector search; relational hot-path indexes need verification.

---

### P2-2: No Redis Stream Consumer Lag Monitoring

**Finding**: While the monitoring stack includes Celery alerts (`celery_alerts.yml`) and SLO alerts, there is no explicit Redis Streams consumer lag monitoring. The event bus uses Redis Streams for multiple consumers (preference, galaxy, task, achievement, execution, profile, cognitive, capsule, intervention, social signal, etc.).

**Risk**: Consumer lag in critical event streams (e.g., task completion -> achievement notification) could delay user-facing features.

**Fix**: Add a Prometheus metric for Redis Stream consumer lag per consumer group, and an Alertmanager rule that fires when lag exceeds threshold (e.g., > 100 pending messages for > 60 seconds).

**Current State**: Not monitored.

---

### P2-3: No LLM Streaming Buffer Size Configuration

**File**: `backend/gateway/internal/agent/client.go` (gRPC stream)
**Finding**: The gRPC stream between Go Gateway and Python Agent does not set explicit buffer sizes for LLM token streaming. The gRPC default window size may cause backpressure when the Python agent produces tokens faster than the Go gateway can forward to WebSocket clients, especially under high concurrency.

**Risk**: Under high chat concurrency, LLM token delivery could experience jank due to gRPC flow control.

**Fix**: Set appropriate `grpc.WithInitialWindowSize` and `grpc.WithInitialConnWindowSize` in the gRPC dial options. Consider batching small delta updates to reduce per-message overhead.

**Current State**: gRPC defaults in use.

---

### P2-4: No WebSocket Write Buffer Tuning

**File**: `backend/gateway/internal/handler/ws_hardening.go` (write timeouts)
**Config**: `WS_WRITE_WAIT_SECONDS=10`, `WS_PONG_WAIT_SECONDS=90`

**Finding**: WebSocket write timeout is 10 seconds, and there's no explicit write buffer size configuration. Under high message rate (LLM streaming with frequent deltas), the gorilla/websocket write buffer may fill up and cause write deadline errors.

**Fix**: Monitor WebSocket write deadline errors via Prometheus and consider increasing `WSWriteWaitSeconds` for streaming scenarios. Set explicit `WriteBufferSize` on the upgrader.

**Current State**: Default gorilla/websocket buffer sizes.

---

## INFRASTRUCTURE FINDINGS

### P1-1: node_exporter and cadvisor Only in Production Compose

**Files**:
- `docker-compose.prod.yml`, lines 619-660
- `monitoring/prometheus.yml`, lines 35-42

**Finding**: node_exporter (host metrics) and cadvisor (container metrics) are defined only in `docker-compose.prod.yml`, not in `docker-compose.yml` (development). Prometheus scrape configs reference both at `cadvisor:8080` and `node_exporter:9100`, but these targets will be DOWN in development, creating noise in monitoring dashboards.

**Risk**: Low -- development monitoring gap only.

**Fix**: Either add node_exporter/cadvisor to docker-compose.yml, or make the Prometheus scrape configs conditional on environment.

**Current State**: Prod-only; dev scrapes fail silently.

---

### P2-1: DB Backup Script Exists but Not Automated

**File**: `scripts/backup_prod_data.sh`
**Finding**: A well-structured backup script exists that dumps PostgreSQL, snapshots Redis, archives MinIO, generates checksums, and prunes old backups. However, there is no cron job, systemd timer, or Kubernetes CronJob definition to run this script automatically.

**Risk**: Database not backed up unless run manually.

**Fix**: Add a Kubernetes CronJob or systemd timer to run `backup_prod_data.sh` daily. The script is ready to use -- it just needs scheduling.

**Current State**: Script exists but requires manual invocation.

---

### P2-2: Docker Health Check Timeouts Could Be Aggressive

**Files**: `docker-compose.yml`, lines 23-28 (sparkle_db), 90-95 (sparkle_api)
**Finding**: The sparkle_api health check (line 93-97) has `start_period: 60s` and `retries: 5` with `interval: 30s` -- giving 60+5*30=210 seconds of startup time, which is generous. However, sparkle_db has no `start_period` set, meaning its 5 retries at 10s intervals start immediately. On slow systems, this could cause the DB to be marked unhealthy before AGE extension initialization completes.

**Risk**: Low. The `sparkle_age_init` service has `depends_on: sparkle_db (condition: service_healthy)` which gates AGE initialization on DB readiness. If DB starts slowly, AGE init could fail, cascading to API and Agent startup failures.

**Fix**: Add `start_period: 30s` to sparkle_db health check.

**Current State**: DB has no start_period.

---

### P2-3: No Resource Limits on sparkle_gateway in dev compose

**File**: `docker-compose.yml`, lines 260-265
**Finding**: The sparkle_gateway service has `deploy.resources.limits.memory: 512M` and `reservations.memory: 256M` in docker-compose.yml. These are reasonable defaults. However, the resource limits are lower than the Go runtime's default memory usage with garbage collection overhead. Under WebSocket load (>2000 connections), the gateway could be OOM-killed.

**Risk**: Low in development. In production, the docker-compose.prod.yml sets `gateway_blue` and `gateway_green` to 512M limits. For 2000 concurrent WebSocket connections with gorilla/websocket (estimated ~16KB per connection = 32MB), plus Go GC overhead, 512MB should suffice -- but is close to the edge.

**Fix**: Monitor Go gateway memory in production and increase limit to 768M if usage exceeds 70% of 512M.

**Current State**: 512M limit; adequate but not generous.

---

### P2-4: No Distributed Tracing Sampling Rate Configuration

**Files**: `docker-compose.yml`, line 152 (`OTEL_EXPORTER_OTLP_ENDPOINT`), `monitoring/tempo.yaml`
**Finding**: Tempo is configured as the OpenTelemetry backend, and the Gateway and Python Engine both instrument gRPC and HTTP calls. However, there is no sampling rate configuration visible in the docker-compose files. OpenTelemetry defaults to always-on sampling, which could generate excessive trace data under load.

**Risk**: Under high request volume (1000+ req/min), trace data could overwhelm Tempo's 256MB memory limit, causing trace loss or Tempo crashes.

**Fix**: Set `OTEL_TRACES_SAMPLER=parentbased_traceidratio` and `OTEL_TRACES_SAMPLER_ARG=0.1` (10% sampling) in the sparkle_api and sparkle_agent environment blocks. Alternatively, use tail-based sampling in Tempo.

**Current State**: Default (always-on) sampling.

---

### P2-5: No Grafana Dashboard for Gateway-specific Metrics

**File**: `monitoring/grafana-dashboards/` (directory exists)
**Finding**: The Grafana provisioning points to `monitoring/grafana-dashboards/` for dashboards. While Aurora-specific dashboards exist in `monitoring/aurora_dashboards/`, there is no dedicated dashboard for Go Gateway operational metrics (WebSocket connection count, gRPC latency, rate limit hits, error rates per endpoint, sanitized error counts).

**Risk**: Gateway operational issues could go unnoticed until user reports.

**Fix**: Create a "Sparkle Gateway Overview" dashboard showing: WS active connections, WS message rate, gRPC call latency (p50/p95/p99), auth success/failure rate, rate limit triggers, sanitized error count by category, DB pool utilization, Redis pool utilization.

**Current State**: No Gateway-specific dashboard.

---

## THINGS THAT ARE DONE WELL

The following security controls are correctly implemented and deserve recognition:

1. **All SQL queries parameterized**: Go uses sqlc-generated parameterized queries exclusively. Python uses SQLAlchemy ORM with parameter binding. No raw SQL string concatenation found with user input.

2. **bluemonday HTML sanitization**: All WebSocket chat messages are sanitized via `bluemonday.UGCPolicy()` at multiple points: `chat_orchestrator.go:543`, `chat_orchestrator.go:598`, `chat_orchestrator_chatflow.go:313`, `chat_orchestrator_protocol.go:118-139`, `websocket_proxy.go:601-626`.

3. **Comprehensive error sanitization**: All REST API errors go through `sanitizeErrorResponse` / `sanitizeErrorPayload` in `error_sanitizer.go`, which strips internal details and tracks via Prometheus. Errors are categorized (auth_error, server_error, client_error) and monitored.

4. **Security headers on every response**: `SecurityHeadersMiddleware` in `security.go` sets CSP, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, HSTS (production), Referrer-Policy, Permissions-Policy, Cross-Origin-Opener-Policy, Cross-Origin-Resource-Policy.

5. **JWT token blacklist with fail-closed mode**: `validateJWT` in `middleware/auth.go` checks JTI blacklist (token-level), user revocation (user-level), and session revocation (device-level). Redis failures in fail-closed mode reject tokens. Local memory cache provides defense-in-depth for up to 10,000 entries.

6. **Constant-time comparison for secrets**: `subtle.ConstantTimeCompare` is used for Admin Secret (`AdminAuthMiddleware`), Internal API Key (`InternalAPIKeyMiddleware`), and signal push key (`signal_push.go:134`).

7. **Internal API protected by dual middleware**: Internal routes require BOTH `InternalAPIKeyMiddleware` (X-Internal-API-Key header, constant-time comparison) AND `InternalIPWhitelistMiddleware` (source IP must be in allowlist of private IP ranges).

8. **Production config guardrails**: The `Load()` function in `config.go` enforces 13 production invariants: JWT_SECRET must be set + non-default, ADMIN_SECRET must be set + non-default, AGENT_TLS_INSECURE must be false, ALLOW_WS_QUERY_TOKEN must be false, INTERNAL_API_KEY must be set, MinIO credentials must be non-default, RBAC must be enabled.

9. **File upload validation**: Size limits (`FILE_MAX_UPLOAD_SIZE`, default 50MB), filename sanitization (`sanitizeFilename` in `file_handler.go:506`), presigned upload URLs with short expiration.

10. **WebSocket authentication**: Token validation via JWT in header (primary) or ticket system (POST /api/v1/ws/ticket to obtain short-lived ticket). Query param token support disabled in non-development.

11. **CORS with strict origin validation**: `IsOriginAllowed` validates scheme + host + port against whitelist. Wildcard (`*`) origins rejected in production. Wildcard subdomain matching uses suffix check. Invalid/unsafe origin URLs are rejected rather than falling through to insecure comparison.

12. **HNSW indexes on all vector columns**: 6 HNSW indexes on `cognitive_fragments`, `document_chunks`, `episodic_memories`, `knowledge_nodes`, `scenes`, `seed_items` for fast approximate nearest neighbor search.

13. **1066 total database indexes**: Comprehensive index coverage across 200+ tables.

14. **Graceful shutdown**: Signal handlers in Main (Go) and grpc_server.py (Python) for SIGINT/SIGTERM. Shutdown timeout configurable.

15. **Tempo + Loki + Prometheus + Grafana stack**: Full observability pipeline configured and provisioned.

---

## RECOMMENDED PRE-LAUNCH ACTION ITEMS

### Must Fix (P0) -- before any production traffic

| # | Finding | File | Fix |
|---|---------|------|-----|
| P0-1 | mTLS client cert env vars not bound | `config.go:387-450` | Add `AGENT_TLS_CLIENT_CERT`, `AGENT_TLS_CLIENT_KEY` to envKeys |
| P0-2 | No TLS MinVersion in gRPC client | `agent/client.go:101` | Add `MinVersion: tls.VersionTLS12` |
| P0-3 | CSP unsafe-inline styles | `middleware/security.go:18` | Remove `unsafe-inline` or add nonce support |

### Should Fix (P1) -- before first 100 users

| # | Finding | File | Fix |
|---|---------|------|-----|
| P1-1 | Redis allkeys-lru eviction | `docker-compose.yml:60` | Change to `volatile-lru` or separate Redis for security keys |
| P1-3 | passlib/bcrypt compatibility | `backend/app/main.py:140` | Pin `bcrypt<5.0.0` |
| P1-5 | gRPC cert path validation | `grpc_server.py:191` | Add file existence checks |
| P1-2 | DB single connection pool | `cmd/server/setup.go:115` | Separate critical vs. background pools |
| P1-1 (perf) | Same as Security P1-1 | - | Same fix |

### Nice to Fix (P2) -- within first month

Remaining P2 items as listed above.

---

## AUDIT METHODOLOGY

The audit was performed via static analysis only, using pattern-based grep searches across the entire codebase:

- **Secrets scan**: Regex for `password`, `secret`, `api_key`, `token`, `private_key` followed by assignment operators and quoted strings. Cross-referenced against `.gitignore` patterns.
- **Injection scan**: Looked for raw SQL construction (`fmt.Sprintf` with SQL keywords, `+` concatenation of queries), shell execution (`exec.Command`, `subprocess.run`, `os.system`), and dynamic HTML generation.
- **Configuration audit**: Read all config files (`docker-compose.yml`, `docker-compose.prod.yml`, `nginx.conf`, `prometheus.yml`, `go.mod`, config structs, settings classes).
- **Security control verification**: Checked JWT validation (algorithm enforcement, expiry, issuer, audience, token type), HTML sanitization (bluemonday usage), error sanitization, rate limiting (token bucket, sliding window, hybrid Redis+local), and authentication (internal API key, admin secret, WebSocket auth, session revocation).
- **Performance assessment**: Verified index existence (HNSW, B-tree), connection pooling, caching strategy, goroutine lifecycle management.
- **Infrastructure review**: Checked health checks, resource limits, volume mounts, monitoring pipeline, backup scripts.

No dynamic testing, fuzzing, or penetration testing was performed. Docker containers were not running during the audit. This is a code-level and configuration-level review.

---

**End of Report**
