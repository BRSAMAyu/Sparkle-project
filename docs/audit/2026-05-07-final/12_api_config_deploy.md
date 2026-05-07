# API Endpoints, Configuration & Deployment Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Sparkle project has a well-architected, production-grade deployment configuration with comprehensive health checks, structured error handling, robust security validations, and a sophisticated Aurora kill-switch system. The codebase shows careful attention to operational concerns including rate limiting, idempotency, PII redaction, and distributed tracing. Several medium-priority issues were identified around health endpoint redundancy, production template defaults, and observability configuration.

## Critical Issues (P0)

None found.

## High Issues (P1)

### P1-1: `.env.production.example` has `SPARKLE_RBAC_ENABLED=false` and `GRPC_REQUIRE_TLS=false`

- **File**: `.env.production.example:45,206`
- The production template ships with `SPARKLE_RBAC_ENABLED=false`, but the settings validator (`backend/app/config/settings.py:1020-1021`) enforces `SPARKLE_RBAC_ENABLED must be True in production`. This creates a confusing mismatch: anyone copying the production template will get a startup crash.
- Similarly, `GRPC_REQUIRE_TLS=false` contradicts the production validation at `settings.py:1023-1024`.
- **Recommendation**: Change both defaults in `.env.production.example` to `true` and add a comment noting these are enforced.

### P1-2: `.env.production.example` has Aurora MODE values set to `shadow` while `docker-compose.prod.yml` and `settings.py` default to `live`

- **File**: `.env.production.example:284-318`
- The production example sets many Aurora switches to `shadow` (e.g., `AURORA_BAYESIAN_MODE=shadow`, `AURORA_SRL_MODE=shadow`), while the `docker-compose.prod.yml` service definitions all use `${VAR:-live}` and `settings.py` defaults to `live`. This inconsistency means:
  - If operators use the `.env.production.example` template, Aurora features will be in shadow mode
  - If they rely on docker-compose defaults, everything will be `live`
- **Recommendation**: Align the production template with the intended production posture. Document which Aurora stages should be `shadow` vs `live` at launch, and ensure both files agree.

## Medium Issues (P2)

### P2-1: Duplicate health check endpoint sets with different semantics

- **Files**: `backend/app/api/v1/health.py` and `backend/app/api/v1/health_production.py`
- Two separate health check routers exist, mounted at the same prefix `/health`:
  - `health.py` (mounted at root): `/health`, `/health/liveness`, `/health/readiness`, `/health/database` -- unauthenticated, returns status/degraded/unhealthy
  - `health_production.py` (mounted at `/health`): `/health`, `/health/ready`, `/health/live`, `/health/detailed`, `/health/metrics`, `/health/capacity`, etc. -- most require superuser auth
- The router registration order in `router.py` registers `health_production` second (line 215), so its `/health` route overrides `health.py`'s unauthenticated health check. This means the Docker healthcheck `curl -f http://localhost:8000/health` (used in `docker-compose.yml:190`) will fail because it requires superuser authentication.
- **Recommendation**: Either (a) ensure the unauthenticated `/health` endpoint is always reachable for Docker/K8s probes, or (b) update all Docker healthcheck URLs to use an unauthenticated path like `/health/liveness`.

### P2-2: Production `.env` template has hardcoded placeholder domain `api.sparkle.com`

- **File**: `.env.production.example:102,159`
- `BACKEND_CORS_ORIGINS=["https://api.sparkle.com"]` and `PRODUCTION_URL=https://api.sparkle.com` use a placeholder domain. If operators miss replacing these, the CORS validation in `settings.py:1064-1067` will reject requests to the actual domain.
- **Recommendation**: Use `<your-domain>` style placeholders consistent with the rest of the file, or add a loud comment.

### P2-3: Celery healthcheck for beat scheduler uses worker ping

- **File**: `docker-compose.prod.yml:386-391`
- The `celery_beat` service healthcheck uses `celery inspect ping -d celery@${HOSTNAME}` but the beat process does not respond to inspect ping (only workers do). This healthcheck will always fail.
- **Recommendation**: Use a file-based or process-based healthcheck for the beat scheduler (e.g., check for the PID file or use `celery -A app.core.celery_app inspect ping` without specifying a hostname).

### P2-4: `docker-compose.celery.yml` uses hardcoded `change-me` passwords as defaults

- **File**: `docker-compose.celery.yml:16-19`
- Default password values like `${REDIS_PASSWORD:-change-me}` are weak. While this is a standalone celery compose file, if it's ever used in a semi-production context, these defaults could be a security risk.
- **Recommendation**: Remove default fallbacks or require the variables to be set explicitly (use the `:?` syntax like the main compose file does for some secrets).

### P2-5: Error messages expose `str(e)` from database errors in health check

- **File**: `backend/app/api/v1/health.py:95-98`
- The `DatabaseHealth` model includes `error: str(e)` from database connection failures. In production, this could expose database hostname, port, or connection details.
- **Recommendation**: Sanitize the error message in production (strip host/port info) or only return it when `DEBUG=True`.

### P2-6: `settings.py` uses `ALGORITHM: str = "HS256"` but CLAUDE.md mentions RS256 for production

- **File**: `backend/app/config/settings.py:218`
- The comment says "Set to RS256 in production for asymmetric signing" but there is no production validator enforcing this. JWT_PRIVATE_KEY and JWT_PUBLIC_KEY are optional empty strings. Production could run with HS256.
- **Recommendation**: Add a production validator that requires RS256 and non-empty key paths when `ENVIRONMENT=production`.

### P2-7: `APP_VERSION: str = "0.1.0"` in settings

- **File**: `backend/app/config/settings.py:127`
- The app version is hardcoded as `0.1.0` and not overridable via environment variable. The `mobile/pubspec.yaml` shows version `1.0.0+1`. This version mismatch will appear in health check responses and monitoring.
- **Recommendation**: Make `APP_VERSION` configurable via env var or derive it from git tags / `pyproject.toml`.

### P2-8: OTLP exporter uses `insecure=True` unconditionally

- **File**: `backend/app/core/tracing.py:20`
- `OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)` always uses plaintext gRPC for trace export. In production, traces could be intercepted on the network between the Python engine and Tempo.
- **Recommendation**: Make this configurable via an env var (e.g., `OTEL_EXPORTER_OTLP_INSECURE`), defaulting to `True` for local dev but allowing TLS in production deployments where Tempo is on a separate host.

## Low Issues (P3)

### P3-1: Monitoring stack ports exposed on all interfaces in dev compose

- **File**: `docker-compose.yml:459,527,536`
- Prometheus (`9090`), Grafana (`3000`), and other monitoring ports are exposed on `0.0.0.0` (all interfaces) in the development compose file. The production compose correctly binds to `127.0.0.1`.
- **Recommendation**: Consider binding dev monitoring ports to `127.0.0.1` as well for consistency and local-only access.

### P3-2: Go Gateway Dockerfile uses `goproxy.cn` proxy unconditionally

- **File**: `backend/gateway/Dockerfile:8`
- `ENV GOPROXY=https://goproxy.cn,direct` is hardcoded for China network optimization. International builds will still use the China mirror as primary.
- **Recommendation**: Make this a build arg: `ARG GOPROXY=https://goproxy.cn,direct`.

### P3-3: API root endpoint has incomplete endpoint list

- **File**: `backend/app/api/v1/router.py:263-295`
- The `/api/v1/` root endpoint returns a hardcoded list of endpoints that does not include many registered routes (e.g., `/cognitive`, `/galaxy`, `/memory`, `/recommendations`, etc.). This is cosmetic but misleading for API discovery.
- **Recommendation**: Either auto-generate the list from registered routes or remove the hardcoded list.

### P3-4: `.env.example` does not document the `ADMIN_SECRET` variable

- **File**: `.env.example:41`
- `ADMIN_SECRET` is set in `.env.example` but not documented with a description of its purpose. The production template and docker-compose files reference it but never explain what it protects.
- **Recommendation**: Add a comment explaining that `ADMIN_SECRET` is used for admin-level endpoint protection.

### P3-5: Rate limiting key includes path, which may cause high cardinality

- **File**: `backend/app/core/rate_limiting.py:26-27`
- The rate limit key is `f"{ip}:{request.url.path}"`. This means each unique path creates a separate rate limit bucket. For a service with many parameterized paths (e.g., `/api/v1/tasks/{id}`), this could create high cardinality in the rate limit storage.
- **Recommendation**: Consider using the route template (without path parameters) instead of the full URL path.

### P3-6: `requirements.txt` includes development dependencies without a separate dev file

- **File**: `backend/requirements.txt:38-50`
- Development tools (`pytest`, `black`, `ruff`, `flake8`, `mypy`, `locust`) are included in the main requirements file. These get installed into the Docker image, increasing its size and attack surface.
- **Recommendation**: Split into `requirements.txt` (runtime) and `requirements-dev.txt` (development). The Dockerfile only installs the runtime file.

## Positive Findings

1. **Comprehensive production security validation** (`settings.py:1000-1144`): The settings model enforces SECRET_KEY presence, production-mode DEBUG=False, RBAC enabled, TLS required, HTTPS-only CORS, and validates all critical secrets are not placeholders. This is excellent defense-in-depth.

2. **Well-structured Docker configuration**: Both dev and prod compose files use multi-stage builds, non-root users (UID/GID 10001), resource limits, health checks with proper intervals/timeouts, and service dependencies with health conditions. The prod compose adds network isolation (edge/app networks), Redis ACL-based RBAC, and MinIO bucket-level access policies.

3. **Robust error handling**: Safe error messages (`safe_error_messages.py`) prevent internal details from leaking to clients. The error taxonomy (`error_codes.py` + `exceptions.py`) provides structured, user-friendly error responses in both Chinese and English via the `_zh()` i18n helper.

4. **Production-grade event bus**: The Redis Streams event bus (`event_bus.py`) includes retry with exponential backoff, dead letter queue with persistence, idempotency, stale message recovery via XAUTOCLAIM, auto-restart on consumer crash, and Prometheus metrics for DLQ depth and consumer lag.

5. **Idempotency middleware**: The `IdempotencyMiddleware` handles both regular and streaming (SSE) responses with proper cache key construction, size limits, and conflict detection.

6. **Aurora kill-switch system**: All 40+ Aurora feature switches follow the tri-state protocol (off/shadow/live) with proper env var propagation through all Docker compose files. The `AURORA_DEFAULT_MODE` override provides a convenient way to mass-control switch states.

7. **Structured logging and tracing**: Loguru with contextualized request IDs, OpenTelemetry integration with FastAPI/Redis/SQLAlchemy auto-instrumentation, and Prometheus metrics endpoint provide comprehensive observability.

8. **PII protection**: The `logsafe.py` module provides consistent PII hashing and masking across Python and Go layers, ensuring user IDs, emails, and usernames never appear in raw form in logs.

9. **Auth security**: Rate limiting per endpoint type (stricter in production), account lockout after failed attempts, JWT blacklist via Redis, session management with rotation on refresh, and anti-enumeration on registration.

10. **Buf proto management**: Proto files have linting (STANDARD rules), breaking change detection, and Go code generation via buf remote plugins, with a separate Dart generation config for mobile.

## Files Audited

### API Endpoints
- `backend/app/api/v1/router.py` -- main API router (295 lines, ~90 endpoint modules)
- `backend/app/api/v1/health.py` -- basic health check endpoints
- `backend/app/api/v1/health_production.py` -- production health with metrics/capacity
- `backend/app/api/v1/monitoring.py` -- WebSocket monitoring + device registration
- `backend/app/api/v1/observability.py` -- admin observability endpoints
- `backend/app/api/v1/event_bus_health.py` -- event bus admin health/DLQ
- `backend/app/api/v1/auth.py` -- authentication (register/login/social/guest)
- `backend/app/api/v1/tasks.py` -- task CRUD
- `backend/app/api/v1/plans.py` -- plan CRUD
- `backend/app/api/deps.py` -- dependency injection (auth, i18n)
- `backend/app/api/middleware.py` -- request context, idempotency middleware
- `backend/app/api/v1/__init__.py`

### Configuration
- `backend/app/config/settings.py` -- comprehensive settings with 200+ fields
- `backend/app/config/aurora.py`
- `backend/app/config/phase5_config.py`
- `backend/app/config/__init__.py`

### Core Infrastructure
- `backend/app/core/error_codes.py` -- error code enum
- `backend/app/core/exceptions.py` -- custom exception hierarchy
- `backend/app/core/event_bus.py` -- Redis Streams event bus
- `backend/app/core/rate_limiting.py` -- slowapi rate limiting
- `backend/app/core/metrics.py` -- Prometheus metrics definitions
- `backend/app/core/logsafe.py` -- PII redaction helpers
- `backend/app/core/safe_error_messages.py` -- user-safe error mapping
- `backend/app/core/tracing.py` -- OpenTelemetry setup
- `backend/app/core/celery_tasks.py` -- Celery task definitions (partial)
- `backend/app/main.py` -- FastAPI application entry point

### Docker & Deployment
- `docker-compose.yml` -- development compose (10 services)
- `docker-compose.prod.yml` -- production compose (17 services with monitoring)
- `docker-compose.celery.yml` -- standalone Celery stack
- `docker-compose.dev.yml` -- dev overlay (disables monitoring)
- `backend/Dockerfile` -- Python multi-stage build
- `backend/gateway/Dockerfile` -- Go multi-stage build
- `backend/docker-entrypoint.sh` -- DB migration entrypoint

### Build & Config Files
- `Makefile` -- 566 lines, comprehensive build/dev/test targets
- `.env.example` -- development environment template
- `.env.production.example` -- production environment template (426 lines)
- `.env.deploy.example` -- deployment environment template
- `buf.yaml` -- proto lint/breaking config
- `buf.gen.yaml` -- Go proto generation config
- `buf.gen.dart.yaml` -- Dart proto generation config
- `backend/requirements.txt` -- 114 Python dependencies
- `backend/gateway/go.mod` -- Go 1.24.0 module
- `mobile/pubspec.yaml` -- Flutter 1.0.0+1 project
