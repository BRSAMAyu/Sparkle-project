# Community & Accountability System — Complete Audit Summary

**Date**: 2026-05-10
**Auditors**: 3x Opus agents + Chief Architect direct verification
**Scope**: Full stack — Flutter UI/UX, Python backend, Go Gateway, Database, Cross-layer contracts

---

## Executive Summary

**Total issues found: 113** across 5 audit reports.

| Severity | Flutter | Python | Go/DB | Cross-Layer | Total |
|----------|---------|--------|-------|-------------|-------|
| **P0** | 0 | 5 | 3 | 1 | **9** |
| **P1** | 5 | 12 | 7 | 3 | **27** |
| **P2** | 14 | 18 | 7 | 3 | **42** |
| **P3** | 12 | 10 | 5 | 1 | **28** |
| **Total** | 31 | 45 | 22 | 8 | **113** |

### Must-Fix Before Launch (P0 = 9 issues)

| # | Area | Issue | Impact |
|---|------|-------|--------|
| 1 | Go/DB | `community_query.go` references `community_posts` table, but actual table is `posts` | Feed broken on DB fallback path |
| 2 | Go/DB | `post:likes:{post_id}` Redis sets never written — `isLikedByMe` always false | Like state invisible to users |
| 3 | Go/DB | `GET /community/feed` has NO authentication middleware | Publicly exposes all posts |
| 4 | Python | PII (user display name) leaked in Redis event stream | Privacy violation |
| 5 | Python | Partnership unique constraint doesn't cover reverse direction | Duplicate partnerships possible |
| 6 | Python | Privacy budget engine is ephemeral (per-request instance) | Zero actual privacy protection |
| 7 | Python | Unbounded N+1 queries in achievement evaluation (14*N) | DB freeze under load |
| 8 | Flutter/API | `community/resources` response shape mismatch (frontend expects List, backend returns Map) | Resource quality list always empty |
| 9 | Security | JWT token in WebSocket URL query string | Token exposed in logs/proxies |

---

## Detailed Reports (see individual files)

| Report | File | Issues |
|--------|------|--------|
| Flutter UI/UX | [flutter_ui_ux_audit.md](flutter_ui_ux_audit.md) | 31 (5P1, 14P2, 12P3) |
| Python Backend | [python_backend_audit.md](python_backend_audit.md) | 45 (5P0, 12P1, 18P2, 10P3) |
| Go Gateway & DB | [go_gateway_db_audit.md](go_gateway_db_audit.md) | 22 (3P0, 7P1, 7P2, 5P3) |
| Cross-Layer Contract | [cross_layer_contract_audit.md](cross_layer_contract_audit.md) | 7 (2P0, 3P1, 2P2) |
| Cross-Layer Integration | [cross_layer_integration_audit.md](cross_layer_integration_audit.md) | 8 (1P0, 3P1, 3P2, 1P3) |

---

## Top 10 Most Critical Issues (Ranked by Business Impact)

### 1. JWT Token in WebSocket URL (P0 — Security)
**File**: `mobile/.../community_websocket_service.dart:144,195`
**What**: Access token passed as `?token=$token` in WebSocket URL.
**Impact**: Token visible in gateway logs, proxy logs, CDN logs.
**Fix**: Move to `Sec-WebSocket-Protocol` header or initial auth message.
**Context**: Flutter sends `ws://host/community/groups/$groupId/ws?token=JWT...`

### 2. Feed Table Name Mismatch (P0 — Broken Feature)
**File**: `backend/gateway/internal/service/community_query.go`
**What**: SQL query references `community_posts` table; actual table is `posts`.
**Impact**: Community feed returns 500 when Redis cache misses (fallback to DB).
**Fix**: Change table reference from `community_posts` to `posts`.

### 3. `isLikedByMe` Always Returns False (P0 — Broken Feature)
**File**: `backend/gateway/internal/service/community_command.go` + `community_query.go`
**What**: `post:likes:{post_id}` Redis sets are never written. Only `post:{id}` hash is set with like_count. Query reads sets that don't exist.
**Impact**: Users never see their liked posts as "liked". Creates confusion and potential duplicate likes.
**Fix**: Add `SADD post:likes:{post_id} {user_id}` in like command, `SREM` in unlike.

### 4. PII Leak in Event Bus (P0 — Privacy)
**File**: `backend/app/services/social_signal_bridge.py:455`
**What**: User display name (`target_name`) included in `ACCOUNTABILITY_STRUGGLE_DETECTED` event on shared Redis stream.
**Impact**: Any consumer of the stream sees PII. Violates privacy architecture.
**Fix**: Remove `target_name` from payload; consumer resolves name via DB `user_id`.

### 5. Community Resources Response Mismatch (P0 — Broken Feature)
**File**: `mobile/.../community_share_repository.dart:44`
**What**: Frontend checks `if (data is! List) return []`. Backend returns `{"resources": [...], "total": N}`.
**Impact**: Quality-ranked resource list always empty for real users.
**Fix**: Parse response correctly: `data['resources'] as List`.

### 6. Feed Endpoint Has No Auth (P0 — Security)
**File**: `backend/gateway/internal/api/v1/community.go:31`
**What**: `group.GET("/feed", h.GetFeed)` is outside the `protected` group.
**Impact**: Anyone can read all community posts without authentication.
**Fix**: Move `GET /feed` inside the `protected.Use(authMiddleware)` block.

### 7. Privacy Budget Engine Is Ephemeral (P0 — Logic)
**File**: `backend/app/services/community_signal_bridge.py:71` + `backend/app/signals/privacy_community_intelligence.py`
**What**: `PrivacyPreservingCommunityEngine()` created per-request. In-memory budgets reset every time.
**Impact**: Zero actual privacy budget enforcement. Unlimited queries possible.
**Fix**: The DB-backed `PrivacyBudgetLedger` is the real guard (see `_check_daily_budget`). Remove misleading in-memory engine or make it Redis-backed.

### 8. Partnership Race Condition (P0 — Data Integrity)
**File**: `backend/app/models/accountability.py:91-95`
**What**: `UniqueConstraint("initiator_id", "partner_id")` doesn't cover (B,A) when (A,B) exists. Concurrent requests can create duplicate partnerships.
**Impact**: Users end up in two partnerships with the same person.
**Fix**: Add canonical ordering (always store smaller UUID as `initiator_id`) or add application-level reverse check + DB advisory lock.

### 9. Unbounded N+1 Achievement Queries (P0 — Performance)
**File**: `backend/app/services/accountability_achievement_service.py:492-533`
**What**: For each partnership, runs 14 individual DB queries (7 days × 2 users) without LIMIT.
**Impact**: DB freeze when many partnerships exist. Celery task timeout.
**Fix**: Rewrite as single query fetching all checkins for the 7-day window, group by date in Python.

### 10. Schema Owner Drift: 1606 Objects Owned by `brsama` (P1 — Infrastructure)
**File**: `backend/gateway/internal/db/schema.sql`
**What**: 68% of DB objects owned by local dev user `brsama` instead of `postgres`.
**Impact**: Permission errors if production uses different DB user. Drift propagates via `make sync-db`.
**Fix**: `REASSIGN OWNED BY brsama TO postgres` → regenerate schema.sql. Add CI check.

---

## Systemic Issues (Cross-Cutting)

### 1. i18n Bypass — 32 Files, 219+ Occurrences
**Pattern**: `I18nService.instance.isChinese ? '中文' : 'English'` instead of ARB l10n
**Affected files**: `community_main_screen`, `create_post_screen`, `accountability_screen`, `partners_tab`, `favorites_screen`, `blocked_users_screen`, `group_tasks_screen`, `create_group_screen`, `group_moderation_screen`, `community_accountability_hub_card`, and 22 more.
**Root cause**: Two patterns co-exist — `context.l10n` (correct) and `isChinese` ternary (bypass).
**Fix strategy**: Batch migration sprint. Start with P1 screens (create_post, community_main, accountability_screen), then sweep remaining.

### 2. Inconsistent Timezone Handling — ~40% of Code Uses Wrong Timezone
**Affected**: Achievement calculations, Celery tasks, perfect month checks, mutual support detection.
**Pattern**: 60% uses user-aware timezone (correct), 40% uses raw UTC or naive datetime.
**Impact**: Wrong streak counts, missed achievements, incorrect "today" boundaries for non-UTC users.
**Fix**: Audit all `created_at` comparisons. Unify through `_day_range_for_timezone()`.

### 3. Dead CQRS Code in Go Gateway
**Files**: `community.go`, `community_command.go`, `community_query.go`
**What**: `CommunityHandler` with full CQRS implementation exists but is never registered in `setup.go`. All community routes proxy to Python instead.
**Impact**: Confusion for future developers. Tests exist for dead code.
**Fix**: Either remove CQRS handler + tests, or document as "future optimization path".

### 4. Missing API Endpoints (Frontend Calls That 404)
| Frontend Call | Expected Backend | Status |
|---------------|-----------------|--------|
| `POST /community/tasks/$id/complete` | No route exists | 404 |
| `GET /community/groups/$id/moderation` | Only PUT exists | 405 |
| `POST /community/groups/$gid/members/$uid/unmute` | Backend expects `DELETE .../mute` | 404+405 |
| `GET /community/resources` | Exists but response shape wrong | Empty list |
| `POST /community/shared-resources/$id/reject` | No route exists | Silent fail |

### 5. Incomplete Soft-Delete Pattern
**Models**: `AccountabilityPolicy`, `CommunityAggregateSignal`, and several community models define `deleted_at` but queries inconsistently apply the filter. Some API endpoints may return soft-deleted records.

---

## Recommended Fix Priority

### Phase 1: Critical Fixes (Before Any Testing)
1. Fix `community_posts` → `posts` table name in Go query service
2. Add `post:likes:{id}` Redis set writes in Go command service
3. Move `GET /feed` behind auth middleware
4. Fix `community/resources` response parsing in Flutter
5. Remove `target_name` from struggle event payload

### Phase 2: Security & Data Integrity
6. Move JWT out of WebSocket URL
7. Fix partnership unique constraint (canonical ordering)
8. Fix privacy budget enforcement (make DB-backed path authoritative)
9. Fix N+1 achievement queries
10. Reassign DB schema ownership

### Phase 3: API Contract Fixes
11. Add `POST /community/tasks/{id}/complete` backend route
12. Add `GET /community/groups/{id}/moderation` backend route
13. Fix unmute endpoint (POST→DELETE, /unmute→/mute)
14. Fix `rejectResource` backend endpoint

### Phase 4: i18n Migration
15. Migrate top 10 affected screens to ARB l10n
16. Fix `community_accountability_hub_l10n.dart` custom extension → ARB

### Phase 5: Code Quality & Performance
17. Remove dead CQRS handler from Go Gateway
18. Unify timezone handling in achievement/tasks
19. Add missing DB indexes (posts.created_at, checkins covering index)
20. Add idempotency to event publishing

---

## Audit Files

```
docs/audit/community_accountability_2026-05-10/
├── SUMMARY.md                        ← This file
├── flutter_ui_ux_audit.md            ← 31 issues (Flutter presentation layer)
├── python_backend_audit.md           ← 45 issues (Python services/models/API)
├── go_gateway_db_audit.md            ← 22 issues (Go CQRS/schema/events)
├── cross_layer_contract_audit.md     ← 7 issues (API contract mismatches)
└── cross_layer_integration_audit.md  ← 8 issues (architecture/security/integration)
```
