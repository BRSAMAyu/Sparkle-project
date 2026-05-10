# Card System Full-Stack Audit — Summary Report

**Date**: 2026-05-09
**Scope**: Flutter UI/UX → Go Gateway → Python Backend → Database | Card types, protocols, flows, AI integration, cross-user sharing
**Auditors**: 3 Opus agents (Backend, Gateway/DB, Frontend) + Chief Architect personal verification
**Reports**: See `01-frontend-uiux-audit.md`, `02-backend-ai-card-audit.md`, and `03-gateway-proto-db-audit.md` for full details.

---

## Severity Distribution

| Severity | Backend | Gateway/DB | Frontend | Total |
|----------|---------|------------|----------|-------|
| P0 (data loss/crash) | 3 | 2 | 1 | **6** |
| P1 (broken feature) | 8 | 5 | 4 | **17** |
| P2 (performance/quality) | 7 | 14 | 29 | **50** |
| P3 (cleanup) | 5 | 6 | 24 | **35** |
| **Total** | **23** | **27** | **58** | **108** |

---

## Top Priority Fixes (P0 — Must Fix Immediately)

### P0-01: `archived_at` Column Referenced in Code but Not Declared on Card Model
- **File**: `backend/app/models/card_protocol.py` (missing) + `backend/app/services/card_service.py:370`
- **Impact**: `card_service.archive()` sets `card.archived_at` but the SQLAlchemy model has no such column → value never persists to DB
- **DB has the column** (schema.sql:1575) but Python model doesn't declare it
- **Fix**: Add `archived_at = Column(DateTime, nullable=True)` to `Card` class in `card_protocol.py`
- **Detail**: See `02-backend-ai-card-audit.md` P0-01

### P0-02: `build_task_entity_card` Status Case Mismatch
- **File**: `backend/app/tools/entity_cards.py:206`
- **Impact**: All task entity cards have `execution_state: "draft"` regardless of actual status
- **Code**: `task.get("status") in {"IN_PROGRESS", "COMPLETED"}` (uppercase) but actual values are lowercase (`"in_progress"`, `"completed"`)
- **Fix**: `task.get("status", "").lower() in {"in_progress", "completed"}`
- **Detail**: See `02-backend-ai-card-audit.md` P1-08

### P0-03: Soft-Deleted Edge Resurrection
- **File**: `backend/app/services/card_edge_service.py:90-103`
- **Impact**: `_find_edge_by_identity` finds soft-deleted edges, allowing silent resurrection with different metadata
- **Fix**: Add `CardEdge.not_deleted_filter()` to the query
- **Detail**: See `02-backend-ai-card-audit.md` P0-03

### P0-04: DB Default Values Use Triple-Quote Syntax
- **File**: `backend/gateway/internal/db/schema.sql` (14 occurrences in card tables)
- **Impact**: SQL defaults store `'OWNED'` (with quotes) instead of `OWNED`, `'3.0'` instead of `3.0`, etc. Any record created via raw SQL gets wrong values
- **Affected columns**: `card_edges.binding_mode`, `cards.schema_version`, `cards.lifecycle_status`, `cards.visibility`, `cards.source_type`, `cards.created_by`, `cards.updated_by`, `card_snapshots.schema_version`, `card_share_records.permission`, `card_adoption_records.import_mode`, `intervention_records.*`
- **Fix**: Run `ALTER TABLE ... SET DEFAULT 'VALUE'` (without extra quotes) for all affected columns
- **Detail**: See `03-gateway-proto-db-audit.md` DB-02

### P0-05: Card Enum Types Missing from SQL Schema
- **File**: `backend/gateway/internal/db/schema.sql` (card tables)
- **Impact**: All enum columns stored as `varchar` with no DB-level constraint → arbitrary values accepted
- **Fix**: Add PostgreSQL `CREATE TYPE ... AS ENUM` + ALTER columns, or add CHECK constraints
- **Detail**: See `03-gateway-proto-db-audit.md` DB-01

### P0-06: FeedPostCard Crash on Empty Username
- **File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:83`
- **Impact**: `post.user.username[0].toUpperCase()` throws `RangeError` when username is empty string
- **Fix**: `post.user.username.isNotEmpty ? post.user.username[0].toUpperCase() : '?'`
- **Detail**: See `01-frontend-uiux-audit.md` P0-01

---

## High Priority Fixes (P1 — Broken Features)

### P1-01: No Lifecycle Validation in `_transition`
- **File**: `backend/app/services/card_service.py:361-384`
- **Fix**: Add `_VALID_TRANSITIONS` state machine map
- **Detail**: `02-backend-ai-card-audit.md` P1-01

### P1-02: `update_card` Bypasses Lifecycle Validation via kwargs
- **File**: `backend/app/services/card_service.py:155-158`
- **Fix**: Add `PROTECTED_FIELDS = {"id", "created_at", "lifecycle_status"}` filter
- **Detail**: `02-backend-ai-card-audit.md` P1-02

### P1-03: `focus_card` Widget Type Missing from Frontend Message Renderer
- **File**: `mobile/lib/features/chat/presentation/widgets/agent_message_renderer.dart:52-89, 190-278`
- **Impact**: Backend sends `focus_card` but frontend `agent_message_renderer.dart` has no handler → falls through to default showing raw JSON
- **Also missing**: `task_detail`, `web_search_results`, `translation_result`, `system_update` (some handled via `action_card.dart` alternative path)
- **Fix**: Add `focus_card` case to `_widgetConfigs` and `_buildInnerWidget` switch

### P1-04: Go Gateway Action Feedback Drops 10+ Widget Types
- **File**: `backend/gateway/internal/handler/chat_orchestrator_feedback.go:226-303`
- **Impact**: User taps confirm/dismiss on `task_card`, `knowledge_card`, etc. → feedback silently dropped
- **Fix**: Add cases for missing types or add default acknowledgment
- **Detail**: `03-gateway-proto-db-audit.md` GW-01

### P1-05: `import_snapshot` No Transaction Boundary → Dangling Cards on Partial Failure
- **File**: `backend/app/services/card_protocol/card_snapshot_service.py:216-258`
- **Fix**: Wrap in `async with self.db.begin_nested():`
- **Detail**: `02-backend-ai-card-audit.md` P1-07

### P1-06: `adoption_count` Race Condition
- **File**: `backend/app/services/card_protocol/card_snapshot_service.py:1020`
- **Impact**: Concurrent adoptions can lose counts (read-modify-write without locking)
- **Fix**: Use `UPDATE ... SET adoption_count = adoption_count + 1` or derive from COUNT query
- **Detail**: `03-gateway-proto-db-audit.md` SC-01

### P1-07: Dual `ShareService` Class Definitions Risk Divergence
- **File**: `backend/app/services/card_protocol/card_snapshot_service.py` vs `share_service.py`
- **Fix**: Move to single canonical definition
- **Detail**: `02-backend-ai-card-audit.md` P0-02

### P1-08: `widget_data` Merge Overwrites Gateway Fallbacks
- **File**: `backend/gateway/internal/handler/chat_orchestrator_protocol.go:196-204`
- **Fix**: Add non-empty checks before overwriting
- **Detail**: `03-gateway-proto-db-audit.md` GW-02

### P1-09: Card Type Enums Inconsistent Between Python and Go
- **File**: Python `CardType` StrEnum vs Go `string`
- **Fix**: Define Go constants matching Python enum values
- **Detail**: `03-gateway-proto-db-audit.md` XL-01

### P1-10: PlanAdapter Duplicate Edge Creation
- **File**: `backend/app/services/card_protocol/legacy_adapter.py:191-198`
- **Fix**: Handle existing deactivated edges gracefully
- **Detail**: `02-backend-ai-card-audit.md` P1-03

### P1-11: `QueryAllTasksTool` N+1 Query Pattern
- **File**: `backend/app/tools/task_query_tool.py:670-736`
- **Fix**: Use single JOIN query
- **Detail**: `02-backend-ai-card-audit.md` P1-06

### P1-12: Share Expiration Not Enforced on Adoption
- **File**: `backend/app/api/v1/cards.py` (adopt endpoint)
- **Fix**: Add expiration check before allowing adoption
- **Detail**: `03-gateway-proto-db-audit.md` SC-03

### P1-13: `TaskOccurrence.auto_mark_missed` Dead Code — `reference_date` Unused
- **File**: `backend/app/services/task_occurrence_service.py:262`
- **Fix**: Use `reference_date` in the query filter
- **Detail**: `02-backend-ai-card-audit.md` P1-04

### P1-14: Missing Group Membership Check for Group-Scoped Shares
- **File**: `backend/app/api/v1/cards.py:403-445`
- **Fix**: Add `is_group_member` check
- **Detail**: `03-gateway-proto-db-audit.md` SC-02

### P1-15: Frontend Task Type Normalization Mismatch
- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:866-889`
- **Impact**: Python `review → TRAINING` but Flutter `review → REFLECTION` in legacy entity card builder
- **Fix**: Align Flutter `_normalizeTaskType` with Python `TASK_TYPE_ALIAS_MAP`

### P1-16: FeedbackGateEngine Double-Fetches Phase Card
- **File**: `backend/app/services/card_protocol/feedback_gate_engine.py:103-108`
- **Fix**: Fetch once, pass owner_id directly
- **Detail**: `02-backend-ai-card-audit.md` P1-05

### P1-17: EntityCardPayload Children Filter Drops Valid Data
- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:259`
- **Impact**: `children.whereType<Map<Object?, Object?>>()` silently drops `Map<String, dynamic>` children from server payloads
- **Fix**: Change filter to accept both: `.whereType<Map>()` then `Map<String, dynamic>.from()`
- **Detail**: See `01-frontend-uiux-audit.md` P1-02

### P1-18: PlanCard Force Unwrap Crashes on Parse Failure
- **File**: `mobile/lib/features/plan/presentation/widgets/plan_card.dart:34-38`
- **Impact**: `_cachedPayload!` crashes if entity card parsing fails
- **Fix**: Use null-coalescing or guard clause
- **Detail**: See `01-frontend-uiux-audit.md` P1-03

### P1-19: Hardcoded Chinese `'未命名实体'` in Fallback
- **File**: `mobile/lib/shared/utils/entity_card_payloads.dart:860`
- **Impact**: Unknown entity types show Chinese text to all users
- **Fix**: Use i18n key or English fallback
- **Detail**: See `01-frontend-uiux-audit.md` P1-01

---

## P2 Issues (23 total) — Performance / Quality

Key highlights:

| ID | File | Issue |
|----|------|-------|
| i18n-01 | `backend/app/tools/entity_cards.py` (27 occurrences) | Hardcoded Chinese strings in labels/titles ("未命名任务", "查看任务", "分享卡片") — violates i18n rule |
| i18n-02 | `backend/app/orchestration/task_card_generator.py` | Template keywords hardcoded in Chinese |
| DB-04 | `cards` table | Missing index on `updated_at` for pagination |
| DB-05 | `card_share_records` | Missing index for "shared with me" queries |
| DB-06 | `card_edges` | No partial index for `active = true` queries |
| DB-07 | `task_occurrences` | CASCADE delete removes feedback data |
| XL-02 | Python/Go/Flutter | Widget type values diverge across layers (14+ types, inconsistent handling) |
| XL-03 | Go gateway | `nodeId` vs `node_id` naming inconsistency |
| XL-05 | `schema.sql:134-135` | Duplicate `achievementtype` enum value (`'planning'` vs `'PLANNING'`) |
| SC-04 | `card_share_records` | Revocation doesn't affect previously adopted cards (needs documentation) |
| SEC-01 | `proxy_routes.go:205` | Wildcard card path forwarding (potential path traversal) |
| GW-04 | `signal_push.go:107` | No ordering guarantee for signal push delivery |
| GW-05 | `proxy_routes.go:195` | No gateway-side validation of card API requests |
| PB-02 | `agent_service.proto:626` | `widget_type` is untyped string (no enum) |
| PB-03 | Multiple proto files | Duplicate intervention schemas |
| P2-03 | `card_service.py` | Events published before transaction commit |
| P2-04 | `task_occurrence_service.py` | `get_occurrences_for_date` uses `holder_id` instead of `owner_id` |
| P2-07 | `temporal_engine.py:342` | `_parse_clock` crashes on malformed time strings |

Full list in `02-backend-ai-card-audit.md` (P2 section) and `03-gateway-proto-db-audit.md`.

---

## Personal Verification Results

| Finding | Verified | Notes |
|---------|----------|-------|
| `archived_at` missing from Card model | YES | schema.sql:1575 has it, card_protocol.py doesn't declare it |
| Triple-quote DB defaults (14 instances) | YES | Confirmed via regex scan |
| `execution_state` uppercase comparison | YES | entity_cards.py:206 confirmed |
| `adoption_count` read-modify-write | YES | card_snapshot_service.py:1020 confirmed |
| `focus_card` missing from frontend renderer | YES | agent_message_renderer.dart has no case for it |
| Task type normalization mismatch | YES | Python review→TRAINING vs Flutter review→REFLECTION |
| 27 hardcoded Chinese strings in entity_cards.py | YES | Grep confirmed 27 occurrences |

---

## Recommended Fix Priority Order

### Phase 1: Data Integrity (P0, ~2-3 hours)
1. Fix `archived_at` column declaration on Card model
2. Fix `execution_state` case comparison (lowercase)
3. Fix soft-deleted edge resurrection (add filter)
4. Fix triple-quote DB defaults (ALTER TABLE for 14 columns)
5. Document/enforce enum constraints at DB level

### Phase 2: Broken Features (P1, ~1-2 days)
6. Add lifecycle validation state machine
7. Protect `lifecycle_status` in `update_card`
8. Add `focus_card` handler to frontend renderer
9. Add missing widget types to Go action feedback
10. Add transaction boundary to `import_snapshot`
11. Fix `adoption_count` race condition (atomic increment)
12. Unify `ShareService` definitions
13. Fix `widget_data` merge in Go gateway
14. Align task type normalization (Python ↔ Flutter)
15. Add group membership check for shares
16. Add expiration enforcement on adoption

### Phase 3: Quality & Performance (P2, ~2-3 days)
17. i18n all hardcoded Chinese strings in entity_cards.py (27 occurrences)
18. i18n TaskCardGenerator template keywords
19. Add DB indexes (updated_at, "shared with me", active edges)
20. Fix N+1 query in QueryAllTasksTool
21. Add GIN index on cards.metadata JSONB
22. Centralize widget_type registry across layers
23. Move event publishing to post-commit hooks

### Phase 4: Cleanup (P3, ~1 day)
24. Replace `datetime.utcnow()` with `datetime.now(UTC)`
25. Fix `nodeId` → `node_id` in Go gateway
26. Fix duplicate achievementtype enum value
27. Add proto documentation for reserved fields

---

## Files Requiring Changes (by priority)

| Priority | File | Changes Needed |
|----------|------|----------------|
| P0 | `backend/app/models/card_protocol.py` | Add `archived_at` column |
| P0 | `backend/app/tools/entity_cards.py:206` | Fix case comparison |
| P0 | `backend/app/services/card_edge_service.py:90-103` | Add `not_deleted_filter()` |
| P0 | DB migration (new) | Fix 14 triple-quote defaults |
| P1 | `backend/app/services/card_service.py` | Add state machine + protect lifecycle |
| P1 | `mobile/.../agent_message_renderer.dart` | Add focus_card + other missing types |
| P1 | `backend/.../chat_orchestrator_feedback.go` | Add missing widget type handlers |
| P1 | `backend/.../card_snapshot_service.py` | Add SAVEPOINT + fix race condition |
| P2 | `backend/app/tools/entity_cards.py` | i18n 27 Chinese strings |
| P2 | DB migration (new) | Add indexes |
| P2 | `backend/app/tools/task_query_tool.py` | Fix N+1 query |

---

## Detailed Reports

- **`01-frontend-uiux-audit.md`** — 58 Flutter UI/UX issues (1 P0, 4 P1, 29 P2, 24 P3)
- **`02-backend-ai-card-audit.md`** — 23 Python/AI backend issues (3 P0, 8 P1, 7 P2, 5 P3)
- **`03-gateway-proto-db-audit.md`** — 27 Gateway/Proto/DB issues (2 P0, 5 P1, 14 P2, 6 P3)

**Grand Total: 108 issues across the full card system stack.**
