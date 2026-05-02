# CXP-28 Report — Admin, QA, And Internal Control Surfaces

## Goal

Give reviewers and operators enough control to inspect and validate the system.
Internal surfaces should make Aurora flags, memory, traces, routing, moderation,
and user-impacting errors auditable from a unified point, not scattered across
14+ disjoint endpoint pairs.

## Work Completed

### 1. Unified Admin Dashboard (`backend/app/api/v1/admin_dashboard.py`, new)

Created a single `GET /admin/dashboard` endpoint that aggregates:

- System health (Redis + DB + uptime + environment)
- User counts (total / active / superusers)
- All Aurora kill switch modes in one view (13 stages, counts by live/shadow/off/unknown)
- Recent client telemetry errors (last 50 events, filtered for non-ok status)
- Queue health (graph_sync, summarization queue lengths)

All protected by `get_current_active_superuser`.

### 2. Kill Switch Audit Endpoint (`GET /admin/dashboard/kill-switches`)

Added a detailed kill switch audit that uses the expanded `KillSwitchReadinessService`
to show every Aurora stage's current mode, target mode, promotion readiness,
blocking reasons, promotion criteria, and evidence — in a single response.

### 3. Admin Aurora User Inspection (`GET /admin/dashboard/aurora/user/{user_id}`)

New endpoint for admins to inspect any user's Aurora cognitive state:
- Energy level, cooldown status, last L3 session
- Persisted cognitive snapshot availability
- Runtime state across all 3 surfaces (modeling, planning, checkpoint)
- Recent correction telemetry (last 10)

Enables QA to reproduce a user journey and verify Aurora state without
needing the user's credentials.

### 4. Admin Routing History Lookup (`GET /admin/dashboard/routing/user/{user_id}`)

New endpoint for admins to query any user's Spine routing decision history.
Shows causal traces with signal/policy summaries, directive IDs, and timestamps.
Critical for debugging "why did Aurora route this way for this user?"

### 5. Admin Community Moderation (`community.py`)

Added two admin endpoints to the community router:

- `GET /community/admin/reports` — list ALL pending reports across all groups
  (superuser only, no group membership check required)
- `PUT /community/admin/reports/{report_id}/resolve` — admin resolve of any report
  (superuser can act on reports in any group)

Previously, the existing `/reports/{report_id}` endpoint required group owner/admin
membership — superusers had no override path.

### 6. Expanded Kill Switch Readiness Service

`KillSwitchReadinessService` now covers all 14 active Aurora features instead of
only 2 (memory_inferred_write + bayesian_learning):

- stage18_aggregator, stage19_working_memory, stage21_skill_system
- stage23_bayesian, stage24_policy, stage25_reflection, stage26_scene
- stage27_foresight, stage28_traits, stage29_srl, stage30_metacognition
- stage31_idiographic, stage33_journey
- memory_inferred_write

Each with promotion criteria, known blockers, and supporting evidence.

## User Experience Before / After

**Before**: An operator troubleshooting "is Aurora working for user X?" had to:
1. Check 14 separate GET endpoints for kill switch states
2. Guess Aurora state from telemetry summaries (no per-user inspection)
3. Have no way to inspect routing decisions for a specific user
4. Use group-owner credentials to moderate community reports
5. Manually correlate client telemetry errors with system health

**After**: The operator can:
1. Hit `/admin/dashboard` for a complete system overview in one request
2. Hit `/admin/dashboard/aurora/user/{id}` to see exact Aurora state for any user
3. Hit `/admin/dashboard/routing/user/{id}` to see full routing decision history
4. Hit `/community/admin/reports` to see and resolve all pending moderation items
5. Hit `/admin/dashboard/kill-switches` to audit all 14 kill switch states with
   promotion readiness

## Cross-System Links

| Layer | Files Changed |
|-------|--------------|
| **Backend API** | `admin_dashboard.py` (new), `community.py` (+admin endpoints), `router.py` (+registration) |
| **Backend Service** | `kill_switch_readiness_service.py` (expanded 2→14 features) |
| **Auth** | All new endpoints use `get_current_active_superuser` dependency |
| **Data Sources** | Aurora energy store, persistence store, runtime store, causal trace store, Redis telemetry, community report models |

## Verification

- Ruff lint: all 4 files pass with 0 errors
- Import test: `from app.api.v1 import admin_dashboard` succeeds
- Router integrity: 811 routes registered (no regressions)
- Method signature verification:
  - `AuroraEnergyStore.load_energy()` — confirmed correct
  - `CausalTraceStore.get_user_traces()` — confirmed correct (returns `list[CausalTrace]`)
  - `CausalTrace` fields — verified: `trace_id`, `signal_ids`, `policy_decision_id`, `directive_ids`, `receipt_ids`, `created_at`
  - `AuroraRuntimeStore.load_latest_surface_state()` — confirmed correct
  - `AuroraPersistenceStore.load_cognitive_snapshot()` — confirmed correct
  - `KillSwitchReadinessService.get_readiness_report(settings)` — confirmed correct
  - `ReportService.review_report()` — confirmed correct (existing community service)

## Remaining Risks

1. **No admin log inspection API**: Admins still can't query recent system logs
   through the API. This requires a log aggregation endpoint (Loki or file-based).
   **Owner**: Infra/DevOps team.

2. **Admin actions not yet persisted to audit log table**: While admin actions are
   authorized via `get_current_active_superuser`, there's no persistent audit trail
   in the database for admin dashboard queries. The DLQ replay already has audit
   headers — the same pattern should be extended to Aurora inspection and report
   resolution.
   **Owner**: CXP-28 follow-up or CXP-25 (Backend Contract).

3. **Community admin endpoints are in the same router as user endpoints**: The
   admin report endpoints use the same `APIRouter` as user-facing community
   endpoints. While the `get_current_active_superuser` dep provides proper
   authorization, a separate admin router would be cleaner for long-term
   maintenance.
   **Owner**: Future refactor.

4. **Kill switch readiness evaluation is static**: The `KillSwitchReadinessService`
   reads from settings and static catalog data. It doesn't yet check runtime
   metrics (e.g., actual outcome counts for Bayesian shadow mode). This should
   be enhanced when Prometheus metrics are queryable from the API.
   **Owner**: CXP-26 (Observability).

## Commit

Branch: `codex/CXP-28-admin-qa-controls`
Files:
- `backend/app/api/v1/admin_dashboard.py` (new)
- `backend/app/api/v1/community.py` (modified)
- `backend/app/api/v1/router.py` (modified)
- `backend/app/services/kill_switch_readiness_service.py` (modified)
