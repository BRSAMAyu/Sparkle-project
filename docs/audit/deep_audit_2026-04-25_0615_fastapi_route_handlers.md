# Deep Audit #60: Python FastAPI Route Handlers REST Endpoint Layer

**Date**: 2026-04-25
**Auditor**: Claude Opus 4.5 (automated deep audit)
**Scope**: `backend/app/api/` -- all REST endpoint files, dependency injection, middleware, gRPC auth
**Total Files Audited**: 80+ Python files in `backend/app/api/`
**Total Lines**: ~28,000 lines across v1 API files

---

## 1. Audit Scope

### Files Audited (Core Infrastructure)

| File | Lines | Role |
|------|-------|------|
| `backend/app/main.py` | 532 | FastAPI app setup, lifespan, middleware chain, exception handlers |
| `backend/app/api/deps.py` | 151 | Dependency injection (JWT auth, DB session, user resolution) |
| `backend/app/api/middleware.py` | 215 | Request context, idempotency middleware |
| `backend/app/api/grpc_auth.py` | 118 | gRPC JWT interceptor |
| `backend/app/api/v1/router.py` | 202 | Central API router (67 sub-routers) |

### Files Audited (Endpoint Handlers)

| File | Lines | Endpoints |
|------|-------|-----------|
| `backend/app/api/v1/auth.py` | 990 | 13 endpoints (register, login, social, guest, upgrade, password) |
| `backend/app/api/v1/chat.py` | 1044 | 7 endpoints (chat, stream, confirm, sessions, history) |
| `backend/app/api/v1/tasks.py` | 907 | 17 endpoints (CRUD, complete, abandon, feedback, resources) |
| `backend/app/api/v1/plans.py` | 820 | 14 endpoints (CRUD, archive, restore, quota, primary) |
| `backend/app/api/v1/users.py` | 687 | 14 endpoints (profile, password, social, sessions, delete) |
| `backend/app/api/v1/galaxy.py` | 858 | 15 endpoints (graph, nodes, mastery, search, expansion) |
| `backend/app/api/v1/error_book.py` | 222 | 8 endpoints (CRUD, analyze, review, semantic) |
| `backend/app/api/v1/files.py` | 80 | 2 endpoints (process, status) |
| `backend/app/api/v1/notifications.py` | 55 | 3 endpoints (list, create, mark-read) |
| `backend/app/api/v1/memory.py` | 432 | 7 endpoints (preferences, goals, episodic, retract, correct, export) |
| `backend/app/api/v1/memory_admin.py` | 485 | 14 endpoints (stats, health, jobs, budgets, release-gate, rollout) |
| `backend/app/api/v1/focus.py` | 169 | 7 endpoints (sessions, stats, LLM guide, heatmap) |
| `backend/app/api/v1/calendar.py` | ~100+ | CRUD + smart scheduling |
| `backend/app/api/v1/monitoring.py` | 344 | 8 endpoints (WS stats, health, devices) |
| `backend/app/api/v1/devices.py` | 172 | 3 endpoints (register, unregister, list) |
| `backend/app/api/v1/health.py` | 181 | 5 endpoints (health, liveness, readiness, database) |
| `backend/app/api/v1/observability.py` | 49 | 2 endpoints (run ledger, response trace) |
| `backend/app/api/v1/feedback_admin.py` | 49 | 2 endpoints (summary, bandit state) |

Plus ~50 additional endpoint files spot-checked for patterns.

---

## 2. Data Flow Diagram

```
Client (Flutter/Go Gateway)
    |
    |--[HTTPS]--> FastAPI (main.py)
    |               |
    |               +-- SecurityHeadersMiddleware
    |               +-- RequestContextMiddleware (X-Request-ID, X-Trace-ID)
    |               +-- CORSMiddleware
    |               +-- IdempotencyMiddleware (POST/PUT/PATCH on protected paths)
    |               +-- Rate Limiting (slowapi)
    |               |
    |               +-- Exception Handlers:
    |               |   +-- RequestValidationError -> 400 JSON
    |               |   +-- SparkleException -> mapped status JSON
    |               |   +-- Exception (catch-all) -> 500 (debug-only detail)
    |               |
    |               +-- API Router (/api/v1)
    |                   |
    |                   +-- auth.py      (no auth required)
    |                   +-- users.py     (get_current_user)
    |                   +-- chat.py      (get_current_user)
    |                   +-- tasks.py     (get_current_user)
    |                   +-- plans.py     (get_current_user)
    |                   +-- galaxy.py    (get_current_user_id)
    |                   +-- files.py     (verify_internal_token)
    |                   +-- monitoring.py (get_current_user -- WS only)
    |                   +-- memory_admin.py (get_current_active_superuser)
    |                   +-- observability.py (get_current_active_superuser)
    |                   +-- health.py    (public)
    |
    +--[gRPC]--> grpc_auth.py AuthInterceptor
                    |
                    +-- x-internal-api-key (secrets.compare_digest)
                    +-- Bearer JWT (decode_token + user-id cross-check)
```

---

## 3. Findings

### P0 -- Security / Correctness

#### P0-01: Timing-unsafe Internal API Key Comparison (files.py, visual_elements.py, achievements.py)

**Severity**: P0 (Security)
**Files**:
- `backend/app/api/v1/files.py:22`
- `backend/app/api/v1/visual_elements.py:55`
- `backend/app/api/v1/achievements.py:65`

The REST-side `verify_internal_token` uses `!=` for key comparison, which is vulnerable to timing attacks. The gRPC interceptor (`grpc_auth.py:53`) correctly uses `secrets.compare_digest`, but the REST endpoints do not.

```python
# files.py:22 -- VULNERABLE
async def verify_internal_token(x_internal_token: str | None = Header(None)) -> None:
    if settings.INTERNAL_API_KEY and x_internal_token != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal token")

# grpc_auth.py:53 -- CORRECT
if settings.INTERNAL_API_KEY and secrets.compare_digest(
    internal_api_key, settings.INTERNAL_API_KEY
):
```

**Fix**: Replace `!=` with `secrets.compare_digest()` in all three files.

---

#### P0-02: WebSocket Monitoring Endpoint Leaks All Active User/Group IDs

**Severity**: P0 (Security/Privacy)
**File**: `backend/app/api/v1/monitoring.py:53-81`

The `/ws/stats` endpoint returns all active WebSocket group keys and user IDs to any authenticated user. This exposes the online status and identifiers of all connected users.

```python
# monitoring.py:76-78
"details": {
    "groups": list(manager.active_connections.keys()),
    "users": list(manager.user_connections.keys()),
}
```

**Fix**: Replace with counts only, or restrict to `get_current_active_superuser`.

---

#### P0-03: `asyncio.create_task` for Email Sending Without Error Capture

**Severity**: P0 (Reliability)
**File**: `backend/app/api/v1/auth.py:654,726,900`

Email sending uses `asyncio.create_task()` which is fire-and-forget. The task reference is not stored, meaning if the event loop resets or the task raises an unhandled exception, it is silently lost. The registration endpoint (line 351) was correctly migrated to Celery, but `forgot-password`, `send-verification`, and `upgrade-guest` still use `asyncio.create_task`.

```python
# auth.py:654 -- forgot-password
asyncio.create_task(
    email_service.send_password_reset_email(
        to_email=user.email,
        reset_token=reset_token,
        username=user.nickname or user.username,
    )
)

# auth.py:351 -- register (CORRECTLY uses Celery)
from app.core.celery_tasks import send_verification_email_task
send_verification_email_task.delay(...)
```

**Fix**: Migrate all three remaining `asyncio.create_task` calls to Celery tasks.

---

#### P0-04: N+1 Query in Chat Session Listing

**Severity**: P0 (Performance)
**File**: `backend/app/api/v1/chat.py:923-970`

The `GET /sessions` endpoint executes one query for the session list, then issues an individual query for `ChatSessionModel` per row inside a for-loop. With 20 sessions, this is 21 queries.

```python
# chat.py:954-960
for row in rows:
    # N+1: one query per session row
    session_meta = await db.execute(
        select(ChatSessionModel).where(ChatSessionModel.id == row.session_id)
    )
    session_meta = session_meta.scalar_one_or_none()
```

**Fix**: Batch-fetch all `ChatSessionModel` records with a single `WHERE id IN (...)` query.

---

#### P0-05: N+1 Query in Plan Listing (per-plan task count)

**Severity**: P0 (Performance)
**File**: `backend/app/api/v1/plans.py:124-140`

The `GET /plans` endpoint fetches plans, then issues 2 queries per plan (total tasks, completed tasks) inside a for-loop. With 20 plans, this is 1 + 40 = 41 queries.

```python
# plans.py:126-132
for plan in plans:
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0
    completed_query = select(func.count(Task.id)).where(...)
    completed_count = (await db.execute(completed_query)).scalar() or 0
```

**Fix**: Use a single GROUP BY query or a subquery join to compute all task counts in one shot.

---

#### P0-06: N+1 Query in Archived Plans Listing

**Severity**: P0 (Performance)
**File**: `backend/app/api/v1/plans.py:696-712`

Same pattern as P0-05, repeated for the archived plans endpoint.

```python
# plans.py:697-710
for plan in plans:
    task_query = select(func.count(Task.id)).where(Task.plan_id == plan.id)
    task_count = (await db.execute(task_query)).scalar() or 0
    completed_query = select(func.count(Task.id)).where(...)
    completed_count = (await db.execute(completed_query)).scalar() or 0
```

**Fix**: Same as P0-05 -- batch query.

---

### P1 -- Robustness / Consistency

#### P1-01: Inconsistent Authentication Dependency Across Galaxy Endpoints

**Severity**: P1 (Consistency)
**File**: `backend/app/api/v1/galaxy.py`

Galaxy endpoints use `get_current_user_id` (returns raw string ID) while most other endpoints use `get_current_user` (returns User ORM object). This means galaxy endpoints do not touch the auth session (no `auth_session_service.touch_from_payload`), so session activity tracking is incomplete for galaxy interactions.

```python
# galaxy.py:84 -- uses raw user_id string
user_id: str = Depends(get_current_user_id),

# tasks.py:115 -- uses User object with session touch
current_user: User = Depends(get_current_user),
```

**Fix**: Standardize on `get_current_user` for galaxy endpoints, or at minimum add session touch in `get_current_user_id`.

---

#### P1-02: `print()` Statement Left in Production Code

**Severity**: P1 (Code Quality)
**File**: `backend/app/api/v1/chat.py:825`

```python
# chat.py:825
print(f"获取用户上下文时出错: {e}")
```

This should be `logger.warning()` instead of `print()`. The `logger` is already imported at the top of the file.

---

#### P1-03: Duplicate Route Registration for Ingestion Router

**Severity**: P1 (API Design)
**File**: `backend/app/api/v1/router.py:91-92`

The ingestion router is mounted at both `/documents` and `/ingestion`, doubling all ingestion endpoints. This creates ambiguity for API consumers.

```python
api_router.include_router(ingestion.router, prefix="/documents", tags=["ingestion"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
```

**Fix**: Pick one canonical path and deprecate the other.

---

#### P1-04: Chat Stream Endpoint Missing `response_model` and Auth Rate Limiting

**Severity**: P1 (API Design)
**File**: `backend/app/api/v1/chat.py:377-530`

The `/chat/stream` endpoint has no `response_model` annotation and no rate limiting decorator. The non-streaming `/chat` endpoint also lacks rate limiting. Both the `/task/{task_id}` and `/chat/confirm` endpoints also lack rate limiting. Only the auth endpoints use `@limiter.limit()`.

```python
# chat.py:377 -- no rate limit, no response_model
@router.post("/chat/stream")
async def chat_stream(...)
```

**Fix**: Add rate limiting to all chat endpoints. Consider adding response_model for the SSE endpoint.

---

#### P1-05: Chat Session History Missing Pagination Metadata

**Severity**: P1 (API Design)
**File**: `backend/app/api/v1/chat.py:973-1044`

The `GET /history/{session_id}` endpoint returns a flat list without total count or pagination metadata. The `GET /sessions` endpoint similarly lacks total count. Other list endpoints (tasks, plans, errors) return pagination metadata consistently.

```python
# chat.py:1029 -- returns raw list, no meta
return [
    ChatMessageDetail(...)
    for msg in messages
]
```

**Fix**: Wrap in a paginated response model with `total`, `page`, `page_size`.

---

#### P1-06: Focus Session History Lacks Upper Bound on `limit` Parameter

**Severity**: P1 (Input Validation)
**File**: `backend/app/api/v1/focus.py:136-145`

```python
# focus.py:137-138
@router.get("/sessions/history")
async def get_focus_session_history(
    limit: int = 20,       # No upper bound
    offset: int = 0,       # No upper bound
```

Compare with properly bounded endpoints:
```python
# tasks.py:114
page_size: int = Query(20, ge=1, le=100, description="Page size"),
```

**Fix**: Add `le=100` constraint to `limit` and validate `offset`.

---

#### P1-07: Memory Retract/Correct Endpoints Accept Unvalidated `dict` Payload

**Severity**: P1 (Input Validation)
**File**: `backend/app/api/v1/memory.py:239-321`

Both `/memory/retract` and `/memory/correct` accept `payload: dict` instead of a typed Pydantic model. This bypasses all automatic validation and OpenAPI documentation.

```python
# memory.py:243-244
@router.post("/retract")
async def retract_memory(
    payload: dict,  # No validation
```

**Fix**: Define `RetractMemoryRequest` and `CorrectMemoryRequest` Pydantic models.

---

#### P1-08: Health Endpoint Exposes Database Connection Pool Details Without Auth

**Severity**: P1 (Information Disclosure)
**File**: `backend/app/api/v1/health.py:155-180`

The `/health/database` endpoint returns pool size, checked-out count, and configuration details without any authentication. While health endpoints typically need to be unauthenticated for probes, pool details should be restricted.

```python
# health.py:163-179
return {
    "database": {
        "pool": {
            "size": health.pool_size,
            "checked_out": health.pool_checked_out,
            "config": {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
```

**Fix**: Split into a public liveness/readiness probe (minimal) and an authenticated detailed health endpoint.

---

#### P1-09: Notification Create Endpoint Allows Any User to Create Notifications

**Severity**: P1 (Authorization)
**File**: `backend/app/api/v1/notifications.py:30-40`

```python
# notifications.py:30
@router.post("", response_model=NotificationResponse)
async def create_notification(
    notification_in: NotificationCreate,
    current_user: User = Depends(get_current_user),
```

Any authenticated user can create notifications for themselves via this endpoint. The comment says "Test purpose or Manual" but it's exposed on the production API. If intended for internal/system use only, it should require admin or internal token.

**Fix**: Either add admin guard or move to an internal-only router.

---

#### P1-10: Plans Route Conflict -- `/plans/stats/summary` vs `/plans/{plan_id:uuid}`

**Severity**: P1 (API Design)
**File**: `backend/app/api/v1/plans.py:560,186`

`GET /plans/stats/summary` (line 560) and `GET /plans/{plan_id:uuid}` (line 186) could conflict. If "stats" happens to be a valid UUID format (it won't be, but FastAPI's path matching order depends on registration order), the UUID route could shadow the stats route.

```python
# plans.py:560 -- registered AFTER the UUID route
@router.get("/stats/summary", response_model=dict[str, Any])
```

Since FastAPI matches routes in registration order and "stats" is not a valid UUID, this is safe in practice, but it's a fragile ordering dependency.

**Fix**: Move `/plans/stats/summary` registration before `/plans/{plan_id}` or use a non-conflicting prefix like `/plans/_stats/summary`.

---

#### P1-11: Tasks Route Conflict -- `/tasks/feedback/stats` Shadowed by `/tasks/{task_id}`

**Severity**: P1 (API Design)
**File**: `backend/app/api/v1/tasks.py:828`

`GET /tasks/feedback/stats` is registered at line 828, after `GET /tasks/{task_id}` at line 328. "feedback" is not a valid UUID, so this works, but it creates a fragile ordering dependency and the path parameter endpoint will be tried first.

**Fix**: Reorder routes or use `/tasks/_feedback/stats`.

---

#### P1-12: Chat `confirm_action` Endpoint Exposes Internal Error Details

**Severity**: P1 (Security)
**File**: `backend/app/api/v1/chat.py:644`

```python
# chat.py:644
raise HTTPException(status_code=500, detail=f"执行操作时出错: {str(e)}")
```

The raw exception message is exposed to the client.

**Fix**: Log the exception and return a generic error message.

---

#### P1-13: Galaxy Vocabulary/Delete/Update Node Endpoints Expose Internal Error Details

**Severity**: P1 (Security)
**File**: `backend/app/api/v1/galaxy.py:711,733,771`

Three `except Exception` handlers in the vocabulary endpoints include `str(e)` in the response:

```python
# galaxy.py:711
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail=f"Failed to create vocabulary node: {str(e)}"
)
```

**Fix**: Log internally, return generic message to client.

---

#### P1-14: Devices Endpoint (devices.py) Exposes Internal Error Details

**Severity**: P1 (Security)
**File**: `backend/app/api/v1/devices.py:89-91,131-133,170`

```python
# devices.py:90
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail=f"Failed to register device: {str(e)}",
)
```

Three endpoints in this file leak `str(e)`.

**Fix**: Log internally, return generic message.

---

#### P1-15: Monitoring Endpoint Leaks Internal Error Details

**Severity**: P1 (Security)
**File**: `backend/app/api/v1/monitoring.py:81,105,125,142,168,252,299`

Seven exception handlers expose `str(e)` in HTTP error details.

**Fix**: Log internally, return generic message.

---

### P2 -- Minor / Style / Technical Debt

#### P2-01: Inconsistent User Profile Construction (Duplicated `_build_user_profile`)

**Severity**: P2 (DRY Violation)
**Files**: `backend/app/api/v1/auth.py:78`, `backend/app/api/v1/users.py:81`

Both files define their own `_build_user_profile` function with slightly different signatures (auth.py does not include push preferences, users.py does). This will lead to divergence.

**Fix**: Extract to a shared utility module.

---

#### P2-02: Inconsistent `_linked_providers` Duplication

**Severity**: P2 (DRY Violation)
**Files**: `backend/app/api/v1/auth.py:67`, `backend/app/api/v1/users.py:47`

Identical function defined in two places.

---

#### P2-03: Chat Endpoint Inlines Large Helper Functions Instead of Service Layer

**Severity**: P2 (Architecture)
**File**: `backend/app/api/v1/chat.py:648-914`

`get_user_context()`, `get_conversation_history()`, and `save_chat_message()` are defined as module-level functions in the route handler file. These should be in a service layer for reusability and testability.

---

#### P2-04: Router Imports All 67+ Submodules Eagerly

**Severity**: P2 (Startup Performance)
**File**: `backend/app/api/v1/router.py:8-84`

All 67 submodules are imported at module load time. This increases startup latency. Consider lazy loading for rarely-used admin endpoints.

---

#### P2-05: `ChatRequest` and `ChatResponse` Models Defined in Route File

**Severity**: P2 (Code Organization)
**File**: `backend/app/api/v1/chat.py:68-81`

Request/response models should be in `app/schemas/chat.py` alongside the other chat schemas (which already exist there -- `ChatMessageDetail`, `ChatSession`).

---

#### P2-06: Focus Schemas Defined Inline Instead of in Schema Module

**Severity**: P2 (Code Organization)
**File**: `backend/app/api/v1/focus.py:23-43`

`FocusSessionLog`, `FocusStats`, `LLMGuideRequest`, `LLMBreakdownRequest` are defined inline.

---

#### P2-07: No `response_model` on Streaming Endpoints

**Severity**: P2 (Documentation)
**Files**: `backend/app/api/v1/chat.py:377`, `backend/app/api/v1/galaxy.py:606`

SSE/streaming endpoints lack `response_model`. While FastAPI cannot fully enforce response models on streaming responses, at minimum the event payload schemas should be documented.

---

#### P2-08: Duplicate Device Management Endpoints

**Severity**: P2 (API Design)
**Files**: `backend/app/api/v1/monitoring.py:172-253`, `backend/app/api/v1/devices.py:51-171`

Both files implement device registration/unregistration/listing with slightly different logic and response formats. `monitoring.py` creates its own `AsyncSessionLocal()` session, while `devices.py` uses DI.

**Fix**: Consolidate into one canonical device API.

---

#### P2-09: `tasks.py` Route Shadowing Between `/tasks/today` and `/tasks/{task_id}`

**Severity**: P2 (Fragility)
**File**: `backend/app/api/v1/tasks.py:262,328`

Fixed-path routes like `/tasks/today` and `/tasks/recommended` are registered before the parameterized `/tasks/{task_id}`. This is correct but relies on registration order.

---

#### P2-10: Error Book Service Uses `get_current_user_id` Instead of `get_current_user`

**Severity**: P2 (Consistency)
**File**: `backend/app/api/v1/error_book.py:46`

Same as P1-01 pattern. No session touch for error book interactions.

---

## 4. Compliance Items (Positive Findings)

| Area | Status | Detail |
|------|--------|--------|
| **Global Exception Handler** | COMPLIANT | `main.py:481-531` handles `RequestValidationError`, `SparkleException`, and generic `Exception` consistently. Debug-only detail exposure. |
| **JWT Authentication** | COMPLIANT | `deps.py:24-45` properly extracts user ID from JWT `sub` claim. `get_optional_current_user` handles missing tokens gracefully. |
| **Superuser Guard** | COMPLIANT | Admin endpoints (`memory_admin.py`, `observability.py`, `feedback_admin.py`, `health_production.py`, `graph_monitor.py`) all use `get_current_active_superuser` at router level. |
| **Account Lockout** | COMPLIANT | `auth.py:408` checks `account_lockout_service.check_and_handle_lockout` before password verification. |
| **Anti-Enumeration** | COMPLIANT | `auth.py:308-319` returns generic error for duplicate username/email registration. |
| **Rate Limiting on Auth** | COMPLIANT | All auth endpoints use `@limiter.limit()` with dev/prod rate variants. |
| **Password Reset Token Expiry** | COMPLIANT | 15-minute TTL for password reset tokens (`auth.py:62`). |
| **Security Headers** | COMPLIANT | `SecurityHeadersMiddleware` in `main.py:366-399` adds CSP, X-Content-Type-Options, HSTS, X-Frame-Options. |
| **Idempotency Protection** | COMPLIANT | `IdempotencyMiddleware` protects POST/PUT/PATCH on critical paths with Redis-backed cache. |
| **Request Tracing** | COMPLIANT | `RequestContextMiddleware` injects `X-Request-ID` and `X-Trace-ID` into all responses. |
| **Cross-User Data Access Prevention** | COMPLIANT | All data-fetching endpoints filter by `current_user.id` or `user_id` from JWT. |
| **Soft Delete** | COMPLIANT | User deletion (`users.py:515-547`) uses soft delete with data anonymization. Plan deletion uses `is_active=False`. |
| **Pagination Bounds** | MOSTLY COMPLIANT | Most list endpoints have `ge=1, le=100` on `page_size`. Exception: `focus.py` (P1-06). |
| **Pydantic Validation** | MOSTLY COMPLIANT | Most endpoints use typed Pydantic models for request bodies. Exception: `memory.py` retract/correct (P1-07). |

---

## 5. Statistics

### Finding Distribution

| Severity | Count | Category Breakdown |
|----------|-------|--------------------|
| **P0** | 6 | Security (2), Performance (3), Reliability (1) |
| **P1** | 15 | Security (4), Input Validation (2), API Design (5), Authorization (1), Info Disclosure (2), Consistency (1) |
| **P2** | 10 | Code Quality (6), Architecture (2), API Design (2) |
| **Total** | **31** | |

### By Category

| Category | Count |
|----------|-------|
| Security | 6 |
| Performance (N+1) | 3 |
| API Design/Consistency | 8 |
| Input Validation | 2 |
| Code Quality/DRY | 7 |
| Reliability | 1 |
| Information Disclosure | 4 |

### Lines Audited

| Component | Lines |
|-----------|-------|
| Core infrastructure (main, deps, middleware, router, grpc_auth) | ~1,218 |
| Endpoint handlers (v1/*.py) | ~27,884 |
| **Total** | **~29,102** |

### Endpoint Coverage

| Metric | Count |
|--------|-------|
| Total endpoint files | 80+ |
| Total sub-routers registered | 67 |
| Endpoints with auth | ~85% |
| Endpoints with admin guard | ~30 (all in admin-prefixed routers) |
| Endpoints with response_model | ~60% |
| Endpoints with rate limiting | ~15 (auth only) |
| Public endpoints (no auth) | health, auth login/register/guest, files (internal token) |

---

## 6. Remediation Priority

### Immediate (P0 -- This Sprint)

| ID | Fix | Effort |
|----|-----|--------|
| P0-01 | Replace `!=` with `secrets.compare_digest` in 3 files | 15 min |
| P0-02 | Remove user/group ID lists from monitoring stats, or add admin guard | 10 min |
| P0-03 | Migrate 3 `asyncio.create_task` to Celery | 30 min |
| P0-04 | Batch-fetch `ChatSessionModel` in session listing | 30 min |
| P0-05 + P0-06 | Batch task counts in plan listing (both active and archived) | 45 min |

### Next Sprint (P1)

| ID | Fix | Effort |
|----|-----|--------|
| P1-01 | Standardize galaxy to `get_current_user` | 1 hr |
| P1-02 | Replace `print()` with `logger.warning()` | 2 min |
| P1-03 | Remove duplicate ingestion route | 5 min |
| P1-04 | Add rate limiting to chat endpoints | 30 min |
| P1-05 | Add pagination metadata to chat history | 30 min |
| P1-06 | Add bounds to focus pagination params | 5 min |
| P1-07 | Define Pydantic models for memory retract/correct | 30 min |
| P1-08 + P1-09 | Restrict health details and notification creation | 30 min |
| P1-10 + P1-11 | Reorder routes or add underscore prefix | 15 min |
| P1-12 to P1-15 | Replace `str(e)` in error responses (10 instances) | 30 min |

### Backlog (P2)

| ID | Fix | Effort |
|----|-----|--------|
| P2-01 + P2-02 | Extract shared user profile utilities | 1 hr |
| P2-03 | Move chat helpers to service layer | 2 hr |
| P2-04 | Lazy-load admin routers | 1 hr |
| P2-05 + P2-06 | Move inline schemas to schema modules | 30 min |
| P2-08 | Consolidate device management endpoints | 2 hr |

---

## 7. Cross-Round Causal Chains

### Chain 1: Timing Attack -> Internal Token Compromise -> Full API Access
```
P0-01 (Timing-unsafe comparison)
  -> Attacker reconstructs INTERNAL_API_KEY
  -> Can call /files/process and other internal endpoints
  -> Arbitrary file processing triggered
  -> Links to: Round #58 (file upload audit)
```

### Chain 2: N+1 Queries -> Slow Plan Listing -> Gateway Timeout
```
P0-05 (N+1 in plan listing)
  -> 41 queries per page request at 20 plans/page
  -> Each query ~5ms under load = 200ms+ per listing
  -> Go Gateway timeout at 30s unlikely, but mobile UX degradation
  -> Links to: Round #56 (Go Gateway timeout audit)
```

### Chain 3: asyncio.create_task -> Email Lost -> User Cannot Reset Password
```
P0-03 (asyncio.create_task for emails)
  -> Task silently fails if event loop has issues
  -> User never receives password reset email
  -> Account lockout (COMPLIANT) then no recovery path
  -> Links to: Round #57 (auth flow audit)
```

### Chain 4: User ID Leak -> Privacy Violation
```
P0-02 (WS stats leaks all user IDs)
  -> Any authenticated user sees all connected user IDs
  -> Cross-reference with public profile endpoint (users.py:666)
  -> Build complete user directory
  -> Links to: Round #59 (user data exposure audit)
```

### Chain 5: Inconsistent Auth Dep -> Incomplete Session Tracking
```
P1-01 (galaxy uses get_current_user_id)
  + P2-10 (error_book uses get_current_user_id)
  -> Session activity not tracked for ~15 endpoints
  -> "Last active" timestamp is inaccurate
  -> Affects session management UI
  -> Links to: deps.py session touch logic
```
