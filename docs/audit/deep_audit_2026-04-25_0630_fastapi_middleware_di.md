# 深度审计 #62 — Python FastAPI 中间件 + 依赖注入层完整链路

> **日期**: 2026-04-25 06:30
> **模块**: Python FastAPI Middleware + DI — 中间件链 → 依赖注入 → 异常处理 → CORS/安全 → DB会话管理
> **范围**: `backend/app/main.py`, `backend/app/api/deps.py`, `backend/app/api/middleware.py`, `backend/app/core/security.py`, `backend/app/db/session.py`
> **总计**: 16 个文件, ~3,200 行
> **审计员**: Claude Deep Auditor (Round 62)

---

## 1. Audit Scope

| Layer | Coverage |
|-------|----------|
| Middleware Chain | Registration order, BaseHTTPMiddleware usage, request/response flow |
| Dependency Injection | DB session lifecycle, auth resolution, service instantiation |
| Exception Handling | Global handlers, status code mapping, error leakage |
| CORS & Security | Origins, credentials, headers, preflight |
| Performance | Middleware overhead, DB pool, async correctness |
| gRPC Auth | Interceptor logic, JWT validation, impersonation prevention |

---

## 2. File Inventory

| File | Lines | Role |
|------|-------|------|
| `backend/app/main.py` | 532 | App factory, middleware registration, exception handlers, lifespan |
| `backend/app/api/middleware.py` | 215 | RequestContextMiddleware, IdempotencyMiddleware |
| `backend/app/api/deps.py` | 151 | DI: get_current_user_id, get_current_user, get_optional_current_user, get_current_active_user, get_current_active_superuser |
| `backend/app/api/grpc_auth.py` | 118 | gRPC AuthInterceptor with JWT + internal API key |
| `backend/app/core/exceptions.py` | 162 | Custom exception hierarchy (SparkleException family) |
| `backend/app/config/settings.py` | 769 | Pydantic Settings with validators |
| `backend/app/db/session.py` | 189 | AsyncSessionLocal, get_db(), get_db_no_commit(), get_db_context() |
| `backend/app/core/security.py` | 284 | JWT encode/decode, token revocation, blacklist |
| `backend/app/core/rate_limiting.py` | 40 | SlowAPI rate limiter setup |
| `backend/app/core/idempotency.py` | 231 | IdempotencyStore (Memory/Redis/DB implementations) |
| `backend/app/core/cache.py` | 260 | CacheService (Redis + local fallback) |
| `backend/app/core/tracing.py` | 35 | OpenTelemetry tracer setup |
| `backend/app/core/safe_error_messages.py` | 33 | gRPC-safe error message builder |
| `backend/app/core/redis_utils.py` | 57 | Redis URL/password helpers |
| `backend/app/db/url.py` | 36 | DB URL normalization |
| `backend/app/config_production.py` | 380 | Legacy production config (unused?) |

---

## 3. Data Flow: Middleware Execution Order

```
Request In
    |
    v
[1] IdempotencyMiddleware          (last registered = first executed)
    |   POST/PUT/PATCH only, protected paths
    |   Reads body, checks Redis, caches response
    v
[2] CORSMiddleware                  (Starlette built-in)
    |   CORS preflight, origin check
    v
[3] RequestContextMiddleware        (request ID + trace ID injection)
    |   Sets request.state.request_id, request.state.trace_id
    v
[4] SecurityHeadersMiddleware       (first registered = last executed)
    |   Adds X-Content-Type-Options, X-Frame-Options, etc.
    v
[5] SlowAPI Limiter                 (added via setup_rate_limiting)
    |   Rate limit check per IP:path
    v
[6] OpenTelemetry Instrumentation   (auto-instrumented)
    v
Route Handler
    |
    v
DI Resolution: get_db() -> AsyncSession, get_current_user() -> User
    |
    v
Response Out (headers added in reverse)
```

---

## 4. Findings

### P0 (Critical / Blocking)

#### P0-01: `logger` NameError in `security.py:blacklist_token`
**File**: `backend/app/core/security.py:271`
**Severity**: Runtime crash on blacklist failure

The function `blacklist_token` references `logger.error(...)` but no `logger` is imported in the module. The only imports are `asyncio`, `datetime`, `uuid`, `jose`, `passlib`, `sqlalchemy`, and internal app modules. When token blacklisting fails after retries, this will raise `NameError: name 'logger' is not defined`, silently swallowing the original error and potentially returning `None` instead of `False`.

```python
# Line 269-278
                if attempt == max_retries - 1:
                    # Log failure on final attempt
                    logger.error(        # <-- NameError: 'logger' is not defined
                        "token_blacklist_failed",
                        jti_prefix=jti[:8] if len(jti) > 8 else jti,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempts=max_retries
                    )
                    return False
```

**Impact**: Token revocation failures go unlogged and may mask security incidents. The outer `try/except` in callers may catch the NameError, leading to silent security gaps.

**Fix**: Add `from loguru import logger` at the top of `backend/app/core/security.py`.

---

#### P0-02: `get_db_context()` uses `asyncio.run()` -- crashes inside running event loop
**File**: `backend/app/db/session.py:142-173`
**Severity**: Runtime crash in Celery tasks running in async mode

The `get_db_context()` function calls `asyncio.run()` for commit/rollback/close. If used inside a running event loop (e.g., Celery with `gevent`/`eventlet` pool, or any async task runner), this raises `RuntimeError: This event loop is already running`.

```python
# Line 157-173
@contextmanager
def get_db_context():
    session = AsyncSessionLocal()
    try:
        yield session
        import asyncio
        asyncio.run(_commit_session(session))   # <-- Crashes if loop already running
    except Exception:
        import asyncio
        asyncio.run(_rollback_session(session))  # <-- Same crash
        raise
    finally:
        import asyncio
        asyncio.run(_close_session(session))     # <-- Same crash
```

**Impact**: Three Celery task files use this:
- `backend/app/tasks/accountability_tasks.py` (5 call sites)
- `backend/app/tasks/update_similarities.py` (4 call sites)
- `backend/app/tasks/guest_cleanup.py` (2 call sites)

If Celery ever runs in an async context (or if these tasks are called from async code), the DB session will not be properly committed/closed, leading to connection leaks.

**Fix**: Use `asyncio.get_event_loop().run_until_complete()` with a guard, or provide a dedicated async version. Alternatively, use `nest_asyncio` if synchronous Celery tasks must share the process with async code.

---

### P1 (High Priority / Should Fix)

#### P1-01: Three `BaseHTTPMiddleware` subclasses cause body consumption + streaming issues
**File**: `backend/app/main.py:366`, `backend/app/api/middleware.py:16,40`
**Severity**: Performance degradation, potential streaming breakage

All three custom middleware classes inherit from `BaseHTTPMiddleware`. This Starlette base class wraps request/response in a way that:
1. Reads the entire response body into memory before sending (breaks true streaming).
2. Creates a new `Request` object per middleware layer, copying scope.
3. Does not support `background` tasks properly.

The `IdempotencyMiddleware` at line 40 is especially problematic: it calls `await request.body()` (line 131) which consumes the body, then the SSE streaming path re-wraps `response.body_iterator`. Under high concurrency this creates memory pressure.

```python
# backend/app/api/middleware.py:131
body_bytes = await request.body()  # Consumes entire body into memory
```

**Impact**: On streaming chat responses (`/api/v1/chat/stream`), every response is buffered through `BaseHTTPMiddleware`'s internal `iterate_in_threadpool` wrapper, adding latency and memory overhead per request.

**Fix**: Migrate to pure ASGI middleware (implementing `async def __call__(self, scope, receive, send)`) for hot-path middleware, especially `RequestContextMiddleware` and `IdempotencyMiddleware`.

---

#### P1-02: `IdempotencyMiddleware` performs JWT decode on every protected POST request
**File**: `backend/app/api/middleware.py:57-69`
**Severity**: Performance (double JWT decode per request)

The `_extract_user_id` method in `IdempotencyMiddleware` calls `decode_token(token)` which does a full JWT verification + Redis blacklist check + user revocation check. This runs before the route handler, which then runs `get_current_user_id` that does the same decode again.

```python
# Lines 57-69
async def _extract_user_id(self, request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        from app.core.security import decode_token
        payload = await decode_token(token, expected_type="access")  # Full decode #1
        return payload.get("sub")
    except Exception:
        return None
```

Then `deps.py:34` does `payload = await decode_token(token, expected_type="access")` again -- decode #2.

**Impact**: Double JWT verification + double Redis lookups (blacklist + user revocation) per authenticated POST to protected paths. With 494 endpoints using `Depends(get_db)`, the overhead is significant.

**Fix**: Extract user_id from the raw JWT payload (without full verification) for idempotency key namespacing, or store the decoded payload in `request.state` after the first decode and reuse it.

---

#### P1-03: No `HTTPException` custom handler -- inconsistent error response format
**File**: `backend/app/main.py`
**Severity**: API contract inconsistency

There are 3 registered exception handlers:
- `RequestValidationError` (line 481) -> returns `{"success": False, "error_code": "ValidationError", ...}`
- `SparkleException` (line 496) -> returns `{"success": False, "error_code": ..., "message": ..., "request_id": ..., "trace_id": ...}`
- `Exception` (line 513) -> returns `{"success": False, "error_code": "InternalServerError", ...}`

But `HTTPException` (used 494 times across API routes) uses FastAPI's default handler, which returns:
```json
{"detail": "..."}
```

This is a different schema from the custom format. Any client expecting `success`, `error_code`, `request_id`, `trace_id` will not get them for `HTTPException` responses.

**Impact**: Frontend error handling must have two code paths: one for structured errors and one for raw `HTTPException` detail format.

**Fix**: Add a custom `HTTPException` handler that matches the `SparkleException` format.

---

#### P1-04: `get_db()` always commits even for read-only operations
**File**: `backend/app/db/session.py:107-125`
**Severity**: Unnecessary DB round-trips

```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()   # <-- Commits even on GET/read-only endpoints
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

Every endpoint using `Depends(get_db)` triggers a COMMIT on the session, even for pure GET reads. With `pool_size=20` and `max_overflow=40`, this means up to 60 concurrent COMMIT operations even for read-only traffic.

**Impact**: Unnecessary WAL writes on PostgreSQL, increased I/O, slightly elevated latency on read-heavy endpoints.

**Fix**: Use `get_db_no_commit()` for read-only endpoints, or change `get_db()` to only commit if `session.in_transaction()` or `session.dirty`/`session.new` has entries.

---

#### P1-05: `deps.py` has inline structlog import with ImportError fallback -- inconsistent logging
**File**: `backend/app/api/deps.py:68-83, 113-128`
**Severity**: Observability gap

The session touch error logging uses a try/except pattern to import structlog, falling back to stdlib logging:

```python
# Lines 68-83
try:
    import structlog
    structlog.get_logger().warning(
        "session_touch_failed",
        user_id=str(user.id),
        error=str(e),
        error_type=type(e).__name__,
    )
except ImportError:
    logger.warning(
        "session_touch_failed user_id=%s error=%s error_type=%s",
        str(user.id),
        str(e),
        type(e).__name__,
    )
```

`structlog>=24.1.0` is a declared dependency -- the `ImportError` branch is dead code. Worse, the two log formats are incompatible: structlog uses keyword args, stdlib uses `%s` interpolation. The duplication occurs in two places (lines 68-83 and 113-128).

**Impact**: If structlog is somehow unavailable at runtime, log format silently changes from structured JSON to plain text, breaking log aggregation pipelines.

**Fix**: Use `from loguru import logger` consistently (the rest of the codebase uses loguru), or import structlog at module level.

---

#### P1-06: `AuthorizationError` in `get_current_active_superuser` is caught but not by HTTPException handler
**File**: `backend/app/api/deps.py:140-146`
**Severity**: Inconsistent 403 handling

```python
async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        from app.core.exceptions import AuthorizationError
        raise AuthorizationError("...")  # Caught by SparkleException handler -> 403
    return current_user
```

This correctly raises `AuthorizationError` which is a `SparkleException` subclass and handled by the global handler. However, `get_current_active_user` raises `AuthenticationError` for inactive users (line 137), which is also a `SparkleException`. This is correct, but note that many endpoints still raise plain `HTTPException(status_code=403, ...)` instead of using `AuthorizationError`, leading to inconsistent 403 response format.

**Fix**: Audit all `raise HTTPException(status_code=403, ...)` across the API layer and replace with `raise AuthorizationError(...)`.

---

### P2 (Low Priority / Polish)

#### P2-01: Missing security headers: `Referrer-Policy`, `Permissions-Policy`
**File**: `backend/app/main.py:366-399`
**Severity**: Minor security hardening gap

The `SecurityHeadersMiddleware` sets `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Strict-Transport-Security`, and `Content-Security-Policy`. Missing:
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Embedder-Policy: require-corp` (for SSE/Fetch)

**Fix**: Add the missing headers to `SecurityHeadersMiddleware.dispatch()`.

---

#### P2-02: CSP `connect-src 'self'` may block LLM/3rd-party API calls from admin UI
**File**: `backend/app/main.py:388-398`
**Severity**: Potential functional issue for admin/docs UI

The production CSP sets `connect-src 'self'`. If the Swagger UI (`/docs`) or ReDoc (`/redoc`) tries to load external schema references or if any frontend admin panel makes calls to the LLM API from the browser, those will be blocked.

**Fix**: Verify whether `/docs` and `/redoc` are disabled in production (they shouldn't be needed), and add LLM API origins to `connect-src` if needed.

---

#### P2-03: `X-XSS-Protection: 1; mode=block` is deprecated
**File**: `backend/app/main.py:371`
**Severity**: Minor -- header is ignored by modern browsers

The `X-XSS-Protection` header is deprecated. Chrome removed XSS auditor in 2019. Modern browsers rely on CSP instead.

**Fix**: Remove `X-XSS-Protection` or set to `0` to avoid triggering legacy browser XSS auditor bugs.

---

#### P2-04: Idempotency lock TTL is 30 seconds -- may be too short for long requests
**File**: `backend/app/core/idempotency.py:94`
**Severity**: Potential concurrent duplicate processing

```python
self._lock_ttl = 30  # seconds
```

If a request (e.g., plan creation with LLM reasoning) takes more than 30 seconds, the lock expires and a duplicate request could be processed concurrently.

**Fix**: Make TTL configurable or extend to 120 seconds.

---

#### P2-05: `RedisIdempotencyStore.lock()` fails open on Redis errors
**File**: `backend/app/core/idempotency.py:135`
**Severity**: Reduced idempotency guarantee under Redis failure

```python
except Exception as exc:
    logger.warning(f"Redis idempotency lock failed: {exc}")
    return True  # Fail open to avoid blocking requests
```

When Redis is unavailable, lock acquisition returns `True` (success), meaning duplicate requests will not be prevented.

**Fix**: Consider failing closed (return `False`) for critical write paths, or at least log a structured warning.

---

#### P2-06: `config_production.py` appears to be unused legacy code
**File**: `backend/app/config_production.py`
**Severity**: Code hygiene

This file defines a separate `ProductionSettings` class with its own `settings` singleton. The main app uses `app.config.settings` from `app/config/settings.py`. Having two settings systems creates confusion.

**Fix**: Remove or clearly deprecate `config_production.py`.

---

#### P2-07: `get_db_context()` leaks sessions on asyncio.run() failure
**File**: `backend/app/db/session.py:157-173`
**Severity**: Connection leak edge case

If `asyncio.run(_commit_session(session))` raises (e.g., DB connection lost), the `finally` block calls `asyncio.run(_close_session(session))` which may also fail. The session is never explicitly returned to the pool.

**Fix**: Use `try/finally` with `session.close()` directly, or use a more robust async-in-sync pattern.

---

#### P2-08: Rate limiter default is 600/min with IP:path key -- may be too generous
**File**: `backend/app/core/rate_limiting.py:29-32`
**Severity**: Potential abuse vector

```python
limiter = Limiter(
    key_func=get_real_ip,
    default_limits=["600 per minute"]
)
```

600 requests/minute per IP per path is quite generous. An attacker with a botnet could make 600 requests/minute to each endpoint from each IP.

**Fix**: Consider lowering to 120-200/min for default, with endpoint-specific overrides for expensive operations (chat, LLM).

---

## 5. Compliance Items (Verified OK)

| Item | Status | Detail |
|------|--------|--------|
| JWT validation in DI | OK | `decode_token` checks exp, sub, type, jti blacklist, user revocation, session revocation |
| gRPC impersonation prevention | OK | `AuthInterceptor` validates metadata user-id matches JWT sub claim |
| Constant-time key comparison | OK | `secrets.compare_digest` for internal API key |
| Request tracing propagation | OK | X-Request-ID + X-Trace-ID set in middleware, returned in error responses |
| Production SECRET_KEY enforcement | OK | Settings validator raises if empty |
| Production CORS wildcard rejection | OK | Settings validator raises if `*` in production origins |
| DEBUG=False enforced in production | OK | Model validator raises if DEBUG=True in prod |
| TLS enforcement for gRPC in production | OK | `GRPC_REQUIRE_TLS` defaults to True in prod |
| Token blacklist TTL aligned to expiry | OK | Blacklist TTL = token exp - now, auto-expires |
| Session lifecycle management | OK | get_db() auto-commit/rollback/close with async context |
| Idempotency key size limit | OK | 256 byte max prevents Redis OOM |
| Error response format consistency (partial) | OK for SparkleException | See P1-03 for HTTPException gap |

---

## 6. Statistics

| Metric | Value |
|--------|-------|
| Files audited | 16 |
| Total lines reviewed | ~3,200 |
| Middleware classes | 3 custom + 1 CORS + 1 rate limiter + OTEL |
| Exception handler registrations | 4 (ValidationError, SparkleException, Exception, RateLimitExceeded) |
| DI functions | 5 (get_current_user_id, get_current_user, get_optional_current_user, get_current_active_user, get_current_active_superuser) |
| DB session factories | 3 (get_db, get_db_no_commit, get_db_context) |
| Endpoints using Depends(get_db) | ~494 |
| Endpoints using Depends(get_current_user) | ~496 |
| P0 findings | 2 |
| P1 findings | 6 |
| P2 findings | 8 |

---

## 7. Fix Priority

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| **P0-01** | logger NameError in security.py | 1 line | Prevents silent security failures |
| **P0-02** | asyncio.run() in get_db_context() | Small | Prevents runtime crashes in async Celery |
| **P1-01** | BaseHTTPMiddleware streaming issues | Medium | Reduces streaming latency |
| **P1-02** | Double JWT decode in idempotency | Small | Cuts auth overhead ~50% on POST |
| **P1-03** | Missing HTTPException handler | Small | Consistent error format |
| **P1-04** | Unnecessary commits on reads | Small | Reduces DB write load |
| **P1-05** | Inconsistent structlog/loguru usage | Small | Log format consistency |
| **P1-06** | Mixed AuthorizationError/HTTPException(403) | Medium | Consistent 403 format |
| **P2-01** | Missing security headers | Small | Defense in depth |
| **P2-04** | Idempotency lock TTL too short | Small | Prevents duplicate processing |
| **P2-06** | Unused config_production.py | Small | Code hygiene |

---

## 8. Cross-Round Causal Chains

| From Round | Finding | Links to This Round |
|------------|---------|---------------------|
| Data Utilization (2026-04-06) | "5.0/10 data utilization" claim | The DI layer (`get_current_user`) correctly injects user context but the pipeline after that is what drops data -- the DI layer itself is structurally sound |
| Aurora Stage 20 (2026-04-21) | Sufficiency Judge + Conflict Resolver | These rely on `get_db()` session management -- P1-04 (unnecessary commits) adds latency to Stage 20 features |
| Aurora Stage 22 Dispatch | Baseline Repair | P0-01 (logger NameError) could mask Stage 22 telemetry failures during token blacklist operations |
| Profile Section Audit (2026-03-31) | "4 P0 + 6 P1" fixes | Several of those fixes touched auth endpoints that still use `HTTPException` directly (P1-03) |

---

*End of Deep Audit #61*

---

## Chris (Session 7) 复核 — 2026-04-23

> 逐项验证 P0 发现对主项目当前代码 (`/Users/brsama/code/GitHub/Sparkle-project/`)。

### P0 验证

| 原始发现 | 文件 | 行号 | 当前状态 | 结论 |
|----------|------|------|---------|------|
| P0-01 logger NameError in blacklist_token | `security.py` | :271 `logger.error(...)` | `from loguru import logger` 未导入, 仍仅使用 `jose/passlib/sqlalchemy` 等 | **CONFIRMED** |
| P0-02 asyncio.run() in get_db_context | `session.py` | :164, :168, :173 | `asyncio.run()` 仍用于 commit/rollback/close | **CONFIRMED** |

### P1 抽样验证

| 发现 | 结论 |
|------|------|
| P1-03 无 HTTPException 自定义处理器 | **CONFIRMED** — `main.py` 仍仅有 ValidationError + SparkleException + Exception 三个 handler |
| P1-04 get_db() 无条件 commit | **CONFIRMED** — `session.py:107-125` 仍在 yield 后直接 `await session.commit()` |

### P2 修正

| 发现 | 结论 |
|------|------|
| P2-01 缺少 Referrer-Policy/Permissions-Policy | **部分 FALSE** — Go Gateway (`security.go:41-45`) 已有完整设置。Python 层仅在绕过 Go 的本地开发场景下缺失 |

### 总结

报告质量高，行号精确。2个P0全部确认仍存在。P0-01(添加1行 `from loguru import logger`) 是最高优先级修复——单行即可消除 NameError 风险。P0-02(asyncio.run) 需要更谨慎的修复方案。报告覆盖面广(16文件)，数据流图准确。
