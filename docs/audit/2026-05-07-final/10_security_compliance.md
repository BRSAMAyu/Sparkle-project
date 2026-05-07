# Security & Compliance Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Sparkle project demonstrates a mature, defense-in-depth security posture across all three layers (Go Gateway, Python Engine, Flutter). Authentication, authorization, rate limiting, PII handling, and production hardening are well-implemented with consistent patterns. There are no show-stopper P0 vulnerabilities. Several P1 issues should be addressed before or shortly after launch, mostly relating to production template configuration drift and a missing password complexity policy.

## Critical Issues (P0)

None found.

## High Issues (P1)

### P1-1: Production template uses HS256 JWT instead of RS256
- **File**: `.env.production.example:98` -- `ALGORITHM=HS256`
- **Risk**: The production environment template ships with `ALGORITHM=HS256`. While the code fully supports RS256 and the `docker-compose.prod.yml` agent service sets `GRPC_REQUIRE_TLS=true`, the JWT signing configuration still defaults to symmetric HS256. This means the shared secret (`JWT_SECRET`) is present in both the Go Gateway and Python Engine, increasing the blast radius of a key compromise.
- **Context**: The Go Gateway `auth.go:171-180` and Python `security.py:48-55` both support RS256 with proper key parsing. The code defaults to RS256 in production when `JWT_PRIVATE_KEY` is set. However, the `.env.production.example` never sets `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` and explicitly sets `ALGORITHM=HS256`.
- **Recommendation**: Update `.env.production.example` to set `ALGORITHM=RS256` and add `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` fields with instructions for generating RSA key pairs.

### P1-2: RBAC disabled in production template
- **File**: `.env.production.example:45` -- `SPARKLE_RBAC_ENABLED=false`
- **Risk**: The Python settings validator (`settings.py:1019-1021`) correctly enforces `SPARKLE_RBAC_ENABLED=True` in production, meaning this template value will actually be **rejected at startup** with a `ValueError`. However, the template itself documents the wrong value, which will confuse operators.
- **Recommendation**: Change `.env.production.example` to `SPARKLE_RBAC_ENABLED=true` and add corresponding RBAC database URLs.

### P1-3: Access token expiry set to 24 hours in production template
- **File**: `.env.production.example:96` -- `ACCESS_TOKEN_EXPIRE_MINUTES=1440`
- **Risk**: 24-hour access tokens are excessively long for a mobile app. If a token is leaked, the attacker has a full day of access. The code default is 30 minutes (`settings.py:216`), which is appropriate.
- **Recommendation**: Change to `ACCESS_TOKEN_EXPIRE_MINUTES=30` (or maximum 60) in the production template.

### P1-4: Password minimum length only 6 characters
- **File**: `backend/app/schemas/user.py:48` -- `min_length=6, max_length=100`
- **Risk**: 6-character passwords are trivially crackable. No complexity requirements (uppercase, digits, special characters) are enforced.
- **Recommendation**: Increase `min_length` to 8 minimum and add a password complexity validator (at least one digit, one uppercase letter).

### P1-5: gRPC user-id metadata used without cross-validation in some code paths
- **File**: `backend/app/services/agent_grpc_service.py:200-229` and `backend/app/api/grpc_auth.py:100-118`
- **Risk**: The `get_verified_user_id()` function in `grpc_auth.py:116-118` returns `metadata.get("user-id")` directly. While the `AuthInterceptor` validates that the metadata `user-id` matches the JWT `sub` claim when both are present, if only `user-id` metadata is provided (no JWT), and the call goes through the `INTERNAL_API_KEY` path, the user-id is trusted without validation. The `agent_grpc_service.py` has its own `_validate_request` that extracts user-id from metadata at line 200.
- **Mitigation**: Internal API key calls are service-to-service only, and both interceptor and gateway set the user-id from the JWT. The risk is low in practice but the defense-in-depth could be improved.
- **Recommendation**: Add an explicit comment or assertion that internal API key calls must only come from trusted services, and consider adding a secondary user-id validation for high-sensitivity operations.

## Medium Issues (P2)

### P2-1: No account deletion hard-delete implementation visible
- **File**: `backend/app/api/v1/users.py:595-604`
- **Risk**: Account deletion schedules `purge_deleted_account` via Celery with a 30-day countdown, but the actual hard-delete logic was not found during this audit. If the Celery task is not implemented, user data will be anonymized but never truly purged.
- **Recommendation**: Verify `purge_deleted_account` task implementation exists and covers all user data tables (conversations, memories, files, sessions, achievements, etc.).

### P2-2: WS query token auth disabled in production but not explicitly documented
- **File**: `backend/app/config/settings.py:1112` -- `WS_ALLOW_QUERY_TOKEN` defaults to `False` in production.
- **Mitigation**: The code correctly disables JWT-in-query-string for production. However, `.env.production.example` does not explicitly document this setting.
- **Recommendation**: Add `WS_ALLOW_QUERY_TOKEN=false` to `.env.production.example` with a comment explaining why.

### P2-3: Token revocation `revoke_all_user_tokens` is a no-op
- **File**: `backend/app/core/token_revocation.py:82-100`
- **Risk**: The `revoke_all_user_tokens` method returns 0 and logs, with a comment acknowledging it needs Redis SCAN for production use. The `set_user_revoked_before` in `security.py` is the actual mechanism used for "revoke all" -- the token revocation service method is dead code.
- **Mitigation**: The actual logout flow uses `set_user_revoked_before` and `revoke_all_sessions_for_user` which work correctly. The dead code in `token_revocation_service` is misleading.
- **Recommendation**: Remove or implement the `revoke_all_user_tokens` method; add a code comment explaining the actual revocation mechanism.

### P2-4: Guest login creates accounts with predictable usernames and no rate limit per device
- **File**: `backend/app/api/v1/auth.py:812-918`
- **Risk**: Guest login has a rate limit of `5/15minutes` in production, but there is no device fingerprinting. An attacker could create unlimited guest accounts by rotating IPs. Guest accounts get a 7-day access token (`access_expires_delta=timedelta(days=7)`) which is very long.
- **Recommendation**: Consider adding device fingerprinting or CAPTCHA for guest account creation. Reduce guest access token expiry to 24 hours max.

### P2-5: No CSRF protection for non-WebSocket endpoints
- **File**: `backend/gateway/internal/middleware/cors.go`
- **Risk**: The Go Gateway relies entirely on CORS and Bearer token auth for CSRF protection. For API-only backends serving a mobile app, this is generally sufficient. However, if any browser-based admin panels are added, CSRF tokens would be needed.
- **Recommendation**: Document that CSRF protection is provided by Bearer token auth (not cookies) and ensure no cookie-based auth is introduced.

### P2-6: File upload MIME type validation only checks extension
- **File**: `backend/gateway/internal/handler/file_handler.go:24-44`
- **Risk**: `allowedMimeTypesByExt` maps extensions to MIME types, but the actual content of uploaded files is not inspected (no magic byte checking). An attacker could upload a malicious file with a `.pdf` extension.
- **Mitigation**: File content is processed by the Python backend which has its own validation. The prepare/complete upload flow goes through MinIO presigned URLs.
- **Recommendation**: Consider adding server-side content-type verification (magic bytes) in the upload completion handler.

### P2-7: Rate limiter bypass potential via X-Forwarded-For header
- **File**: `backend/app/core/rate_limiting.py:18-27`
- **Risk**: The Python rate limiter uses `X-Forwarded-For` header directly as the client identifier. An attacker behind the same proxy could spoof this header to bypass rate limits. The Go Gateway rate limiter uses `c.ClientIP()` which is Gin's built-in method and is similarly affected if not configured with `TrustedProxies`.
- **Mitigation**: In production, the Go Gateway sits behind nginx which should set/override X-Forwarded-For. The Python rate limiter is secondary to the Gateway's limiter.
- **Recommendation**: Configure Gin's `TrustedProxies` to only trust the nginx/load-balancer IP. For Python, rely primarily on the Gateway's rate limiting.

## Low Issues (P3)

### P3-1: Admin secret comparison logging in development
- **File**: `backend/gateway/internal/middleware/auth.go:365-367` -- `log.Printf("Auth failed: missing token")` and similar
- **Risk**: These log statements are at INFO level and do not contain sensitive data, but they could be more structured.
- **Recommendation**: Migrate to structured logging (zap) for consistency with the rest of the middleware.

### P3-2: CORS `Access-Control-Max-Age` set to 24 hours
- **File**: `backend/gateway/internal/middleware/cors.go:20`
- **Risk**: A 24-hour preflight cache (`Access-Control-Max-Age: 86400`) means CORS policy changes take up to a day to propagate to clients. This is fine for stable production but may confuse during development.
- **Recommendation**: Consider reducing to 1 hour (`3600`).

### P3-3: `.env` file is tracked in repository root
- **File**: `.env` exists at repository root and is in `.gitignore` (`**/.env`)
- **Risk**: The `.env` file is properly ignored, but its existence at the root could lead to accidental commits if `.gitignore` rules are modified.
- **Recommendation**: Verify no secrets are in the tracked `.env` file via `git ls-files .env`.

### P3-4: LLM safety service patterns are regex-only
- **File**: `backend/app/core/llm_safety.py:43-94`
- **Risk**: Prompt injection detection relies on regex pattern matching, which can be bypassed with encoding tricks, Unicode variations, or creative phrasing. The `is_safe` threshold (no violations AND `risk_score < 0.7`) allows medium-risk content through.
- **Mitigation**: The safety service is defense-in-depth, not the primary security boundary. Actual LLM output is controlled by system prompts and tool constraints.
- **Recommendation**: Consider periodic updates to patterns and eventually integrate a lightweight classifier model.

### P3-5: Event retention only 30 days
- **File**: `backend/app/config/settings.py:753-754` -- `EVENT_RETENTION_DAYS: int = 30`
- **Risk**: 30-day retention is appropriate for operational data but may conflict with regulatory requirements for audit log retention in some jurisdictions.
- **Recommendation**: Make retention configurable per data category (audit logs: 1+ year, behavioral events: 30 days, session data: 7 days).

## Positive Findings

1. **RS256 JWT Support**: Full asymmetric JWT implementation with graceful HS256 backward compatibility during migration. Go Gateway verifies with public key only; Python Engine signs with private key. (`auth.go:452-469`, `security.py:48-71`)

2. **Fail-Closed Token Validation**: Both Go Gateway (`auth.go:516-599`) and Python Engine (`security.py:189-210`) implement fail-closed behavior for token revocation when Redis is unavailable in production. The Go Gateway has a sophisticated local blacklist cache for additional protection.

3. **Multi-Layer Rate Limiting**: Redis-backed distributed rate limiting with local fallback (`distributed_rate_limiter.go`), adaptive rate limiting for different endpoint types, and separate WebSocket connection/message rate limits.

4. **Comprehensive Security Headers**: CSP without `unsafe-inline`, HSTS in production, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy, and Cross-Origin isolation headers. (`security.go:9-49`)

5. **Strict CORS Configuration**: Origin validation uses proper URL parsing with scheme/host/port matching, wildcard subdomain support, and production enforcement rejecting `*` wildcard and requiring HTTPS origins. (`cors.go:10-30`, `config.go:140-211`)

6. **PII Redaction**: Comprehensive PII redaction in the Aurora privacy module (`privacy.py`) covering emails, phone numbers, Chinese IDs, bank card numbers, and names. Laplace noise for differential privacy. SHA-256 hashing for log-safe identifiers.

7. **Field-Level Encryption**: AES-256-GCM via Fernet for PII at rest (`crypto.py`) with graceful migration support for legacy plaintext.

8. **Account Lockout**: Brute-force protection with 5 attempts / 15-minute lockout (`account_lockout.py`).

9. **Error Message Sanitization**: Both Go Gateway (`error_sanitizer.go`) and Python middleware sanitize error messages in production to prevent information leakage. Raw errors are logged internally but replaced with generic messages for clients.

10. **WebSocket Security**: Origin checking against allowed list, ticket-based authentication with single-use tickets (GET+DEL atomic script), JWT header/query validation, message size limits, message rate limiting, and XSS sanitization via bluemonday.

11. **gRPC Security**: JWT authentication with user-id impersonation prevention (`grpc_auth.py:76-83`), constant-time internal API key comparison, mTLS support, and production TLS enforcement.

12. **Admin Endpoint Protection**: Admin routes require both admin secret (constant-time comparison) and admin JWT claim. Separate rate limiting. Chaos engineering routes have additional guard middleware.

13. **Internal API Protection**: Double-layer protection with API key (constant-time) and IP whitelist for `/internal` routes.

14. **Production Configuration Guards**: Python settings (`settings.py:1000-1145`) enforce SECRET_KEY, reject DEBUG=True, reject CORS `*`, require HTTPS origins, require PRODUCTION_URL, reject placeholder secrets, and enforce RBAC.

15. **Data Minimization**: GOV-013 Data Minimization Auditor (`data_minimization.py`) with per-model scope enforcement, stripping unauthorized fields before persistence.

16. **Kill Switch Safety**: Tri-state (off/shadow/live) protocol with Redis override, Prometheus gauge exposure, and proper normalization. (`kill_switch.py`)

17. **Container Security**: Production compose runs as non-root user (`SPARKLE_APP_UID:10001`), internal-only Docker network for app services, nginx handles external TLS termination.

18. **GDPR Compliance**: Account deletion endpoint with re-authentication requirement, immediate anonymization, and 30-day hard-delete scheduling. (`users.py:540-606`)

19. **Secret Management**: `.env` files properly gitignored, secrets validated as non-placeholder in production, separate per-service credentials for Redis and database.

## Files Audited

### Go Gateway
- `backend/gateway/internal/middleware/auth.go` (671 lines)
- `backend/gateway/internal/middleware/cors.go` (31 lines)
- `backend/gateway/internal/middleware/security.go` (51 lines)
- `backend/gateway/internal/middleware/rate_limit.go` (537 lines)
- `backend/gateway/internal/middleware/distributed_rate_limiter.go` (364 lines)
- `backend/gateway/internal/middleware/ws_auth.go` (173 lines)
- `backend/gateway/internal/middleware/internal_api.go` (28 lines)
- `backend/gateway/internal/middleware/internal_ip_whitelist.go` (72 lines)
- `backend/gateway/internal/middleware/request_context.go` (44 lines)
- `backend/gateway/internal/config/config.go` (330+ lines examined)
- `backend/gateway/internal/handler/auth.go` (232 lines)
- `backend/gateway/internal/handler/websocket_proxy.go` (667 lines)
- `backend/gateway/internal/handler/ws_hardening.go` (49 lines)
- `backend/gateway/internal/handler/file_handler.go` (549 lines)
- `backend/gateway/internal/handler/error_sanitizer.go` (219 lines)
- `backend/gateway/cmd/server/setup.go` (route registration lines)

### Python Engine
- `backend/app/core/security.py` (338 lines)
- `backend/app/core/crypto.py` (64 lines)
- `backend/app/core/logsafe.py` (57 lines)
- `backend/app/core/rate_limiting.py` (40 lines)
- `backend/app/core/token_revocation.py` (105 lines)
- `backend/app/core/kill_switch.py` (139 lines)
- `backend/app/core/account_lockout.py` (89 lines)
- `backend/app/core/llm_safety.py` (395 lines)
- `backend/app/core/data_minimization.py` (712 lines)
- `backend/app/aurora/privacy.py` (143 lines)
- `backend/app/config/settings.py` (1150 lines)
- `backend/app/api/v1/auth.py` (1062 lines)
- `backend/app/api/v1/users.py` (account deletion section)
- `backend/app/api/grpc_auth.py` (119 lines)
- `backend/grpc_server.py` (gRPC TLS/reflection section)

### Configuration & Infrastructure
- `.env.example` (260 lines)
- `.env.production.example` (426 lines)
- `docker-compose.prod.yml` (759 lines)
- `.gitignore` (env file rules)
