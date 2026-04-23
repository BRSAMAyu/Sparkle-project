# Loop Handoff Document — Session 1

> Operator: Chris | Date: 2026-04-23 | Branch: integration/phase-i-exit

## Changes Made

### 1. Event Bus XADD MAXLEN (backend/app/core/event_bus.py)
- **Issue**: `_publish_once()` called `redis.xadd()` without `maxlen`, causing unbounded stream growth
- **Fix**: Added `maxlen=50000` (configurable via `EVENT_BUS_STREAM_MAXLEN`) with `approximate=True`
- **How to inspect**: `git diff backend/app/core/event_bus.py` — line ~936 now passes maxlen to xadd
- **Verify**: `grep -A5 'async def _publish_once' backend/app/core/event_bus.py` should show maxlen param

### 2. CORS Wildcard Production Guard (backend/gateway/internal/config/config.go)
- **Issue**: `IsOriginAllowed()` accepted `"*"` wildcard even in production
- **Fix**: Added `if c.IsProduction() { continue }` before returning true for wildcard
- **How to inspect**: `git diff backend/gateway/internal/config/config.go` — lines 149-153 now block wildcard in prod
- **Verify**: `grep -A3 'allowed == .\\*' backend/gateway/internal/config/config.go` should show production check

### 3. str(e) Error Leak Sanitization (4 files)
- **Issue**: Multiple API endpoints exposed internal error details via `str(e)` to users
- **Files fixed**:
  - `backend/app/api/v1/recommendations.py` — 6 instances
  - `backend/app/api/v1/multi_intent.py` — 4 instances
  - `backend/app/api/v1/analytics.py` — 2 instances
  - `backend/app/api/v1/ingestion.py` — 2 instances (background task cache)
- **Fix pattern**: `detail=f"...: {str(e)}"` → `detail="..."` (no internal details)
- **How to inspect**: `grep -rn 'detail=.*str(e)' backend/app/api/v1/` should return 0 results in fixed files
- **Verify**: `grep -rn 'str(e)' backend/app/api/v1/recommendations.py backend/app/api/v1/multi_intent.py backend/app/api/v1/analytics.py` — only logger.error uses remain

## Validation Status

| Check | Result |
|-------|--------|
| Go build | PASS (`go build ./...`) |
| Python compile | PASS (all 5 files) |
| Ingestion API tests | PASS (3/3) |
| Go config tests | N/A (no test files) |

## Remaining str(e) Instances

These were NOT fixed (lower priority or acceptable usage):
- `signals.py:128,230` — internal error type matching, not user-facing
- `seed_libraries.py` — multiple instances, 403/400 error contexts
- `visual_elements.py:218` — 404 detail
- `focus.py:77` — 400 detail
- `inventory.py:95,157` — 400 detail

## Triage Summary (19 ⚠️ Audit Items)

| Verdict | Count | Details |
|---------|-------|---------|
| **FIXED this session** | 3 | EventBus MAXLEN, CORS guard, str(e) sanitization |
| **Already fixed (prior work)** | 3 | Rate limit token bucket, STT origin check, JWT fail-closed production |
| **REAL but skip (architectural)** | 7 | JWT rotation, RLS, prompt injection, OAuth encryption, user_revoked_before, XAUTOCLAIM, achievement atomicity |
| **REAL needs investigation** | 4 | WS break path DoneEvent, community signal bridge, Celery Beat/date, calendar ContextManager |
| **Stale/acceptable** | 2 | Local cache sync (acceptable with TTL), CORS (now fixed) |

## Next Session Priorities

1. Validate WS proxy break path DoneEvent handling
2. Investigate community signal bridge social_context_renderer deletion
3. Check Celery Beat/date comparison issues
4. Run broader test suite on changed files
5. Consider fixing remaining str(e) in seed_libraries, visual_elements, focus
