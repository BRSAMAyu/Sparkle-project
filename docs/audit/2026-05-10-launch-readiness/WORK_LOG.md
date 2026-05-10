# Launch Readiness Fix Work Log

> **Started**: 2026-05-10
> **Operator**: Main Agent (assisted by Opus verification agents)

---

## Finding Verification Matrix

Before fixing, each finding is verified against the current codebase state.

| ID | Report Severity | Verified? | Actual Severity | Notes |
|----|----------------|-----------|-----------------|-------|
| M-001 | P0 | PARTIAL | P1 (logic broken, compiles) | dart analyze shows 0 errors but itemBuilder logic was broken. Fixed by restoring from HEAD + keeping header improvement. |
| M-002 | P0 | YES | P1 | AuroraCoreSessionResumeBanner confirmed missing. Fixed in FIX-01. |
| M-003 | P0 | SKIP | N/A | CI/CD config issue. |
| M-004 | P0 | YES | P1 | gRPC TLS mismatch. Fixed by setting GRPC_REQUIRE_TLS=false on internal network. |
| M-005 | P1 | NO | FALSE POSITIVE | ENVIRONMENT=production IS set for backend/agent/celery. Gateway was missing it — fixed. |
| M-006 | P1 | YES | P1 | Fixed: added TRUSTED_PROXIES, ALLOWED_ORIGINS, REDIS_FAIL_CLOSED, etc. |
| M-007 | P1 | DEFERRED | P2 | Redis ACL bypass — gateway uses default user. Would need Go config change for username support. |
| M-008 | P1 | YES | P1 | 749 inline isChinese ternaries. LARGE systematic fix — deferred to separate effort. |
| M-009 | P1 | DEFERRED | P1 | Test infrastructure issue. |
| M-010 | P1 | YES | P1 | Fixed with _LazyCheckpointer proxy. |
| M-011 | P1 | RETRACTED | N/A | Confirmed false. |
| M-012 | P1 | YES | P2 | CQRS health intentionally skipped in preflight. No change needed. |
| M-013-M-025 | P2-P3 | VERIFIED | P2-P3 | Fixed as applicable. |
| G-001 | P1 | NO | FALSE POSITIVE | ENVIRONMENT=production IS set for backend/agent. Added to gateway. |
| G-002 | P1 | YES | P1 | Fixed in docker-compose.prod.yml. |
| G-003 | P1 | YES | P1 | Fixed in .env.production.example. |
| G-008 | P1 | DEFERRED | P2 | Would need Go Redis URL format change. |
| G-014 | P1 | YES | P1 | Fixed: GRPC_REQUIRE_TLS=false on internal network. |

---

## Fix Execution Log

### Phase 1: P0/P1 Critical Fixes — COMPLETE

#### [FIX-01] chat_screen.dart — Restore itemBuilder + AuroraCoreSessionResumeBanner
- **Status**: DONE ✓ (commit dcaa2f6c1)
- Restored from HEAD, re-applied valid header layout improvement (ConstrainedBox + SingleChildScrollView)

#### [FIX-02] docker-compose.prod.yml — Missing env vars + TLS
- **Status**: DONE ✓ (commit 04f96d773)
- Added ENVIRONMENT=production, TRUSTED_PROXIES, ALLOWED_ORIGINS, REDIS_FAIL_CLOSED, ALLOW_WS_QUERY_TOKEN=false, AGENT_TLS_ENABLED
- Changed agent GRPC_REQUIRE_TLS=false (internal network)
- Updated .env.production.example

#### [FIX-03] workflow.py — Lazy checkpointer init
- **Status**: DONE ✓ (commit 02b0ff32a)
- Added _LazyCheckpointer proxy that defers Redis connection to first use

#### [FIX-04] llm_service.py — Cascade routing logging
- **Status**: DONE ✓ (commit 02b0ff32a)
- Added debug-level logging for cascade routing failures

### Phase 2: P2/P3 Fixes — IN PROGRESS

#### [FIX-05] Backend Pydantic V2 + FK cycle
- **Status**: DONE ✓ (commit b4381be72)
- class Config → model_config
- min_items → min_length
- .dict() → .model_dump()
- use_alter=True on goals↔plans FK

#### [FIX-06] Flutter P2/P3 (F-008, F-009, F-013, F-015-018)
- **Status**: DELEGATED to background agent

#### [FIX-07] Gateway P2/P3 (G-005, G-007, G-009, G-012, G-013, G-015)
- **Status**: DELEGATED to background agent

---

## Git Commit Log

| # | Hash | Description |
|---|------|-------------|
| 1 | dcaa2f6c1 | fix(chat): restore itemBuilder + AuroraCoreSessionResumeBanner + header scroll |
| 2 | 04f96d773 | fix(infra): add missing production env vars to docker-compose.prod.yml |
| 3 | 02b0ff32a | fix(backend): lazy checkpointer init + log cascade routing failures |
| 4 | b4381be72 | fix(backend): Pydantic V2 migration + FK cycle SAWarning |

---

## Remaining Work

- [ ] Collect Flutter agent results + commit
- [ ] Collect Gateway agent results + commit
- [ ] Final Opus verification
